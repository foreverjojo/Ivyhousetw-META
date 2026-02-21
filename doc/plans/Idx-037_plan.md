# Plan: Idx-037

**Index**: Idx-037
**Created**: 2026-02-20
**Planner**: GitHub Copilot (Ivy Coordinator)

---

## 🎯 目標

在不新增新頁面、不破壞既有 Step B/C/E/F 流程的前提下，將「三顧問交叉審核（E2，3→3）」落地到實際 pipeline：
- Step E1 完成後執行 E2（A/B/C 交叉審核）
- E2 產物落盤並做 schema 驗證
- Step F（Moderator）將 cross_reviews 納入最終總結與派工（必要時以可選欄位方式擴充 `workflow_state.v1`）
- 自動化驗證：self_test/pytest 至少覆蓋 schema 與 graceful degradation

---

## 📋 SPEC

### Goal
在 `ui/steps.py` 的 Step E 後新增 E2 交叉審核流程，並確保：可落盤、可驗證、可降級、可回滾。

### Non-goals
- ❌ 不新增新的 Streamlit page（僅在既有報告生成流程增加一個可選開關或沿用既有 config）
- ❌ 不更動既有 E1（三顧問）輸出 schema（`consultant_notes.v1`）
- ❌ 不要求模型一定 100% 遵循（必須支援 graceful degradation：E2 失敗時仍可繼續 Step F）

### Acceptance Criteria
1. ✅ 新增 E2 產物落盤：在版本資料夾內新增 `consultant_cross_reviews.json`（命名可調整，但需固定且文件化）。
2. ✅ 新增 schema 驗證：E2 產物可用 `schemas/consultant_cross_review.v1.json` 驗證；失敗時有明確降級策略。
3. ✅ Step F 能讀取 cross_reviews 並在 `workflow_state.json`/`meeting.md` 反映（至少摘要 critical_issues + recommended_edits + guardrails）。
4. ✅ 測試與自檢通過：`scripts/self_test.py`（或等價測試）新增 E2 schema fixture；`pytest tests/ -v` 不新增失敗。

### Edge cases
- E2 其中一位顧問失敗（timeout / 非 JSON / schema fail）
  - 預設：該 reviewer 以 `error` 形式記錄並降級，其他 reviewer 仍可完成，Moderator 以「可用者優先」總結。
- E2 成本/延遲過高
  - 預設：提供 `enable_cross_review` 開關（預設 OFF），並在 UI 顯示預估增加的呼叫數。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- `doc/plans/Idx-036_plan.md`（E2 schema 與規格）
- `ui/steps.py`（現行 Step E/F pipeline）
- `scripts/consultants.py`（E1 產生 consultant_notes 的現行路徑）
- `scripts/moderator.py` / `scripts/moderator_meeting.py`（workflow_state 與 meeting 產物）
- `core/model_settings.py`（顧問角色模型設定 single source of truth）

### Assumptions
- ✅ VERIFIED - 使用「方案 1：E2 仍然是 A/B/C 三位顧問」。
- ⚠️ RISK: unverified - `workflow_state.v1` 是否要加入 cross_reviews 欄位：若直接改 v1 schema 可能造成既有資料回讀風險；較安全作法是新增 optional 欄位或改為 v1.1（需協調）。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `schemas/consultant_cross_review.v1.json` - 引用 Idx-036 產物（若尚未合併，則本 Idx 需一併新增）
- `core/validation.py` - 新增 `validate_consultant_cross_review(...)`（或等價命名）
- `core/__init__.py` - 導出 validation API（如需）
- `scripts/consultants.py` - 新增 E2 交叉審核的產生函式（可沿用既有 retry/repair）
- `scripts/moderator.py` - 讓 Moderator 讀入 cross_reviews（可選）
- `scripts/moderator_meeting.py` - meeting.md 需反映 cross_reviews 摘要（可選，保持最小改動）
- `schemas/workflow_state.v1.json` - 僅允許「新增 optional 欄位」或保持不變；不得破壞既有必填（需在實作前做 Gate）
- `ui/steps.py` - 在 Step E 後插入 E2（可選開關預設 OFF），並處理落盤/驗證/降級
- `ui/navigation.py` - 在 sidebar 設定區新增 `enable_cross_review` 開關（預設 OFF）
- `scripts/self_test.py` - 新增 fixture + expect_fail（如需要）
- `tests/**` - 只允許新增/修改與 E2 schema/降級策略直接相關的測試

（Scope exception - workflow reliability）
- `tools/vscode_terminal_orchestrator/extension.js` - workflow loop：避免 script raw log 覆寫、強化 marker 偵測
- `tools/vscode_terminal_monitor/extension.js` - 監測/擷取：強化 ANSI 清理，並阻擋 `.venv/bin/activate` 注入

### Done 定義
1. ✅ E2 可在本機跑通（不要求真實 API key；可用 fixture 方式驗證 schema & pipeline branching）。
2. ✅ 開關 OFF 時，現行流程輸出不變。
3. ✅ 開關 ON 且 E2 任一顧問失敗時，流程仍可走到 Step F（graceful degradation）。

### Rollback 策略
- **Level**: L2
- **前置條件**: 變更範圍集中在 Step E/F；需可快速回復到無 E2 的狀態。
- **回滾動作**: 以 feature flag 將 `enable_cross_review` 永久關閉，並移除 E2 插入點；保留 schema 檔不影響既有資料。

### Max rounds
- **估計**: 2（一次工程落地 + 一次 QA/修正）
- **超過處理**: 若觸及 `workflow_state` 版本升級爭議，拆出 Idx-038 專責處理 schema versioning。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| schemas/consultant_cross_review.v1.json | 新增/引用 | E2 交叉審核 schema |
| core/validation.py | 修改 | 新增 E2 schema 驗證入口 |
| core/__init__.py | 修改 | 導出新的 validate 函式（如需要） |
| scripts/consultants.py | 修改 | 新增 E2 交叉審核產生函式（重用 retry/repair） |
| ui/steps.py | 修改 | Step E 後插入 E2（開關預設 OFF）並落盤/驗證/降級 |
| ui/navigation.py | 修改 | sidebar 設定區新增 enable_cross_review（預設 OFF） |
| scripts/moderator.py | 修改 | 納入 cross_reviews（可選，最小整合） |
| schemas/workflow_state.v1.json | 修改（可選） | 僅新增 optional 欄位；不破壞必填 |
| scripts/self_test.py | 修改 | 新增 E2 fixture + 自檢 |
| tests/** | 修改（可選） | 覆蓋 schema/降級策略 |
| tools/vscode_terminal_orchestrator/extension.js | 修改（scope exception） | workflow loop 穩定性修復（TUI transcript/marker） |
| tools/vscode_terminal_monitor/extension.js | 修改（scope exception） | 阻擋 venv activation 注入、改善擷取清理 |

---

## 📝 邏輯細節

### 1. scripts/consultants.py（E2 產生）
- 新增 `generate_consultant_cross_reviews(...)`（命名可調整）
- 輸入：`report_summary`、`report_insights`、`consultant_notes`（E1）
- 每位 reviewer（A/B/C）拿到：
  - 原始報表（summary/insights）
  - 另外兩位顧問 E1 的摘要（建議做 compact，避免 token 爆）
- 輸出：符合 `consultant_cross_review.v1` 的 JSON；失敗走 repair 重試（與既有 parse/repair 一致）。

### 2. ui/steps.py（插入 E2）
- 在 Step E1 完成、寫入 `consultant_notes.json` 後：
  - 若 `enable_cross_review` 為 OFF：略過
  - 若 ON：執行 E2 並將 `consultant_cross_reviews.json` 落盤
- 驗證策略：
  - schema PASS：寫入成功狀態
  - schema FAIL / exception：記錄 error，但不阻擋 Step F（graceful degradation）

### 3. scripts/moderator.py（納入 E2）
- 若 cross_reviews 存在：Moderator 在輸出中加一段「交叉審核結論摘要」
- 最小化整合：僅引用 `critical_issues`、`recommended_edits`、`stoploss_or_guardrails`

### 4. schemas/workflow_state.v1.json（可選）
- 若要保存 cross_reviews：以 optional 欄位加入（例如 `cross_reviews_summary`），避免破壞既有回讀。

---

## ⚠️ 注意事項

- **風險提示**：E2 增加呼叫數（3 次），延遲會上升；必須保留開關且預設 OFF。
- **資安考量**：不得把 raw prompts/headers/token 落盤。
- **相依性**：與 Step E/F 的 schema 驗證相依；需保持向下相容。

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-02-20
plan_approved: 2026-02-20
scope_policy: strict
expert_required: false
expert_conclusion: N/A
execution_backend_policy: extension-sendtext-required
scope_exceptions: ["ui/navigation.py", "tools/vscode_terminal_orchestrator/extension.js", "tools/vscode_terminal_monitor/extension.js"]

# Engineer 執行
executor_tool: opencode
executor_backend: ivyhouse_sendtext_extension
monitor_backend: ivyhouse_monitor_extension_fallback
executor_tool_version: pending
executor_user: pending
executor_start: pending
executor_end: pending
session_id: pending
last_change_tool: pending

# QA 執行
qa_tool: codex-cli
qa_tool_version: pending
qa_user: pending
qa_start: pending
qa_end: pending
qa_result: pending
qa_compliance: pending

# 收尾
log_file_path: doc/logs/Idx-037_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

**預期 Rollback Level**: L2

---

## ✅ 用戶確認

- [ ] Spec 已確認，可進入 Engineer 執行
- [ ] Engineer Tool 已選擇：`codex-cli` 或 `opencode`
- [ ] QA Tool 已選擇：必須 ≠ last_change_tool
- [ ] 是否允許修改 `schemas/workflow_state.v1.json`（僅 optional 欄位）：Yes/No
- [ ] 是否需要在 UI 顯示 `enable_cross_review` 開關：Yes/No（預設 Yes 且 OFF）
