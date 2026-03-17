from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ..domain import GuardrailWarning, InputGuardrailResult, QueryUnderstandingOutput, SearchQueryInput


_SYMBOL_ONLY_RE = re.compile(r"^[\s\W_]+$", re.UNICODE)
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_LETTER_OR_CJK_RE = re.compile(r"[A-Za-z\u3040-\u30ff\u3400-\u9fff]")
_TOKEN_RE = re.compile(r"[A-Za-z0-9\u3040-\u30ff\u3400-\u9fff]{2,}")

_ROLE_HINT_WORDS = {
    "engineer",
    "developer",
    "manager",
    "analyst",
    "architect",
    "scientist",
    "designer",
    "consultant",
    "specialist",
    "administrator",
    "technician",
    "accountant",
    "recruiter",
    "marketer",
    "エンジニア",
    "開発",
    "マネージャ",
    "分析",
    "アナリスト",
    "設計",
}


@dataclass(slots=True)
class InputGuardrailService:
    """
    FR-07-01 input guardrail service contract.
    Step 1 defines the interface and settings-backed shape; rule logic is added in Step 2.
    """

    enabled: bool = True
    min_query_length: int = 20
    max_query_length: int = 2000
    require_skill_or_occupation: bool = False
    prohibited_terms_csv: str = ""

    def evaluate(
        self,
        search_input: SearchQueryInput,
        understood: QueryUnderstandingOutput | None = None,
    ) -> InputGuardrailResult:
        if not self.enabled:
            return InputGuardrailResult(retry_required=False)

        text = search_input.query_text.strip()
        conflict_fields: list[str] = []
        reasons: list[str] = []
        warnings: list[GuardrailWarning] = []

        if not text:
            conflict_fields.append("query_text")
            reasons.append("query_text is empty")
            return InputGuardrailResult(
                retry_required=True,
                conflict_fields=_dedupe_preserve_order(conflict_fields),
                conflict_reason="; ".join(reasons),
                warnings=warnings,
            )

        if len(text) < self.min_query_length:
            conflict_fields.append("query_text")
            reasons.append(f"query_text is too short (< {self.min_query_length} characters)")
        if len(text) > self.max_query_length:
            conflict_fields.append("query_text")
            reasons.append(f"query_text is too long (> {self.max_query_length} characters)")

        if _looks_like_non_natural_language(text):
            conflict_fields.append("query_text")
            reasons.append("query_text must be natural-language job requirement text")

        prohibited_hit = _find_prohibited_term(text, self.prohibited_terms_csv)
        if prohibited_hit is not None:
            conflict_fields.append("query_text")
            reasons.append(f"query_text contains prohibited term: {prohibited_hit}")
        if _EMAIL_RE.search(text):
            conflict_fields.append("query_text")
            reasons.append("query_text appears to include personal contact information")

        if self.require_skill_or_occupation and not _has_required_role_or_skill_info(
            search_input=search_input,
            understood=understood,
        ):
            conflict_fields.extend(["skill_terms", "occupation_terms"])
            reasons.append("at least one skill or occupation requirement is required")

        # Guidance-only warnings (non-blocking)
        if understood is not None:
            if not _has_experience_info(search_input, understood):
                warnings.append(
                    GuardrailWarning(
                        code="missing_experience_hint",
                        message="Experience requirement is not explicit; result quality may vary.",
                        field="experience",
                    )
                )
            if not _has_education_info(search_input, understood):
                warnings.append(
                    GuardrailWarning(
                        code="missing_education_hint",
                        message="Education requirement is not explicit; result quality may vary.",
                        field="education",
                    )
                )
            if not _has_industry_info(search_input, understood):
                warnings.append(
                    GuardrailWarning(
                        code="missing_industry_hint",
                        message="Industry requirement is not explicit; result quality may vary.",
                        field="industry_terms",
                    )
                )

        return InputGuardrailResult(
            retry_required=bool(conflict_fields),
            conflict_fields=_dedupe_preserve_order(conflict_fields),
            conflict_reason="; ".join(reasons) if reasons else "no guardrail violation",
            warnings=warnings,
        )


def _looks_like_non_natural_language(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if _SYMBOL_ONLY_RE.fullmatch(stripped):
        return True
    if _looks_like_json_payload(stripped):
        return True
    if not _LETTER_OR_CJK_RE.search(stripped):
        return True
    token_count = len(_TOKEN_RE.findall(stripped))
    if token_count == 0:
        return True
    return False


def _looks_like_json_payload(text: str) -> bool:
    if not text:
        return False
    if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
        try:
            parsed = json.loads(text)
        except Exception:
            return False
        return isinstance(parsed, (dict, list))
    return False


def _find_prohibited_term(text: str, prohibited_terms_csv: str) -> str | None:
    lowered = text.lower()
    for raw in prohibited_terms_csv.split(","):
        term = raw.strip().lower()
        if not term:
            continue
        if term in lowered:
            return raw.strip()
    return None


def _has_required_role_or_skill_info(
    *,
    search_input: SearchQueryInput,
    understood: QueryUnderstandingOutput | None,
) -> bool:
    if any(value.strip() for value in search_input.requested_skill_terms):
        return True
    if any(value.strip() for value in search_input.requested_occupation_terms):
        return True

    if understood is not None:
        # Post-understanding phase: require explicit or extracted signals only.
        return any(value.strip() for value in understood.skill_terms) or any(
            value.strip() for value in understood.occupation_terms
        )

    # Pre-understanding phase: fallback to weak role hints to avoid premature rejection.
    lowered = search_input.query_text.lower()
    return any(hint in lowered for hint in _ROLE_HINT_WORDS)


def _has_experience_info(search_input: SearchQueryInput, understood: QueryUnderstandingOutput) -> bool:
    req = search_input.requested_experience
    ext = understood.experience
    return any(
        value is not None
        for value in (req.min_months, req.max_months, ext.min_months, ext.max_months)
    )


def _has_education_info(search_input: SearchQueryInput, understood: QueryUnderstandingOutput) -> bool:
    req = search_input.requested_education
    ext = understood.education
    return any(
        value is not None
        for value in (req.min_rank, req.max_rank, ext.min_rank, ext.max_rank)
    )


def _has_industry_info(search_input: SearchQueryInput, understood: QueryUnderstandingOutput) -> bool:
    if any(value.strip() for value in search_input.requested_industry_terms):
        return True
    if any(value.strip() for value in understood.industry_terms):
        return True
    return False


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out
