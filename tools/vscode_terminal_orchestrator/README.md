# IvyHouse Terminal Orchestrator (local VS Code extension)

目的：
- 自動啟動並維持兩個「可見的互動 VS Code terminal」：
  - `Codex CLI`
  - `OpenCode CLI`
- **所有對這兩個 terminal 的啟動/指令下達都透過 `terminal.sendText()`**（避免 terminal collision 的覆寫問題）。

## 安裝（Dev Container / VS Code Server）

在 repo root 執行：

```bash
bash scripts/vscode/install_terminal_orchestrator.sh
```

完成後請在 VS Code 內執行「Developer: Reload Window」。

## 使用

Command Palette：
- `IvyHouse: Start Codex Terminal`
- `IvyHouse: Restart Codex Terminal`
- `IvyHouse: Start OpenCode Terminal`
- `IvyHouse: Start Codex + OpenCode Terminals`
- `IvyHouse: Send Text to Codex Terminal`
- `IvyHouse: Send Text to OpenCode Terminal`
- `IvyHouse: Capture Codex Output (sendText)`
- `IvyHouse: Open Last Codex Capture`
- `IvyHouse: Clear Codex Capture`
- `IvyHouse: Clear .service/terminal_capture (after QA PASS + log)`
- `IvyHouse: Codex Capture Diagnostics`
- `IvyHouse: Start Workflow Loop (Engineer→QA→Fix)`
- `IvyHouse: Stop Workflow Loop`
- `IvyHouse: Show Workflow Status`

## 設定

Workspace Settings：
- `ivyhouseTerminalOrchestrator.autoStart`（預設 `true`）
- `ivyhouseTerminalOrchestrator.codexCommand`
- `ivyhouseTerminalOrchestrator.opencodeCommand`
- `ivyhouseTerminalOrchestrator.captureMaxSeconds`（預設 `10`）
- `ivyhouseTerminalOrchestrator.captureSilenceMs`（預設 `800`）
- `ivyhouseTerminalOrchestrator.captureMaxBytes`（預設 `65536`）
- `ivyhouseTerminalOrchestrator.captureDir`（預設 `.service/terminal_capture`）
- `ivyhouseTerminalOrchestrator.workflowPollIntervalMs`（預設 `5000`）
- `ivyhouseTerminalOrchestrator.workflowMaxRounds`（預設 `10`）
- `ivyhouseTerminalOrchestrator.workflowTimeoutMs`（預設 `1800000`）
- `ivyhouseTerminalOrchestrator.workflowTailLines`（預設 `200`）
- `ivyhouseTerminalOrchestrator.workflowReadyTimeoutMs`（預設 `60000`）
- `ivyhouseTerminalOrchestrator.workflowReadyPollIntervalMs`（預設 `300`）
- `ivyhouseTerminalOrchestrator.workflowSendRetryCount`（預設 `3`）
- `ivyhouseTerminalOrchestrator.workflowSendAckTimeoutMs`（預設 `3000`）
- `ivyhouseTerminalOrchestrator.workflowSendRetryDelayMs`（預設 `1200`）
- `ivyhouseTerminalOrchestrator.workflowPrimeEnterCount`（預設 `2`）

## （新增）Codex 輸出擷取（/status read-back）

此功能會：
- 僅用 `terminal.sendText()` 對 `Codex CLI` 送出指令（預設 `/status`）
- 在短時間窗口內擷取該 terminal 的輸出
- 將 raw 輸出寫到：`.service/terminal_capture/codex_last.txt`（此目錄已被 `.gitignore` 忽略）

### 前置：啟用 VS Code Proposed API

此功能使用 Proposed API `terminalDataWriteEvent`。

請用啟用 Proposed API 的方式啟動 VS Code：

```bash
code --enable-proposed-api ivyhouse-local.ivyhouse-terminal-orchestrator
```

注意：Remote/Dev Container 情境下，旗標通常要加在「本機 VS Code client」啟動參數（不是容器內的 `code` binary）。

### Fallback（不靠 Proposed API）

若 `IvyHouse: Codex Capture Diagnostics` 顯示：
- `Proposed API onDidWriteTerminalData available: false`

extension 會改用 **Shell Integration** 的 execution stream 來擷取 *codex 這個長跑程序* 的 raw output。

限制：必須在 codex 從 shell 啟動的當下掛上串流，所以你需要先重啟一次 codex。

最短流程：
1. 確認 VS Code 設定 `terminal.integrated.shellIntegration.enabled = true`
2. 執行 `IvyHouse: Restart Codex Terminal`
3. 等 codex prompt 出現後，執行 `IvyHouse: Capture Codex Output (sendText)`（預設 `/status`）

### 使用步驟

1. 先確定 `Codex CLI` terminal 已進入 codex 的互動 prompt（可先執行 `IvyHouse: Start Codex Terminal`）
2. 執行 `IvyHouse: Capture Codex Output (sendText)`
3. 保留預設輸入 `/status` 或改成你要送的指令
4. 擷取結果可用 `IvyHouse: Open Last Codex Capture` 開啟檔案查看

補充說明：
- `opencode` 通常會啟動一個 Web UI 服務，terminal 可能看起來「卡住/沒輸出」，其實是服務正在跑。
- 你可以從 VS Code 的 **Ports** 面板找到對應 port，然後用 **Open in Browser** 開啟。

### （可選）固定 port

若你希望每次都固定同一個 port（方便 bookmark 或 Ports forwarding），可把：
- `ivyhouseTerminalOrchestrator.opencodeCommand` 設成 `opencode --port 35103`

### Troubleshooting

若你在 repo 端找不到 `.service/terminal_capture/codex_last.txt`：
- 代表「extension 的 capture/open 指令尚未執行過」，或 capture 因 Proposed API 未啟用而提前退出。
- 先執行 `IvyHouse: Open Last Codex Capture`（它會建立目錄與空檔），再執行 capture。
- 或直接跑 `IvyHouse: Codex Capture Diagnostics`，到 Output 面板查看 Proposed API 是否生效與實際落地路徑。

若 Diagnostics 顯示 Proposed API 為 `false` 且 Capture 提示「no shell-read stream attached」：
- 先跑 `IvyHouse: Restart Codex Terminal`
- 再跑一次 `IvyHouse: Capture Codex Output (sendText)`

若 OpenCode CLI terminal 看起來沒有反應：
1. 先看 VS Code **Ports** 面板是否已出現 OpenCode 的 port。
2. 再執行一次 `IvyHouse: Start OpenCode Terminal`（手動 start 會再次送出啟動命令）。
3. 若仍想清除狀態，可執行 `IvyHouse: Reset Terminal Orchestrator Session State` 後再試。

## 注意

- 任何「在同一個 terminal」執行第二個命令，都可能導致長期服務退出；因此這個 extension 會把啟動與輸入統一走 `sendText`。
- 若你想把 git/pytest/ruff 等命令放到第三個 terminal，請使用一般 terminal（例如命名 `Project`）即可。

### 技術債

- **extension.js 檔案長度**：目前 ~1000 行，已超過建議的主程式上限（800 行）。未來應考慮拆分為：
  - `workflow-loop.js`（Workflow Loop 狀態機）
  - `capture.js`（Terminal 輸出擷取）
  - `commands.js`（Command 註冊）
  - 保留 extension.js 作為入口點

---

## 🔄 Workflow Loop（自動化 Engineer → QA → Fix 循環）

### 功能概述

Workflow Loop 是一個自動化編排功能，可以：
- 自動協調 Engineer 終端（實作）和 QA 終端（審查）的工作流程
- 透過 `terminal.sendText()` 注入指令，並監控輸出檔案（log polling）
- 偵測特定 marker（`[ENGINEER_DONE]`、`[QA_DONE]`、`[FIX_DONE]`）來推進狀態機
- 當 QA 回報 `FAIL` 時，自動將問題摘要送回 Engineer 要求修正
- 直到 QA 回報 `PASS`，或達到 timeout/max rounds 上限

### 使用方式

1. **啟動 Workflow Loop**：
   - Command Palette → `IvyHouse: Start Workflow Loop (Engineer→QA→Fix)`
   - 依序選擇：
     - Engineer 終端（負責實作的工具，例如 `OpenCode CLI`）
     - QA 終端（負責審查的工具，例如 `Codex CLI`）
     - 輸入任務描述（例如：`實作 Idx-023 workflow loop`）

2. **查看狀態**：
   - Command Palette → `IvyHouse: Show Workflow Status`
   - 會在 Output 面板顯示當前狀態、輪次、已耗時間等資訊

3. **停止 Workflow Loop**：
   - Command Palette → `IvyHouse: Stop Workflow Loop`
   - 安全停止 polling，不會強制關閉 terminal

4. **（收尾）清空 `.service/terminal_capture/`**：
  - 自動提示：當你在啟動 Workflow Loop 時於「Associated Idx」欄位填入 `Idx-XXX`，且在執行中偵測到 QA `PASS`，若 `.agent/logs/Idx-XXX_log.md` 已存在，extension 會自動彈出 modal 提示是否清空 `.service/terminal_capture/`（此行為可透過設定 `ivyhouseTerminalOrchestrator.workflowPromptClearCaptureOnPass` 關閉）。
  - 前提：QA 已回報 `PASS`，且對應的 log 已確定建立（例如 `.agent/logs/Idx-024_log.md`）。
  - Command Palette → `IvyHouse: Clear .service/terminal_capture (after QA PASS + log)`
  - 這個命令會先檢查 `.agent/logs/<Idx-XXX>_log.md` 是否存在，並嘗試從最新的 `qa_<timestamp>_raw.log` 偵測 `[QA_DONE]` 與 `QA_RESULT=PASS`；若找不到，會要求你手動再次確認後才能繼續。

### Marker 規範

Workflow Loop 依賴工具輸出特定 marker 來判斷完成狀態：

| 角色 | 完成標記 | 說明 |
|------|----------|------|
| Engineer | `[ENGINEER_DONE]` | 實作完成後必須輸出 |
| Engineer (Fix) | `[FIX_DONE]` | 修正完成後必須輸出 |
| QA | `[QA_DONE]` | 審查完成後必須輸出 |
| QA | `QA_RESULT=PASS` 或 `QA_RESULT=FAIL` | 跟在 `[QA_DONE]` 後面，表示審查結果 |

> ⚠️ **重要**：工具必須輸出這些 marker，否則 workflow loop 會一直等待（直到 timeout）

額外限制（為避免 prompt echo 誤判）：
- marker 必須是「獨立成行」的輸出（例如最後一行單獨輸出 `[ENGINEER_DONE]`）
- 除了 marker 那一行之外，請避免在其他文字中提到 `ENGINEER_DONE` / `QA_DONE` / `FIX_DONE`

### 設定參數

在 Workspace Settings 可調整：

| 設定 | 預設值 | 說明 |
|------|--------|------|
| `ivyhouseTerminalOrchestrator.workflowPollIntervalMs` | `5000` | 每 N 毫秒掃描 log 檔案一次 |
| `ivyhouseTerminalOrchestrator.workflowMaxRounds` | `10` | 最多允許幾輪 QA（防止無限循環） |
| `ivyhouseTerminalOrchestrator.workflowTimeoutMs` | `1800000` | 總超時時間（預設 30 分鐘） |
| `ivyhouseTerminalOrchestrator.workflowTailLines` | `200` | compact tail log 保留最後 N 行 |
| `ivyhouseTerminalOrchestrator.workflowReadyTimeoutMs` | `60000` | 等待 TUI ready 的最長時間（依 raw transcript tail 判斷） |
| `ivyhouseTerminalOrchestrator.workflowReadyPollIntervalMs` | `300` | ready 判斷的輪詢間隔 |
| `ivyhouseTerminalOrchestrator.workflowSendRetryCount` | `3` | sendText 無弱 ACK 時的重試次數 |
| `ivyhouseTerminalOrchestrator.workflowSendAckTimeoutMs` | `3000` | 每次 sendText 後等待弱 ACK 的時間 |
| `ivyhouseTerminalOrchestrator.workflowSendRetryDelayMs` | `1200` | 重送之間的等待時間 |
| `ivyhouseTerminalOrchestrator.workflowPrimeEnterCount` | `2` | 送 prompt 前先送幾次空行（幫助某些 TUI 聚焦輸入） |

### Log 檔案位置

Workflow Loop 會同時產出兩種 log：

1) **Compact tail logs（建議日常看這個）**：只保留最後 N 行（預設 200 行），並「覆蓋更新」
- `.service/terminal_capture/engineer_<timestamp>.log`
- `.service/terminal_capture/qa_<timestamp>.log`

2) **Raw transcript logs（除錯用，可能很大/很雜訊）**：完整轉錄，會持續追加
- `.service/terminal_capture/engineer_<timestamp>_raw.log`
- `.service/terminal_capture/qa_<timestamp>_raw.log`

3) **Workflow events log（推薦除錯先看這個）**：JSONL，每行一筆事件（ready / send / ack / timeout）
- `.service/terminal_capture/workflow_<timestamp>_events.jsonl`

events log 會記錄：
- 哪個 terminal ready 是否逾時（`ready_wait_timeout`）
- 是否真的有送出 prompt（`send_attempt`）
- 送出後是否觀測到 transcript 變化（弱 ACK；`send_ack` / `send_no_ack`）

> 注意：events log 不會保存完整 prompt，只會寫入 `payloadLen` 與 `payloadSha256`（避免落下敏感資訊）。

這些檔案已被 `.gitignore`，不會被提交到版本控制。

> 為什麼 raw log 會很大、且 `wc -l` 行數很少？
> - Codex/OpenCode 這類互動式 CLI 常用 TUI（全螢幕 UI），輸出包含大量 ANSI escape sequences（顏色、游標移動、重繪）。
> - TUI 通常大量使用 `\r`（carriage return）而不是換行；透過 `script`（PTY transcript）或 terminal data stream 擷取時，控制碼會被原樣寫入檔案，造成「檔案很大但換行很少」。
> - compact tail log 會自動去除 ANSI/控制字元並只保留尾端 N 行，方便閱讀與 marker 偵測。

### Workflow 狀態機

```
IDLE → ENGINEERING → WAIT_ENGINEER_DONE
  → QA → WAIT_QA_DONE
    → (PASS) DONE
    → (FAIL) FIXING → WAIT_FIX_DONE → (back to QA)
```

### Troubleshooting

**問題：Workflow loop 一直卡在等待狀態**
- 確認工具有正確輸出 marker（例如 `[ENGINEER_DONE]`）
- 用 `IvyHouse: Show Workflow Status` 查看當前狀態
- 手動檢查 `.service/terminal_capture/*.log` 內容
- 優先檢查 `.service/terminal_capture/workflow_<timestamp>_events.jsonl`：
  - 若看到 `ready_wait_timeout`：提高 `workflowReadyTimeoutMs` 或檢查工具是否確實啟動成功
  - 若看到 `send_no_ack` 連續出現：可能 TUI 未接收輸入；可調高 `workflowPrimeEnterCount` 或增加 `workflowSendAckTimeoutMs`
- 若確認無法繼續，用 `IvyHouse: Stop Workflow Loop` 停止

**問題：QA 結果無法正確偵測**
- 確認 QA 工具同時輸出 `[QA_DONE]` 和 `QA_RESULT=PASS` 或 `QA_RESULT=FAIL`
- 這兩個標記必須在同一次輸出中出現，且各自獨立成行

**問題：達到 max rounds 上限**
- 檢查是否陷入 FAIL 循環（修正後仍然 FAIL）
- 考慮調高 `workflowMaxRounds`，或手動介入修正

**問題：Log 檔案沒有內容**
- 若環境沒有 `script` 命令，且 Proposed API 未啟用，log capture 可能不完整
- 建議啟用 Proposed API（參考上方「Codex 輸出擷取」章節）或安裝 `util-linux` 套件
