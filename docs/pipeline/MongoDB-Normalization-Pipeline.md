# MongoDB Normalization Pipeline (1st_data -> normalized_candidates)

## Scope
- Input: `source_1st_resumes` (with `extracted_fields`)
- Reference: ESCO raw collections (`raw_esco_occupations`, `raw_esco_skills`, relation collections)
- Output: `normalized_candidates`

## Current Strategy (Issue #14)
- Base matching: `exact + alt_label + fuzzy`
- Embedding retrieval (Milvus):
  - Occupation: `A + B1` (RRF fusion)
  - Skill: `A` only
- LLM usage is in **candidate generation** (not rerank):
  - Input: extracted resume evidence + ESCO classification snippets
  - Output: seed ESCO IDs + expansion terms
  - Seeds are merged before profile filtering
- Final ranking path:
  - profile filter
  - graph rerank (ESCO occupation-skill relation)
  - category guardrail

## LLM Rerank Rollback
- We previously tested LLM rerank after graph rerank.
- Result: quality gain was limited relative to added latency/cost and operational complexity.
- Decision: **rollback LLM rerank** and remove it from default flow.
- Current LLM role: candidate generation only.

## Output Policy for RAG Recall
- `occupation_candidates`: store Top 20
- `skill_candidates`: store Top 50

## Main Script
- Normalization: `script/pipeline_mongo/normalize_1st_to_mongo.py`
- Evaluation: `script/pipeline_mongo/evaluate_normalization.py`
- Milvus index build: `script/pipeline_mongo/build_esco_milvus_index.py`

## Required Environment Variables
- `OPENAI_API_KEY`
- `MILVUS_URI`
- `MILVUS_TOKEN` (optional)
- `MILVUS_DB_NAME` (optional)
- `MILVUS_OCC_COLLECTION` (optional, default: `occupation_collection`)
- `MILVUS_SKILL_COLLECTION` (optional, default: `skill_collection`)

## Typical Commands
1. Build Milvus index
```bash
python .\script\pipeline_mongo\build_esco_milvus_index.py --db-name prodapt_capstone --drop-existing
```

2. Full normalization
```bash
python .\script\pipeline_mongo\normalize_1st_to_mongo.py --db-name prodapt_capstone --limit 0 --ranking-profile balanced --threshold-strictness medium --metrics-out .\script\pipeline_mongo\metrics_issue14_full.json
```

3. Baseline without LLM candidate generation
```bash
python .\script\pipeline_mongo\normalize_1st_to_mongo.py --db-name prodapt_capstone --limit 0 --llm-candidate-mode off --metrics-out .\script\pipeline_mongo\metrics_issue14_no_llm_candidate.json
```

4. Parallel normalization
```bash
python .\script\pipeline_mongo\normalize_1st_to_mongo.py --db-name prodapt_capstone --limit 0 --record-workers 4 --llm-candidate-mode always --metrics-out .\script\pipeline_mongo\metrics_issue14_workers4.json
```
