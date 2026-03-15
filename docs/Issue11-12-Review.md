# Issue #11/#12 Readiness Review

- Generated at (UTC): 2026-03-13T22:32:23.960375
- Dataset size: 2484

## Full-run Distribution (Issue #10 output)
- Status: success 2027 (81.6%), partial 427 (17.19%), failed 30 (1.21%)
- Graph rerank applied: 1181 docs (47.54%)
- Graph rank changed: 590 docs (23.75%)
- Avg candidates: occupation 3.698, skill 7.421

## Issue #11 Handoff Cohort
- Rerank trigger docs: 26 (1.05%)
- Extraction trigger docs: 781 (31.44%)
- Suggested default: keep `llm_mode=off`, run targeted `rerank` / `extraction` only for trigger=true docs.

## Issue #12 Integrity Check
- Duplicate upsert keys: 0
- Missing candidate_id docs: 0
- Current upsert model is suitable for idempotent rerun.

## Top Categories (partial/failed)
- ARTS: 29
- HEALTHCARE: 27
- SALES: 27
- CONSTRUCTION: 27
- TEACHER: 26
- CHEF: 26
- FITNESS: 25
- CONSULTANT: 25
- HR: 22
- BUSINESS-DEVELOPMENT: 22

## Proposed Issue Updates
### Issue #11
- Add trigger-gated execution using `llm_handoff` fields to keep call rate controlled.
- Add persistent cache key on `(source_dataset, source_record_id, normalizer_version, llm_mode)` hash.
- Keep fallback guarantee: if LLM fails, preserve rule-based result.
### Issue #12
- Keep `normalization_status` and `extraction_confidence` as mandatory output fields.
- Add indexes for `llm_handoff.rerank_trigger` and `llm_handoff.extraction_trigger` to support #11 queueing.
- Keep batch upsert idempotent on `source_dataset + source_record_id`.

## Poor-case Ruleization (2 cases)
- Implemented in `normalize_1st_to_mongo.py`:
  - Category short-word expansion (ex: `HR` -> `human resources`)
  - Fuzzy misfire guard:
    - drop occupation candidate when all of the following are true:
      - `match_method == fuzzy`
      - `confidence < 0.85` (balanced/precision)
      - `graph_hits == 0`
      - no category-anchor match in occupation label
- Targeted rerun (`source_record_id in [19818707, 25213006]`) result:
  - both bad fuzzy occupation candidates were removed
  - `19818707`: success -> partial
  - `25213006`: partial -> failed
  - behavior: prefer abstaining over confident wrong occupation suggestion
