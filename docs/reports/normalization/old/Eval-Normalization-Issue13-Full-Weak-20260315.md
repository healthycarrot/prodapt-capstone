# Normalization Evaluation Report (Issue #13)

- Generated at (UTC): 2026-03-15T09:40:14.032543
- Mode: weak
- K: 10
- Collection: normalized_candidates
- Docs: 2484

## Status Distribution
- success: 2051
- partial: 412
- failed: 21

## Overall Ranking Metrics
| target | docs_evaluated | p@1 | p@5 | mrr@k | map@k | coverage@k |
|---|---:|---:|---:|---:|---:|---:|
| occupation | 2484 | 0.3160 | 0.1573 | 0.3606 | 0.3512 | 0.4477 |
| skill | 2484 | 0.0370 | 0.0299 | 0.0650 | 0.0566 | 0.1486 |

## LLM Cohorts
- rerank_trigger_docs: 9 (0.0036)
- extraction_trigger_docs: 760 (0.3060)

## Embedding B1 Adoption
- top1_docs: 3 (rate=0.0012)
- any_docs: 56 (rate=0.0225)

## Top Partial/Failed Categories
- HEALTHCARE: 30
- CONSTRUCTION: 28
- ARTS: 28
- CHEF: 26
- FITNESS: 25
- CONSULTANT: 25
- TEACHER: 24
- BANKING: 24
- SALES: 23
- AVIATION: 22

## Warnings
- weak skill coverage_at_10=0.1486 < threshold 0.4000

