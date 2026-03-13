# MongoDB Normalization Pipeline (1st_data -> normalized_candidates)

## 方針
- ESCO は raw 構造のまま MongoDB に格納して参照する。
- 1st_data (`Resume.csv`) を入力として正規化し、`normalized_candidates` に保存する。
- 初期マッチングは `exact + alt_label + fuzzy(>=0.85)`。
- 将来 LLM を追加できるよう、matcher をモジュール化する。

## コレクション

### Raw 参照コレクション (ESCO)
- `raw_esco_occupations`
- `raw_esco_skills`
- `raw_esco_isco_groups`
- `raw_esco_skill_groups`
- `raw_esco_broader_relations_occ`
- `raw_esco_broader_relations_skill`
- `raw_esco_occupation_skill_relations`

### 入力コレクション
- `source_1st_resumes`

### 正規化出力コレクション
- `normalized_candidates`

## 実装ファイル
- CSV取込: [script/pipeline_mongo/ingest_csv_to_mongo.py](script/pipeline_mongo/ingest_csv_to_mongo.py)
- 正規化: [script/pipeline_mongo/normalize_1st_to_mongo.py](script/pipeline_mongo/normalize_1st_to_mongo.py)

## 必要パッケージ
- `pymongo`
- `rapidfuzz`

## 実行手順

1. CSV を MongoDB にロード
- ESCO raw CSV
- 1st_data `Resume.csv`

2. 正規化パイプライン実行
- `source_1st_resumes` を読み取り
- occupation/skill を ESCO 参照で候補化
- `normalized_candidates` へ upsert

## 正規化ルール (確定)
- `candidate_id`: UUID v4
- `source_dataset`: `1st_data`
- `source_record_id`: 1st の `ID`
- fuzzy 閾値: `0.85`
- rank: `confidence` 降順
- is_primary: `rank = 1`
- 再実行: upsert（既存候補/子配列差し替え）

## モジュール構成 (将来LLM対応)
- `ExactMatcher`
- `AltLabelMatcher`
- `FuzzyMatcher`
- 将来追加: `LLMMatcher`

`normalize_1st_to_mongo.py` は matcher インターフェース経由で呼ぶため、LLM matcher を追加しても既存処理に最小変更で対応できる。
