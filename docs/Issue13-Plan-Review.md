# Issue #13 Plan Review (Updated)

- Updated at (UTC): 2026-03-15
- Reviewed with:
- Issue #10 full run (`balanced + medium`, 2484 docs)
- Issue #11/#12 readiness review
- 10-sample LLM qualitative eval
- Milvus A/B experiment (`A`, `B1`, `B2`, `G_B1`, `G_B2`)
- Refactor decision: Occupation=`B1`, Skill=`A`

## 1) Decision Summary (Plan Change)

- Occupation retrieval: adopt `A + B1` (separate query execution + `RRF` fusion).
- Skill retrieval: keep `A` only (do not append Experience).
- Low-confidence gate variants (`G_B1`, `G_B2`) are not primary path for now.
- Weak-label metrics remain supplementary. Gold evaluation is required for final go/no-go.

## 2) Evidence Behind The Change

### Full-run baseline (#10)
- total: 2484
- status: success 2027 / partial 427 / failed 30
- graph rerank applied: 1181
- graph rank changed: 590
- weak pilot: `P@1=0.1884`, `MRR@10=0.2291`, `coverage@10=0.3003`
- llm handoff: rerank trigger 26 (1.05%), extraction trigger 781 (31.44%)

### A/B experiment (60 samples)
- Occupation:
- `A -> B1` improved pseudo metrics:
- pseudo_hit@1: `0.0175 -> 0.0877`
- pseudo_hit@5: `0.1579 -> 0.2281`
- pseudo_mrr@10: `0.0711 -> 0.1381`
- avg_top1_conf: `0.558 -> 0.5915`
- Skill:
- `A` was better or comparable to `B1/B2`.
- `B1` degraded pseudo_hit@5 (`0.0784 -> 0.0189`).
- Therefore Skill keeps `A` only.

### 10-sample LLM qualitative check
- Avg Top1 fit: 72.5
- Avg Top3 ranking: 68.6
- Avg overall: 70.3
- Verdict: good 2 / mixed 6 / poor 2
- poor 2 cases were ruleized (category short-word expansion + fuzzy misfire guard).

## 3) Revised Scope For Issue #13

1. Evaluation runner must compare at least 2 configs:
- baseline (pre-Occupation-B1 behavior)
- current (Occupation=`B1`, Skill=`A`)
2. Mandatory report segments:
- by `normalization_status` (success/partial/failed)
- by `llm_handoff` cohort (rerank/extraction trigger)
- by `match_method` (`exact`, `alt_label`, `fuzzy`, `embedding`, `embedding_b1`)
- by category (top partial/failed categories)
3. Output artifacts:
- JSON summary
- Markdown report
- A/B diff table (absolute delta + relative delta)
4. Integrity block:
- duplicate upsert key count
- missing `candidate_id` count

## 4) Acceptance Criteria (Updated)

1. Smoke run (50 docs) and full run (`--limit 0`) both produce evaluation artifacts.
2. Gold mode and weak mode both run successfully.
3. Diff report clearly shows Occupation and Skill metric movement separately.
4. No data integrity regression:
- duplicate upsert keys = 0
- missing `candidate_id` = 0
5. Operational metrics are included:
- LLM trigger rate
- `embedding_b1` usage rate in final occupation candidates

## 5) Risks / Open Questions

- Weak labels are noisy and can under/over-estimate true quality.
- In short smoke runs, occupation `embedding_b1` may be executed but not survive final top-K after hybrid ranking. Full-run verification is required.
- Need to freeze a reproducible baseline snapshot for strict A/B comparison (same dataset slice, same Milvus collections, same model).

## 6) Recommended Next Step

1. Run full normalization with current strategy (Occupation=`B1`, Skill=`A`).
2. Run Issue #13 evaluator in weak + gold mode and generate A/B diff artifacts.
3. Review 20 low-confidence samples manually (or via LLM rubric) to validate metric interpretation before final threshold setting.
