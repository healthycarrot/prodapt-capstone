# Agent Scoring and Score Formula Specification

Last updated: 2026-03-18

## Purpose

This document defines the current fixed score logic used by the search serving flow and by the frontend `View Score Details` explanation surface.

It covers:

- FR-01 to FR-03 retrieval-stage scores
- FR-04 agent scores
- final integrated ranking score
- fallback and re-normalization rules

This is a documentation snapshot of the current implementation. If weights, blending strategy, or fallback rules change later, this file should be updated in the same task.

## Related Issues

- [#15](https://github.com/healthycarrot/prodapt-capstone/issues/15) FR-01 retrieval baseline
- [#16](https://github.com/healthycarrot/prodapt-capstone/issues/16) FR-02 parallel keyword + vector retrieval and fusion
- [#17](https://github.com/healthycarrot/prodapt-capstone/issues/17) FR-03 cross-encoder rerank
- [#18](https://github.com/healthycarrot/prodapt-capstone/issues/18) FR-04 agent-based scoring
- [#31](https://github.com/healthycarrot/prodapt-capstone/issues/31) fixed score-logic display in `View Score Details`

## Score Labels in the UI

- `Integrated Final Score` maps to `final_score`
- `Retrieval` maps to `retrieval_final_score`
- `Agent score` maps to `fr04_overall_score`
- `Keyword` maps to `keyword_score`
- `Vector` maps to `vector_score`
- `Fusion` maps to `fusion_score`
- `Cross Encoder` maps to `cross_encoder_score`

The frontend currently formats displayed values with 4 decimal places.

## Common Helpers

### Clamp

All final score values are bounded to the closed interval `[0, 1]`.

```text
clamp01(x) = min(1, max(0, x))
```

### Weight Normalization

Whenever a group of weights is used, the implementation first normalizes non-negative weights to sum to `1.0`.

```text
normalized_weight_i = max(0, weight_i) / sum(max(0, weight_j))
```

If the sum is `0` or less, uniform weights are used across the available items.

## Stage Sizes

Current fixed stage caps:

- vector search: top 100
- keyword search: top 100
- fusion output: top 50
- cross-encoder output: top 50
- rerank output: top 20

## Retrieval-Stage Scores

### 1. Vector Score

Vector retrieval is computed from two query paths:

- skill vector search
- occupation vector search

Each path is normalized independently with query-local min-max normalization.

```text
skill_vector_score_norm =
  (skill_vector_score_raw - min_skill_raw) / (max_skill_raw - min_skill_raw)

occupation_vector_score_norm =
  (occupation_vector_score_raw - min_occupation_raw) / (max_occupation_raw - min_occupation_raw)
```

If all raw scores in one path are identical, that path is assigned `1.0` for all returned hits.

The combined vector score uses weighted aggregation, not max pooling.

```text
if both skill and occupation scores exist:
  vector_score = 0.50 * skill_vector_score_norm
               + 0.50 * occupation_vector_score_norm

if only skill exists:
  vector_score = skill_vector_score_norm

if only occupation exists:
  vector_score = occupation_vector_score_norm

if neither exists:
  vector_score = 0.0
```

### 2. Keyword Score

Mongo `$text` scores are normalized before fusion.

The current normalization is query-local percentile clipping followed by min-max normalization.

```text
low  = percentile(raw_keyword_scores, 5)
high = percentile(raw_keyword_scores, 95)

clipped_score = min(max(raw_keyword_score, low), high)

keyword_score =
  (clipped_score - min(clipped_scores)) / (max(clipped_scores) - min(clipped_scores))
```

If only one keyword hit exists, or all clipped scores are identical, the normalized value becomes `1.0`.

### 3. Fusion Score

The current default fusion strategy is `weighted_sum`.

```text
fusion_score = 0.50 * vector_score + 0.50 * keyword_score
```

The implementation also supports `rrf` as an alternative strategy:

```text
fusion_score = 1 / (rrf_k + rank_vector) + 1 / (rrf_k + rank_keyword)
```

Current default:

```text
rrf_k = 60
```

### 4. Cross-Encoder Score

The cross-encoder stage reranks the fused top 50 candidates.

```text
cross_encoder_score = clamp01(model_score(query_text, candidate_text))
```

If the cross-encoder is unavailable, raises an error, or returns an invalid output size:

- `cross_encoder_applied = false`
- `cross_encoder_score = 0.0`
- retrieval ranking falls back to a fusion-based path

### 5. Medium ESCO Match Score

Medium-confidence ESCO candidates are not used for hard filter. They are used only as a weak rerank feature.

The score is the overlap ratio between:

- medium-band ESCO IDs produced by query normalization
- ESCO IDs attached to the candidate profile

```text
medium_ids = {query ESCO ids where band == "medium"}
candidate_esco_ids = ESCO ids attached to the candidate

medium_esco_match_score = |intersection(candidate_esco_ids, medium_ids)| / |medium_ids|
```

If there are no medium-band ESCO IDs, the score is effectively `0.0`.

### 6. Retrieval Final Score

When cross-encoder reranking succeeds:

```text
retrieval_final_score =
    0.60 * cross_encoder_score
  + 0.30 * fusion_score
  + 0.10 * medium_esco_match_score
```

When cross-encoder reranking falls back:

```text
retrieval_final_score =
    0.90 * fusion_score
  + 0.10 * medium_esco_match_score
```

## Agent Scores (FR-04)

The current implementation does not trust the LLM-returned `score` field as the final agent score.
Instead, the backend recomputes each agent score deterministically from the returned breakdown fields.

### 1. Skill Match Agent

Breakdown inputs:

- `match_score`
- `skill_depth_score`
- `management_score`

Dynamic query-analysis weights are normalized before use.

```text
(w_match, w_depth, w_management) =
  normalize_weights(skill_weight_match, skill_weight_depth, skill_weight_management)

skill_match =
  clamp01(
      w_match      * match_score
    + w_depth      * skill_depth_score
    + w_management * management_score
  )
```

Current default weights before normalization:

```text
skill_weight_match = 0.50
skill_weight_depth = 0.25
skill_weight_management = 0.25
```

### 2. Experience Match Agent

Breakdown inputs:

- `industry_match_score`
- `experience_level_match_score`
- `recency_score`

Industry and level weights are normalized before use.

```text
(w_industry, w_level) =
  normalize_weights(experience_weight_industry, experience_weight_level)

base =
    w_industry * industry_match_score
  + w_level    * experience_level_match_score

recency_bonus =
  (1 - base) * recency_score * 0.20

experience_match =
  clamp01(base + recency_bonus)
```

Current default weights before normalization:

```text
experience_weight_industry = 0.50
experience_weight_level = 0.50
```

### 3. Education Match Agent

```text
education_match = clamp01(education_match_score)
```

This agent is executed only when the orchestrator decides that the query contains education requirements.

### 4. Career Progression Agent

Breakdown inputs:

- `vertical_growth_score`
- `scope_expansion_score`

```text
career_progression =
  clamp01((vertical_growth_score + scope_expansion_score) / 2)
```

### 5. Soft Skill Agent

Breakdown inputs:

- `communication_score`
- `teamwork_score`
- `adaptability_score`

```text
soft_skill =
  clamp01((communication_score + teamwork_score + adaptability_score) / 3)
```

## FR-04 Overall Score

`fr04_overall_score` is the weighted average of executed and successful agents only.

Configured weights:

```text
skill_match        = 0.40
experience_match   = 0.35
education_match    = 0.10
career_progression = 0.075
soft_skill         = 0.075
```

These are re-normalized over only the agents that were actually executed and succeeded for the candidate.

```text
available_agent_weights = configured weights of executed and succeeded agents
normalized_agent_weight_i =
  available_agent_weight_i / sum(available_agent_weights)

fr04_overall_score =
  sum(normalized_agent_weight_i * agent_score_i)
```

Important notes:

- if the education agent is skipped, its weight is removed and the remaining executed-agent weights are re-normalized
- if some agents fail, successful agents still contribute
- if all agents fail, the system falls back to retrieval-only ranking

## Integrated Final Score

The final ranking score returned by `/search` is a weighted blend of retrieval and FR-04.

```text
final_score =
    0.60 * retrieval_final_score
  + 0.40 * fr04_overall_score
```

This is the value shown in the UI as `Integrated Final Score`.

## Fallback Rules

### All-Agent Failure Fallback

If no FR-04 agent succeeds:

```text
fr04_overall_score = 0.0
final_score = retrieval_final_score
```

### Output-Audit Ranking Fallback

If output audit determines that FR-04 ranking rationale must be disabled for a candidate:

```text
fr04_overall_score = 0.0
final_score = retrieval_final_score
```

The system also appends:

```text
output_audit_retrieval_fallback_applied
```

to `agent_errors`.

## Current Defaults Summary

| Item | Current default |
|---|---|
| Retrieval blend into final score | retrieval `0.60`, FR-04 `0.40` |
| FR-04 agent weights | skill `0.40`, experience `0.35`, education `0.10`, career `0.075`, soft skill `0.075` |
| Skill agent breakdown weights | `0.50 / 0.25 / 0.25` before normalization |
| Experience agent breakdown weights | `0.50 / 0.50` before normalization |
| Experience recency bonus cap | `0.20` |
| Vector aggregation | `0.50 * skill + 0.50 * occupation` |
| Fusion strategy | `weighted_sum` |
| Fusion default weights | vector `0.50`, keyword `0.50` |
| Retrieval rerank blend | cross `0.60`, fusion `0.30`, medium ESCO `0.10` |
| Retrieval fallback blend | fusion `0.90`, medium ESCO `0.10` |
| UI formatting | 4 decimal places |

## Source of Truth in Code

Current implementation references:

- `backend/app/services/vector_search.py`
- `backend/app/services/keyword_search.py`
- `backend/app/services/fusion.py`
- `backend/app/services/cross_encoder.py`
- `backend/app/services/rerank.py`
- `backend/app/services/agent_scoring/agents/common.py`
- `backend/app/services/agent_scoring/orchestrator.py`
- `backend/app/services/agent_scoring/aggregator.py`
- `backend/app/services/search_orchestration.py`
- `frontend/src/App.tsx`
