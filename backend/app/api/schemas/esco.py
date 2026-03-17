from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EscoDomainParam = Literal["skill", "occupation", "industry"]


class EscoSuggestItem(BaseModel):
    esco_id: str
    label: str


class EscoSuggestResponse(BaseModel):
    domain: EscoDomainParam
    query: str
    results: list[EscoSuggestItem] = Field(default_factory=list)
