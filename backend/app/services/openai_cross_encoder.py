from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Sequence

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


_SYSTEM_PROMPT = """\
You score how well each candidate matches a hiring query.
Return strict JSON only in this shape:
{"scores":[{"i":0,"score":0.0}]}

Rules:
- score range is 0.0 to 1.0
- higher means stronger overall fit for role, skills, and seniority
- include every input index exactly once
- no extra keys
"""


@dataclass(slots=True)
class OpenAICrossEncoderModel:
    api_key: str
    model: str = "gpt-4.1-mini"
    temperature: float = 0.0
    max_text_chars: int = 800
    _client: Any | None = field(default=None, init=False, repr=False)

    @staticmethod
    def is_available() -> bool:
        return OpenAI is not None

    def score(self, query_text: str, candidate_texts: Sequence[str]) -> Sequence[float]:
        if not candidate_texts:
            return []

        client = self._ensure_client()
        payload = {
            "query": _normalize_text(query_text, max_chars=600),
            "candidates": [
                {"i": index, "text": _normalize_text(text, max_chars=self.max_text_chars)}
                for index, text in enumerate(candidate_texts)
            ],
        }

        content = self._request_json(client=client, payload=payload)
        return _parse_scores(content=content, expected_size=len(candidate_texts))

    def _request_json(self, *, client: Any, payload: dict[str, Any]) -> str:
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        try:
            response = client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                response_format={"type": "json_object"},
                messages=messages,
            )
        except Exception:
            response = client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=messages,
            )
        message = response.choices[0].message if response.choices else None
        content = getattr(message, "content", "") if message is not None else ""
        return str(content or "{}")

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        if OpenAI is None:
            raise RuntimeError("openai package is not installed.")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        self._client = OpenAI(api_key=self.api_key)
        return self._client


def _normalize_text(value: str | None, *, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _parse_scores(*, content: str, expected_size: int) -> list[float]:
    parsed = _try_parse_json_object(content)
    result = [0.0 for _ in range(expected_size)]
    if not parsed:
        return result

    raw_scores = parsed.get("scores")
    if not isinstance(raw_scores, list):
        return result

    if raw_scores and all(not isinstance(item, dict) for item in raw_scores):
        for index in range(min(expected_size, len(raw_scores))):
            result[index] = _clamp01(_to_float(raw_scores[index]))
        return result

    for item in raw_scores:
        if not isinstance(item, dict):
            continue
        index = _to_int(item.get("i"))
        if index is None or index < 0 or index >= expected_size:
            continue
        result[index] = _clamp01(_to_float(item.get("score")))
    return result


def _try_parse_json_object(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {}


def _to_float(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except Exception:
            return 0.0
    return 0.0


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except Exception:
            return None
    return None


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value
