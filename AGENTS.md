# Agent

## Pipeline Change Rule
- For any change related to the normalization pipeline, read `Pipeline.md` before editing code or docs.

# Github issue rule
- When you have to check issues, you must access the remote repository and check the issues on GitHub. You can use the GitHub API or any other method to access the issues. Make sure to check for any relevant issues that may be related to the task you are working on.

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
