# フィールド対応表: スキーマ → HTMLセクション → 抽出方式

Issue: #7 – [Pipeline v2] Step 2: スキーマ→セクション対応表作成
Source: `docs/dbdiagram.normalized.dbml`
Reference: `script/for_1st/reanalyze_1st_resume_structure_report.json` (Issue #6)

---

## HTMLセクション型リファレンス

Issue #6 の再解析で確認されたセクション型と出現率:

| セクション型 | 説明 | Docs coverage |
|---|---|---|
| `NAME` | 氏名・肩書ヘッダー | 99.8% (2480/2484) |
| `SUMM` | Summary / Professional Summary | 99.9% (2482/2484) |
| `HILT` | Highlights / Core Qualifications | 90.5% (2247/2484) |
| `EXPR` | Experience / Work History | 100.0% (2483/2484) |
| `EDUC` | Education | 99.6% (2473/2484) |
| `SKLL` | Skills | 96.5% (2397/2484) |
| `ACCM` | Accomplishments | 52.4% (1302/2484) |
| `AFIL` | Affiliations / Memberships | 31.4% (781/2484) |
| `ADDI` | Additional Information | 20.4% (506/2484) |
| `CERT` | Certifications | 13.4% (332/2484) |
| `TSKL` | Technical Skills | 1.9% (48/2484) |
| `INTR` | Interests | 10.1% (250/2484) |
| `PRIN` | Personal Information | 5.4% (133/2484) |
| Other | WRKH, PUBL, LANG, CUST, etc. | <6% each |

---

## 抽出モード定義

| `extractor_mode` | 説明 |
|---|---|
| `as_is` | 生データからそのままコピー（変換なし） |
| `generated` | パイプライン内部で生成する値（UUID, timestamp 等） |
| `regex` | 正規表現でパターンマッチ抽出 |
| `heuristic` | ルールベースのヒューリスティック抽出 |
| `esco_matcher` | ESCO参照DBとのマッチング（exact → alt → fuzzy → graph） |
| `computed` | 他フィールドから計算で導出 |
| `llm_fallback` | 上記で低信頼時にのみLLMで補完 |

---

## Table: `candidates`

| Column | Nullable | source_section | extractor_mode | Fallback Order | Notes |
|---|---|---|---|---|---|
| `candidate_id` | NOT NULL | — | `generated` | — | UUID v4. パイプライン生成 |
| `source_dataset` | NOT NULL | — | `as_is` | — | 固定値 `"1st_data"` |
| `source_record_id` | NOT NULL | — | `as_is` | — | MongoDB `source_record_id` をコピー |
| `normalizer_version` | NOT NULL | — | `generated` | — | スクリプトバージョン文字列 |
| `normalized_at` | NOT NULL | — | `generated` | — | 実行時タイムスタンプ |
| `normalization_status` | NOT NULL | — | `computed` | — | 全フィールド充填率から判定: success / partial / failed |
| `current_location` | nullable | `NAME` | `regex` → `llm_fallback` | 1. NAME セクションから "City, State" パターン<br>2. EXPR 先頭から地名抽出<br>3. LLM fallback | 正規表現: `/([A-Z][a-z]+)\s*,\s*([A-Z]{2})/` |
| `resume_text` | NOT NULL | (all) | `as_is` | — | `resume_text` フィールドをそのままコピー |
| `extraction_confidence` | nullable | — | `computed` | — | 全子テーブルの confidence 加重平均 |

---

## Table: `candidate_occupation_candidates`

候補元セクション: `NAME` (肩書) + `SUMM` (要約内の職種言及) + `EXPR` (職歴タイトル)

| Column | Nullable | source_section | extractor_mode | Fallback Order | Notes |
|---|---|---|---|---|---|
| `id` | NOT NULL | — | `generated` | — | Auto-increment |
| `candidate_id` | NOT NULL | — | `generated` | — | 親 candidates への FK |
| `raw_text` | NOT NULL | `NAME` > `SUMM` > `EXPR` | `heuristic` | 1. NAME セクションの肩書テキスト（最優先）<br>2. SUMM 冒頭の職種フレーズ<br>3. EXPR の各職歴タイトル | NAME はほぼ全件に肩書が含まれる |
| `esco_id` | nullable | — | `esco_matcher` | exact → alt_label → fuzzy → graph rerank | ESCO occupation URI |
| `preferred_label` | nullable | — | `esco_matcher` | — | ESCO preferred_label |
| `confidence` | NOT NULL | — | `esco_matcher` | — | マッチング信頼度スコア |
| `match_method` | NOT NULL | — | `esco_matcher` | — | `exact` / `alt_label` / `fuzzy` / `embedding` / `llm` |
| `rank` | NOT NULL | — | `computed` | — | confidence 降順 |
| `is_primary` | NOT NULL | — | `computed` | — | rank = 1 → true |
| `hierarchy_json` | nullable | — | `esco_matcher` | — | `broaderRelationsOccPillar` から構築 |
| `source_span` | nullable | source_section | `heuristic` | — | 抽出元テキストの位置情報 |

---

## Table: `candidate_skill_candidates`

候補元セクション: `SKLL` + `HILT` + `TSKL` (直接的スキル列挙) + `EXPR` (本文中のスキル言及)

| Column | Nullable | source_section | extractor_mode | Fallback Order | Notes |
|---|---|---|---|---|---|
| `id` | NOT NULL | — | `generated` | — | Auto-increment |
| `candidate_id` | NOT NULL | — | `generated` | — | 親 candidates への FK |
| `raw_text` | NOT NULL | `SKLL` > `HILT` > `TSKL` > `EXPR` | `heuristic` | 1. SKLL セクションを bullet/comma/semicolon で分割<br>2. HILT セクションを同様に分割<br>3. TSKL セクションを同様に分割<br>4. EXPR 本文からスキルキーワード抽出 | 区切り文字: `,` `;` `\|` `•` `\n` |
| `esco_id` | nullable | — | `esco_matcher` | exact → alt_label → fuzzy | ESCO skill URI |
| `preferred_label` | nullable | — | `esco_matcher` | — | ESCO preferred_label |
| `confidence` | NOT NULL | — | `esco_matcher` | — | マッチング信頼度スコア |
| `match_method` | NOT NULL | — | `esco_matcher` | — | `exact` / `alt_label` / `fuzzy` / `embedding` / `llm` |
| `rank` | NOT NULL | — | `computed` | — | confidence 降順 |
| `is_primary` | NOT NULL | — | `computed` | — | rank = 1 → true |
| `hierarchy_json` | nullable | — | `esco_matcher` | — | `broaderRelationsSkillPillar` から構築 |
| `source_span` | nullable | source_section | `heuristic` | — | 抽出元テキストの位置情報 |

---

## Table: `candidate_experiences`

候補元セクション: `EXPR` (1セクション → 複数 experience レコードに分割)

| Column | Nullable | source_section | extractor_mode | Fallback Order | Notes |
|---|---|---|---|---|---|
| `experience_id` | NOT NULL | — | `generated` | — | Auto-increment |
| `candidate_id` | NOT NULL | — | `generated` | — | 親 candidates への FK |
| `title` | nullable | `EXPR` | `regex` → `llm_fallback` | 1. 正規表現: 職歴ブロック先頭行<br>2. LLM fallback | 大文字タイトル or bold タグ内テキスト |
| `raw_title` | nullable | `EXPR` | `heuristic` | — | 正規化前の元テキスト |
| `company` | nullable | `EXPR` | `regex` → `llm_fallback` | 1. "Company Name" パターン<br>2. "at [Company]" パターン<br>3. LLM fallback | HTMLでは `<span class="companyname">` も利用可 |
| `start_date` | nullable | `EXPR` | `regex` | 1. MM/YYYY パターン<br>2. "Month YYYY" パターン<br>3. YYYY のみ | ISO date に正規化 |
| `end_date` | nullable | `EXPR` | `regex` | 同上 | "Current"/"Present" → null + is_current=true |
| `is_current` | NOT NULL | `EXPR` | `heuristic` | — | end_date が "Current"/"Present" → true, default false |
| `location` | nullable | `EXPR` | `regex` | 1. "City, State" パターン<br>2. "- City, State" パターン | 経験ブロック内の地名 |
| `duration_months` | nullable | — | `computed` | — | end_date - start_date（月単位）. is_current なら現在日まで |
| `description_raw` | nullable | `EXPR` | `as_is` | — | 経験ブロックのテキスト全体 |

### EXPR セクション内の分割ロジック
EXPR セクションは単一テキストに複数の職歴が含まれる。以下の境界で分割:
1. **日付レンジパターン**: `MM/YYYY to MM/YYYY` or `Month YYYY to Present`
2. **"Company Name"** キーワード
3. **大文字タイトル行** + 直後の会社名
4. フォールバック: `\s{3,}` 空白ブロック

---

## Table: `experience_occupation_candidates`

候補元: `candidate_experiences.title` / `candidate_experiences.raw_title`

| Column | Nullable | source_section | extractor_mode | Fallback Order | Notes |
|---|---|---|---|---|---|
| `id` | NOT NULL | — | `generated` | — | Auto-increment |
| `experience_id` | NOT NULL | — | `generated` | — | 親 candidate_experiences への FK |
| `raw_text` | NOT NULL | `EXPR` (via experience.title) | `heuristic` | — | experience の title をそのまま使用 |
| `esco_id` | nullable | — | `esco_matcher` | exact → alt_label → fuzzy → graph rerank | ESCO occupation URI |
| `preferred_label` | nullable | — | `esco_matcher` | — | ESCO preferred_label |
| `confidence` | NOT NULL | — | `esco_matcher` | — | マッチング信頼度スコア |
| `match_method` | NOT NULL | — | `esco_matcher` | — | `exact` / `alt_label` / `fuzzy` / `embedding` / `llm` |
| `rank` | NOT NULL | — | `computed` | — | confidence 降順 |
| `is_primary` | NOT NULL | — | `computed` | — | rank = 1 → true |
| `hierarchy_json` | nullable | — | `esco_matcher` | — | `broaderRelationsOccPillar` から構築 |

---

## Table: `candidate_educations`

候補元セクション: `EDUC`

| Column | Nullable | source_section | extractor_mode | Fallback Order | Notes |
|---|---|---|---|---|---|
| `education_id` | NOT NULL | — | `generated` | — | Auto-increment |
| `candidate_id` | NOT NULL | — | `generated` | — | 親 candidates への FK |
| `institution` | nullable | `EDUC` | `regex` → `llm_fallback` | 1. 大学名パターン ("University", "College", "Institute")<br>2. HTMLの `<span>` 構造<br>3. LLM fallback | 長文化防止: 100文字/10語ガード |
| `degree` | nullable | `EDUC` | `regex` → `llm_fallback` | 1. "Bachelor/Master/PhD/Associate/Certificate" パターン<br>2. 略称 "BS/BA/MS/MA/MBA/PhD" パターン<br>3. LLM fallback | |
| `field_of_study` | nullable | `EDUC` | `regex` → `llm_fallback` | 1. "in [Field]" / ": [Field]" パターン<br>2. degree 直後のフレーズ<br>3. LLM fallback | |
| `start_date` | nullable | `EDUC` | `regex` | YYYY パターン | 教育機関では年のみが多い |
| `end_date` | nullable | `EDUC` | `regex` | YYYY パターン | |
| `graduation_year` | nullable | `EDUC` | `regex` | 1. 明示的 graduation year<br>2. end_date の年部分 | |
| `location` | nullable | `EDUC` | `regex` | "City, State" パターン | |

### EDUC セクション内の分割ロジック
EDUC セクションに複数学歴が含まれる場合:
1. **学位キーワード** ("Bachelor", "Master", "Associate", "Certificate") で境界検出
2. **年パターン** + 学校名の組み合わせ
3. フォールバック: `\s{3,}` 空白ブロック

---

## セクション型 → テーブル マッピングサマリ

| HTML Section Type | Primary Target Table(s) | Secondary Usage |
|---|---|---|
| `NAME` | `candidates.current_location`, `candidate_occupation_candidates.raw_text` | 肩書から職種候補抽出 |
| `SUMM` | `candidate_occupation_candidates.raw_text` | 要約内の職種キーワード |
| `HILT` | `candidate_skill_candidates.raw_text` | Core Qualifications / Highlights |
| `EXPR` | `candidate_experiences.*`, `experience_occupation_candidates.*` | 職歴ブロック分割→複数レコード |
| `EDUC` | `candidate_educations.*` | 学歴ブロック分割→複数レコード |
| `SKLL` | `candidate_skill_candidates.raw_text` | Skills セクション |
| `TSKL` | `candidate_skill_candidates.raw_text` | Technical Skills（SKLL と同等扱い） |
| `ACCM` | (supplementary) | accomplishments → スキル候補の補助ソース |
| `AFIL` | (supplementary) | affiliations → 現時点では未使用、将来拡張候補 |
| `CERT` | (supplementary) | certifications → スキル候補の補助ソース |
| `ADDI` | (supplementary) | additional info → 現時点では未使用 |
| `INTR` | (not used) | interests → スコープ外 |
| `PRIN` | (not used) | personal info → スコープ外 |

---

## フォールバック戦略

```
Primary: BeautifulSoup HTML parser (parsed_sections from #8)
    ↓ (section_count < 2)
Fallback 1: Whitespace-block (\s{3,}) splitting on resume_text
    ↓ (text_length < 22)
Fallback 2: Mark as normalization_status = "failed", skip extraction
```

---

## 信頼度スコア方針

| extractor_mode | Base Confidence |
|---|---|
| `as_is` | 1.0 |
| `generated` | 1.0 |
| `regex` (high pattern match) | 0.9 |
| `regex` (weak pattern match) | 0.6 |
| `heuristic` | 0.7 |
| `esco_matcher` (exact) | 1.0 |
| `esco_matcher` (alt_label) | 0.95 |
| `esco_matcher` (fuzzy ≥ 0.90) | 0.85 |
| `esco_matcher` (fuzzy ≥ 0.85) | 0.75 |
| `llm_fallback` | LLM応答の自己申告 confidence（0.0–1.0） |
| `computed` | 入力フィールドの confidence から導出 |
