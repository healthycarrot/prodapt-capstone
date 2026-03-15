# Normalization Evaluation Report (Issue #13)

- Generated at (UTC): 2026-03-15T04:30:53.223982
- Mode: weak
- K: 10
- Collection: normalized_candidates
- Docs: 50

## Status Distribution
- success: 42
- partial: 7
- failed: 1

## Overall Ranking Metrics
| target | docs_evaluated | p@1 | p@5 | mrr@k | map@k | coverage@k |
|---|---:|---:|---:|---:|---:|---:|
| occupation | 50 | 0.2400 | 0.1240 | 0.3173 | 0.3080 | 0.4400 |
| skill | 50 | 0.0200 | 0.0560 | 0.0765 | 0.0766 | 0.2000 |

## LLM Cohorts
- rerank_trigger_docs: 0 (0.0000)
- extraction_trigger_docs: 16 (0.3200)

## Embedding B1 Adoption
- top1_docs: 0 (rate=0.0000)
- any_docs: 0 (rate=0.0000)

## Top Partial/Failed Categories
- CONSTRUCTION: 2
- FITNESS: 2
- BUSINESS-DEVELOPMENT: 1
- CHEF: 1
- HEALTHCARE: 1
- DESIGNER: 1

## Warnings
- weak skill coverage_at_10=0.2000 < threshold 0.4000

