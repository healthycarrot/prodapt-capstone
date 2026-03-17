from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..domain import EscoCandidate, NormalizedEscoOutput, QueryBuilderOutput, QueryUnderstandingOutput, SearchQueryInput


class QueryRephraser(Protocol):
    """Optional rephraser adapter (LLM or rule-based)."""

    def rephrase(self, *, prompt: str) -> str:
        ...


@dataclass(slots=True)
class QueryBuilderService:
    rephraser: QueryRephraser | None = None
    max_terms_per_domain: int = 8

    def build(
        self,
        search_input: SearchQueryInput,
        understanding: QueryUnderstandingOutput,
        normalized: NormalizedEscoOutput,
    ) -> QueryBuilderOutput:
        skill_terms = _dedupe(
            understanding.skill_terms + _labels(normalized.skill_candidates, self.max_terms_per_domain)
        )
        occupation_terms = _dedupe(
            understanding.occupation_terms + _labels(normalized.occupation_candidates, self.max_terms_per_domain)
        )
        industry_terms = _dedupe(
            understanding.industry_terms + _labels(normalized.industry_candidates, self.max_terms_per_domain)
        )

        skill_prompt = (
            f"Original query: {search_input.query_text}\n"
            f"Skills: {', '.join(skill_terms)}\n"
            f"Occupations: {', '.join(occupation_terms)}\n"
            "Write a concise vector retrieval query focused on required skills."
        )
        occupation_prompt = (
            f"Original query: {search_input.query_text}\n"
            f"Occupations: {', '.join(occupation_terms)}\n"
            f"Industries: {', '.join(industry_terms)}\n"
            "Write a concise vector retrieval query focused on occupation fit."
        )

        skill_vector_query = self._rephrase_or_fallback(
            prompt=skill_prompt,
            fallback=_fallback_query(search_input.query_text, skill_terms, occupation_terms, "skills"),
        )
        occupation_vector_query = self._rephrase_or_fallback(
            prompt=occupation_prompt,
            fallback=_fallback_query(search_input.query_text, occupation_terms, industry_terms, "occupations"),
        )
        keyword_query = _fallback_query(
            search_input.query_text,
            _dedupe(skill_terms + occupation_terms + industry_terms),
            [],
            "keyword",
        )

        return QueryBuilderOutput(
            skill_vector_query=skill_vector_query,
            occupation_vector_query=occupation_vector_query,
            keyword_query=keyword_query,
        )

    def _rephrase_or_fallback(self, *, prompt: str, fallback: str) -> str:
        if self.rephraser is None:
            return fallback
        try:
            rewritten = self.rephraser.rephrase(prompt=prompt).strip()
            return rewritten if rewritten else fallback
        except Exception:
            return fallback


def _labels(candidates: list[EscoCandidate], limit: int) -> list[str]:
    ordered = sorted(candidates, key=lambda item: (-item.confidence, item.label.lower()))
    return [item.label for item in ordered[:limit] if item.label]


def _fallback_query(base: str, primary_terms: list[str], secondary_terms: list[str], mode: str) -> str:
    chunks = [base.strip()]
    if primary_terms:
        chunks.append(f"{mode} terms: {', '.join(primary_terms)}")
    if secondary_terms:
        chunks.append(f"context: {', '.join(secondary_terms)}")
    return " | ".join(chunk for chunk in chunks if chunk)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value.strip())
    return result
