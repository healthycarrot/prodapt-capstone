from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from ..core.config import Settings, get_settings
from ..services.vector_search import CandidateVectorRepo, VectorRepoHit

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
class MilvusCandidateRepository(CandidateVectorRepo):
    settings: Settings = field(default_factory=get_settings)
    embedding_model: str = "text-embedding-3-small"
    metric_type: str = "COSINE"
    search_ef: int = 128
    _openai_client: Any | None = field(default=None, init=False, repr=False)
    _collection: Any | None = field(default=None, init=False, repr=False)
    _embedding_cache: dict[str, list[float]] = field(default_factory=dict, init=False, repr=False)

    def search_skill(self, query: str, *, top_k: int, filter_expr: str) -> Sequence[VectorRepoHit]:
        return self._search(query=query, anns_field="skill_vector", top_k=top_k, filter_expr=filter_expr)

    def search_occupation(self, query: str, *, top_k: int, filter_expr: str) -> Sequence[VectorRepoHit]:
        return self._search(query=query, anns_field="occupation_vector", top_k=top_k, filter_expr=filter_expr)

    def _search(self, *, query: str, anns_field: str, top_k: int, filter_expr: str) -> Sequence[VectorRepoHit]:
        if not query.strip():
            return []
        vector = self._embed_query(query)
        if not vector:
            return []

        collection = self._ensure_collection()
        search_params = {
            "metric_type": self.metric_type,
            "params": {"ef": self.search_ef},
        }
        raw = collection.search(
            data=[vector],
            anns_field=anns_field,
            param=search_params,
            limit=top_k,
            expr=filter_expr or None,
            output_fields=["candidate_id"],
        )
        hits = raw[0] if raw else []
        out: list[VectorRepoHit] = []
        for hit in hits:
            candidate_id = ""
            entity = getattr(hit, "entity", None)
            if entity is not None:
                try:
                    candidate_id = str(entity.get("candidate_id") or "")
                except Exception:
                    candidate_id = ""
            if not candidate_id:
                candidate_id = str(getattr(hit, "id", ""))
            if not candidate_id:
                continue
            score = _to_float(getattr(hit, "score", getattr(hit, "distance", 0.0)))
            out.append(VectorRepoHit(candidate_id=candidate_id, score=score))
        return out

    def _embed_query(self, query: str) -> list[float] | None:
        key = query.strip()
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

    def _ensure_collection(self) -> Any:
        if self._collection is not None:
            return self._collection
        if Collection is None or connections is None or utility is None:
            raise RuntimeError("pymilvus is not installed.")
        connect_kwargs: dict[str, Any] = {"alias": "default", "uri": self.settings.milvus_uri}
        if self.settings.milvus_token:
            connect_kwargs["token"] = self.settings.milvus_token
        if self.settings.milvus_db_name:
            connect_kwargs["db_name"] = self.settings.milvus_db_name
        connections.connect(**connect_kwargs)

        name = self.settings.milvus_candidate_collection
        if not utility.has_collection(name):
            raise RuntimeError(f"Milvus candidate collection not found: {name}")
        self._collection = Collection(name=name)
        self._collection.load()
        return self._collection


def _to_float(value: Any) -> float:
    try:
        score = float(value)
    except Exception:
        return 0.0
    return score
