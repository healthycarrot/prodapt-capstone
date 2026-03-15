# GitHub Issues Draft (Pipeline Improvement)

Repository: `healthycarrot/prodapt-capstone`
Target area: `script/pipeline_mongo`

## Note on Deprecated Direction
- We tested LLM-based reranking for occupation ordering.
- Outcome was not strong enough for the added latency/cost/ops complexity.
- This direction is deprecated and removed from current default pipeline.
- Current LLM usage is candidate generation only.

## Issue 1 - Graph-based Occupation Ranking
Title: `feat(pipeline): rerank occupation candidates using ESCO occupation-skill graph`
- Keep deterministic graph boost using ESCO occupation-skill relations.
- Validate impact with `MRR@10` and `coverage@10`.

## Issue 2 - Embedding Retrieval Integration
Title: `feat(pipeline): integrate Milvus embedding retrieval for occupation/skill`
- Occupation: A + B1 query path with RRF fusion.
- Skill: A query path.
- Merge embedding candidates into lexical candidate pool.

## Issue 3 - LLM Candidate Generation (Current)
Title: `feat(pipeline): use LLM for ESCO seed candidate generation`
- Input: `source_1st_resumes.extracted_fields` + ESCO classification snippets.
- Output: occupation seed IDs + skill seed IDs + term expansions.
- Apply before profile filtering.

## Issue 4 - Education Extraction Cleanup
Title: `fix(parser): add dedicated education text cleaning pipeline`
- Improve institution/degree separation and reduce long noisy strings.

## Issue 5 - Evaluation Runner
Title: `feat(eval): add evaluation runner for P@K / MRR@K / coverage@K`
- Produce repeatable JSON/MD reports.
- Support weak and gold mode.

## Issue 6 - Gold Annotation Workflow
Title: `feat(eval): generate annotation templates and stratified samples`
- Auto-generate 50-row template and 200-row stratified sample.
- Speed up human labeling workflow.
