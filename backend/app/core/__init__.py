from .config import Settings, get_settings


def get_mongo_repository():
    from .dependencies import get_mongo_repository as _fn

    return _fn()


def get_milvus_candidate_repository():
    from .dependencies import get_milvus_candidate_repository as _fn

    return _fn()


def get_esco_lexical_repository():
    from .dependencies import get_esco_lexical_repository as _fn

    return _fn()


def get_esco_embedding_repository():
    from .dependencies import get_esco_embedding_repository as _fn

    return _fn()


def get_retrieval_pipeline_service():
    from .dependencies import get_retrieval_pipeline_service as _fn

    return _fn()


def get_search_orchestration_service():
    from .dependencies import get_search_orchestration_service as _fn

    return _fn()

__all__ = [
    "Settings",
    "get_settings",
    "get_mongo_repository",
    "get_milvus_candidate_repository",
    "get_esco_lexical_repository",
    "get_esco_embedding_repository",
    "get_retrieval_pipeline_service",
    "get_search_orchestration_service",
]
