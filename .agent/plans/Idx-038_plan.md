# Plan: Idx-038

**Index**: Idx-038
**Created**: 2026-02-20
**Planner**: GitHub Copilot（Coordinator）

---

## 🎯 目標

修復 dev-team workflow 注入穩定性兩個 P0 blocker：
1) OpenCode/Codex 的指令/文字注入後，必須可靠送出 Enter（目前看到文字進到對話框，但沒有 submit）。
2) `script -q -f ... -c 'codex' ...` 這類「啟動/錄製指令」不應被送進 OpenCode/Codex TUI（會導致 CLI 退出又重啟），workflow loop 應改為「不重啟終端、只在既有 TUI 內注入」。

---

## 📋 SPEC

### Goal
讓 `/workflow/start` 與 `/send` 在「固定 OpenCode CLI / Codex CLI 終端」模式下穩定可用：注入必 submit、且不再重啟/不再把 `script ...` 當作 TUI 輸入。

### Non-goals
- ❌ 不新增任何 UI/頁面/互動式設定面板（僅修正 extension 行為與必要設定鍵）。
- ❌ 不重做整個 workflow 架構（維持既有 sendtext bridge + workflow loop 的 API/檔案輸出）。
- ❌ 不把 Orchestrator 完全移除（雖然它標記 DEPRECATED，但目前仍是 `/workflow/start` 的承載者）。

### Acceptance Criteria
1. ✅ 呼叫 `/send` 時，若 request body 未提供 `submit`，預設必須為 `true`（能觀察到有 Enter/送出行為）。
2. ✅ 呼叫 `/workflow/start` 不會 dispose / 重啟 `OpenCode CLI` 與 `Codex CLI` 終端（除非顯式 opt-in）。
3. ✅ 在 OpenCode/Codex TUI 中不再出現 `script -q -f ... -c 'codex' ...` 或 `script -q -f ... -c 'opencode' ...` 被當作輸入內容。
4. ✅ workflow events 應能記錄到 `post_send_enter`（或等價事件）以佐證已嘗試 submit。

### Edge cases
- Proposed API `onDidWriteTerminalData` 不可用：
  - 預設行為：拒絕以 `script -c` 強行重啟 TUI（避免再次把 script 指令打進對話框）；改以明確錯誤訊息提示需要啟用 Proposed API 或改用替代監測。
- OpenCode/Codex 已在 TUI 中、且注入後無輸出導致 ACK 偵測失敗：
  - 調整 ready/ack 策略：在「不重啟模式」下，ready 不應依賴啟動 banner；允許短暫 grace window 後直接送出 prompt + Enter。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- `tools/vscode_terminal_orchestrator/extension.js`：
  - `/send` 端點目前 `submit` 以 `Boolean(body?.submit)` 解析，未提供時會變成 `false`。
  - workflow loop 目前在啟動時會 dispose 兩個 TUI terminal，且 captureMode 只要 `script` 可用就優先選 `script`，並送出 `script -q -f -a -c ...`。
- `tools/vscode_terminal_orchestrator/package.json`：現有設定貢獻（目前未包含 workflow loop 的部分設定鍵）。
- `tools/vscode_terminal_injector/extension.js`：parseSendArgs 預設 submit=true，且 submit 會送 `\r`。

### Assumptions
- ✅ VERIFIED - 目前環境 `vscode.window.onDidWriteTerminalData` 可用（Monitor/Orchestrator 都有啟用 `terminalDataWriteEvent` proposal）。
- ✅ VERIFIED - 目前 `/workflow/start` 會觸發「重啟終端 + script -c」行為，與使用者觀察一致。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `tools/vscode_terminal_orchestrator/extension.js` - 修正 `/send` 預設 submit、workflow loop 的 capture/restart 行為。
- `tools/vscode_terminal_orchestrator/package.json` -（如需要）新增/文件化新的設定鍵（例如 restart/捕捉模式的 opt-in）。

> 本任務不修改專案功能程式（`core/`、`ui/`、`scripts/`），僅修 workflow 工具鏈。

### Done 定義
1. ✅ 依 Acceptance Criteria 1~4 逐條通過。
2. ✅ 能用同一組固定終端跑起 workflow 注入，不再看到 TUI 被 `script ...` 汙染或重啟。

### Rollback 策略
- **Level**: L2
- **前置條件**: 變更僅限上述 whitelist。
- **回滾動作**:
  - 直接 `git restore --worktree --staged -- tools/vscode_terminal_orchestrator` 還原。
  - 重新 Reload Window 讓 extension 回到舊行為。

### Max rounds
- **估計**: 2
- **超過處理**: 若涉及 Proposed API 不可用導致需要改 monitor/bridge 架構，拆出新 Idx。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| tools/vscode_terminal_orchestrator/extension.js | 修改 | `/send` 預設 submit=true；workflow loop 改為不 dispose 終端、captureMode 優先 terminalData；不再把 `script -c` 送進 TUI |
| tools/vscode_terminal_orchestrator/package.json | 修改（可選） | 若需要新增設定鍵（例如 `workflowRestartTerminals` / `workflowCapturePreference`）則補上設定貢獻與說明 |

---

## 📝 邏輯細節

### 1) `/send` submit 預設值（避免沒 Enter）
- 位置：`tools/vscode_terminal_orchestrator/extension.js` 的 `/send` handler。
- 現況：`const submit = Boolean(body?.submit);` → 未提供會變 `false`。
- 修正：
  - 若 `submit` 欄位不存在，預設 `true`。
  - 僅當明確傳 `submit:false` 才不送 Enter。

### 2) workflow loop：禁止預設 dispose/restart 固定終端
- 位置：`startWorkflowLoopCore()` 內「Start / restart terminals to ensure clean session.」區段。
- 修正方向：
  - 預設不 dispose 兩個 terminal。
  - 僅當（可選）設定 `workflowRestartTerminals=true` 時才允許重啟。

### 3) workflow loop：captureMode 選擇策略調整（避免 script -c）
- 位置：`startWorkflowLoopCore()` 內 captureMode 決策。
- 現況：只要 `script` 可用就選 `script`。
- 修正：
  - 優先使用 `terminalData`（Proposed API）以避免 `script -c`。
  - 若 `terminalData` 不可用：
    - 預設直接拒絕啟動 workflow（回報可行動錯誤訊息），避免再把 `script ...` 送進 TUI。
    - （可選）提供顯式 opt-in 才允許 script 模式。

### 4) ready 偵測策略（不重啟模式）
- 位置：`waitForWorkflowTerminalReady()` / `isTerminalReadyFromTail()`。
- 現況：依賴啟動 banner（OpenCode: “Ask anything.../ctrl+p commands”）。
- 修正：
  - 在「不重啟模式」下，允許用短 grace window（例如 0.5~1s）直接視為 ready。
  - 避免因為 raw log 是新檔、但 TUI 已在跑而永遠等不到 banner。

---

## ⚠️ 注意事項

- **風險提示**：不重啟終端可能會保留上一輪上下文/狀態；但此風險低於「重啟導致 workflow 無法開始」。
- **資安考量**：不新增任何 token/secret；不把敏感資料寫入 capture。
- **相依性**：依賴 VS Code Proposed API `terminalDataWriteEvent`；若不可用，需明確提示而非 fallback 到 `script -c` 汙染 TUI。

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-02-20 20:00:00
plan_approved: 2026-02-20 20:00:00
scope_policy: strict
expert_required: false
expert_conclusion: N/A
execution_backend_policy: extension-sendtext-required
scope_exceptions: []

# Engineer 執行
executor_tool: opencode
executor_backend: ivyhouse_sendtext_extension
monitor_backend: proposed_api_monitor
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
log_file_path: .agent/logs/Idx-038_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

---

## ✅ 用戶確認

- [ ] 你已確認此 Plan 的目標與檔案白名單
- [ ] 你同意「workflow 預設不重啟 OpenCode/Codex 終端」
- [ ] 你同意「若 Proposed API 不可用，預設拒絕 script 模式以避免汙染 TUI」
- [ ] Engineer Tool 選擇：`codex-cli` 或 `opencode`
- [ ] QA Tool 選擇：必須 ≠ last_change_tool
