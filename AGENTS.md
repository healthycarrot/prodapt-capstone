# Agent

## Pipeline Change Rule
- For any change related to the normalization pipeline, read `Pipeline.md` before editing code or docs.

# Github issue rule
- When you have to check issues, you must access the remote repository and check the issues on GitHub. You can use the GitHub API or any other method to access the issues. Make sure to check for any relevant issues that may be related to the task you are working on.

## Issue Spec Management Rule
- Treat GitHub Issues as the primary source of truth for requirements/spec changes.
- Before starting implementation or docs updates, identify and read all related remote issues.
- Maintain per-issue summaries in `docs/issues/issue-index.md` (single index file).
- Consolidate key information from legacy files under `docs/issues/` into `docs/issues/issue-index.md`.
- When issue scope/decision/status changes, update `docs/issues/issue-index.md` in the same task.

## GitHub CLI (`gh`)
- `gh` is available via the executable path:
  - `C:\Program Files\GitHub CLI\gh.exe`
- Current authenticated account:
  - `healthycarrot`
- If `gh` is not resolved from `PATH`, run it by full path.

## What Counts As Pipeline Change
- Files under `script/pipeline_mongo/`
- Pipeline-related docs under `docs/`
- Schema/index changes that affect `source_1st_resumes` or `normalized_candidates`
- ESCO matching, ranking, graph rerank, embedding, LLM handoff, or evaluation flow changes

## Update Rule
- If behavior/defaults/commands change, update `Pipeline.md` in the same task.
- Keep Issue timeline continuity (Issue #6 onward) and append new decisions rather than rewriting history.

## Documentation Rule
- Organize docs by topic under `docs/`: `overview/`, `pipeline/`, `schema/`, `issues/`, `reports/`.
- Keep `docs/index.md` as the single entry point; update it whenever docs are added, moved, or removed.
- For execution outputs and reports, keep active files in the category folder and move older snapshots into that category's `old/` folder.
- Do not place new standalone docs directly under `docs/` except `docs/index.md`.
