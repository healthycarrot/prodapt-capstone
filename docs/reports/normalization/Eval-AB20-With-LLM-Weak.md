# Normalization Evaluation Report (Issue #13)

- Generated at (UTC): 2026-03-15T18:13:13.028885
- Mode: weak
- K: 10
- Collection: normalized_candidates_ab_with_llm_20
- Docs: 20

## Status Distribution
- success: 17
- partial: 3

## Overall Ranking Metrics
| target | docs_evaluated | p@1 | p@5 | mrr@k | map@k | coverage@k |
|---|---:|---:|---:|---:|---:|---:|
| occupation | 20 | 0.2500 | 0.1500 | 0.3117 | 0.2986 | 0.4500 |
| skill | 20 | 0.0500 | 0.0800 | 0.1142 | 0.1137 | 0.2500 |

## LLM Cohorts
- rerank_trigger_docs: 0 (0.0000)
- extraction_trigger_docs: 8 (0.4000)

## Embedding B1 Adoption
- top1_docs: 0 (rate=0.0000)
- any_docs: 0 (rate=0.0000)

## Top Partial/Failed Categories
- CONSTRUCTION: 1
- BUSINESS-DEVELOPMENT: 1
- FITNESS: 1

## Warnings
- weak skill coverage_at_10=0.2500 < threshold 0.4000

