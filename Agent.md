# Agent

## Pipeline Change Rule
- For any change related to the normalization pipeline, read `Pipeline.md` before editing code or docs.

## What Counts As Pipeline Change
- Files under `script/pipeline_mongo/`
- Pipeline-related docs under `docs/`
- Schema/index changes that affect `source_1st_resumes` or `normalized_candidates`
- ESCO matching, ranking, graph rerank, embedding, LLM handoff, or evaluation flow changes

## Update Rule
- If behavior/defaults/commands change, update `Pipeline.md` in the same task.
- Keep Issue timeline continuity (Issue #6 onward) and append new decisions rather than rewriting history.
