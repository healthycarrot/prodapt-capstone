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
| [#30](https://github.com/healthycarrot/prodapt-capstone/issues/30) | OPEN | FR-06/FR-09 実装Issue: ESCO suggest API と frontend hard filter 候補制約（`/search` 契約維持）。 |

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

## Update Log (2026-03-17): Issue #18 Education Agent Trigger Decision
- Source: Issue #18 comment
  - https://github.com/healthycarrot/prodapt-capstone/issues/18#issuecomment-4072714986
- Decision:
  - Education Agent trigger source is `OrchestratorAgent` (not `query_normalizer`).
  - OrchestratorAgent analyzes user query with LLM (few-shot) and decides whether education requirements are present.
  - Education Agent is executed only when that Orchestrator decision is true.

## Update Log (2026-03-17): Issue #18 Implementation Sync
- Source: Issue #18 comment
  - https://github.com/healthycarrot/prodapt-capstone/issues/18#issuecomment-4072839134
- Implementation status:
  - Added `/retrieve` (FR-01..03) and moved integrated agent flow to `/search`.
  - Applied #28 rollback alignment (`raw_candidates` removal and temp route removal).
  - Added orchestrator + multi-agent scoring service (OpenAI Agent SDK based).
  - Added FR-04 score aggregation and final score integration into search ranking.
  - Added API response explainability fields (summary, breakdown, gaps).
  - Added/updated backend tests for `/retrieve` and `/search`.

## Update Log (2026-03-17): Issue #21 FR-07 Requirements Detailing Draft
- Source: Issue #21 comment
  - https://github.com/healthycarrot/prodapt-capstone/issues/21#issuecomment-4072770791
- Related issues checked:
  - #20 (FR-06 API contract), #24 (tracker), #26 (industry metadata), #28 (temporary response rollback), #18 (FR-04 orchestration)
- Draft scope alignment:
  - Guardrail application points are fixed as:
    - request input stage (`FR-07-01`)
    - normalization pipeline validation stage (`FR-07-02`)
    - metadata filtering stage + pre-response re-check (`FR-07-03`)
    - final response pre-return audit (`FR-07-04`)
- Draft contract highlights:
  - `FR-07-01`:
    - define non-natural-language / too-short / too-long / inappropriate-input handling
    - keep existing response style: HTTP `200` + `retry_required=true` + `results=[]` + required conflict metadata
  - `FR-07-02`:
    - define PASS/WARN/FAIL by section presence and consistency checks
    - FAIL records are excluded from serving publish; WARN records are kept with warnings
  - `FR-07-03`:
    - explicit API filters are primary, extracted filters are supplemental
    - OR within same filter category, AND across categories/scalars
    - industry filtering uses `industry_esco_ids_json` intersection (no new dependency on legacy single-value field)
  - `FR-07-04`:
    - audit both ranking rationale text and explanation text for prohibited attributes/proxies
    - explanation-only violation: sanitize explanation + warning
  - ranking-rationale violation: fallback to retrieval ranking + warning
  - persist reviewable audit logs (`request_id`, `candidate_id`, `rule_id`, `detected_text_hash`, `action`, `timestamp`)

## Update Log (2026-03-17): Issue #18 Agent Score Determinism Sync
- Source: local implementation update for #18
- Decision and implementation:
  - Agent `score` is now recomputed server-side from `breakdown` instead of trusting LLM-returned `score`.
  - Deterministic formulas are applied per agent:
    - skill_match: weighted sum of `match_score`, `skill_depth_score`, `management_score` using orchestrator weights.
    - experience_match: weighted base (`industry_match_score`, `experience_level_match_score`) + linear recency bonus.
    - education_match: `education_match_score`.
    - career_progression: average of `vertical_growth_score` and `scope_expansion_score`.
    - soft_skill: average of `communication_score`, `teamwork_score`, `adaptability_score`.
- Validation:
  - Added unit tests for recompute formulas.
  - Verified `/search` response now returns scores consistent with breakdown-based formulas.

## Update Log (2026-03-17): Issue #15 Query Normalizer Fuzzy Score Safety Fix
- Source: local implementation update for #15 (`FR-01-03-01/02/03` quality hardening)
- Decision and implementation:
  - Fixed lexical fuzzy score merge in `backend/app/repositories/esco_lexical_repo.py`.
  - Replaced `merged_score = max(confidence, repo_match.score)` with
    `merged_score = min(confidence, repo_match.score)`.
  - This prevents fuzzy candidates from being artificially promoted to high confidence
    due to lexical base scores (`0.98` / `0.87`).
- Validation:
  - Added unit tests in `backend/tests/test_esco_lexical_repo.py`.
  - Verified test suite passes after the change.

## Update Log (2026-03-17): Issue #16 Mongo Keyword Filter Fallback for Scalar Fields
- Source: local implementation update for #16 (`FR-02` keyword path stability)
- Decision and implementation:
  - Updated `backend/app/services/hard_filter_compiler.py` so Mongo `$text` path no longer applies
    `experience_months_total` and `highest_education_level_rank` constraints.
  - Milvus-side hard filter behavior is unchanged and continues to apply experience/education scalar filters.
- Reason:
  - `normalized_candidates` does not store those scalar fields, and applying them on Mongo caused
    keyword path false-zero outcomes.
- Validation:
  - Extended `backend/tests/test_hard_filter_compiler.py` with Milvus-only expectation for
    experience/education conditions.
  - Verified backend tests pass.

## Update Log (2026-03-17): Issue #23 FR-09 MVP Frontend Implementation
- Related issues checked:
  - #23 (FR-09 frontend requirement)
  - #24 (requirements tracker)
  - #19 (explainable response expectation)
  - #20 (API endpoint contract)
- Scope decisions for this task:
  - Implement frontend MVP under `/frontend` using React + TypeScript + MUI.
  - Keep initial scope to search list UI only (candidate detail page deferred to a next phase).
  - Expose all `/search` hard-filter fields in the UI (`skill_terms`, `occupation_terms`, `industry_terms`, `experience`, `education`, `locations`, `limit`).
  - Use English UI copy.
  - Use backend endpoint `http://localhost:8000/search` via Vite dev proxy (`/api/search`).
- Implementation summary:
  - Added industrial-style search console UI with input panel and response panel.
  - Added API client integration for `POST /search` with loading/error/empty state handling.
  - Added ranking card rendering for scores, recommendation summary, matches, gaps, and agent score chips.

## Update Log (2026-03-17): Issue #23 FR-09 Score Detail Modal Update
- Related issues checked:
  - #23 (FR-09 frontend)
  - #24 (requirements tracker)
- Scope update for this task:
  - Added per-candidate modal UI to inspect score details.
  - Modal now shows score breakdown and reason text for each agent score.
  - Core score values (final/retrieval/FR-04/keyword/vector/fusion/cross-encoder) are shown in one section.
  - Updated page title text from `Industrial Candidate Search Interface` to `Candidate Search Interface`.
- Notes:
  - API reason text is currently available on agent score entries; core metrics remain numeric outputs.

## Update Log (2026-03-17): Issue #23 Frontend Runtime Stability Fix (Search Repeat)
- Trigger:
  - Re-running search caused frontend crash with `NotFoundError` (`insertBefore` on Node).
- Stability updates applied:
  - Score detail dialog changed to always-mounted mode (`keepMounted`) with `open` state control.
  - Candidate/detail lists now use collision-safe keys (index fallback appended).
  - Search execution no longer clears `responseData` before response arrives (reduced mount/unmount churn).
  - Dialog open state separated from selected candidate state to avoid abrupt portal teardown.
- Validation:
  - `frontend` lint/build passed after the fix.

## Update Log (2026-03-17): Issue #23 Additional UI Crash Hardening (insertBefore NotFoundError)
- Trigger:
  - Re-running search still occasionally raised `NotFoundError: Failed to execute 'insertBefore' on 'Node'` in React dev runtime.
- Additional hardening:
  - Disabled portal behavior for `Dialog` and all `Autocomplete` components (`disablePortal`) to avoid cross-root DOM insertion conflicts.
  - Removed React `StrictMode` wrapper in frontend entry (`src/main.tsx`) to avoid dev double-commit side effects around dynamic UI trees.
  - Added `notranslate` hints in `frontend/index.html` (`translate="no"` + `meta google notranslate`) to reduce browser translation DOM mutations.
- Validation:
  - `frontend` lint/build passed after the changes.

## Update Log (2026-03-17): Issue #19/#20 Contract Decision Sync (`/search` Consolidation)
- Source:
  - https://github.com/healthycarrot/prodapt-capstone/issues/19#issuecomment-4073626898
  - https://github.com/healthycarrot/prodapt-capstone/issues/20#issuecomment-4073625972
- Decision:
  - `FR-06-04` / `FR-06-04-01` are interpreted as fulfilled by `/search` response payload.
  - Dedicated ranking-rationale endpoint is out of scope.
  - `FR-05-03-02` / `FR-05-03-03` remain required but are fulfilled in `/search` response contract.
  - `FR-06-03` (candidate detail API) and `FR-05-07` (raw resume data API) remain separate required endpoints.

## Update Log (2026-03-17): Issue #20 FR-06-03 Candidate Detail API Implementation
- Source:
  - https://github.com/healthycarrot/prodapt-capstone/issues/20#issuecomment-4073753361
- Implemented:
  - Added `GET /candidates/{candidate_id}` endpoint.
  - Input validation uses UUID path parameter (`422` on invalid format).
  - Returns normalized candidate detail fields:
    - `candidate_id`
    - `source_dataset`
    - `source_record_id`
    - `current_location`
    - `category`
    - `resume_text`
    - `occupation_candidates`
    - `skill_candidates`
    - `experiences`
    - `educations`
  - `404` is returned when target candidate does not exist.
- Files:
  - `backend/app/api/routes/candidates.py`
  - `backend/app/api/schemas/candidate.py`
  - `backend/app/repositories/mongo_repo.py`
  - router/schema exports updated.
- Validation:
  - Added API tests: `backend/tests/test_candidate_detail_api.py` (`200/404/422`).

## Update Log (2026-03-17): Issue #19 FR-05-07 Raw Resume API Implementation
- Source:
  - https://github.com/healthycarrot/prodapt-capstone/issues/19#issuecomment-4073773744
- Implemented:
  - Added `GET /candidates/{candidate_id}/resume` endpoint.
  - Response fields:
    - `candidate_id`
    - `source_dataset`
    - `source_record_id`
    - `resume_text`
  - Data source policy:
    - primary: `normalized_candidates`
    - if resolvable, `source_1st_resumes.resume_text` is used via `source_dataset + source_record_id` lookup
    - fallback: `normalized_candidates.resume_text`
  - Error policy:
    - `422` for invalid UUID path parameter
    - `404` when candidate is not found
- Files:
  - `backend/app/api/routes/candidates.py`
  - `backend/app/api/schemas/candidate.py`
  - `backend/app/repositories/mongo_repo.py`
  - `backend/tests/test_candidate_detail_api.py`
- Validation:
  - Resume endpoint tests added (`200/404/422`) in `backend/tests/test_candidate_detail_api.py`.

## Update Log (2026-03-17): Issue #23 Frontend Detail Modal Integration (`/candidates` + `/resume`)
- Source:
  - https://github.com/healthycarrot/prodapt-capstone/issues/23#issuecomment-4073842200
- Implemented:
  - Added `View Detail` button on each search result card.
  - Added a larger detail modal (`maxWidth=lg`, `minHeight≈78vh`).
  - Detail modal concurrently calls:
    - `GET /candidates/{candidate_id}`
    - `GET /candidates/{candidate_id}/resume`
  - Modal renders:
    - structured profile summary
    - occupation/skill candidates
    - experiences
    - educations
    - raw resume text
  - Existing `View Score Details` modal remains available.
- Files:
  - `frontend/src/App.tsx`
  - `frontend/src/api.ts`
  - `frontend/src/types.ts`
- Validation:
  - `npm run lint` passed.
  - `npm run build` passed.

## Update Log (2026-03-17): Issue #30 ESCO Suggest API + Frontend Hard Filter Constraint Planning
- Related issues checked:
  - #15 (FR-01 hard filter / ESCO normalization)
  - #20 (FR-06 API endpoint contract)
  - #23 (FR-09 frontend requirement)
  - #24 (requirements tracker)
- New implementation issue:
  - https://github.com/healthycarrot/prodapt-capstone/issues/30
- Scope decision for this issue:
  - Add backend ESCO suggest API for `skill` / `occupation` / `industry`.
  - Constrain frontend hard-filter selection to ESCO-backed autocomplete candidates only.
  - Keep `/search` external request contract unchanged in this phase:
    - continue using `skill_terms`
    - continue using `occupation_terms`
    - continue using `industry_terms`
  - Frontend stores selected ESCO options as `{ esco_id, label }` internally, but posts `label[]` to `/search`.
  - Backend must re-validate explicit filter labels against ESCO lexical data and reject invalid values with `422`.
- Non-goals recorded in the issue:
  - no `*_esco_ids` added to `/search` in this phase
  - no query-understanding contract change
  - no ranking / rerank / agent-scoring behavior change
- Suggest API spec recorded in the issue:
  - `GET /esco/suggest`
  - query params:
    - `domain=skill|occupation|industry`
    - `q`
    - optional `limit` (default `10`, max `20`)
  - response envelope includes:
    - `domain`
    - `query`
    - `results[]`
  - each result contains:
    - `esco_id`
    - `label`
  - result ordering policy:
    - exact preferred label
    - exact alt label
    - prefix/substring lexical match
    - fuzzy lexical match
  - suggest path stays lexical-only for now (no embedding search)
- Frontend behavior spec recorded in the issue:
  - remove `freeSolo` from skill / occupation / industry autocomplete
  - keep multiple selection
  - add debounce (`250-300ms` recommended)
  - add short-lived in-memory cache keyed by `domain + query`
  - keep `disablePortal`
- Acceptance criteria recorded in the issue:
  - UI no longer accepts arbitrary text in ESCO-backed hard-filter fields
  - `/search` body shape remains unchanged
  - frontend-selected ESCO labels succeed through `/search`
  - direct `/search` calls with invalid non-ESCO labels are rejected
  - `query_text` natural-language extraction continues unchanged
