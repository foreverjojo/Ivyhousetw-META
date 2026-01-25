# IvyHouse Terminal Orchestrator (local VS Code extension)

目的：
- 自動啟動並維持兩個「可見的互動 VS Code terminal」：
  - `Codex CLI`
  - `OpenCode CLI`
- **提供 SendText Bridge（HTTP API）**：允許 Coordinator（如 GitHub Copilot Chat）透過 HTTP 對這些終端注入指令
- **所有對這兩個 terminal 的啟動/指令下達都透過 `terminal.sendText()`**（避免 terminal collision 的覆寫問題）。

---

## HTTP SendText Bridge

### 功能

SendText Bridge 是一個 **localhost-only HTTP API**，讓 Coordinator 可以透過 HTTP 請求對 Codex/OpenCode 終端注入指令。

**安全性**：
- **localhost-only**：僅監聽 `127.0.0.1`（硬規則）
- **Token 認證**：所有 API 請求必須提供 Bearer token
- **Terminal 白名單**：僅允許對 `Codex CLI` / `OpenCode CLI` 注入
- **Rate Limiting**：預設 1 req/sec（burst 2）
- **Fail-closed**：任何配置/認證失敗都會拒絕所有請求

### 設定

**Token 來源（按優先順序）**：
1. 環境變數：`IVY_SENDTEXT_BRIDGE_TOKEN`
2. Token 檔案：`.service/sendtext_bridge/token`

**Workspace Settings**：
- `ivyhouseTerminalOrchestrator.sendtextBridgeEnabled`（預設 `true`）
- `ivyhouseTerminalOrchestrator.sendtextBridgeHost`（固定 `127.0.0.1`）
- `ivyhouseTerminalOrchestrator.sendtextBridgePort`（預設 `8765`）
- `ivyhouseTerminalOrchestrator.sendtextBridgeMaxPayloadBytes`（預設 `32768`，32 KiB）
- `ivyhouseTerminalOrchestrator.sendtextBridgeMaxRequestBytes`（預設 `65536`，64 KiB）
- `ivyhouseTerminalOrchestrator.sendtextBridgeRateLimit`（預設 `1.0`，每秒請求數）
- `ivyhouseTerminalOrchestrator.sendtextBridgeRateBurst`（預設 `2`）

### API Endpoints

#### `GET /healthz`
健康檢查。

**Response**：
```json
{
  "status": "ok",
  "ts": "2026-01-22T12:00:00.000Z"
}
```

#### `POST /send`
對指定終端注入文字（使用 Idx-024 normalize + chunk pipeline）。

**Request**：
```json
{
  "terminalKind": "codex",
  "text": "請完成 Idx-025 的實作",
  "submit": false,
  "mode": "single"
}
```

**Parameters**：
- `terminalKind`（必填）：`"codex"` 或 `"opencode"`
- `text`（必填）：要傳送的文字
- `submit`（選填，預設 `false`）：是否在傳送後按 Enter
- `mode`（選填，預設 `"single"`）：`"single"` 或 `"chunked"`（chunked 模式會自動切分超長文字）

**Headers**：
- `Authorization: Bearer <token>` 或 `X-Ivy-Token: <token>`

**Response**：
```json
{
  "status": "sent",
  "terminalKind": "codex",
  "textBytes": 72
}
```

#### `POST /workflow/start`
從 Plan 啟動 workflow（提取 Goal（目標）與 SPEC 章節，包含 Goal/Non-goals 子章節）。

**Request**：
```json
{
  "planId": "Idx-025",
  "scope": "workflow"
}
```

**Scope 說明**：
- `workflow`：`.agent/plans/Idx-XXX_plan.md`
- `project`：`doc/plans/Idx-XXX_plan.md`

**Response**：
```json
{
  "status": "started",
  "workflowRunId": "wf_20260122120000_abc123",
  "planId": "Idx-025",
  "extractedSections": "..."
}
```

#### `GET /workflow/status`
取得 workflow 狀態。

**Response**：
```json
{
  "workflowRunId": "wf_20260122120000_abc123",
  "planId": "Idx-025",
  "state": "running",
  "startedAtIso": "2026-01-22T12:00:00.000Z",
  "lastOutputTs": "2026-01-22T12:05:00.000Z",
  "lastRawLogSizeBytes": 123456,
  "lastOutputSource": "active_engineer"
}
```

**State 值**：
- `starting`: 正在啟動
- `running`: 執行中
- `paused`: 已暫停（例如 timeout 等待用戶選擇）
- `idle`: 閒置
- `completed`: 已完成
- `error`: 錯誤
- `interrupted`: 被中斷（例如 reload）

**lastOutputSource 值**：
- `active_engineer`: 使用 active workflow 的 engineer raw log
- `active_qa`: 使用 active workflow 的 QA raw log
- `persisted_engineer`: 使用 persisted 的 engineer raw log（same workflowRunId）
- `persisted_qa`: 使用 persisted 的 QA raw log（same workflowRunId）
- `raw_log_not_found`: 找不到 raw log
- `none`: 無 raw log 資訊

### Python 客戶端

使用 `scripts/sendtext_bridge_client.py`：

```bash
# Health check
python scripts/sendtext_bridge_client.py healthz

# 對終端注入文字（預設不按 Enter）
python scripts/sendtext_bridge_client.py send \
  --terminal-kind codex \
  --text "請完成 Idx-025 的實作"

# 對終端注入文字並按 Enter
python scripts/sendtext_bridge_client.py send \
  --terminal-kind codex \
  --text "請完成 Idx-025 的實作" \
  --submit

# 對終端注入文字（chunked 模式，適合長文字）
python scripts/sendtext_bridge_client.py send \
  --terminal-kind codex \
  --text "很長的文字..." \
  --mode chunked

# 從 Plan 啟動 workflow
python scripts/sendtext_bridge_client.py workflow-start \
  --plan-id Idx-025 \
  --scope workflow

# 查詢 workflow 狀態
python scripts/sendtext_bridge_client.py workflow-status
```

### Audit Log

所有 bridge 請求都會記錄在 `.service/terminal_capture/sendtext_bridge_events.jsonl`，格式：

```jsonl
{"ts":"2026-01-22T12:00:00.000Z","endpoint":"/send","result":"success","requestId":"req_abc123","terminalKind":"codex","submit":false,"mode":"single","textBytes":72,"payloadSha256":"abc123...","tokenHash":"def456...","ip":"127.0.0.1"}
```

---

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
- `ivyhouseTerminalOrchestrator.workflowPollIntervalMs`（預設 `10000`）
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

- **extension.js 檔案長度**：目前 ~3400 行，已超過建議的主程式上限（800 行）。未來應考慮拆分為：
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
- 偵測特定 marker（`WORKFLOW_MARKERS.engineerDone`、`WORKFLOW_MARKERS.qaDone`、`WORKFLOW_MARKERS.fixDone`）來推進狀態機
- 當 QA 回報不通過（對應 `WORKFLOW_MARKERS.qaFail`）時，自動將問題摘要送回 Engineer 要求修正
- 直到 QA 回報通過（對應 `WORKFLOW_MARKERS.qaPass`），或達到 timeout/max rounds 上限

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
   - 注意：若在 window reload 後重新啟動 extension，會自動將先前的 workflow 標記為 `interrupted_by_reload`

4. **（收尾）清空 `.service/terminal_capture/`**：
  - 自動提示：當你在啟動 Workflow Loop 時於「Associated Idx」欄位填入 `Idx-XXX`，且在執行中偵測到 QA 通過（對應 `WORKFLOW_MARKERS.qaPass`），若 `.agent/logs/Idx-XXX_log.md` 已存在，extension 會自動彈出 modal 提示是否清空 `.service/terminal_capture/`（此行為可透過設定 `ivyhouseTerminalOrchestrator.workflowPromptClearCaptureOnPass` 關閉）。
  - 前提：QA 已回報通過（對應 `WORKFLOW_MARKERS.qaPass`），且對應的 log 已確定建立（例如 `.agent/logs/Idx-024_log.md`）。
  - Command Palette → `IvyHouse: Clear .service/terminal_capture (after QA PASS + log)`
  - 這個命令會先檢查 `.agent/logs/<Idx-XXX>_log.md` 是否存在，並嘗試從最新的 `qa_<timestamp>_raw.log` 偵測 `WORKFLOW_MARKERS.qaDone` 與 `WORKFLOW_MARKERS.qaPass`；若找不到，會要求你手動再次確認後才能繼續。

### Marker 規範（Idx-030 統一格式）

Workflow Loop 依賴工具輸出特定 marker 來判斷完成狀態。

**格式版本**：Idx-030（統一 5 行格式）

#### Engineer / QA / Fix 統一完成格式

所有角色（Engineer、QA、Fix）現在使用統一的 **5 行格式**：

```
<COMPLETION_MARKER>  // Engineer: WORKFLOW_MARKERS.engineerDone
                     // QA: WORKFLOW_MARKERS.qaDone
                     // Fix: WORKFLOW_MARKERS.fixDone
TIMESTAMP=YYYY-MM-DDTHH:mm:ssZ
NONCE=<8-16位16進位字符>
TASK_ID=Idx-XXX
<角色特定結果行>
```

> **註**：實際輸出時，第 1 行必須是對應的 marker（帶方括號），但此 README 不直接展示字面值以避免污染 marker buffer。請參考 extension.js 中的 `WORKFLOW_MARKERS` 常數定義。

**角色特定結果行**：
- Engineer: `ENGINEER_RESULT=COMPLETE`
- QA: `QA_RESULT=PASS` 或 `QA_RESULT=FAIL`
- Fix: `FIX_ROUND=N`（N 為當前修正輪次）

**範例**：

> **重要**：以下範例中的 `<MARKER>` 占位符代表實際的 completion marker。實際輸出時必須使用對應的 marker 常數（見 `WORKFLOW_MARKERS` 定義），但為避免污染 marker buffer，此 README 不直接展示字面值。

**Engineer 完成**：
```
<WORKFLOW_MARKERS.engineerDone>
TIMESTAMP=2026-01-23T14:30:00Z
NONCE=a3f9d8e2c4b5e6f7
TASK_ID=Idx-030
ENGINEER_RESULT=COMPLETE
```

**QA 通過**：
```
<WORKFLOW_MARKERS.qaDone>
TIMESTAMP=2026-01-23T14:35:00Z
NONCE=a3f9d8e2c4b5e6f7
TASK_ID=Idx-030
QA_RESULT=PASS
```

**Fix 完成**：
```
<WORKFLOW_MARKERS.fixDone>
TIMESTAMP=2026-01-23T14:40:00Z
NONCE=a3f9d8e2c4b5e6f7
TASK_ID=Idx-030
FIX_ROUND=1
```

#### 重要規則

> ⚠️ **關鍵要求**：
> 1. 這 5 行必須是輸出的**最後 5 個非空行**
> 2. 每一行必須**獨立成行**（不要合併）
> 3. TIMESTAMP 必須是 **UTC 時區**（以 `Z` 結尾）
> 4. NONCE 必須與 session nonce **完全一致**（系統會在 workflow 啟動時通過環境變數 `WORKFLOW_SESSION_NONCE` 注入）
>    - ⚠️ **禁止輸出字面值**：不要輸出 `$WORKFLOW_SESSION_NONCE` 或 `<nonce>` 等 placeholder，必須輸出實際的 hex 值
> 5. TASK_ID 必須匹配當前任務 ID
> 6. 除了最後 5 行以外，**不要在其他地方提到任何 marker 文字**（避免誤判）

#### Session Nonce 機制

- 每次 workflow 啟動時，系統會生成一個隨機的 8-16 字元 hex nonce（例如 `a3f9d8e2c4b5e6f7`）
- 此 nonce 會通過環境變數 `WORKFLOW_SESSION_NONCE` 注入到 Engineer 和 QA 終端
- 工具必須從環境變數讀取並在完成格式中回顯此 nonce
- 這個機制用於：
  - **隔離不同 workflow session**：防止舊 log 中的 marker 被新 session 誤判
  - **延遲驗證**：系統會在首次檢測到完成格式時驗證 env 是否正確注入

#### Near-Miss Detection 與 Nudge 機制

當工具輸出接近正確格式但有錯誤時（near-miss），系統會：
1. 偵測具體問題（例如：缺少 TIMESTAMP、NONCE 不匹配等）
2. 向工具發送**糾正提示（nudge）**，說明具體問題
3. 最多 nudge **3 次**（每個階段獨立計數）
4. 若 3 次後仍未正確，workflow 停止並標記為 phase-specific reason：
   - Engineer 階段：`engineer_completion_verification_exhausted`
   - QA 階段：`qa_completion_verification_exhausted`
   - Fix 階段：`fix_completion_verification_exhausted`

**常見 near-miss 類型**：
- 缺少某一行（例如缺少 TIMESTAMP）
- 格式錯誤（例如 TIMESTAMP 不是 ISO 8601 格式）
- NONCE 不匹配
- TASK_ID 不匹配
- 結果值無效（例如 QA_RESULT 不是 PASS 或 FAIL）

### 設定參數

在 Workspace Settings 可調整：

| 設定 | 預設值 | 說明 |
|------|--------|------|
| `ivyhouseTerminalOrchestrator.workflowPollIntervalMs` | `10000` | 每 N 毫秒掃描 log 檔案一次 |
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
    → (QA 通過) DONE
    → (QA 不通過) FIXING → WAIT_FIX_DONE → (back to QA)
```

### Timeout 行為

當 workflow 達到 timeout（預設 30 分鐘）時：
- **不會自動停止 workflow**，而是暫停 polling 並彈出 VS Code modal
- Modal 提供三個選項：
  1. **Abort**：中止 workflow
  2. **Allow +5m**：延長 5 分鐘超時時間
  3. **Allow +30m (this run)**：延長 30 分鐘超時時間（僅限本次執行）
- 選擇後會記錄到 workflow events log
- 這個設計避免在工具仍在執行時強制中止，造成狀態不一致

### Troubleshooting

**問題：Workflow loop 一直卡在等待狀態**
- 確認工具有正確輸出 marker（例如 `WORKFLOW_MARKERS.engineerDone` 對應的 marker）
- 用 `IvyHouse: Show Workflow Status` 查看當前狀態
- 手動檢查 `.service/terminal_capture/*.log` 內容
- 優先檢查 `.service/terminal_capture/workflow_<timestamp>_events.jsonl`：
  - 若看到 `ready_wait_timeout`：提高 `workflowReadyTimeoutMs` 或檢查工具是否確實啟動成功
  - 若看到 `send_no_ack` 連續出現：可能 TUI 未接收輸入；可調高 `workflowPrimeEnterCount` 或增加 `workflowSendAckTimeoutMs`
- 若確認無法繼續，用 `IvyHouse: Stop Workflow Loop` 停止

**問題：QA 結果無法正確偵測**
- 確認 QA 工具有輸出完整的 Idx-030 格式（5 行）
- 檢查輸出的最後 5 個非空行是否符合格式（可查看 `.service/terminal_capture/qa_<timestamp>_raw.log`）
- 確認 NONCE 是否匹配（從環境變數讀取，不是字面值 `$WORKFLOW_SESSION_NONCE`）
- 若系統發送 nudge，請依照提示修正後重新輸出

**問題：達到 max rounds 上限**
- 檢查是否陷入不通過循環（修正後仍然不通過）
- 考慮調高 `workflowMaxRounds`，或手動介入修正

**問題：Log 檔案沒有內容**
- 若環境沒有 `script` 命令，且 Proposed API 未啟用，log capture 可能不完整
- 建議啟用 Proposed API（參考上方「Codex 輸出擷取」章節）或安裝 `util-linux` 套件
