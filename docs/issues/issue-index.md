# Issue Index

GitHub Issue を仕様管理の一次情報源とし、要点をこのファイルに集約する。
最終更新日: 2026-03-17

## 運用ルール
- 作業前に、関連する GitHub Issue をリモートで確認する（`gh issue view/list`）。
- 仕様・方針・受け入れ条件が更新されたら、同じタスク内で本ファイルを更新する。
- `docs/issues/` 配下の旧ファイルは参照元とし、新規の要約は本ファイルへ追記する。

## 現在の主要 Issue（GitHub）
| Issue | 状態 | 要約 |
|---|---|---|
| [#24](https://github.com/healthycarrot/prodapt-capstone/issues/24) | OPEN | FR/PR 全体のトラッカー。 |
| [#15](https://github.com/healthycarrot/prodapt-capstone/issues/15) | OPEN | FR-01: RAG検索と事前ハードフィルタ。 |
| [#16](https://github.com/healthycarrot/prodapt-capstone/issues/16) | OPEN | FR-02: キーワード+ベクトル並列検索と融合。 |
| [#17](https://github.com/healthycarrot/prodapt-capstone/issues/17) | OPEN | FR-03: Cross-encoder 再ランキング。 |
| [#18](https://github.com/healthycarrot/prodapt-capstone/issues/18) | OPEN | FR-04: Agent ベース多面的スコアリング。 |
| [#19](https://github.com/healthycarrot/prodapt-capstone/issues/19) | OPEN | FR-05: 説明可能な結果返却。 |
| [#20](https://github.com/healthycarrot/prodapt-capstone/issues/20) | OPEN | FR-06: API エンドポイント提供。 |
| [#21](https://github.com/healthycarrot/prodapt-capstone/issues/21) | OPEN | FR-07: ガードレール。 |
| [#22](https://github.com/healthycarrot/prodapt-capstone/issues/22) | OPEN | FR-08: 品質評価。 |
| [#23](https://github.com/healthycarrot/prodapt-capstone/issues/23) | OPEN | FR-09: 採用担当者向けフロントエンド。 |
| [#28](https://github.com/healthycarrot/prodapt-capstone/issues/28) | OPEN | FR-06 rollback: `/search` の temporary raw Mongo response 撤去。 |

## 旧 `docs/issues` ファイル統合サマリ

### 1. Pipeline 改善 Draft（旧: `GitHub-Issues-Draft.md`）
- 旧提案の要点:
  - Graph-based Occupation Ranking
  - Embedding Retrieval Integration
  - LLM Candidate Generation
  - Education Extraction Cleanup
  - Evaluation Runner
  - Gold Annotation Workflow
- 方向性メモ:
  - Occupation の LLM rerank は、品質改善に対して latency/cost/ops の負担が大きく、デフォルト方針から外した。
  - 現在の LLM 活用は candidate generation（seed IDs/term expansion）が中心。

### 2. Issue #11/#12 Readiness（旧: `Issue11-12-Review.md`）
- 対象データ: 2484件
- Full-run（Issue #10 出力）:
  - success 2027 (81.6%)
  - partial 427 (17.19%)
  - failed 30 (1.21%)
  - graph rerank applied 1181 (47.54%)
  - graph rank changed 590 (23.75%)
- #11 handoff cohort:
  - rerank trigger 26 (1.05%)
  - extraction trigger 781 (31.44%)
  - 後続方針で LLM rerank は rollback。trigger は診断情報として保持。
- #12 integrity:
  - duplicate upsert key 0
  - missing `candidate_id` 0
  - `source_dataset + source_record_id` の idempotent upsert 方針は有効。
- poor-case ruleization（2ケース）:
  - category short-word expansion（例: `HR -> human resources`）
  - fuzzy misfire guard（低信頼・graph支援なし・anchorなし候補を除外）
  - 方針: 「誤った確信」より「保留」を優先。

### 3. Issue #13 Plan Review（旧: `Issue13-Plan-Review.md`）
- 決定:
  - Occupation retrieval: `A + B1`（別実行 + RRF 融合）
  - Skill retrieval: `A` のみ
  - Gold 評価を最終判断の必須条件とする（weak は補助）
- 根拠（60サンプル A/B）:
  - Occupation 側は `A -> B1` で疑似指標改善
  - Skill 側は `A` が `B1/B2` と比較して同等以上
- 評価 runner の要求:
  - baseline/current 比較
  - `normalization_status` / `llm_handoff` / `match_method` / category セグメント
  - JSON + Markdown + A/B diff
  - integrity 指標（duplicate key, missing candidate_id）
- 受け入れ条件:
  - 50件 smoke と全件（`--limit 0`）で評価成果物が出る
  - gold/weak 両モード実行可能
  - Occupation/Skill 差分を分離して確認できる

### 4. Issue #13 GitHub Issue Body（旧: `Issue13-GitHub-Issue-Body.md`）
- タイトル案:
  - `[Pipeline v2] Step 8: 評価パイプライン`
- 目的:
  - #10 全件結果 + Milvus A/B 検証を踏まえ、運用判断可能な評価パイプラインへ拡張。
- 主要タスク:
  - `evaluate_normalization.py` 実装/更新
  - 指標: P@1/P@5/MRR@10/MAP@K/coverage@10
  - Gold/Weak 評価モード
  - セグメント別出力（status, llm_handoff, match_method, category）
  - 整合性チェック（duplicate key, missing candidate_id）
  - A/B 差分表（absolute/relative delta）
- 依存:
  - #12（正規化出力の整合性）

## 旧 Pipeline Steps（閉鎖済み Issue）参照
| Issue | 状態 | メモ |
|---|---|---|
| [#6](https://github.com/healthycarrot/prodapt-capstone/issues/6) | CLOSED | Pipeline v2 Step 1 |
| [#7](https://github.com/healthycarrot/prodapt-capstone/issues/7) | CLOSED | Pipeline v2 Step 2 |
| [#8](https://github.com/healthycarrot/prodapt-capstone/issues/8) | CLOSED | Pipeline v2 Step 3 |
| [#9](https://github.com/healthycarrot/prodapt-capstone/issues/9) | CLOSED | Pipeline v2 Step 4 |
| [#10](https://github.com/healthycarrot/prodapt-capstone/issues/10) | CLOSED | Pipeline v2 Step 5 |
| [#11](https://github.com/healthycarrot/prodapt-capstone/issues/11) | CLOSED | Pipeline v2 Step 6 |
| [#12](https://github.com/healthycarrot/prodapt-capstone/issues/12) | CLOSED | Pipeline v2 Step 7 |
| [#13](https://github.com/healthycarrot/prodapt-capstone/issues/13) | CLOSED | Pipeline v2 Step 8 |
| [#14](https://github.com/healthycarrot/prodapt-capstone/issues/14) | CLOSED | Pipeline v2 Step 9 |
| [#26](https://github.com/healthycarrot/prodapt-capstone/issues/26) | CLOSED | PR-07 industry multi-level metadata |

## 参照元（統合済み）
- `docs/issues/GitHub-Issues-Draft.md`
- `docs/issues/Issue11-12-Review.md`
- `docs/issues/Issue13-Plan-Review.md`
- `docs/issues/Issue13-GitHub-Issue-Body.md`

## Update Log (2026-03-17): Issue #18 FR-04 Decision Sync
- Source: Issue #18 comment
  - https://github.com/healthycarrot/prodapt-capstone/issues/18#issuecomment-4072696245
- Scope decision:
  - Out of scope for this implementation: `FR-04-04` (occupation match), `FR-04-06` (certification match).
  - In scope: Skill / Experience / Education / Career Progression / Soft Skill + FR-04-09 aggregation.
- Endpoint decision:
  - Keep FR01-03 pipeline as `/retrieve` (after #28 rollback: remove `raw_candidates`).
  - New `/search` calls retrieve-internal result, then runs FR-04 orchestrator and returns integrated ranking.
- Orchestration decision:
  - OpenAI Agent SDK.
  - No handoff.
  - Orchestrator selects agents and runs them via `asyncio.gather()`.
  - Execution unit is candidate batch, not candidate-by-candidate.
  - Partial failure returns partial results; full failure falls back to retrieval ranking.
- Scoring decision:
  - FR-04 overall score is weighted average of executed agents (Skill/Experience emphasized).
  - Final integrated ranking score is weighted blend of retrieval final score and FR-04 overall score.
  - Explanations and score breakdowns from each agent are returned in `/search` response.
- Data and reproducibility:
  - Field naming aligned to real data (`educations`, etc.).
  - If profile fields are sparse, use `resume_text` as fallback evidence within batch scoring.
  - Recency decay is linear; missing date means no recency bonus.
  - Determinism target: few-shot prompt + temperature 0 + fixed JSON schema.
