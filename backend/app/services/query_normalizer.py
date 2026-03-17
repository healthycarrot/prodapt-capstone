from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence

from ..domain import EscoCandidate, EscoDomain, EscoMatchMethod, NormalizedEscoOutput, QueryUnderstandingOutput

_METHOD_PRIORITY = {"exact": 0, "alt": 1, "fuzzy": 2, "embedding": 3}


@dataclass(slots=True)
class NormalizerThresholds:
    """Central confidence thresholds."""

    high: float = 0.85
    medium: float = 0.60


@dataclass(slots=True)
class RepoMatch:
    esco_id: str
    label: str
    score: float


class EscoLexicalRepo(Protocol):
    def find_exact(self, domain: EscoDomain, term: str, limit: int = 5) -> Sequence[RepoMatch]:
        ...

    def find_alt(self, domain: EscoDomain, term: str, limit: int = 5) -> Sequence[RepoMatch]:
        ...

    def find_fuzzy(self, domain: EscoDomain, term: str, limit: int = 5) -> Sequence[RepoMatch]:
        ...


class EscoEmbeddingRepo(Protocol):
    def search(self, domain: EscoDomain, text: str, limit: int = 5) -> Sequence[RepoMatch]:
        ...


@dataclass(slots=True)
class QueryNormalizerService:
    lexical_repo: EscoLexicalRepo
    embedding_repo: EscoEmbeddingRepo | None = None
    thresholds: NormalizerThresholds = field(default_factory=NormalizerThresholds)
    per_term_limit: int = 5
    per_domain_limit: int = 30

    def normalize(self, understanding: QueryUnderstandingOutput) -> NormalizedEscoOutput:
        return NormalizedEscoOutput(
            skill_candidates=self._normalize_domain("skill", understanding.skill_terms),
            occupation_candidates=self._normalize_domain("occupation", understanding.occupation_terms),
            industry_candidates=self._normalize_domain("industry", understanding.industry_terms),
        )

    def _normalize_domain(self, domain: EscoDomain, terms: list[str]) -> list[EscoCandidate]:
        merged: dict[str, EscoCandidate] = {}
        for term in terms:
            for candidate in self._normalize_term(domain, term):
                current = merged.get(candidate.esco_id)
                if current is None or _is_better(candidate, current):
                    merged[candidate.esco_id] = candidate
        ordered = sorted(
            merged.values(),
            key=lambda item: (-item.confidence, _METHOD_PRIORITY[item.method], item.label.lower()),
        )
        return ordered[: self.per_domain_limit]

    def _normalize_term(self, domain: EscoDomain, term: str) -> list[EscoCandidate]:
        candidates: list[EscoCandidate] = []

        for match in self.lexical_repo.find_exact(domain, term, self.per_term_limit):
            candidates.append(self._to_candidate(domain, match, "exact"))
        for match in self.lexical_repo.find_alt(domain, term, self.per_term_limit):
            candidates.append(self._to_candidate(domain, match, "alt"))
        for match in self.lexical_repo.find_fuzzy(domain, term, self.per_term_limit):
            candidates.append(self._to_candidate(domain, match, "fuzzy"))
        if self.embedding_repo is not None:
            try:
                for match in self.embedding_repo.search(domain, term, self.per_term_limit):
                    candidates.append(self._to_candidate(domain, match, "embedding"))
            except Exception:
                # Keep lexical path active when embedding backend is temporarily unavailable.
                pass

        # Keep best per ESCO id for this single term first, then caller merges across terms.
        by_id: dict[str, EscoCandidate] = {}
        for candidate in candidates:
            current = by_id.get(candidate.esco_id)
            if current is None or _is_better(candidate, current):
                by_id[candidate.esco_id] = candidate
        return list(by_id.values())

    def _to_candidate(self, domain: EscoDomain, match: RepoMatch, method: EscoMatchMethod) -> EscoCandidate:
        confidence = _clamp01(match.score)
        if method == "exact":
            confidence = max(confidence, 0.95)
        elif method == "alt":
            confidence = max(confidence, 0.85)

        return EscoCandidate(
            domain=domain,
            esco_id=match.esco_id,
            label=match.label,
            confidence=confidence,
            band=_to_band(confidence, self.thresholds),
            method=method,
        )


def _to_band(confidence: float, thresholds: NormalizerThresholds) -> str:
    if confidence >= thresholds.high:
        return "high"
    if confidence >= thresholds.medium:
        return "medium"
    return "low"


def _clamp01(score: float) -> float:
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def _is_better(candidate: EscoCandidate, current: EscoCandidate) -> bool:
    if candidate.confidence != current.confidence:
        return candidate.confidence > current.confidence
    return _METHOD_PRIORITY[candidate.method] < _METHOD_PRIORITY[current.method]
