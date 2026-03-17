from fastapi import APIRouter

from .candidates import router as candidates_router
from .retrieve import router as retrieve_router
from .search import router as search_router

api_router = APIRouter()
api_router.include_router(candidates_router)
api_router.include_router(retrieve_router)
api_router.include_router(search_router)

__all__ = ["api_router", "candidates_router", "retrieve_router", "search_router"]
