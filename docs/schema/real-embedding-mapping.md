# candidate_search_collection Mapping (Planned)

Target schema:
- `docs/schema/dbdiagram.real_embedding.dbml`

Reference docs:
- `docs/design/Pipeline.md`
- `docs/schema/dbdiagram.normalized.dbml`
- `docs/schema/dbdiagram.raw.dbml`

## Purpose
- `candidate_search_collection` は PR-06 real embedding phase で publish される Milvus serving collection の論理スキーマ。
- MongoDB の `normalized_candidates` と `source_1st_resumes` を source of truth とし、検索に必要な vector と scalar filter のみを保持する。
- 説明生成や候補者詳細表示は MongoDB 側を参照する。

## Source Priority
1. `normalized_candidates`
2. `source_1st_resumes`
3. publish-time generated metadata

## Field Mapping

| Field | Nullable | Source | Derivation | Notes |
|---|---|---|---|---|
| `vector_doc_id` | NOT NULL | publish job metadata + `normalized_candidates.candidate_id` | `generated` | 推奨形式: `<snapshot_version>:<candidate_id>` |
| `candidate_id` | NOT NULL | `normalized_candidates.candidate_id` | `as_is` | 候補者の安定キー |
| `normalized_doc_id` | NOT NULL | `normalized_candidates._id` | `as_is` | Mongo の正規化文書キー |
| `source_dataset` | NOT NULL | `normalized_candidates.source_dataset` | `as_is` | source resume への逆引き用 |
| `source_record_id` | NOT NULL | `normalized_candidates.source_record_id` | `as_is` | source resume への逆引き用 |
| `snapshot_version` | NOT NULL | publish job metadata | `generated` | index publish 単位のスナップショット識別子 |
| `normalizer_version` | NOT NULL | `normalized_candidates.normalizer_version` | `as_is` | 正規化バージョン |
| `embedding_model` | NOT NULL | embedding builder config | `generated` | 例: 利用 embedding model 名 |
| `embedding_version` | NOT NULL | embedding builder config | `generated` | テキスト組み立て規則のバージョン文字列 |
| `skill_vector` | NOT NULL | `normalized_candidates.skill_candidates[*]`, `source_1st_resumes.extracted_fields.skills[*]`, `normalized_candidates.experiences[*]`, `normalized_candidates.occupation_candidates[*]` | `computed` | 下記 Assembly Rule を参照 |
| `occupation_vector` | NOT NULL | `normalized_candidates.occupation_candidates[*]`, `source_1st_resumes.extracted_fields.occupation_candidates[*]`, `normalized_candidates.experiences[*]`, `source_1st_resumes.extracted_fields.name_title` | `computed` | 下記 Assembly Rule を参照 |
| `category` | nullable | `normalized_candidates.category` | `as_is` | 既存 category guardrail / 互換フィルタ用 |
| `industry_esco_id` | nullable | `normalized_candidates.occupation_candidates[*].hierarchy_json` | `computed` | primary occupation candidate の直近親 ESCO component |
| `occupation_esco_ids_json` | NOT NULL | `normalized_candidates.occupation_candidates[*].esco_id` | `computed` | rank 順で保持（候補なしは `[]`） |
| `skill_esco_ids_json` | NOT NULL | `normalized_candidates.skill_candidates[*].esco_id` | `computed` | rank 順で保持（候補なしは `[]`） |
| `experience_months_total` | nullable | `normalized_candidates.experiences[*].duration_months` | `computed` | null を除いて合計 |
| `highest_education_level_rank` | nullable | `normalized_candidates.educations[*].degree`, `normalized_candidates.educations[*].field_of_study` | `computed` | degree ヒューリスティックで最大 rank を採用 |
| `current_location` | nullable | `normalized_candidates.current_location` | `as_is` | exact / prefix filter 用 |

## `skill_vector` Assembly Rule

Assembly order:
1. `normalized_candidates.skill_candidates`
2. `source_1st_resumes.extracted_fields.skills`
3. `normalized_candidates.experiences`
4. `normalized_candidates.occupation_candidates`（軽い domain anchor のみ）

Detailed mapping:

| Order | Source Field | Transform | Recommended Cap | Notes |
|---|---|---|---|---|
| 1 | `normalized_candidates.skill_candidates[*].preferred_label` | rank 順に採用、重複除去 | top 12 | canonical skill label を優先 |
| 2 | `normalized_candidates.skill_candidates[*].raw_text` | lower/trim 後に dedup | top 12 | normalized candidate 側で保持している raw phrase |
| 3 | `source_1st_resumes.extracted_fields.skills[*].raw_text` | lower/trim 後に dedup | top 20 | ESCO 未正規化語彙を補完 |
| 4 | `normalized_candidates.experiences[*].title` | 直近経験から抽出 | up to 3 exp | skill の文脈 anchor |
| 5 | `normalized_candidates.experiences[*].description_raw` | skill-bearing snippet のみ抽出 | up to 3 exp | 長文全文は入れない |
| 6 | `normalized_candidates.occupation_candidates[*].preferred_label` | 補助入力 | top 2 | domain anchor のみ |

Exclusion:
- `company`
- `current_location`
- `resume_text`
- `matching_debug`
- `llm_handoff`
- parsed `summary` section（現時点では不採用）

## `occupation_vector` Assembly Rule

Assembly order:
1. `normalized_candidates.occupation_candidates`
2. `source_1st_resumes.extracted_fields.occupation_candidates`
3. `normalized_candidates.experiences`
4. `source_1st_resumes.extracted_fields.name_title`

Detailed mapping:

| Order | Source Field | Transform | Recommended Cap | Notes |
|---|---|---|---|---|
| 1 | `normalized_candidates.occupation_candidates[*].preferred_label` | rank 順に採用、重複除去 | top 3 | primary/top occupation labels |
| 2 | `normalized_candidates.occupation_candidates[*].hierarchy_json[*].label` | narrow -> broad 順で連結 | top 3 occ | broader role context |
| 3 | `normalized_candidates.occupation_candidates[*].raw_text` | lower/trim 後に dedup | top 3 | normalized candidate 側で保持している raw phrase |
| 4 | `source_1st_resumes.extracted_fields.occupation_candidates[*]` | lower/trim 後に dedup | top 5 | raw occupation phrase 補完 |
| 5 | `normalized_candidates.experiences[*].title` | 直近順に採用 | up to 5 exp | strongest raw role evidence |
| 6 | `normalized_candidates.experiences[*].raw_title` | title 欠損時の補完 | up to 5 exp | original role string |
| 7 | `source_1st_resumes.extracted_fields.name_title` | optional fallback | 1 | headline/title 補助 |

Exclusion:
- `company`
- `current_location`
- `resume_text`
- `matching_debug`
- `llm_handoff`
- parsed `summary` section（現時点では不採用）
- ESCO の full description（query-side / normalization-side で既に活用するため candidate vector には入れない）

## Scalar Derivation Rules

### `industry_esco_id`
- Source:
  - `normalized_candidates.occupation_candidates`
  - `normalized_candidates.occupation_candidates[*].hierarchy_json`
- Rule:
  - `is_primary = true` の occupation candidate を first choice とする。
  - その `hierarchy_json` のうち、対象 occupation の直近親 component の `id` を採用する。
  - 直近親が取得できない場合は null。

### `occupation_esco_ids_json`
- Source:
  - `normalized_candidates.occupation_candidates[*].esco_id`
- Rule:
  - `rank` 昇順で ESCO ID を配列化。
  - null / duplicate は除外。
  - 候補が存在しない場合は `null` ではなく空配列 `[]` を設定する。

### `skill_esco_ids_json`
- Source:
  - `normalized_candidates.skill_candidates[*].esco_id`
- Rule:
  - `rank` 昇順で ESCO ID を配列化。
  - null / duplicate は除外。
  - 候補が存在しない場合は `null` ではなく空配列 `[]` を設定する。

## Publish Inclusion Rule
- `occupation_esco_ids_json` と `skill_esco_ids_json` がどちらも空配列でも publish 対象から除外しない。
- hard filter 不一致時に除外される可能性はあるが、index publish 自体は実施する。

### `experience_months_total`
- Source:
  - `normalized_candidates.experiences[*].duration_months`
- Rule:
  - non-null の月数のみ合計。
  - 全件 null の場合は null。

### `highest_education_level_rank`
- Source:
  - `normalized_candidates.educations[*].degree`
  - `normalized_candidates.educations[*].field_of_study`
- Rule:
  - degree 文字列を rank に正規化し、候補者内の最大値を採用。
  - 推奨 ordinal:
    - `0`: unknown
    - `1`: secondary / high school
    - `2`: associate / diploma
    - `3`: bachelor
    - `4`: master / mba
    - `5`: doctorate / phd / md / jd

## Non-goals
- `education_vector` は作らない。
- `summary_vector` は作らない。
- explanation 用の長文や UI 表示用 denormalized text は Milvus に保持しない。

## Retrieval Flow Reminder
1. Milvus で `skill_vector` / `occupation_vector` を検索
2. scalar metadata で filter
3. `candidate_id` / `normalized_doc_id` で MongoDB の詳細を引く
4. 後段 rerank / explanation を実行
