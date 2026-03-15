# Milvus A/B Experience Query Comparison

- Generated at (UTC): 2026-03-15T03:24:25.610051
- Sample size: 60
- Top-K: 10
- Embedding model: text-embedding-3-small
- Low-confidence threshold: 0.45

## Variant Definition
- A: base query only
- B1: base + raw experience (top 2 experiences)
- B2: base + summarized experience (titles + representative terms)
- G_B1: low-confidence gate (A default, switch to B1 only when A top1 confidence < threshold)
- G_B2: low-confidence gate (A default, switch to B2 only when A top1 confidence < threshold)
- Fusion: RRF for multi-query variants (A + B1_input / A + B2_input)

## Occupation Metrics

| variant | docs_with_results | expected_count | pseudo_hit@1 | pseudo_hit@5 | pseudo_mrr@10 | avg_top1_conf | heuristic_hit |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 60 | 57 | 0.0175 | 0.1579 | 0.0711 | 0.558 | 0.6833 |
| B1 | 60 | 57 | 0.0877 | 0.2281 | 0.1381 | 0.5915 | 0.6167 |
| B2 | 60 | 57 | 0.0702 | 0.2105 | 0.1387 | 0.5892 | 0.6333 |
| G_B1 | 60 | 57 | 0.0175 | 0.1579 | 0.0711 | 0.558 | 0.6833 |
| G_B2 | 60 | 57 | 0.0175 | 0.1579 | 0.0711 | 0.558 | 0.6833 |

## Skill Metrics

| variant | docs_with_results | expected_count | pseudo_hit@1 | pseudo_hit@5 | pseudo_mrr@10 | avg_top1_conf | heuristic_hit |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 55 | 51 | 0.0 | 0.0784 | 0.0384 | 0.4831 | 0.5818 |
| B1 | 60 | 53 | 0.0 | 0.0189 | 0.0203 | 0.5196 | 0.4909 |
| B2 | 60 | 53 | 0.0 | 0.0755 | 0.0318 | 0.525 | 0.5091 |
| G_B1 | 60 | 53 | 0.0 | 0.0755 | 0.0369 | 0.5083 | 0.5455 |
| G_B2 | 60 | 53 | 0.0 | 0.0755 | 0.0369 | 0.5084 | 0.5273 |

## Low-Confidence Cohort (A-based gate)

- low_conf_doc_count: 60 / 60
- occupation_gate_ratio: 0.0
- skill_gate_ratio: 0.35

## Notes
- pseudo_* metrics use current `normalized_candidates` top1 as weak target.
- heuristic_hit is:
  - occupation: top1 label has category anchor
  - skill: top1 label token overlaps base skill query tokens
