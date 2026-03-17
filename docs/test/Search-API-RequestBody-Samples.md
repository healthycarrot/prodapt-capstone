# Search API Request Body Samples (`/search`)

`POST /search` をすぐ試せるように、代表的な Request Body をまとめます。  
対象スキーマ: `backend/app/api/schemas/search.py` の `SearchRequest`

## 1. 最小リクエスト
```json
{
  "query_text": "backend engineer with API development experience",
  "occupation_terms": ["backend engineer"]
}
```

## 2. 基本フィルタあり（推奨スタート）
```json
{
  "query_text": "backend engineer with Python and FastAPI",
  "skill_terms": ["Python", "FastAPI"],
  "occupation_terms": ["backend developer"],
  "industry_terms": ["information technology"],
  "experience_min_months": 36,
  "education_min_rank": 3,
  "locations": ["Tokyo", "Yokohama"],
  "limit": 20
}
```

## 3. フィルタを広めにした検索
```json
{
  "query_text": "software engineer",
  "skill_terms": [],
  "occupation_terms": ["software engineer"],
  "industry_terms": [],
  "locations": [],
  "limit": 30
}
```

## 4. シニア寄り条件
```json
{
  "query_text": "senior data engineer for ETL and Spark",
  "skill_terms": ["Spark", "ETL", "SQL"],
  "occupation_terms": ["data engineer"],
  "experience_min_months": 72,
  "education_min_rank": 3,
  "limit": 15
}
```

## 5. 学歴条件を明示した検索（Education Agentが動きやすい）
```json
{
  "query_text": "machine learning engineer, master degree preferred",
  "skill_terms": ["Machine Learning", "Python"],
  "occupation_terms": ["machine learning engineer"],
  "education_min_rank": 4,
  "limit": 20
}
```

## 6. バリデーションエラー確認（experience範囲逆転: 422）
```json
{
  "query_text": "backend engineer",
  "experience_min_months": 60,
  "experience_max_months": 24,
  "limit": 20
}
```

## 7. バリデーションエラー確認（education範囲逆転: 422）
```json
{
  "query_text": "data analyst",
  "education_min_rank": 5,
  "education_max_rank": 3,
  "limit": 20
}
```

## 8. フルフィールド入力（回帰テスト向け）
```json
{
  "query_text": "frontend engineer with React and TypeScript",
  "skill_terms": ["React", "TypeScript", "CSS"],
  "occupation_terms": ["frontend developer", "web developer"],
  "industry_terms": ["software", "e-commerce"],
  "experience_min_months": 24,
  "experience_max_months": 120,
  "education_min_rank": 2,
  "education_max_rank": 5,
  "locations": ["Osaka", "Kyoto", "Remote"],
  "limit": 20
}
```

## 補足
- `limit` の許容範囲は `1..50`。
- `query_text` は入力ガードレールで長さチェックされ、デフォルトは `20..2000` 文字（違反時は `HTTP 200 + retry_required=true`）。
- 入力ガードレールでは、`skill_terms` または `occupation_terms` の明示入力（または query-understanding 抽出結果）が必要。
- `skill_terms` / `occupation_terms` / `industry_terms` は ESCO の preferred label または alt label を指定する（未登録語は `422`）。
- `education rank` は `0..5`（0: unknown, 1: secondary, 2: associate/diploma/certificate, 3: bachelor, 4: master, 5: doctorate）。
- エージェント実行込みの結果確認は `/search`、FR-01..03 のみ確認したい場合は `/retrieve` を使用。
