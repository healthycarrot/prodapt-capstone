# Issue Index

GitHub Issue を仕様管理の一次情報源とし、要点をこのファイルに集約する。
最終更新日: 2026-03-18

## 運用ルール
- 作業前に、関連する GitHub Issue をリモートで確認する（`gh issue view/list`）。
- 仕様・方針・受け入れ条件が更新されたら、同じタスク内で本ファイルを更新する。
- `docs/issues/` 配下の旧ファイルは参照元とし、新規の要約は本ファイルへ追記する。

## 現在の主要 Issue（GitHub）
| Issue | 状態 | 要約 |
|---|---|---|
| [#24](https://github.com/healthycarrot/prodapt-capstone/issues/24) | OPEN | FR/PR 全体のトラッカー。 |
| [#15](https://github.com/healthycarrot/prodapt-capstone/issues/15) | CLOSED | FR-01: RAG検索と事前ハードフィルタ。 |
| [#16](https://github.com/healthycarrot/prodapt-capstone/issues/16) | CLOSED | FR-02: キーワード+ベクトル並列検索と融合。 |
| [#17](https://github.com/healthycarrot/prodapt-capstone/issues/17) | CLOSED | FR-03: Cross-encoder 再ランキング。 |
| [#18](https://github.com/healthycarrot/prodapt-capstone/issues/18) | CLOSED | FR-04: Agent ベース多面的スコアリング。 |
| [#19](https://github.com/healthycarrot/prodapt-capstone/issues/19) | CLOSED | FR-05: 説明可能な結果返却。 |
| [#20](https://github.com/healthycarrot/prodapt-capstone/issues/20) | CLOSED | FR-06: API エンドポイント提供。 |
| [#21](https://github.com/healthycarrot/prodapt-capstone/issues/21) | CLOSED | FR-07: ガードレール（2026-03-18 時点で pragmatic scope でクローズ）。 |
| [#22](https://github.com/healthycarrot/prodapt-capstone/issues/22) | OPEN | FR-08: 品質評価。初回実装スコープは `Faithfulness` / `AnswerRelevancy` / `ContextualPrecision` / `ContextualRelevancy` / `GEval(Skill Coverage, Experience Fit)` / `Bias`。 |
| [#23](https://github.com/healthycarrot/prodapt-capstone/issues/23) | OPEN | FR-09: 採用担当者向けフロントエンド。 |
| [#28](https://github.com/healthycarrot/prodapt-capstone/issues/28) | OPEN | FR-06 rollback: `/search` の temporary raw Mongo response 撤去。 |
| [#30](https://github.com/healthycarrot/prodapt-capstone/issues/30) | OPEN | FR-06/FR-09 実装Issue: ESCO suggest API と frontend hard filter 候補制約（`/search` 契約維持）。 |
| [#31](https://github.com/healthycarrot/prodapt-capstone/issues/31) | OPEN | FR-09/FR-05 実装Issue: `View Score Details` の各スコアへ `i` マークで固定算出ロジック表示。 |
| [#32](https://github.com/healthycarrot/prodapt-capstone/issues/32) | OPEN | FR-01/FR-06 implementation issue: add default DI wiring for QueryUnderstanding / QueryBuilder LLM. |

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

## Update Log (2026-03-17): Issue #21 Minimal Implementation Plan (FR-07-01 / FR-07-04)
- Source: Issue #21 comment
  - https://github.com/healthycarrot/prodapt-capstone/issues/21#issuecomment-4073989892
- Related issues checked:
  - #20, #24, #28
- Scope decision:
  - In scope (minimum implementation): `FR-07-01` and `FR-07-04` only.
  - Out of scope in this step: `FR-07-02`, `FR-07-03`.
- Planned implementation placement:
  - `FR-07-01`:
    - API shape/range validation remains at request mapper.
    - semantic input guardrail is added at retrieval pipeline entry as a dedicated service.
    - violation response reuses existing conflict contract (`retry_required=true`, `results=[]`).
  - `FR-07-04`:
    - output audit step is inserted in search orchestration before API response mapping.
    - explanation-only violation -> sanitize explanation + warning.
    - ranking-rationale violation -> disable FR-04 contribution and fallback to retrieval ranking.
    - reviewable audit logs are persisted via Mongo repository.
- Planned execution order:
  - contract definitions -> FR-07-01 implementation -> FR-07-04 implementation -> audit log persistence -> API warning field extension -> unit/integration tests -> docs sync.

## Update Log (2026-03-17): Issue #21 Step 1 Contract Implementation Sync
- Source: Issue #21 comment
  - https://github.com/healthycarrot/prodapt-capstone/issues/21#issuecomment-4074067641
- Implemented (contract definitions only):
  - Domain DTOs for FR-07 (`GuardrailWarning`, `InputGuardrailResult`, `OutputAuditLogEntry`, `OutputAuditResult`).
  - No-op service contracts:
    - `InputGuardrailService`
    - `OutputAuditService`
    - `GuardrailAuditLogRepo` protocol
  - API response schema extension:
    - added `warnings` surfaces to retrieve/search response models.
  - Config/env contract extension:
    - guardrail toggles/thresholds/template settings.
    - Mongo audit log collection setting.
  - Mongo repository contract:
    - `insert_guardrail_audit_logs(...)` method.
- Validation:
  - Syntax compile checks passed.
  - New service import/runtime smoke passed.
  - Full pytest run was blocked by local runtime dependency mismatch (`pydantic_core` import error).
- Scope note:
  - Step 1 did not add runtime guardrail behavior yet (no input blocking/sanitize/fallback execution yet).

## Update Log (2026-03-17): Issue #21 Step 2 FR-07-01 Runtime Wiring Sync
- Source: Issue #21 comment
  - https://github.com/healthycarrot/prodapt-capstone/issues/21#issuecomment-4074144741
- Implemented scope:
  - FR-07-01 runtime logic is now wired at retrieval pipeline entry.
- Implementation details:
  - `InputGuardrailService` now evaluates:
    - query length bounds
    - non-natural-language input heuristics
    - inappropriate content checks (config-based prohibited terms + contact info pattern)
    - required role/skill information checks (pre/post-understanding phases)
    - non-blocking warning generation for missing optional hints
  - `RetrievalPipelineService.run()` now executes:
    - pre-guardrail check before query understanding
    - post-guardrail check after query understanding
    - early return via conflict contract on violation (`retry_required=true`, empty results)
  - DI update:
    - retrieval pipeline now receives configured input guardrail service.
- Validation:
  - Added unit tests:
    - `backend/tests/test_input_guardrail.py`
    - `backend/tests/test_retrieval_pipeline_guardrail.py`
  - Executed unittest run for those files; all tests passed.
- Scope boundary:
  - FR-07-04 output audit wiring is not included in this step.

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

## Update Log (2026-03-17): Issue #30 Implementation Sync
- Source:
  - https://github.com/healthycarrot/prodapt-capstone/issues/30
  - https://github.com/healthycarrot/prodapt-capstone/issues/30#issuecomment-4074057122
- Implemented:
  - Added `GET /esco/suggest` endpoint with query params:
    - `domain=skill|occupation|industry`
    - `q`
    - `limit` (`1..20`, default `10`)
  - Added ESCO suggest response contract:
    - `domain`
    - `query`
    - `results[]` with `{ esco_id, label }`
  - Extended lexical repository with suggest path:
    - exact preferred label
    - exact alt label
    - prefix/substring lexical match
    - fuzzy lexical match (fallback)
  - Kept `/search` contract unchanged (`skill_terms` / `occupation_terms` / `industry_terms` remain `list[str]`).
  - Added backend re-validation for explicit ESCO filter labels on `/search` and `/retrieve`:
    - valid when exact/alt lexical match exists
    - invalid labels return `422`
  - Updated frontend hard-filter UI:
    - replaced static skill/occupation/industry options with remote ESCO autocomplete
    - removed `freeSolo` on those three fields
    - keep selected values internally as `{ esco_id, label }`
    - map to `label[]` when posting `/search`
    - added debounce + short-lived frontend cache via suggest API client
- Files:
  - `backend/app/api/routes/esco.py`
  - `backend/app/api/routes/_request_mapper.py`
  - `backend/app/api/routes/search.py`
  - `backend/app/api/routes/retrieve.py`
  - `backend/app/api/routes/__init__.py`
  - `backend/app/api/schemas/esco.py`
  - `backend/app/api/schemas/__init__.py`
  - `backend/app/api/__init__.py`
  - `backend/app/repositories/esco_lexical_repo.py`
  - `backend/tests/test_esco_api.py`
  - `backend/tests/test_esco_lexical_repo.py`
  - `backend/tests/test_search_api.py`
  - `backend/tests/test_retrieve_api.py`
  - `frontend/src/types.ts`
  - `frontend/src/api.ts`
  - `frontend/src/App.tsx`
  - `docs/test/Search-API-RequestBody-Samples.md`

## Update Log (2026-03-17): Issue #31 Score Logic Info UI Planning
- Source:
  - https://github.com/healthycarrot/prodapt-capstone/issues/31
- Scope decision:
  - Add `i` info markers in `View Score Details` modal for:
    - core scores (`Final`, `Retrieval`, `FR-04`, `Keyword`, `Vector`, `Fusion`, `Cross Encoder`)
    - per-agent scores
    - breakdown rows (e.g. `match_score`, `management_score`)
  - Do not show `i` for failed / not executed / not displayed scores.
- Display policy:
  - Show fixed formulas and fixed logic text only (no runtime dynamic values in tooltip/popover).
  - Keep English keys as-is (no key localization).
  - Include FR-04 explanation that only executed agents are used and weights are re-normalized.
- API policy:
  - No API contract change or response field addition; frontend-only implementation.
- Risk note:
  - Because formulas are fixed copy, future config/weight/strategy changes can cause UI-text drift; accepted in issue scope.

## Update Log (2026-03-17): FR-01..FR-06 Issue Closure Sync (#15..#20)
- Source:
  - https://github.com/healthycarrot/prodapt-capstone/issues/15#issuecomment-4074093834
  - https://github.com/healthycarrot/prodapt-capstone/issues/16#issuecomment-4074096371
  - https://github.com/healthycarrot/prodapt-capstone/issues/17#issuecomment-4074096370
  - https://github.com/healthycarrot/prodapt-capstone/issues/18#issuecomment-4074096392
  - https://github.com/healthycarrot/prodapt-capstone/issues/19#issuecomment-4074099077
  - https://github.com/healthycarrot/prodapt-capstone/issues/20#issuecomment-4074099082
- Status update:
  - Closed as `completed`: #15, #16, #17, #18, #19, #20.
- Closure assumptions accepted in this task:
  - FR-04 closure follows Issue #18 scope decision:
    - out of scope: `FR-04-04` (occupation match), `FR-04-06` (certification match).
  - FR-05 closure accepts current `/search` explanation schema as sufficient for this phase.
- Validation evidence attached in closure comments:
  - backend test run: `python -m unittest discover -s tests -v` (30 passed, 1 skipped live test).

## Update Log (2026-03-18): Issue #21 Step 3 FR-07-04 Output Audit Wiring Sync
- Source:
  - https://github.com/healthycarrot/prodapt-capstone/issues/21#issuecomment-4074210194
- Related issues checked:
  - #21 (FR-07 guardrail)
  - #20 (FR-06 API contract)
  - #24 (tracker)
- Implemented scope:
  - FR-07-04 output audit is now connected before `/search` response return.
- Implementation details:
  - `backend/app/services/output_audit.py`:
    - detects prohibited attributes/proxy terms in `recommendation_summary` and `agent_scores[*].reason`
    - explanation-only violation: sanitize summary + warning + audit log
    - ranking-rationale violation: sanitize reason + retrieval fallback marker + warning + audit log
  - `backend/app/services/search_orchestration.py`:
    - calls output audit after FR-04 aggregation
    - applies sanitize targets to summary/reason fields
    - applies retrieval fallback for flagged candidates:
      - `final_score = retrieval_final_score`
      - `fr04_overall_score = 0.0`
      - append `output_audit_retrieval_fallback_applied` to `agent_errors`
    - reranks final list and recalculates `rank`
    - returns warnings at response-level and candidate-level
    - persists audit logs via repository when available
  - `backend/app/repositories/mongo_repo.py`:
    - added `insert_guardrail_audit_logs(...)`
    - writes to configurable `MONGO_GUARDRAIL_AUDIT_COLLECTION`
  - `backend/app/core/dependencies.py`:
    - injects `OutputAuditService` and Mongo audit log repository into search orchestration
  - `backend/app/api/routes/search.py`:
    - maps orchestration warnings into API response schema
- Validation:
  - Added tests:
    - `backend/tests/test_output_audit.py`
    - `backend/tests/test_search_orchestration_output_audit.py`
  - Executed:
    - `python -m unittest tests.test_output_audit tests.test_search_orchestration_output_audit tests.test_search_api tests.test_retrieve_api tests.test_input_guardrail tests.test_retrieval_pipeline_guardrail -v`
  - Result:
    - 19 passed
- Scope note:
  - FR-07-02 / FR-07-03 remain out of scope in this minimum implementation step.



## Update Log (2026-03-18): Issue #32 QueryUnderstanding / QueryBuilder LLM DI Wiring Planning
- Source:
  - https://github.com/healthycarrot/prodapt-capstone/issues/32
- Related issues checked:
  - #24 (tracker)
  - #20 (FR-06 API)
  - #15 (FR-01 retrieval baseline)
- Problem statement:
  - Retrieval pre-stage DI currently wires:
    - `QueryUnderstandingService(llm_client=None)`
    - `QueryBuilderService(rephraser=None)`
  - As a result, extraction/rewrite behavior remains rule-based by default even when OpenAI model settings exist.
- Planned scope:
  - Add DI wiring for query understanding and query builder LLM clients.
  - Keep fallback behavior when API key/model is missing.
  - Add feature-flag based ON/OFF and basic observability for fallback reasons.
  - Keep `/retrieve` and `/search` response contracts unchanged.
- Acceptance criteria snapshot:
  - LLM path works when OpenAI config is present.
  - Existing non-LLM path remains backward-compatible when config is absent.
  - Tests cover both LLM and fallback paths.

## Update Log (2026-03-18): Issue #21 Closure Decision (Pragmatic Scope Compromise)
- Source:
  - https://github.com/healthycarrot/prodapt-capstone/issues/21
- Status update:
  - Issue #21 is closed.
- Accepted closure scope:
  - Implemented/accepted:
    - `FR-07-01` input guardrail
    - `FR-07-04` output audit (sanitize, retrieval fallback, audit logging)
  - Explicitly compromised in this phase:
    - strict `FR-07-02` / `FR-07-03` execution as originally drafted
    - full PASS/WARN/FAIL validation contract and hard publish-gating exclusion
- Agreed substitute for this phase:
  - parse/extract stage monitoring and error counting
  - normalization status classification (`success` / `partial` / `failed`)
- Risk note:
  - strict validation/gating is deferred; low-quality records may still pass serving paths.
  - if quality regressions are observed, reopen FR-07 via dedicated hardening issue.

## Update Log (2026-03-18): Issue #22 FR-08 Initial Metric Scope Decision
- Source:
  - https://github.com/healthycarrot/prodapt-capstone/issues/22#issuecomment-4074357095
- Related issues checked:
  - #22 (FR-08 quality evaluation)
  - #24 (tracker)
  - #19 (FR-05 explainable results)
- Scope decision:
  - First implementation slice for FR-08 uses the following metric set:
    - `FaithfulnessMetric`
    - `AnswerRelevancyMetric`
    - `ContextualPrecisionMetric`
    - `ContextualRelevancyMetric`
    - `GEval` for `Skill Coverage`
    - `GEval` for `Experience Fit`
    - `BiasMetric`
- Evaluation target mapping:
  - `/search`:
    - evaluate `recommendation_summary` grounding and relevance
    - primary metrics:
      - `FaithfulnessMetric`
      - `AnswerRelevancyMetric`
      - `GEval(Skill Coverage)`
      - `GEval(Experience Fit)`
      - `BiasMetric`
  - `/retrieve`:
    - evaluate retrieval/ranking quality before FR-04 explanation generation
    - primary metrics:
      - `ContextualPrecisionMetric`
      - `ContextualRelevancyMetric`
- Requirement alignment snapshot:
  - `FR-08-02`: covered in this slice
  - `FR-08-03`: first implementation via `GEval(Skill Coverage)`
  - `FR-08-04`: first implementation via `GEval(Experience Fit)`
  - bias-evaluation intent from advanced requirements: covered in this slice via `BiasMetric`
- Deferred from this slice:
  - `FR-08-02-01` / `FR-08-02-02`: diversity metrics
  - `FR-08-05` / `FR-08-05-01`: culture fit / soft-skill fit metric
  - `FR-08-06`: baseline vs improved comparison harness
  - `FR-08-07`: full reporting output layer
  - `FR-08-08`: final quality-threshold judgment workflow
  - `ContextualRecallMetric`: deferred until stable expected-output / gold data is prepared
- Rationale:
  - This slice balances:
    - recommendation grounding / hallucination control
    - query-to-explanation relevance
    - retrieval ranking quality
    - hiring-specific custom evaluation
    - bias detection in generated explanations

## Update Log (2026-03-18): Issue #21 Guardrail Minimum-Term Requirement Relaxed
- Source:
  - https://github.com/healthycarrot/prodapt-capstone/issues/21#issuecomment-4074506165
- Related issues checked:
  - #21 (FR-07 guardrail)
  - #20 (FR-06 API contract)
  - #23 (FR-09 frontend behavior)
  - #24 (requirements tracker)
- Decision:
  - `skill_terms` / `occupation_terms` are no longer a minimum required condition for `FR-07-01`.
  - `/search` and `/retrieve` may run with `query_text` only.
  - Existing guardrail checks for query quality/safety remain active.
  - Explicit ESCO filters remain optional, but when provided they are still validated and prioritized.
- Implementation sync:
  - changed the input-guardrail default so the minimum-term rule is OFF unless explicitly re-enabled by config
  - updated API tests to cover requests without `skill_terms` / `occupation_terms`
  - updated request-body samples to show `query_text`-only search as valid
- Contract note:
  - conflict response contract is unchanged and still applies only to real guardrail/conflict cases (`HTTP 200`, `retry_required=true`, `results=[]`)

## Update Log (2026-03-18): Issue #22 FR-08 DeepEval Harness Implementation Sync
- Source:
  - https://github.com/healthycarrot/prodapt-capstone/issues/22#issuecomment-4074992282
- Implemented files:
  - `backend/tests/eval_harness.py`
  - `backend/tests/fixtures/search_eval_cases.json`
  - `backend/tests/test_retrieve_quality_eval.py`
  - `backend/tests/test_search_quality_eval.py`
  - `backend/tests/test_eval_harness_support.py`
  - `backend/requirements.txt`
  - `backend/.env.example`
- Implemented coverage:
  - `/retrieve`:
    - `ContextualPrecisionMetric`
    - `ContextualRelevancyMetric`
  - `/search`:
    - `FaithfulnessMetric`
    - `AnswerRelevancyMetric`
    - `GEval(Skill Coverage)`
    - `GEval(Experience Fit)`
    - `BiasMetric`
- Harness behavior:
  - live evals are test-harness based and are not wired into runtime API responses
  - candidate evidence is fetched from Mongo by `candidate_id`
  - evaluation context uses:
    - `resume_text`
    - `occupation_labels`
    - `skill_labels`
    - `experiences`
    - `educations`
  - fixture cases are separated from code in `search_eval_cases.json`
- Runtime controls:
  - `RUN_LIVE_EVALS=1` enables live DeepEval suites
  - `EVAL_ENFORCE_THRESHOLDS=true` enables score-based quality gating
  - default runtime/cost guardrails:
    - `EVAL_CASE_LIMIT=1`
    - `EVAL_SEARCH_RESULT_TOPN=1`

## Update Log (2026-03-18): Issue #22 FR-08 Golden Eval Dataset Expansion
- Related issue checked:
  - #22 (FR-08 quality evaluation)
- Implementation sync:
  - expanded `backend/tests/fixtures/search_eval_cases.json` from 3 to 30 cases
  - kept the same fixture schema so existing `/retrieve` and `/search` eval harness code remains unchanged
  - strengthened support coverage to assert that the eval fixture keeps at least 30 cases
- Dataset shape:
  - preserves the initial tech-focused cases for frontend, backend, data, ML, and ETL searches
  - adds broader business-domain cases drawn from occupations and skills observed in the current normalized candidate dataset
  - keeps each case aligned to the live harness contract:
    - `request`
    - `expected_output`
    - `required_skills`
    - `preferred_skills`
    - `experience_expectations`
    - `top_k`
    - `top_search_results`
- Intended next step:
  - run multi-case live eval baselines with `EVAL_CASE_LIMIT` increased beyond `1`
  - refine thresholds only after inspecting score distributions across the expanded fixture set

## Update Log (2026-03-18): Issue #22 FR-08 Report Output Baseline
- Related issues checked:
  - #22 (FR-08 quality evaluation)
  - #24 (requirements tracker)
- Implementation sync:
  - added `backend/tests/export_eval_report.py` to export live eval results as JSON + Markdown
  - generated first active report snapshot for 10 cases:
    - `docs/reports/eval/FR-08-Live-Eval-10cases-20260318.md`
    - `docs/reports/eval/FR-08-Live-Eval-10cases-20260318.json`
- Coverage note:
  - this is the first baseline for `FR-08-07` report output
  - report contents now include:
    - selected case list
    - per-case `/retrieve` and `/search` execution status
    - metric row details
    - endpoint-by-metric summary distributions
- Current run highlights:
  - `frontend_react_typescript` returned `422` due invalid explicit ESCO labels
  - `machine_learning_engineer` returned `200` with zero ranked results
  - `FaithfulnessMetric` remains the weakest search-side metric in the first 10-case baseline
- Validation:
  - passed:
    - `python -m unittest tests.test_eval_harness_support -v`
    - `RUN_LIVE_EVALS=1 python -m unittest tests.test_retrieve_quality_eval -v`
    - `RUN_LIVE_EVALS=1 python -m unittest tests.test_search_quality_eval -v`
    - `RUN_LIVE_EVALS=1 python -m unittest tests.test_eval_harness_support tests.test_retrieve_quality_eval tests.test_search_quality_eval -v`
- Scope note:
  - still deferred:
    - diversity metrics
    - culture-fit / soft-skill fit metric
    - baseline-vs-improved comparison harness
    - full report output layer
    - mandatory threshold workflow by default
    - `ContextualRecallMetric`


