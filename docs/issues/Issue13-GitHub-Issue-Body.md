# [Pipeline v2] Step 8: 評価パイプライン

## 概要
Issue #10 の全件実行結果と Milvus A/B 検証結果を踏まえ、評価パイプラインを「運用判断に使える形」に拡張する。

## 背景（2026-03-15 時点）
- Full run: 2484 件
- status: success 2027 / partial 427 / failed 30
- graph rank changed: 590
- weak pilot: P@1 0.1884, MRR@10 0.2291, coverage@10 0.3003
- LLM handoff: rerank trigger 26 (1.05%), extraction trigger 781 (31.44%)
- Retrieval 方針（現行）:
  - Occupation: `A + B1`（別実行 + RRF 融合）
  - Skill: `A` のみ（Experience 付与なし）

## タスク
- [ ] 評価スクリプト実装/更新: `script/pipeline_mongo/evaluate_normalization.py`
- [ ] ランキング指標: P@1, P@5, MRR@10, MAP@K, coverage@10
- [ ] フィールド充填率: 全体 + `normalization_status` 別
- [ ] Gold ラベルモード: `--gold-file` 指定で評価
- [ ] Weak ラベルモード: 補助評価として実行（warning 条件付き）
- [ ] セグメント別出力:
  - `normalization_status`（success/partial/failed）
  - `llm_handoff` cohort（rerank/extraction trigger）
  - `match_method`（exact/alt_label/fuzzy/embedding/embedding_b1）
  - category 別（partial/failed 上位カテゴリ）
- [ ] 整合性チェック出力:
  - duplicate source key count
  - missing `candidate_id` count
- [ ] A/B 比較出力:
  - before/after 差分表（absolute delta + relative delta）
- [ ] 出力形式: JSON + Markdown（必要なら CSV も）

## 受け入れ基準
- [ ] 50 件 smoke で全指標とセグメント出力が生成される
- [ ] 全件（`--limit 0`）summary が生成される
- [ ] Gold / Weak の両モードで実行できる
- [ ] A/B 差分表で Occupation と Skill の差分を分離して確認できる
- [ ] 整合性回帰なし（duplicate key=0, missing candidate_id=0）
- [ ] 運用メトリクスを含む（LLM trigger rate、occupation の `embedding_b1` 採用率）

## 関連ファイル
- `script/pipeline_mongo/evaluate_normalization.py`
- `script/pipeline_mongo/normalize_1st_to_mongo.py`
- `docs/issues/Issue13-Plan-Review.md`
- `docs/pipeline/MongoDB-Normalization-Pipeline.md`

## 依存
- Depends on: #12（正規化出力の整合性を前提）
