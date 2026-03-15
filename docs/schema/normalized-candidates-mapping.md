# normalized_candidates Mapping (Current)

Target script:
- `script/pipeline_mongo/normalize_1st_to_mongo.py`
- `NORMALIZER_VERSION = issue14_llm_candidate_generation_v2`

## High-level Flow
1. Read `source_1st_resumes` (+ `extracted_fields` if present)
2. Build lexical phrases for occupation/skill
3. Optional embedding retrieval from Milvus
4. LLM candidate generation (seed IDs + expansion terms)
5. Merge candidates and apply profile filter
6. Apply graph rerank + guardrail
7. Store capped candidates into `normalized_candidates`

## Top-level Fields
| Field | Source | Notes |
|---|---|---|
| `candidate_id` | generated UUID | set on insert |
| `source_dataset` | source doc | usually `1st_data` |
| `source_record_id` | source doc | upsert key with dataset |
| `category` | source doc | used as anchor/guardrail hint |
| `resume_text` | source doc | also passed to LLM candidate generation |
| `experiences` | `extracted_fields.experiences` | kept in output |
| `educations` | `extracted_fields.educations` | kept in output |
| `occupation_candidates` | ESCO match result | **Top 20** stored |
| `skill_candidates` | ESCO match result | **Top 50** stored |
| `normalization_status` | derived | `success` / `partial` / `failed` |
| `llm_handoff` | derived | trigger diagnostics for downstream ops |
| `matching_debug` | derived | execution diagnostics |

## Candidate Creation Notes
- Occupation and skill candidates are produced by combining:
  - lexical matching (`exact`, `alt_label`, `fuzzy`)
  - optional embedding retrieval
  - LLM candidate generation seeds
- LLM candidate generation input:
  - extracted phrases and experience/education signals from `extracted_fields`
  - category
  - resume excerpt
  - ESCO reference snippets (`preferred`, `description`, `hierarchy`, `alt_labels`)

## Rerank Policy
- Graph rerank is active (deterministic ESCO relation-based boost).
- **LLM rerank is rolled back** (not used in the current ranking path).
- `llm_handoff.rerank_trigger` remains as ambiguity-monitoring metadata only.

## Output Caps for Retrieval
- `occupation_candidates`: Top 20
- `skill_candidates`: Top 50

## matching_debug Key Points
- `matching_debug.embedding.*`: embedding execution and candidate counts
- `matching_debug.llm_candidate_generation.*`: LLM candidate generation diagnostics
- `matching_debug.graph.*`: graph rerank diagnostics
- `matching_debug.output_caps.*`: applied output limits
