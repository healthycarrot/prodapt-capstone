from __future__ import annotations

from fastapi import FastAPI

from .api import search_router

app = FastAPI(
    title="Prodapt Capstone Search API",
    version="0.1.0",
)

app.include_router(search_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
