# Plan: Idx-038

**Index**: Idx-038
**Created**: 2026-02-23
**Planner**: GitHub Copilot Chat

---

## 🎯 目標

修正 Step E2（三顧問交叉審核）落盤的單筆 `consultant_cross_review.v1` 輸出，確保在 UI 執行 E2 時不再出現 schema 驗證警告，且 `consultant_cross_reviews.json` 內每位 reviewer 的 review 都符合 `schemas/consultant_cross_review.v1.json`。

---

## 📋 SPEC

### Goal
讓 E2 交叉審核每位 reviewer 的輸出「穩定符合」`consultant_cross_review.v1` schema（必填欄位齊全、型別正確、無額外欄位）。

### Non-goals
- ❌ 不修改 `schemas/consultant_cross_review.v1.json`（schema 規格維持不變）。
- ❌ 不改變 E2 的呼叫次數（仍為 3 次 LLM 呼叫；不新增「驗證失敗就重試」的額外呼叫）。
- ❌ 不讓 Step F 依賴 E2（E2 仍為可選附加產物，維持 graceful degradation）。
- ❌ 不調整其他 Step（B/C/D/E/F）的流程與 UI。

### Acceptance Criteria
1. ✅ 勾選「啟用 E2 交叉審核」執行一鍵最終後，不再出現「schema 驗證失敗」的警告訊息。
2. ✅ 落盤 `history/<week>/meta/versions/<fp>/consultant_cross_reviews.json` 存在，且其中 `reviews.reviewer_A/B/C` 皆可通過 `validate_consultant_cross_review()` 驗證。
3. ✅ 既有測試通過，並新增/補齊測試涵蓋「常見不合規輸出 → 正規化後合規」的案例。

### Edge cases
- LLM 回傳舊格式欄位（如 `conclusions/next_steps/reason/reviewer_role`）→ 需 deterministic 正規化到 schema 欄位。
- `strengths` 可能被輸出為物件陣列（含 `point/evidence` 或中文鍵 `依據`）→ 需轉成 schema 要求的字串陣列。
- `critical_issues/assumptions_to_validate` 可能夾帶多餘欄位（如 `依據`）→ 需移除或映射到 `evidence_ref`。
- 若內容不足導致某些 required 欄位缺失 → 以「最小且誠實的預設值」補齊並通過 schema（不引入額外 LLM 呼叫）。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- `schemas/consultant_cross_review.v1.json`（E2 單筆輸出 schema）
- `scripts/consultants.py`（E2 產生器：`generate_consultant_cross_reviews()` / `_single_cross_review()`）
- `core/validation.py`（`validate_consultant_cross_review()`）
- `ui/steps.py`（E2 執行與 schema 驗證顯示）

### Assumptions
- ✅ VERIFIED - 目前 schema 警告主要源自「LLM 輸出欄位/型別不一致」，而非驗證器或 schema 檔本身錯誤。
- ✅ VERIFIED - 以 deterministic 正規化方式修正輸出，可在不增加 LLM 呼叫次數前提下消除大多數 schema 失敗。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `scripts/consultants.py` - 調整 E2 prompt 並新增輸出正規化（normalize）。
- `tests/test_e2_cross_review.py` - 新增/補齊測試，覆蓋不合規輸出轉合規。
- `doc/Implementation_Plan_index.md` - 登記 Idx-038 任務列。
- `doc/plans/Idx-038_plan.md` - 本計畫文件（允許後續小幅修訂）。

### Done 定義
1. ✅ E2 reviewer A/B/C 的 review JSON 均符合 `consultant_cross_review.v1`。
2. ✅ UI 不再顯示 schema 驗證失敗警告（或僅在 truly-error 時顯示）。
3. ✅ `pytest` 相關測試通過（至少包含新增的正規化測試）。

### Rollback 策略
- **Level**: L2
- **前置條件**: worktree 可回復（不包含未追蹤重要檔案）。
- **回滾動作**:
  - 還原 tracked 變更：`git restore --worktree --staged -- .`
  - 若新增測試造成問題，可先回滾測試變更，再聚焦修正 `scripts/consultants.py`。

### Max rounds
- **估計**: 2
- **超過處理**: 若第 2 輪仍無法穩定通過 schema，停止並回報 `SCOPE BREAK`，由你決定是否允許：
  - 增加「驗證失敗 → 追加一次修復 LLM 呼叫」的策略，或
  - 放寬 schema（不建議）。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `scripts/consultants.py` | 修改 | E2 prompt 對齊 schema + 新增輸出正規化（normalize），確保 required 欄位與型別一致。 |
| `tests/test_e2_cross_review.py` | 修改 | 新增正規化單元測試：涵蓋 reviewer_A/B/C 常見不合規輸出樣式。 |
| `doc/Implementation_Plan_index.md` | 修改 | 新增 Idx-038 任務列。 |
| `doc/plans/Idx-038_plan.md` | 新增 | 本計畫文件。 |

---

## 📝 邏輯細節

### 1) `scripts/consultants.py`

#### 1.1 修正 E2 的 prompt，使其不再誘導輸出違反 schema
- 更新 `_cross_review_system_prompt()`：
  - 移除/改寫「每個結論都要寫依據」這類會誘導產出額外欄位（如 `依據`）的描述。
  - 明確要求「只允許輸出 schema 定義的欄位」，禁止輸出 `conclusions/next_steps/reviewer_role/依據` 等。
  - 將 evidence 的要求集中在 `critical_issues[].evidence_ref`；`strengths` 改為純字串（可在字串末尾用括號附上 `source:...` 參考）。

- 更新 `_cross_review_task_prompt()`：
  - 用清楚的欄位規則與一個「最小合法 JSON 範例」約束模型輸出格式。

#### 1.2 新增 deterministic 正規化函式（核心修正）
- 新增 `normalize_consultant_cross_review(review: dict[str, Any], reviewer: str, targets: list[str]) -> dict[str, Any]`：
  - 強制寫入：`review_version/reviewer/reviewed_targets`（以函式參數為準）。
  - 移除額外欄位（schema `additionalProperties: false`）。
  - `strengths`：
    - 若為 `[{point, evidence}]` 或含 `依據` 的物件 → 轉為字串（合併 point + evidence），並截斷至 300 字。
  - `critical_issues`：
    - 若物件含 `依據` 但缺 `evidence_ref` → 映射 `依據` 到 `evidence_ref`（必要時擷取第一個 `source:` 片段；若完全沒有，使用保底 `source:report_context.week_id`）。
    - 確保每項至少具備 `issue/evidence_ref`。
  - `assumptions_to_validate`：
    - 移除多餘欄位（如 `依據`），保留 `assumption/validation_step`。
  - `recommended_edits/stoploss_or_guardrails/why/confidence`：
    - 支援從別名欄位補齊（如 `reason` → `why`）。
    - 若缺失，填入最小且誠實的預設值（避免捏造具體商業結論），以通過 schema 並提示需重跑。
  - 對每個 list 欄位套用 schema 的 `minItems/maxItems` 與長度限制（必要時截斷）。

- 在 `_single_cross_review()` 的 `parsed = _parse_or_repair(...)` 後呼叫 normalize：
  - `parsed = normalize_consultant_cross_review(parsed, reviewer, targets)`

### 2) `tests/test_e2_cross_review.py`

- 新增測試：
  - Case A：輸出含 `conclusions/next_steps/task/status/reason`（舊格式）→ normalize 後通過 schema。
  - Case B：`strengths` 為 `[{point, evidence}]` → normalize 後為字串陣列。
  - Case C：`critical_issues/assumptions_to_validate` 含中文鍵 `依據` → normalize 後移除或映射為 `evidence_ref`。

- 測試方式：
  - 直接呼叫 `normalize_consultant_cross_review()`，再呼叫 `validate_consultant_cross_review()` 驗證不拋例外。

---

## ⚠️ 注意事項

- **資安考量**：不得在 prompt / log / tests 中寫入任何 token/key。
- **成本與延遲**：不得新增額外 LLM 呼叫次數（避免把 E2 從「3 次呼叫」變成不確定次數）。
- **相容性**：保持 E2 graceful degradation；normalize 不能影響 Step F。

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-02-23 01:55:56 UTC
plan_approved: 2026-02-23 02:06:29 UTC
scope_policy: strict
expert_required: false
expert_conclusion: N/A
execution_backend_policy: extension-sendtext-required
scope_exceptions: []

# Engineer 執行
executor_tool: opencode
executor_backend: ivyhouse_sendtext_extension
monitor_backend: proposed_api_monitor
executor_tool_version: 1.2.6
executor_user: pending
executor_start: 2026-02-23 02:13:58 UTC
executor_end: pending
session_id: pending
last_change_tool: opencode

# QA 執行
qa_tool: codex-cli
qa_tool_version: 0.104.0
qa_user: pending
qa_start: pending
qa_end: pending
qa_result: pending
qa_compliance: pending

# 收尾
log_file_path: doc/logs/Idx-038_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->
