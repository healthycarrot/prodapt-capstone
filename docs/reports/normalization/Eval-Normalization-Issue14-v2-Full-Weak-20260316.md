# Normalization Evaluation Report (Issue #13)

- Generated at (UTC): 2026-03-16T03:13:59.750396
- Mode: weak
- K: 10
- Collection: normalized_candidates
- Docs: 2484

## Status Distribution
- success: 2141
- partial: 325
- failed: 18

## Overall Ranking Metrics
| target | docs_evaluated | p@1 | p@5 | mrr@k | map@k | coverage@k |
|---|---:|---:|---:|---:|---:|---:|
| occupation | 2484 | 0.3917 | 0.2293 | 0.4369 | 0.4213 | 0.5085 |
| skill | 2484 | 0.1373 | 0.1794 | 0.1999 | 0.1983 | 0.3261 |

## LLM Cohorts
- rerank_trigger_docs: 7 (0.0028)
- extraction_trigger_docs: 594 (0.2391)

## Embedding B1 Adoption
- top1_docs: 0 (rate=0.0000)
- any_docs: 8 (rate=0.0032)

## Top Partial/Failed Categories
- ARTS: 29
- CONSTRUCTION: 28
- CHEF: 26
- CONSULTANT: 25
- SALES: 24
- AVIATION: 24
- BANKING: 24
- APPAREL: 21
- PUBLIC-RELATIONS: 20
- FITNESS: 18

## Warnings
- weak skill coverage_at_10=0.3261 < threshold 0.4000

