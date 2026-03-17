from __future__ import annotations

from functools import lru_cache

from ..domain import StageCaps
from ..repositories import (
    EscoEmbeddingMilvusRepository,
    EscoLexicalMongoRepository,
    MilvusCandidateRepository,
    MongoRepository,
)
from ..services import (
    ConflictCheckerService,
    CrossEncoderService,
    FusionService,
    HardFilterCompilerService,
    KeywordSearchService,
    NormalizerThresholds,
    OpenAICrossEncoderModel,
    QueryBuilderService,
    QueryNormalizerService,
    QueryUnderstandingService,
    RerankService,
    ResponseBuilderService,
    RetrievalPipelineService,
    VectorSearchService,
)
from .config import get_settings


@lru_cache(maxsize=1)
def get_mongo_repository() -> MongoRepository:
    return MongoRepository(settings=get_settings())


@lru_cache(maxsize=1)
def get_milvus_candidate_repository() -> MilvusCandidateRepository:
    settings = get_settings()
    return MilvusCandidateRepository(
        settings=settings,
        embedding_model=settings.openai_embedding_model,
        metric_type=settings.milvus_metric_type,
        search_ef=settings.milvus_search_ef,
    )


@lru_cache(maxsize=1)
def get_esco_lexical_repository() -> EscoLexicalMongoRepository:
    return EscoLexicalMongoRepository(settings=get_settings())


@lru_cache(maxsize=1)
def get_esco_embedding_repository() -> EscoEmbeddingMilvusRepository:
    settings = get_settings()
    return EscoEmbeddingMilvusRepository(
        settings=settings,
        embedding_model=settings.openai_embedding_model,
        metric_type=settings.milvus_metric_type,
        search_ef=settings.milvus_search_ef,
    )


@lru_cache(maxsize=1)
def get_retrieval_pipeline_service() -> RetrievalPipelineService:
    settings = get_settings()
    mongo_repo = get_mongo_repository()
    milvus_repo = get_milvus_candidate_repository()
    lexical_repo = get_esco_lexical_repository()
    embedding_repo = get_esco_embedding_repository()
    cross_encoder_model = _build_cross_encoder_model()

    return RetrievalPipelineService(
        query_understanding=QueryUnderstandingService(llm_client=None),
        query_normalizer=QueryNormalizerService(
            lexical_repo=lexical_repo,
            embedding_repo=embedding_repo,
            thresholds=NormalizerThresholds(
                high=settings.normalizer_high_threshold,
                medium=settings.normalizer_medium_threshold,
            ),
        ),
        conflict_checker=ConflictCheckerService(),
        hard_filter_compiler=HardFilterCompilerService(),
        query_builder=QueryBuilderService(rephraser=None),
        vector_search=VectorSearchService(
            repo=milvus_repo,
            default_top_k=settings.vector_top_k,
            skill_weight=settings.vector_skill_weight,
            occupation_weight=settings.vector_occupation_weight,
        ),
        keyword_search=KeywordSearchService(
            repo=mongo_repo,
            default_top_k=settings.keyword_top_k,
        ),
        fusion=FusionService(
            strategy=settings.fusion_strategy if settings.fusion_strategy in {"weighted_sum", "rrf"} else "weighted_sum",
            vector_weight=settings.fusion_vector_weight,
            keyword_weight=settings.fusion_keyword_weight,
            rrf_k=settings.fusion_rrf_k,
            default_top_k=settings.fusion_top_k,
        ),
        cross_encoder=CrossEncoderService(
            text_repo=mongo_repo,
            model=cross_encoder_model,
            default_top_k=settings.cross_encoder_top_k,
        ),
        rerank=RerankService(
            candidate_esco_repo=mongo_repo,
            default_top_k=settings.rerank_top_k,
        ),
        response_builder=ResponseBuilderService(),
        stage_caps=StageCaps(
            vector_top_k=settings.vector_top_k,
            keyword_top_k=settings.keyword_top_k,
            fusion_top_k=settings.fusion_top_k,
            cross_encoder_top_k=settings.cross_encoder_top_k,
            rerank_top_k=settings.rerank_top_k,
        ),
    )


def _build_cross_encoder_model() -> OpenAICrossEncoderModel | None:
    settings = get_settings()
    if not settings.cross_encoder_enabled:
        return None
    if not settings.openai_api_key:
        return None
    if not settings.openai_model_cross_encoder:
        return None
    if not OpenAICrossEncoderModel.is_available():
        return None
    return OpenAICrossEncoderModel(
        api_key=settings.openai_api_key,
        model=settings.openai_model_cross_encoder,
    )
