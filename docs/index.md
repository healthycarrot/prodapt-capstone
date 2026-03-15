# Docs Index

`docs/` 配下のドキュメント一覧と用途です。新規追加・移動時はこのファイルを更新してください。

## 運用ルール
- ドキュメントは用途別フォルダに配置する（`overview/`, `pipeline/`, `schema/`, `issues/`, `reports/`）。
- 実行結果・評価レポートは各カテゴリ直下に最新を置き、旧版は同カテゴリの `old/` に移動する。
- `docs/` 直下に新規ドキュメントを増やさない（例外: `docs/index.md`）。

## overview
| Path | 内容 |
|---|---|
| `docs/overview/AI-Powered Resume Matching System-jp.md` | システム全体像、課題、設計方針を説明する日本語版の提案/解説ドキュメント。 |
| `docs/overview/AI-Powered Resume Matching System.pdf` | 上記の配布用PDF。 |
| `docs/overview/Resume-Dataset-Comparison-jp.md` | 1st〜5thデータセット比較、用途別の推奨使い分け。 |

## pipeline
| Path | 内容 |
|---|---|
| `docs/pipeline/MongoDB-Normalization-Pipeline.md` | `source_1st_resumes` から `normalized_candidates` までの現行正規化パイプライン仕様。 |
| `docs/pipeline/Issue6-Script-IO-Map.md` | Issue #6以降の主要スクリプトの入力/出力/永続化先の対応表。 |

## schema
| Path | 内容 |
|---|---|
| `docs/schema/dbdiagram.dbml` | 全体スキーマ定義（DBML）。 |
| `docs/schema/dbdiagram.dbdiagram` | 全体スキーマの dbdiagram 用定義。 |
| `docs/schema/dbdiagram.raw.dbml` | rawコレクション相当のスキーマ定義（DBML）。 |
| `docs/schema/dbdiagram.raw.dbdiagram` | rawスキーマの dbdiagram 用定義。 |
| `docs/schema/dbdiagram.normalized.dbml` | normalizedコレクション相当のスキーマ定義（DBML）。 |
| `docs/schema/dbdiagram.normalized.dbdiagram` | normalizedスキーマの dbdiagram 用定義。 |
| `docs/schema/field-mapping.md` | HTMLセクションから各正規化フィールドへ落とし込む抽出・対応表。 |
| `docs/schema/normalized-candidates-mapping.md` | `normalized_candidates` の実装準拠マッピング（トップレベル/候補配列の意味）。 |

## issues
| Path | 内容 |
|---|---|
| `docs/issues/Issue11-12-Review.md` | Issue #11/#12 の readiness・整合性レビュー。 |
| `docs/issues/Issue13-Plan-Review.md` | Issue #13 の計画見直しと評価方針。 |
| `docs/issues/Issue13-GitHub-Issue-Body.md` | Issue #13 用の GitHub issue 本文案。 |
| `docs/issues/GitHub-Issues-Draft.md` | パイプライン改善向け Issue 起票案の草稿。 |

## reports/llm
| Path | 内容 |
|---|---|
| `docs/reports/llm/LLM-Eval-Issue14-v2-Custom-10samples-20260316.md` | Issue14 v2（LLM候補生成）を対象にした代表10件の LLM 評価レポート。 |
| `docs/reports/llm/LLM-Eval-10samples-20260316-Latest.md` | 代表10件の最新 LLM 評価結果。 |
| `docs/reports/llm/old/LLM-Eval-10samples.md` | 初回版の LLM 評価レポート（旧版）。 |
| `docs/reports/llm/old/LLM-Eval-10samples-after-guardrail.md` | guardrail 適用後の LLM 評価レポート（旧版）。 |
| `docs/reports/llm/old/LLM-Eval-10samples-post-rerun.md` | 再実行後の LLM 評価レポート（旧版）。 |

## reports/normalization
| Path | 内容 |
|---|---|
| `docs/reports/normalization/Eval-Normalization-Issue13-20-Weak-After-Target-Refresh.md` | 20件 weak 評価（ターゲット更新後）の現行参照結果。 |
| `docs/reports/normalization/Eval-AB20-With-LLM-Weak.md` | AB20（LLMあり） weak 評価レポート。 |
| `docs/reports/normalization/Eval-AB20-No-LLM-Weak.md` | AB20（LLMなし） weak 評価レポート。 |
| `docs/reports/normalization/old/Eval-Normalization-Issue13-20-Weak-Latest.md` | 20件 weak の旧版（refresh前）。 |
| `docs/reports/normalization/old/Eval-Normalization-Issue13-Full-Weak-20260315.md` | 全件 weak 評価（2026-03-15時点）の履歴。 |
| `docs/reports/normalization/old/Eval-Normalization-Issue13-Gold-200-PreHuman.md` | Gold 200件の pre-human 評価履歴。 |
| `docs/reports/normalization/old/Eval-Normalization-Issue13-Gold-50-PreHuman.md` | Gold 50件の pre-human 評価履歴。 |
| `docs/reports/normalization/old/Eval-Normalization-Issue13-Smoke50.md` | 50件 smoke 評価の履歴。 |

## reports/retrieval
| Path | 内容 |
|---|---|
| `docs/reports/retrieval/Milvus-Retrieval-Samples.md` | Milvus 検索サンプル可視化（代表サンプル）。 |
| `docs/reports/retrieval/Milvus-AB-Experience-Comparison.md` | A/B/B1/B2 系の Milvus 検索比較結果。 |
