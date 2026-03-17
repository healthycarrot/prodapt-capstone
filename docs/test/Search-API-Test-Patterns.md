# Search API Test Patterns (`/search`)

`/search` のハードフィルタ挙動と Vector 検索挙動を確認するためのリクエストパターン集です。  
対象エンドポイント: `POST /search`

## 前提
- `candidate_id` の完全一致までは期待値にしない（データ更新で変動するため）。
- 期待値は「レスポンス構造」「件数傾向」「順位傾向」で定義する。

## Pattern 1: Baseline
Request
```json
{
  "query_text": "software engineer frontend",
  "limit": 20
}
```
期待値
- HTTP 200
- `retry_required=false`
- `results` 件数が `1..20`
- `final_score` が降順

## Pattern 2: Conflict (experience)
Request
```json
{
  "query_text": "backend engineer with 3+ years experience",
  "experience_min_months": 0,
  "experience_max_months": 12,
  "limit": 20
}
```
期待値
- HTTP 200
- `retry_required=true`
- `conflict_fields` に `experience` を含む
- `results=[]`

## Pattern 3: Conflict (education)
Request
```json
{
  "query_text": "master degree required",
  "education_min_rank": 1,
  "education_max_rank": 2,
  "limit": 20
}
```
期待値
- HTTP 200
- `retry_required=true`
- `conflict_fields` に `education` を含む
- `results=[]`

## Pattern 4: Hard filter (location should narrow to zero)
Request
```json
{
  "query_text": "software engineer",
  "locations": ["__NO_SUCH_LOCATION__"],
  "limit": 20
}
```
期待値
- HTTP 200
- `retry_required=false`
- `results.length=0`

## Pattern 5: Hard filter effect (with/without explicit terms)
Request A
```json
{
  "query_text": "frontend engineer",
  "limit": 20
}
```
Request B
```json
{
  "query_text": "frontend engineer",
  "skill_terms": ["JavaScript", "CSS"],
  "occupation_terms": ["web developer"],
  "limit": 20
}
```
期待値
- `B.results.length <= A.results.length`（同数は許容）
- B の上位は A より frontend 寄り（`raw_candidates` の title/skills で確認）

## Pattern 6: Vector semantic similarity (paraphrase robustness)
Request A
```json
{
  "query_text": "frontend software engineer react javascript",
  "limit": 20
}
```
Request B
```json
{
  "query_text": "ui web application developer with react and js",
  "limit": 20
}
```
期待値
- A/B の Top5 に重なりが出る（目安 2 件以上）
- 上位候補で `vector_score` が継続して高い

## Pattern 7: Vector discrimination (different role intent)
Request A
```json
{
  "query_text": "frontend react engineer",
  "limit": 20
}
```
Request B
```json
{
  "query_text": "data engineer spark etl",
  "limit": 20
}
```
期待値
- A/B の Top5 重複が少ない（目安 0〜1 件）
- 上位候補の職務文脈が明確に分かれる

## Pattern 8: Validation error (422)
Request
```json
{
  "query_text": "string",
  "experience_min_months": 24,
  "experience_max_months": 12,
  "limit": 20
}
```
期待値
- HTTP 422
- `detail = "experience_min_months must be <= experience_max_months"`

## Extra: User-provided full payload smoke
Request
```json
{
  "query_text": "string",
  "skill_terms": ["string"],
  "occupation_terms": ["string"],
  "industry_terms": ["string"],
  "experience_min_months": 0,
  "experience_max_months": 0,
  "education_min_rank": 5,
  "education_max_rank": 5,
  "locations": ["string"],
  "limit": 20
}
```
期待値
- HTTP 200
- バリデーション通過
- `retry_required` はデータ依存（`true/false` どちらもあり得る）
