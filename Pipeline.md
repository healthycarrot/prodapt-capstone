# Pipeline

## Scope
- This file is the canonical pipeline memo for `script/pipeline_mongo`.
- Covers implementation history from Issue #6 onward and current default behavior.

## Issue Timeline (Issue #6 -> current)
1. Issue #6: Mongo ingestion baseline
- Loaded ESCO raw CSV and 1st dataset into MongoDB.
- Established source collections and idempotent source key (`source_dataset + source_record_id`).
- Main script: `script/pipeline_mongo/ingest_csv_to_mongo.py`.

2. Issue #7: Section parsing layer
- Added parsed section storage and parser reports for source resumes.
- Prepared downstream deterministic extraction.
- Main script: `script/pipeline_mongo/parse_sections_to_mongo.py`.

3. Issue #8: Parser quality and structure refinement
- Improved section parsing stability and reporting.
- Reduced malformed section carry-over into extraction stage.

4. Issue #9: Deterministic field extraction
- Added rule-based extraction for experience/education/skills.
- Stored `extracted_fields` in source docs.
- Main scripts:
  - `script/pipeline_mongo/extract_fields.py`
  - `script/pipeline_mongo/extract_fields_to_mongo.py`

5. Issue #10: Simple but effective normalization pipeline
- Implemented occupation/skill matching using:
  - exact label
  - alt label
  - fuzzy fallback
- Added graph rerank by ESCO occupation-skill relations.
- Added guardrail for fuzzy misfire suppression.
- Added `llm_handoff` trigger fields for controlled downstream LLM usage.
- Main script: `script/pipeline_mongo/normalize_1st_to_mongo.py`.
- Full-run reference result (all 2484):
  - `success`: 2027
  - `partial`: 427
  - `failed`: 30
  - graph rank changed: 590

6. Issue #11 readiness (LLM gating)
- Confirmed trigger-gated strategy:
  - rerank trigger: 26 docs (1.05%)
  - extraction trigger: 781 docs (31.44%)
- Keep rule output as fallback if LLM fails.

7. Issue #12 readiness (data integrity)
- Confirmed idempotent upsert strategy is valid:
  - duplicate upsert key count: 0
  - missing `candidate_id`: 0
- Keep indexes for operational filtering (`normalization_status`, `llm_handoff.*`).

8. Issue #13 review
- No major plan rewrite required.
- Keep ranking metrics; add segmentation and integrity blocks in evaluation outputs.

9. Embedding + Milvus baseline
- Added hybrid embedding retrieval to normalization:
  - enabled for both occupation and skill candidates
  - merges embedding candidates with existing lexical candidates before profile filtering
  - safe fallback: if config/deps are missing, embedding auto-disables and lexical pipeline continues
- Added ESCO embedding index builder for Milvus cloud:
  - `script/pipeline_mongo/build_esco_milvus_index.py`
  - Occupation payload:
    - preferred + alt + description + hierarchy + essential skills
  - Skill payload:
    - preferred + alt + description + hierarchy + related occupations (essential)

10. Retrieval strategy refinement (2026-03-15)
- Occupation retrieval switched to `A + B1`:
  - A: base occupation semantic query
  - B1: base + raw experience query
  - final merge: RRF fusion before profile filtering
- Skill retrieval kept as `A` only:
  - experience-augmented query is not used in current default path
- Added embedding debug counters for:
  - occupation A candidates
  - occupation B1 candidates
  - fused occupation candidates
  - skill A candidates

11. Issue #13 implementation update (2026-03-16)
- Added LLM-based occupation adjudication stage after graph rerank:
  - candidate pool expansion (dedupe by ESCO id)
  - resume role-profile extraction by LLM
  - multi-judge (`jury`) occupation scoring/ranking
  - consensus-based rerank merge into final occupation confidence
- Added `matching_debug.llm_occupation` block:
  - applied flag, reason, candidate_count, judge_runs, consensus_rate
  - top1 before/after, fallback_used
- Added per-candidate LLM signals in output:
  - `llm_fit_score`
  - `llm_rank_score`
- Updated normalizer version:
  - `issue13_llm_occ_jury_v1`

## Current Default Behavior
- Normalizer script: `script/pipeline_mongo/normalize_1st_to_mongo.py`
- `--embedding-mode auto` is default.
- `--llm-occ-rerank-mode always` is default.
- When embedding is enabled:
  - Occupation: `A + B1` (RRF fusion)
  - Skill: `A` only
- Occupation final ranking path:
  - lexical/embedding candidate generation
  - profile filter
  - graph rerank
  - LLM occupation rerank (jury aggregation)
  - category guardrail
- In `auto`, pipeline attempts embedding only when all are available:
  - `OPENAI_API_KEY`
  - `MILVUS_URI`
  - Milvus collections for occupation/skill embeddings
  - required packages (`openai`, `pymilvus`)
- If embedding is unavailable, pipeline runs without embedding.
- If LLM occupation rerank is unavailable, pipeline falls back to non-LLM ranking path.

## Environment Variables
- `OPENAI_API_KEY`
- `MILVUS_URI`
- `MILVUS_TOKEN` (optional)
- `MILVUS_DB_NAME` (optional)
- `MILVUS_OCC_COLLECTION` (optional, default: `esco_occupation_embeddings`)
- `MILVUS_SKILL_COLLECTION` (optional, default: `esco_skill_embeddings`)

## Recommended Commands
1. Build Milvus embedding collections
```bash
python .\script\pipeline_mongo\build_esco_milvus_index.py --db-name prodapt_capstone --drop-existing
```

2. Run normalization (full)
```bash
python .\script\pipeline_mongo\normalize_1st_to_mongo.py --db-name prodapt_capstone --limit 0 --ranking-profile balanced --threshold-strictness medium --metrics-out .\script\pipeline_mongo\metrics_issue10_full_balanced_medium.json
```

3. Run normalization (targeted IDs)
```bash
python .\script\pipeline_mongo\normalize_1st_to_mongo.py --db-name prodapt_capstone --source-record-ids 19818707,25213006 --limit 0 --metrics-out .\script\pipeline_mongo\metrics_targeted.json
```

4. Run normalization without LLM occupation rerank (for speed/baseline)
```bash
python .\script\pipeline_mongo\normalize_1st_to_mongo.py --db-name prodapt_capstone --limit 0 --llm-occ-rerank-mode off --metrics-out .\script\pipeline_mongo\metrics_no_llm_occ.json
```

5. Compare A/B1/B2 experience-query variants (Milvus retrieval)
```bash
python .\script\pipeline_mongo\evaluate_milvus_ab_experience.py --db-name prodapt_capstone --sample-size 60 --top-k 10
```

6. Generate gold annotation CSV samples (50 template + 200 stratified)
```bash
python .\script\pipeline_mongo\generate_gold_annotation_samples.py --db-name prodapt_capstone --template-size 50 --stratified-size 200 --out-template-csv .\script\pipeline_mongo\gold_annotation_template_50.csv --out-stratified-csv .\script\pipeline_mongo\gold_annotation_sample_200_stratified.csv --out-summary-json .\script\pipeline_mongo\gold_annotation_sampling_summary.json
```

## Related Docs
- `docs/Issue11-12-Review.md`
- `docs/Issue13-Plan-Review.md`
- `docs/MongoDB-Normalization-Pipeline.md`
- `docs/Issue6-Script-IO-Map.md`
- `docs/Milvus-AB-Experience-Comparison.md`
