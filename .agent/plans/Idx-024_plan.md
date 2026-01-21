# Plan: Idx-024

**Index**: Idx-024
**Created**: 2026-01-21
**Planner**: GitHub Copilot（Coordinator 代行 Planner 產出）

---

## 🎯 目標

修補 VS Code extension workflow loop 的可靠性：在 `IvyHouse: Start Workflow Loop (Engineer→QA→Fix)` 執行時，確保 Engineer/QA 的指令注入（僅 `terminal.sendText`）在工具真正 ready 後才送出，並具備可觀測性與可重試機制，避免出現「兩個 CLI 停在啟動畫面、任務未開始」的狀況。

（本次修訂）當 workflow loop 偵測到 `PASS` 且確認 `.agent/logs/Idx-024_log.md` 已建立後，自動彈出提示詢問是否清空 `.service/terminal_capture/`（不自動清空；需使用者明確確認）。

---

## 📋 SPEC

### Goal
讓 Workflow Loop 在 Codex/OpenCode TUI 啟動速度不穩時仍可穩定推進（Engineer→QA→Fix），並能從落檔（raw/tail + events）快速定位是「未 ready / 注入丟失 / CLI 未回應」。

### Non-goals
- ❌ 不重構/拆分 `extension.js`（雖然檔案過長，但本任務聚焦可靠性修補）。
- ❌ 不改變既有 marker 協議（`[ENGINEER_DONE] / [QA_DONE] / [FIX_DONE]` 與 `QA_RESULT=PASS|FAIL`）。
- ❌ 不新增任何 bridge/server（嚴格維持 VS Code Native + `terminal.sendText` 注入）。

### Acceptance Criteria
1. ✅ 在 `script` capture mode 下，Workflow Loop 會先偵測 Engineer/QA terminal ready（基於 raw transcript 特徵字串），再送出第一個 Engineer prompt。
2. ✅ 若注入後在合理時間內無任何「輸出成長/狀態變化」跡象，會以有限次數重試注入，並在 Output 與 events log 中留下可追蹤紀錄。
3. ✅ 針對使用者提供的案例（兩個 CLI 只停在啟動畫面），修補後可在同環境下讓 Engineer 至少開始回應（例如開始輸出/spinner/或進入對話），並可推進到 QA（不要求一定一次 PASS，但要求不再卡在完全無反應）。
4. ✅ 新增的可觀測性檔案位於 `.service/terminal_capture/`，且不影響 marker 偵測（不把 marker 字面寫入 prompt、marker 仍需獨立成行）。
5. ✅ 新增「受保護的清理流程」：僅在 QA 確認 `PASS` 且 `.agent/logs/Idx-024_log.md` 已存在後，才允許清空 `.service/terminal_capture/` 內檔案（避免清掉稽核/除錯證據）。
6. ✅ Workflow Loop 在偵測到 `PASS` 後，若 `.agent/logs/Idx-024_log.md` 已存在，會自動彈出 modal prompt 詢問是否立即清空 `.service/terminal_capture/`；使用者選擇「不清理」時不做任何破壞性動作。

### Edge cases
- TUI 大量 ANSI/CR 重繪導致 raw log 噪訊：ready 偵測需基於 `tailFile + cleanForTail` 後的內容，避免被控制碼干擾。
- `script` 已存在但 CLI 啟動慢：ready timeout 要可調；超時要停止 workflow 並給出可行動訊息。
- 注入可能成功但 raw transcript 不回顯輸入：避免以「看不到 prompt」作為失敗判定；改用「輸出是否成長/是否出現模型回應特徵」作為弱 ACK。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- `.agent/workflows/dev-team.md`
- `ivy_house_rules.md`
- `.agent/Workflow_Plan_index.md`
- 使用者提供的 logs：`.service/terminal_capture/engineer_20260121001936.log`、`.service/terminal_capture/qa_20260121001936_raw.log`

### Assumptions
- ✅ VERIFIED - `script` 在此環境可用，且 raw transcript 可捕捉到 TUI 內文（例如 OpenCode 的 `Ask anything...`、Codex 的 `OpenAI Codex` 區塊）。
- ⚠️ RISK: unverified - 部分情況下 sendText 可能在 CLI 尚未進入 input loop 時被丟棄；需要 ready gate + retry 才能穩定。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `tools/vscode_terminal_orchestrator/extension.js` - 新增 ready 偵測、注入重試、events log。
- `tools/vscode_terminal_orchestrator/package.json` - 新增/調整 workflow loop 相關設定（timeout/retry）。
- `tools/vscode_terminal_orchestrator/README.md` - 文件化 ready/retry/events log 與 troubleshooting。
- `.agent/Workflow_Plan_index.md` - 登記 Idx-024。
- `.agent/logs/Idx-024_log.md` - 完成後的流程 log（收尾階段建立）。

### Done 定義
1. ✅ 以 ready gate 取代固定 `sleepMs(2500)`（或至少：`sleep` 變為 fallback，預設走 ready gate）。
2. ✅ 每次 workflow 注入都會寫 events log（包含 ts、phase、terminal、attempt、payload 長度/雜湊）。
3. ✅ 具備有限次數 retry + 明確停機訊息（包含建議下一步：重啟 terminals / 調整 timeout / 檢查 `script`）。
4. ✅ 提供 VS Code 命令可在「QA PASS + log 存在」條件成立後清空 `.service/terminal_capture/`（命令需有 modal confirm；缺少條件時要阻擋或要求明確 override）。
5. ✅ Workflow Loop 完成且偵測 `PASS` 後，若 `.agent/logs/Idx-024_log.md` 已建立，會自動提示是否清理 `.service/terminal_capture/`（仍保留至少一次 modal confirm；缺少條件不得清理）。

### Rollback 策略
- **Level**: L2
- **前置條件**: 變更僅限 whitelist
- **回滾動作**:
  - 還原 tracked 變更：`git restore --worktree --staged -- .`

### Max rounds
- **估計**: 2-4（包含修補→手動 smoke test→必要的小修）
- **超過處理**: 若仍無法穩定注入，停止於「可觀測性完整 + 明確失敗訊息 + 可重現步驟」，再請 user 決策是否擴 scope（例如調整 capture strategy 或增加 handshake 指令）。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| tools/vscode_terminal_orchestrator/extension.js | 修改 | 新增 ready 偵測、send retry、events log、改良錯誤訊息與狀態輸出 |
| tools/vscode_terminal_orchestrator/package.json | 修改 | 增加 workflow 設定：readyTimeout / sendRetry 次數與等待 |
| tools/vscode_terminal_orchestrator/README.md | 修改 | 補充新設定與除錯流程（events log、ready patterns、retry 行為） |
| .agent/Workflow_Plan_index.md | 修改 | 新增 Idx-024 任務登記 |
| .agent/logs/Idx-024_log.md | 新增 | 任務完成後由 Coordinator 產出 log |

---

## 📝 邏輯細節

### 1) tools/vscode_terminal_orchestrator/extension.js

#### A. Ready 偵測（取代固定 sleep）
- 新增 `waitForWorkflowTerminalReady({ terminalName, rawLogPath, kind })`：
  - 以 `tailFile(rawLogPath, ...)` + `cleanForTail(...)` 擷取乾淨尾端文本
  - 依 `kind`（`opencode` / `codex`）使用不同 regex patterns
    - OpenCode：`/Ask anything/i`、`/ctrl\+p commands/i`、`/opencode/i`
    - Codex：`/OpenAI Codex/i`、`/Tip:/i`、`/context left/i`
  - 每 `pollInterval`（例如 250ms~500ms）重試直到 timeout
  - timeout 時：
    - `stopWorkflowLoop("terminal not ready")`
    - Output 顯示：「哪個 terminal 未 ready、raw log 路徑、建議：重啟 / 調整 timeout / 檢查 script」

#### B. 可靠注入（sendText retry + 弱 ACK）
- 新增 `workflowSendInstructionWithRetry(...)` 包裝既有 `workflowSendInstruction(...)`：
  - 每次送出前 `terminal.show(true)`
  - 送出後等待「raw log size 成長」或「尾端文本變化」作為弱 ACK（不以 prompt 回顯為前提）
  - 若在 `ackTimeoutMs` 內無變化，按 `retryCount` 進行重試（並加上退避等待）
  - 重試訊息需避免導致重複工作：prompt 末尾加入「若你已開始處理，請忽略此重送」的短句（仍維持單行注入）

#### C. Events log（可觀測性）
- 新增 workflow events 檔：`workflow_<ts>_events.jsonl`（寫在 capture dir）
- 每筆事件包含：
  - `ts`（ISO）、`phase`、`action`（start/ready/send/ack/timeout/stop）
  - `terminalName`、`attempt`
  - `payloadLen`、`payloadSha256`（避免落下完整內容）
  - `rawLogSizeBefore/After`（若可得）

#### E. PASS 後自動提示清理（不自動刪除）
- 在 workflow loop 判定 `QA_RESULT=PASS` 且已建立 `.agent/logs/Idx-024_log.md` 後：
  - 以 VS Code modal prompt 顯示：「已 PASS，是否清空 `.service/terminal_capture/`？」
  - 選項至少包含：`清空` / `略過`（或 `稍後再說`）
  - 若使用者選擇 `清空`：
    - **必須再次檢查**（同 manual 命令）：log 存在、且可找到 QA PASS 證據（例如 `[QA_DONE]` + `QA_RESULT=PASS`）
    - 建議保留第二次確認（顯示將刪除的檔案數量/路徑），避免誤觸
  - 若條件不成立（例如 log 尚未落地）：
    - 不進行清理
    - 顯示可行動訊息：請稍後手動執行清理命令（或等待 log 建立再提示）

#### D. 啟動流程調整
- `startWorkflowLoop()`：
  1) 啟動 terminals（維持現行 script / terminalData）
  2) `await waitForWorkflowTerminalReady`（Engineer、必要時也等 QA ready）
  3) `await workflowSendInstructionWithRetry` 送第一個 Engineer prompt
  4) 再啟動 poller

（可選）在切換到 QA / Fix 送 prompt 前，同樣走 ready + retry。

### 2) tools/vscode_terminal_orchestrator/package.json
- 新增設定（含 default）：
  - `ivyhouseTerminalOrchestrator.workflowReadyTimeoutMs`（例如 60000）
  - `ivyhouseTerminalOrchestrator.workflowSendRetryCount`（例如 3）
  - `ivyhouseTerminalOrchestrator.workflowSendAckTimeoutMs`（例如 1500~3000）
  - `ivyhouseTerminalOrchestrator.workflowSendRetryDelayMs`（例如 1000）
  - `ivyhouseTerminalOrchestrator.workflowPromptClearCaptureOnPass`（例如 true；若設為 false 則不在 PASS 後自動提示）

### 3) tools/vscode_terminal_orchestrator/README.md
- 補充：
  - ready gate 依據的 patterns 與如何調整 timeout
  - events log 位置與用途
  - PASS 後自動提示清理的行為與關閉方式（設定 `workflowPromptClearCaptureOnPass`）
  - 若仍卡住：建議用 `IvyHouse: Show Workflow Status` + 檢查 `*_raw.log` / `*_events.jsonl`

### 4) .agent/Workflow_Plan_index.md
- 新增 Idx-024 一列（Status: NOT_STARTED / In progress 依執行後更新），備註：修補 workflow loop 可靠性（ready/retry/observability）。

---

## ⚠️ 注意事項

- **風險提示**：retry 可能造成重複送出 prompt；需以弱 ACK 與重送提示降低重複工作風險。
- **資安考量**：events log 不記錄完整 prompt（只記 length/hash），避免意外落下敏感資訊。
- **相依性**：維持「只能 sendText 注入」硬規則；focus/ready 只做觀測與 VS Code 內建命令呼叫（不注入 shell 指令到 Codex/OpenCode）。

---

## 🔗 相關資源

- `.agent/workflows/dev-team.md`
- `ivy_house_rules.md`
- `.agent/Workflow_Plan_index.md`

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-01-21
plan_approved: 2026-01-21 03:39:07 +0000
scope_policy: strict
expert_required: false
expert_conclusion: N/A
scope_exceptions: []

# Engineer 執行
executor_tool: opencode
executor_tool_version: 1.1.28
executor_user: feature/idx-024-clear-on-pass (automated)
executor_start: 2026-01-21 03:39:07 +0000
executor_end: 2026-01-21 03:55:52 +0000
session_id: [pending]
last_change_tool: opencode

# QA 執行
qa_tool: codex-cli
qa_tool_version: 0.81.0-alpha.8
qa_user: [pending]
qa_start: [pending]
qa_end: [pending]
qa_result: [pending]
qa_compliance: [pending]

# 收尾
log_file_path: .agent/logs/Idx-024_log.md
commit_hash: 28ce69b
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

---

## ✅ 用戶確認

- [ ] Spec 已確認，可進入 Step 2.5（Role Selection Gate）
- [ ] Engineer Tool 已選擇：`[codex-cli|opencode]`
- [ ] QA Tool 已選擇：`[codex-cli|opencode]`（必須 ≠ last_change_tool）
