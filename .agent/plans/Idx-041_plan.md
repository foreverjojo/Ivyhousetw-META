# Plan: Idx-041（needs_user_input 改用 Chat Ask Questions，取代 QuickPick）

**Index**: Idx-041
**Created**: 2026-02-22
**Planner**: GitHub Copilot（Coordinator acting as Planner）

---

## 🎯 目標

把 Orchestrator 在「QA FAIL 且 round >= maxRounds」時的使用者決策互動，從 VS Code `showQuickPick` 改成 **VS Code Chat 內的 Ask Questions UI**（同 Copilot Chat 問答 UI），並符合：
- 新增一個「自由輸入」路徑
- `CONTINUE` 必須 **立刻在同一個 workflow loop 繼續跑下一輪**（不需要手動重啟 workflow）
- `MORE_INFO` 必須在 chat 內追問「要補充什麼/希望看哪些資訊」，並能再回到決策

---

## 📋 SPEC

### Goal
當 workflow 命中 `needs_user_input` 決策點時：
1) Orchestrator 不再用 QuickPick 彈窗
2) 由 Coordinator 在 chat 內用 Ask Questions 收集決策與補充資訊
3) 決策回寫給 Orchestrator 後，workflow loop 可原地續跑（或停止）

### Non-goals
- ❌ 不改動「選 Engineer / 選 QA terminal」的 QuickPick（僅針對 `checkFailAndAskUser()`）
- ❌ 不新增任何 Web UI、設定頁、或外部服務
- ❌ 不引入新的 HTTP bridge server（僅擴充既有 extension 的本機 localhost API）
- ❌ 不調整 completion marker 規範（沿用 Idx-030/039/040 既有格式）

### Acceptance Criteria
1. ✅ 當 `QA_RESULT=FAIL` 且 `round >= maxRounds` 時：不再呼叫 `vscode.window.showQuickPick`（針對決策點）。
2. ✅ `/workflow/status` 能回傳「目前正在等待使用者決策」的狀態與題目 payload（包含 round/maxRounds/idxName/qaSnippet/選項）。
3. ✅ Coordinator 能用 Ask Questions UI 提供：`CONTINUE` / `STOP` / `MORE_INFO` + 「自由輸入」；且回寫後 Orchestrator 能正確接續。
4. ✅ `CONTINUE`：workflow loop 不退出、不重啟，在同一次 loop 內進到下一輪。
5. ✅ `MORE_INFO`：Ask Questions 會追問自由輸入（想補充什麼/想看什麼診斷），Orchestrator 會把該文字記錄為事件並輸出更多診斷，再回到決策。
6. ✅ Timeout（使用者未回覆）時：Orchestrator 必須安全地停止，並持久化狀態為 `needs_user_input`（避免卡住）。

### Edge cases
- 使用者在 Ask Questions 輸入自由文字但未選任何選項：
  - 優先嘗試比對 `continue/stop/more` 關鍵字；否則視為 `CUSTOM_NOTE`（寫入事件）並回到決策。
- 使用者重複提交 decision（雙擊/重送）：
  - 以 `decisionId` 去重，重複 request 回 200 但不重複套用。
- workflow 已不在 waiting 狀態仍收到 decision：
  - 回 409（conflict）並回傳目前 state。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- `tools/vscode_terminal_orchestrator/extension.js`：目前 `checkFailAndAskUser()` 在 `workflowAskMode=interactive` 會呼叫 `showQuickPick`。
- `tools/vscode_terminal_orchestrator/package.json`：`workflowAskMode` enum 目前為 `batch|interactive`。
- `scripts/sendtext_bridge_client.py`：已存在可呼叫 `/workflow/status`、`/workflow/start`、`/stop-workflow` 的本機 client，可擴充為 decision submit。

### Assumptions
- ⚠️ RISK: unverified - VS Code extension 端沒有穩定 API 可直接開啟 Copilot Chat 的 Ask Questions UI；因此採「Orchestrator 暫停等待 + Chat UI 收集 + 回寫 decision」架構。
- ✅ VERIFIED - 此工作流使用者會在 Copilot Chat 中操作 `/dev`，因此 Coordinator 能在需要時呼叫 Ask Questions UI。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `tools/vscode_terminal_orchestrator/extension.js` - 改寫 `checkFailAndAskUser()`：移除決策 QuickPick、改為 pending decision + wait + API submit。
- `tools/vscode_terminal_orchestrator/package.json` - 調整設定說明與 enum（新增 `ask_questions`；保留 `interactive` 但改為 alias，不再 QuickPick）。
- `scripts/sendtext_bridge_client.py` - 新增 subcommand：`workflow-decision`（POST /workflow/decision）。
- `.agent/roles/coordinator.md` - 補一段「needs_user_input → Ask Questions → submit decision」操作 SOP（只加最小必要內容）。
- `.agent/Workflow_Plan_index.md` - 新增 Idx-041 記錄（在執行/交付階段回填）。
- `.agent/logs/Idx-041_log.md` - 收尾閉環（產出 execution log）。

> 限制：不得修改 whitelist 以外檔案；若需擴 scope 必須 `SCOPE BREAK` 停下來詢問用戶。

### Done 定義
1. ✅ Orchestrator 決策點不再使用 QuickPick。
2. ✅ `/workflow/status` 具備 `pendingDecision`（或等價欄位）輸出。
3. ✅ 新增 `/workflow/decision`（或等價端點）可提交：decision + free text + decisionId。
4. ✅ `CONTINUE/STOP/MORE_INFO/自由輸入` 端到端可用（含 timeout 行為）。

### Rollback 策略
- **Level**: L2
- **前置條件**: 只修改 whitelist 內檔案。
- **回滾動作**:
  - `git restore --worktree --staged -- tools/vscode_terminal_orchestrator/extension.js tools/vscode_terminal_orchestrator/package.json scripts/sendtext_bridge_client.py .agent/roles/coordinator.md .agent/Workflow_Plan_index.md`

### Max rounds
- **估計**: 2
  - Round 1：extension + client + minimal doc + manual E2E 驗證
  - Round 2：修補 edge cases（timeout、重送、state 不一致）+ QA
- **超過處理**: 若需要擴充更多互動情境（例如多題表單、更多按鈕），拆成新 Idx。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| tools/vscode_terminal_orchestrator/extension.js | 修改 | `checkFailAndAskUser()` 改為 pending decision + wait；新增 `/workflow/decision` 端點；`/workflow/status` 增加 pending payload |
| tools/vscode_terminal_orchestrator/package.json | 修改 | `workflowAskMode` enum/description：新增 `ask_questions`；`interactive` 改為 alias（不再 QuickPick） |
| scripts/sendtext_bridge_client.py | 修改 | 新增 `workflow-decision` 指令，支援提交 decision + free text |
| .agent/roles/coordinator.md | 修改 | 最小化補強 SOP：收到 needs_user_input 時用 Ask Questions UI 收集並提交 decision |
| .agent/Workflow_Plan_index.md | 修改 | 登記 Idx-041（workflow/gov 任務） |

---

## 📝 邏輯細節

### 1) Orchestrator：Pending decision state + 等待機制
檔案：`tools/vscode_terminal_orchestrator/extension.js`

**核心改動**（在 `checkFailAndAskUser()`）：
- 移除 `showQuickPick` 分支（針對決策點）。
- 建立 `pendingDecision`：
  - `decisionId`: 例如 `${workflowRunId}:${Date.now()}`
  - `question`: 固定為「QA FAIL 達 maxRounds，需要決策」
  - `options`: `CONTINUE|STOP|MORE_INFO|FREEFORM`
  - `context`: round/maxRounds/idxName/qaLogPath/qaSnippet
- 將 `pendingDecision`：
  - 寫入 `workflowLoopState`（active memory）
  - 同步寫入 `workspaceState`（window reload 後仍可由 `/workflow/status` 查到）
- `checkFailAndAskUser()` 改為：
  1) 輸出結構化 prompt（logLine）
  2) 進入 `await waitForWorkflowDecision(timeoutMs)`

**Timeout 行為**：
- 若超時：呼叫 `stopWorkflowLoop("FINAL_FAIL (max rounds reached, needs_user_input)", "needs_user_input")`

**Decision 行為**：
- `CONTINUE`：清掉 pending、回復狀態為 running、`return "CONTINUE"` 讓 caller 繼續下一輪。
- `STOP`：`stopWorkflowLoop("user_stop", "needs_user_input")`（持久化 needs_user_input）。
- `MORE_INFO`：
  1) 先等待一段 `moreInfoText`（由 chat 追問後提交）
  2) 把 `moreInfoText` 寫入 event log + logLine
  3) 輸出更多診斷（例如 QA tail / 指向 qaRawLog 檔案）
  4) 重新建立 pendingDecision（第二次決策：CONTINUE/STOP，仍可自由輸入）

### 2) Bridge API：提交 decision 端點
檔案：`tools/vscode_terminal_orchestrator/extension.js`

新增 protected endpoint（建議）：
- `POST /workflow/decision`

Request body（示意）：
```json
{
  "decisionId": "wf_xxx:1700000000000",
  "decision": "CONTINUE|STOP|MORE_INFO|FREEFORM",
  "freeText": "...",
  "phase": "initial|more_info|final"
}
```

Response（示意）：
- 200：accepted + current state
- 409：no pending decision / state mismatch

### 3) /workflow/status：輸出 pendingDecision
檔案：`tools/vscode_terminal_orchestrator/extension.js`

在 `getWorkflowStatusForApi()` 回傳內補欄位：
- `pendingDecision: { decisionId, question, options, context, createdAtIso } | null`

並調整 state 推導：
- 若 `workflowLoopState.active` 但 pendingDecision 存在，state 仍應回 `needs_user_input`（避免顯示 running 讓 Coordinator 誤判）。

### 4) Python client：workflow-decision
檔案：`scripts/sendtext_bridge_client.py`

新增 subcommand：
- `python scripts/sendtext_bridge_client.py workflow-decision --decision CONTINUE --free-text "..." --decision-id "..."`

用途：讓 Coordinator（或測試腳本）可用一致方式提交 decision。

### 5) Coordinator SOP（最小變更）
檔案：`.agent/roles/coordinator.md`

新增一段：當 `/workflow/status` state = `needs_user_input` 且有 `pendingDecision` 時：
1) 用 `Ask Questions` UI 先問 action（含自由輸入）
2) 若選 `MORE_INFO`：再問 freeform「想補充什麼/想看哪些資訊」
3) 呼叫 `workflow-decision` 提交結果

---

## ⚠️ 注意事項

- **Ask Questions 為 Experimental**：若使用者環境未啟用，Coordinator 需改用純文字在 chat 詢問（仍可透過 `/workflow/decision` 提交）。
- **安全性**：`/workflow/decision` 必須為 protected endpoint（沿用既有 Bearer token 機制）。
- **避免卡死**：務必有 timeout → stop + persisted `needs_user_input`。

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-02-22 00:00:00
plan_approved: 2026-02-22 18:00:00
scope_policy: strict
expert_required: false
expert_conclusion: N/A
execution_backend_policy: extension-sendtext-required
scope_exceptions: []

# Engineer 執行
executor_tool: copilot-chat
executor_backend: vscode-extension
monitor_backend: N/A
executor_tool_version: N/A
executor_user: unknown
executor_start: 2026-02-22
executor_end: 2026-02-22
session_id: N/A
last_change_tool: copilot-apply_patch

# QA 執行
qa_tool: agent-skills+pytest
qa_tool_version: N/A
qa_user: unknown
qa_start: 2026-02-22
qa_end: 2026-02-22
qa_result: pass_with_risk
qa_compliance: qa_tool != last_change_tool（使用 skills/test_runner + code_reviewer 與 pytest/ruff；last_change_tool 為 copilot-apply_patch）

# 收尾
log_file_path: .agent/logs/Idx-041_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

---

## ✅ 用戶確認

> 🛑 **必要停頓點**：請你確認此 Plan 後，我才會進入 Tool Selection Gate 與後續執行。

- [ ] 你同意此任務是 workflow/gov 任務，Plan 位於 `.agent/plans/Idx-041_plan.md`
- [ ] 你同意 Orchestrator 端不再使用 QuickPick（僅針對決策點）
- [ ] 你同意新增 `/workflow/decision` 端點用於 decision 回寫
- [ ] 你同意 `interactive` 會成為 `ask_questions` 的 alias（不再代表 QuickPick）
- [ ] 你同意 `CONTINUE` 必須在同一 workflow loop 內續跑
- [ ] 請選擇 Engineer Tool：`codex-cli` 或 `opencode`
- [ ] 請選擇 QA Tool：必須 ≠ last_change_tool
