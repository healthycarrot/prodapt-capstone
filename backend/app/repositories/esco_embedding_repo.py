from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from ..core.config import Settings, get_settings
from ..domain import EscoDomain
from ..services.query_normalizer import EscoEmbeddingRepo, RepoMatch

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

try:
    from pymilvus import Collection, connections, utility
except Exception:  # pragma: no cover
    Collection = None
    connections = None
    utility = None


@dataclass(slots=True)
class EscoEmbeddingMilvusRepository(EscoEmbeddingRepo):
    settings: Settings = field(default_factory=get_settings)
    embedding_model: str = "text-embedding-3-small"
    metric_type: str = "COSINE"
    search_ef: int = 128
    _openai_client: Any | None = field(default=None, init=False, repr=False)
    _collections: dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _embedding_cache: dict[str, list[float]] = field(default_factory=dict, init=False, repr=False)

    def search(self, domain: EscoDomain, text: str, limit: int = 5) -> Sequence[RepoMatch]:
        if domain == "industry":
            # No dedicated ISCO-group embedding collection in current design.
            return []
        if not text.strip():
            return []
        vector = self._embed(text)
        if not vector:
            return []

        collection_name = self.settings.milvus_skill_collection if domain == "skill" else self.settings.milvus_occ_collection
        collection = self._ensure_collection(collection_name)
        result = collection.search(
            data=[vector],
            anns_field="vector",
            param={"metric_type": self.metric_type, "params": {"ef": self.search_ef}},
            limit=limit,
            output_fields=["esco_id", "preferred_label"],
        )
        hits = result[0] if result else []
        out: list[RepoMatch] = []
        for hit in hits:
            entity = getattr(hit, "entity", None)
            esco_id = ""
            label = ""
            if entity is not None:
                try:
                    esco_id = str(entity.get("esco_id") or "")
                    label = str(entity.get("preferred_label") or "")
                except Exception:
                    esco_id = ""
                    label = ""
            if not esco_id:
                esco_id = str(getattr(hit, "id", ""))
            if not esco_id:
                continue
            score = _score_to_confidence(_to_float(getattr(hit, "score", getattr(hit, "distance", 0.0))))
            out.append(RepoMatch(esco_id=esco_id, label=label or esco_id, score=score))
        return out

    def _embed(self, text: str) -> list[float] | None:
        key = text.strip()
        if not key:
            return None
        cached = self._embedding_cache.get(key)
        if cached is not None:
            return cached
        client = self._ensure_openai_client()
        response = client.embeddings.create(model=self.embedding_model, input=key)
        vector = list(response.data[0].embedding)
        self._embedding_cache[key] = vector
        return vector

    def _ensure_openai_client(self) -> Any:
        if self._openai_client is not None:
            return self._openai_client
        if OpenAI is None:
            raise RuntimeError("openai package is not installed.")
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        self._openai_client = OpenAI(api_key=self.settings.openai_api_key)
        return self._openai_client

    def _ensure_collection(self, name: str) -> Any:
        collection = self._collections.get(name)
        if collection is not None:
            return collection
        if Collection is None or connections is None or utility is None:
            raise RuntimeError("pymilvus is not installed.")

        connect_kwargs: dict[str, Any] = {"alias": "default", "uri": self.settings.milvus_uri}
        if self.settings.milvus_token:
            connect_kwargs["token"] = self.settings.milvus_token
        if self.settings.milvus_db_name:
            connect_kwargs["db_name"] = self.settings.milvus_db_name
        connections.connect(**connect_kwargs)

        if not utility.has_collection(name):
            raise RuntimeError(f"Milvus ESCO collection not found: {name}")
        collection = Collection(name=name)
        collection.load()
        self._collections[name] = collection
        return collection


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _score_to_confidence(score: float) -> float:
    if score < 0:
        return max(0.0, min(1.0, (score + 1.0) / 2.0))
    return max(0.0, min(1.0, score))
