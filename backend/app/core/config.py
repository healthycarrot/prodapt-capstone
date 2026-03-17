from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


_TRUE_VALUES = {"1", "true", "yes", "on"}


def _default_env_path() -> Path:
    # backend/app/core/config.py -> backend/.env
    return Path(__file__).resolve().parents[2] / ".env"


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _get_str(key: str, default: str = "") -> str:
    value = os.getenv(key)
    if value is None:
        return default
    return value


def _get_int(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float(key: str, default: float) -> float:
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in _TRUE_VALUES


@dataclass(frozen=True, slots=True)
class Settings:
    app_env: str
    log_level: str

    # Mongo
    mongo_uri: str
    mongo_db_name: str
    mongo_normalized_collection: str
    mongo_source_collection: str
    mongo_guardrail_audit_collection: str
    mongo_raw_esco_skills_collection: str
    mongo_raw_esco_occupations_collection: str
    mongo_raw_esco_isco_groups_collection: str

    # Milvus
    milvus_uri: str
    milvus_token: str
    milvus_db_name: str
    milvus_candidate_collection: str
    milvus_occ_collection: str
    milvus_skill_collection: str

    # OpenAI
    openai_api_key: str
    openai_model_query_understanding: str
    openai_model_query_builder: str
    openai_model_cross_encoder: str
    openai_model_agent_scoring: str
    openai_embedding_model: str

    # Normalizer thresholds
    normalizer_high_threshold: float
    normalizer_medium_threshold: float

    # Stage caps
    vector_top_k: int
    keyword_top_k: int
    fusion_top_k: int
    cross_encoder_top_k: int
    rerank_top_k: int

    # Scoring defaults
    vector_skill_weight: float
    vector_occupation_weight: float
    fusion_strategy: str
    fusion_vector_weight: float
    fusion_keyword_weight: float
    fusion_rrf_k: int
    cross_encoder_enabled: bool

    # Milvus query params
    milvus_metric_type: str
    milvus_search_ef: int

    # Agent scoring
    search_agent_candidate_top_n: int
    agent_max_parallel: int
    agent_timeout_sec: int
    orchestrator_timeout_sec: int
    integrated_retrieval_weight: float
    integrated_fr04_weight: float
    fr04_weight_skill: float
    fr04_weight_experience: float
    fr04_weight_education: float
    fr04_weight_career: float
    fr04_weight_soft_skill: float

    # Guardrails (FR-07)
    input_guardrail_enabled: bool
    input_guardrail_min_query_length: int
    input_guardrail_max_query_length: int
    input_guardrail_require_skill_or_occupation: bool
    input_guardrail_prohibited_terms_csv: str
    output_audit_enabled: bool
    output_audit_prohibited_terms_csv: str
    output_audit_safe_summary_template: str
    output_audit_safe_reason_template: str

    @property
    def mongo_configured(self) -> bool:
        return bool(self.mongo_uri and self.mongo_db_name)

    @property
    def milvus_configured(self) -> bool:
        return bool(self.milvus_uri and self.milvus_candidate_collection)

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache(maxsize=1)
def get_settings(env_file: str | Path | None = None) -> Settings:
    path = Path(env_file) if env_file is not None else _default_env_path()
    _load_env_file(path)

    return Settings(
        app_env=_get_str("APP_ENV", "local"),
        log_level=_get_str("LOG_LEVEL", "INFO"),
        mongo_uri=_get_str("MONGO_URI", "mongodb://localhost:27017"),
        mongo_db_name=_get_str("MONGO_DB_NAME", "prodapt_capstone"),
        mongo_normalized_collection=_get_str("MONGO_NORMALIZED_COLLECTION", "normalized_candidates"),
        mongo_source_collection=_get_str("MONGO_SOURCE_COLLECTION", "source_1st_resumes"),
        mongo_guardrail_audit_collection=_get_str("MONGO_GUARDRAIL_AUDIT_COLLECTION", "guardrail_audit_logs"),
        mongo_raw_esco_skills_collection=_get_str("MONGO_RAW_ESCO_SKILLS_COLLECTION", "raw_esco_skills"),
        mongo_raw_esco_occupations_collection=_get_str(
            "MONGO_RAW_ESCO_OCCUPATIONS_COLLECTION",
            "raw_esco_occupations",
        ),
        mongo_raw_esco_isco_groups_collection=_get_str(
            "MONGO_RAW_ESCO_ISCO_GROUPS_COLLECTION",
            "raw_esco_isco_groups",
        ),
        milvus_uri=_get_str("MILVUS_URI", ""),
        milvus_token=_get_str("MILVUS_TOKEN", ""),
        milvus_db_name=_get_str("MILVUS_DB_NAME", "default"),
        milvus_candidate_collection=_get_str("MILVUS_CANDIDATE_COLLECTION", "candidate_search_collection_v3"),
        milvus_occ_collection=_get_str("MILVUS_OCC_COLLECTION", "occupation_collection"),
        milvus_skill_collection=_get_str("MILVUS_SKILL_COLLECTION", "skill_collection"),
        openai_api_key=_get_str("OPENAI_API_KEY", ""),
        openai_model_query_understanding=_get_str("OPENAI_MODEL_QUERY_UNDERSTANDING", "gpt-4.1-mini"),
        openai_model_query_builder=_get_str("OPENAI_MODEL_QUERY_BUILDER", "gpt-4.1-mini"),
        openai_model_cross_encoder=_get_str("OPENAI_MODEL_CROSS_ENCODER", ""),
        openai_model_agent_scoring=_get_str("OPENAI_MODEL_AGENT_SCORING", "gpt-4.1-mini"),
        openai_embedding_model=_get_str("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        normalizer_high_threshold=_get_float("NORMALIZER_HIGH_THRESHOLD", 0.85),
        normalizer_medium_threshold=_get_float("NORMALIZER_MEDIUM_THRESHOLD", 0.60),
        vector_top_k=_get_int("VECTOR_TOP_K", 100),
        keyword_top_k=_get_int("KEYWORD_TOP_K", 100),
        fusion_top_k=_get_int("FUSION_TOP_K", 50),
        cross_encoder_top_k=_get_int("CROSS_ENCODER_TOP_K", 50),
        rerank_top_k=_get_int("RERANK_TOP_K", 20),
        vector_skill_weight=_get_float("VECTOR_SKILL_WEIGHT", 0.5),
        vector_occupation_weight=_get_float("VECTOR_OCCUPATION_WEIGHT", 0.5),
        fusion_strategy=_get_str("FUSION_STRATEGY", "weighted_sum"),
        fusion_vector_weight=_get_float("FUSION_VECTOR_WEIGHT", 0.5),
        fusion_keyword_weight=_get_float("FUSION_KEYWORD_WEIGHT", 0.5),
        fusion_rrf_k=_get_int("FUSION_RRF_K", 60),
        cross_encoder_enabled=_get_bool("CROSS_ENCODER_ENABLED", True),
        milvus_metric_type=_get_str("MILVUS_METRIC_TYPE", "COSINE"),
        milvus_search_ef=_get_int("MILVUS_SEARCH_EF", 128),
        search_agent_candidate_top_n=_get_int("SEARCH_AGENT_CANDIDATE_TOPN", 20),
        agent_max_parallel=_get_int("AGENT_MAX_PARALLEL", 4),
        agent_timeout_sec=_get_int("AGENT_TIMEOUT_SEC", 60),
        orchestrator_timeout_sec=_get_int("ORCHESTRATOR_TIMEOUT_SEC", 90),
        integrated_retrieval_weight=_get_float("INTEGRATED_RETRIEVAL_WEIGHT", 0.60),
        integrated_fr04_weight=_get_float("INTEGRATED_FR04_WEIGHT", 0.40),
        fr04_weight_skill=_get_float("FR04_WEIGHT_SKILL", 0.40),
        fr04_weight_experience=_get_float("FR04_WEIGHT_EXPERIENCE", 0.35),
        fr04_weight_education=_get_float("FR04_WEIGHT_EDUCATION", 0.10),
        fr04_weight_career=_get_float("FR04_WEIGHT_CAREER", 0.075),
        fr04_weight_soft_skill=_get_float("FR04_WEIGHT_SOFT_SKILL", 0.075),
        input_guardrail_enabled=_get_bool("INPUT_GUARDRAIL_ENABLED", True),
        input_guardrail_min_query_length=_get_int("INPUT_GUARDRAIL_MIN_QUERY_LENGTH", 20),
        input_guardrail_max_query_length=_get_int("INPUT_GUARDRAIL_MAX_QUERY_LENGTH", 2000),
        input_guardrail_require_skill_or_occupation=_get_bool(
            "INPUT_GUARDRAIL_REQUIRE_SKILL_OR_OCCUPATION",
            False,
        ),
        input_guardrail_prohibited_terms_csv=_get_str("INPUT_GUARDRAIL_PROHIBITED_TERMS_CSV", ""),
        output_audit_enabled=_get_bool("OUTPUT_AUDIT_ENABLED", True),
        output_audit_prohibited_terms_csv=_get_str("OUTPUT_AUDIT_PROHIBITED_TERMS_CSV", ""),
        output_audit_safe_summary_template=_get_str(
            "OUTPUT_AUDIT_SAFE_SUMMARY_TEMPLATE",
            "This recommendation was generated from job-relevant evidence.",
        ),
        output_audit_safe_reason_template=_get_str(
            "OUTPUT_AUDIT_SAFE_REASON_TEMPLATE",
            "Details were sanitized by output guardrail policy.",
        ),
    )
