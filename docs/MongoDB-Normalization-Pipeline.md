# MongoDB Normalization Pipeline (1st_data -> normalized_candidates)

## 方針
- ESCO は raw 構造のまま MongoDB に格納して参照する。
- 1st_data (`Resume.csv`) を入力として正規化し、`normalized_candidates` に保存する。
- 初期マッチングは `exact + alt_label + fuzzy(>=0.85)`。
- 将来 LLM を追加できるよう、matcher をモジュール化する。
- 職種候補は ESCO occupation-skill relation で再ランキングする（graph rerank）。
- 曖昧ケースのみ LLM rerank を発火し、結果はメモリキャッシュする。
- 任意で Top-N のみ embedding rerank を適用する。

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
- 評価ランナー: [script/pipeline_mongo/evaluate_normalization.py](script/pipeline_mongo/evaluate_normalization.py)

## 必要パッケージ
- `pymongo`
- `rapidfuzz`
- `openai`
- `python-dotenv`

## 実行手順

1. CSV を MongoDB にロード
- ESCO raw CSV
- 1st_data `Resume.csv`

2. 正規化パイプライン実行
- `source_1st_resumes` を読み取り
- occupation/skill を ESCO 参照で候補化
- occupation を ESCO relation + optional embedding/LLM で再ランキング
- `normalized_candidates` へ upsert

### 推奨実行例（graph + LLM + embedding）
- `python .\normalize_1st_to_mongo.py --db-name prodapt_capstone --fetch-batch-size 300 --write-batch-size 300 --enable-embedding-rerank --enable-llm-rerank`

### 主な追加フラグ
- `--graph-essential-weight`
- `--graph-optional-weight`
- `--enable-embedding-rerank`
- `--embedding-model`
- `--embedding-top-n`
- `--enable-llm-rerank`
- `--llm-low-confidence-threshold`
- `--llm-min-graph-support`
- `--llm-min-skill-candidates`

## 正規化ルール (確定)
- `candidate_id`: UUID v4
- `source_dataset`: `1st_data`
- `source_record_id`: 1st の `ID`
- fuzzy 閾値: `0.85`
- rank: `confidence` 降順
- is_primary: `rank = 1`
- 再実行: upsert（既存候補/子配列差し替え）
- occupation候補に `graph_support`（essential/optional hit）を付与

## モジュール構成 (将来LLM対応)
- `ExactMatcher`
- `AltLabelMatcher`
- `FuzzyMatcher`
- 将来追加: `LLMMatcher`

`normalize_1st_to_mongo.py` は matcher インターフェース経由で呼ぶため、LLM matcher を追加しても既存処理に最小変更で対応できる。

## 評価ランナー

### 実行
- `python .\evaluate_normalization.py --db-name prodapt_capstone --k 10 --output-json .\eval_report.json --output-md .\eval_report.md`

### 指標
- `P@5`
- `MRR@10`
- `MAP@K`
- `coverage@10`

### 備考
- `--gold-file` を渡すと人手ラベルで評価
- `--gold-file` なしの場合は category と職種ラベルの弱一致で暫定評価

## Issue #11/#12 Handoff (from full run)
- Full run command:
  - `python .\normalize_1st_to_mongo.py --db-name prodapt_capstone --ranking-profile balanced --threshold-strictness medium --limit 0 --metrics-out .\metrics_issue10_full_balanced_medium.json`
- Full run size:
  - `processed_docs`: 2484
- Status distribution:
  - `success`: 2027
  - `partial`: 427
  - `failed`: 30
- Graph rerank effect:
  - applied docs: 1181
  - rank changed docs: 590

### Issue #11 connection fields
- `normalized_candidates.llm_handoff.rerank_trigger`
- `normalized_candidates.llm_handoff.extraction_trigger`
- `normalized_candidates.matching_debug.llm_handoff`

`llm_handoff` is generated from rule output and can be used to gate LLM calls to a controlled cohort.

### Issue #12 integrity checks
- Upsert key: `source_dataset + source_record_id`
- Duplicate key count should remain `0`
- `candidate_id` should be present for all normalized documents

### Review artifacts
- `script/pipeline_mongo/metrics_issue10_full_balanced_medium.json`
- `script/pipeline_mongo/issue11_12_readiness_report.json`
- `docs/Issue11-12-Review.md`
