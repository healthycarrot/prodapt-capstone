# GitHub Issues Draft (Pipeline Improvement)

Repository: healthycarrot/prodapt-capstone
Target area: script/pipeline_mongo

## Issue 1 — ESCO関係グラフで職種再ランキング
**Title**: feat(pipeline): rerank occupation candidates using ESCO occupation-skill graph

**Background**
現状は語彙一致中心で、似た語の別職種が上位に残るケースがある。`skill_candidates` と ESCO `occupation-skill` 関係を使って `occupation_candidates` を再スコアしたい。

**Scope**
- `normalize_1st_to_mongo.py` に occupation-skill relation 読み込みを追加
- `occupation_candidates` 再ランキング関数を追加
- 既存 confidence に graph score を加重合成
- 出力に再ランキング根拠（matched skill count など）を追加

**Acceptance Criteria**
- Top-3 における明らかな誤マッチが減る
- 5件サンプルで `coverage@10` が維持または改善
- 処理時間増加が許容範囲（目安 +20%以内）

**Out of Scope**
- LLM/embedding の導入

---

## Issue 2 — LLM発火条件の強化 + 結果キャッシュ
**Title**: feat(pipeline): tighten LLM rerank trigger and add deterministic cache

**Background**
LLMは高コストのため、曖昧ケースのみで発火すべき。現在は条件が単純。

**Scope**
- `should_use_llm_rerank()` を複合条件化
  - 低信頼
  - 上位僅差
  - 根拠不足（スキル一致不足など）
- 候補セット + resume hash による LLM rerank 結果キャッシュ
- キャッシュヒット率ログ追加

**Acceptance Criteria**
- LLM呼び出し率が低下（目安 < 10%）
- 品質は維持または改善
- 同一入力で同一結果（再現性）

**Out of Scope**
- モデル変更

---

## Issue 3 — 埋め込み再ランキング（Top-Nのみ）
**Title**: feat(pipeline): add embedding rerank for top-N occupation candidates

**Background**
語彙差（パラフレーズ）に弱いケースを補強するため、候補生成は現状維持し、Top-Nのみ埋め込みで再ランキングする。

**Scope**
- `normalize_1st_to_mongo.py` に optional embedding rerank 関数追加
- CLIフラグ追加（enable/disable, model, top-n）
- `requirements.txt` に必要ライブラリ追加

**Acceptance Criteria**
- 5件サンプルで `MRR@10` が改善
- レイテンシ増加は限定的（Top-Nのみ）
- フラグOFF時は現行と同等動作

**Out of Scope**
- 全候補への埋め込み検索

---

## Issue 4 — education抽出のクレンジング専用パス
**Title**: fix(parser): add dedicated education text cleaning pipeline

**Background**
`education.institution` が長文化・ノイズ混入する既知課題がある。

**Scope**
- 区切り記号・住所語・余分句の除去
- degree/institution の抽出規則を強化
- 文字数/語数ガードを追加

**Acceptance Criteria**
- 学校名の長文化が減る
- null率悪化なし
- 5件サンプルで目視品質改善

**Out of Scope**
- 学歴の完全NER化

---

## Issue 5 — 評価ランナー追加（P@5, MRR@10, coverage@10）
**Title**: feat(eval): add evaluation runner for P@5 MRR@10 coverage@10

**Background**
改善の有効性を定量管理するため、反復評価を自動化したい。

**Scope**
- `script/pipeline_mongo` に評価ランナー追加（新規スクリプト）
- 5件反復と全件集計に対応
- 結果を JSON/MD で保存
- `docs/MongoDB-Normalization-Pipeline.md` に実行手順追記

**Acceptance Criteria**
- `P@5`, `MRR@10`, `coverage@10` を出力
- ベースライン比較が可能
- 再実行可能なレポート生成

**Out of Scope**
- 本番ダッシュボード化
