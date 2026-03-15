from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from pymilvus import Collection, connections, utility
except Exception:  # pragma: no cover
    Collection = None
    connections = None
    utility = None


@dataclass
class MilvusSearchHit:
    id: str
    score: float
    esco_id: str
    preferred_label: str
    payload_text: str | None = None


class MilvusSearchClient:
    def __init__(
        self,
        uri: str,
        token: str,
        db_name: str,
        occupation_collection: str,
        skill_collection: str,
        metric_type: str = "COSINE",
        ef: int = 64,
    ) -> None:
        if Collection is None or connections is None or utility is None:
            raise RuntimeError("pymilvus is not installed")

        self.metric_type = metric_type
        self.search_params = {"metric_type": metric_type, "params": {"ef": ef}}
        self._collections: dict[str, Collection] = {}

        connect_kwargs: dict[str, Any] = {"alias": "default", "uri": uri}
        if token:
            connect_kwargs["token"] = token
        if db_name:
            connect_kwargs["db_name"] = db_name

        connections.connect(**connect_kwargs)

        self.occupation_collection = occupation_collection
        self.skill_collection = skill_collection

        self._collections["occupation"] = self._load_collection(occupation_collection)
        self._collections["skill"] = self._load_collection(skill_collection)

    def _load_collection(self, name: str) -> Collection:
        if not utility.has_collection(name):
            raise RuntimeError(f"Milvus collection not found: {name}")
        coll = Collection(name)
        coll.load()
        return coll

    def search_occupation(self, vector: list[float], top_k: int) -> list[MilvusSearchHit]:
        return self._search(self._collections["occupation"], vector, top_k)

    def search_skill(self, vector: list[float], top_k: int) -> list[MilvusSearchHit]:
        return self._search(self._collections["skill"], vector, top_k)

    def _search(self, coll: Collection, vector: list[float], top_k: int) -> list[MilvusSearchHit]:
        result = coll.search(
            data=[vector],
            anns_field="vector",
            param=self.search_params,
            limit=top_k,
            output_fields=["esco_id", "preferred_label", "payload_text"],
        )

        hits = result[0] if result else []
        out: list[MilvusSearchHit] = []
        for hit in hits:
            score = float(getattr(hit, "score", getattr(hit, "distance", 0.0)))
            hit_id = str(getattr(hit, "id", ""))

            esco_id = ""
            preferred_label = ""
            payload_text: str | None = None

            entity = getattr(hit, "entity", None)
            if entity is not None:
                try:
                    esco_id = str(entity.get("esco_id") or "")
                    preferred_label = str(entity.get("preferred_label") or "")
                    payload_text = entity.get("payload_text")
                except Exception:
                    pass

            if not esco_id:
                esco_id = str(getattr(hit, "esco_id", "")) or hit_id
            if not preferred_label:
                preferred_label = str(getattr(hit, "preferred_label", ""))

            out.append(
                MilvusSearchHit(
                    id=hit_id or esco_id,
                    score=score,
                    esco_id=esco_id,
                    preferred_label=preferred_label,
                    payload_text=payload_text,
                )
            )
        return out

    @staticmethod
    def score_to_confidence(score: float) -> float:
        # For cosine-like scores this keeps value in [0, 1].
        if score < 0:
            return max(0.0, min(1.0, (score + 1.0) / 2.0))
        return max(0.0, min(1.0, score))
