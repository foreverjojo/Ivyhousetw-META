# Log: Idx-024

**Index**: Idx-024
**Date**: 2026-01-21
**Goal**: Workflow Loop Reliability Hardening（ready/retry/observability）

---

## ✅ 結果摘要

- Workflow Loop 注入流程改為「ready gate → send retry + 弱 ACK → 才開始輪詢」，避免 CLI 還沒 ready 就 sendText 導致任務完全沒開始。
- 新增 workflow events log：`.service/terminal_capture/workflow_<ts>_events.jsonl`（JSONL），記錄 ready / send / ack / timeout / stop；不落完整 prompt（只記錄長度與 sha256）。
- 新增可調設定（timeout/retry/prime enter），並文件化 troubleshooting：遇到卡住先看 events log 判斷是 ready timeout 或 send 無 ACK。
- 新增「受保護清理」命令：僅在 QA PASS 且 `.agent/logs/Idx-024_log.md` 已存在後，才允許清空 `.service/terminal_capture/`（避免清掉稽核/除錯證據）。

---

## 🧭 Plan / Gate

- Plan: `.agent/plans/Idx-024_plan.md`
- Plan validator: PASS
  - `python .agent/skills/plan_validator.py .agent/plans/Idx-024_plan.md`

---

## 🔧 變更清單（Idx-024 白名單內）

- `tools/vscode_terminal_orchestrator/extension.js`
  - Ready gate：以 raw transcript tail（清理 ANSI/CR）判斷 Codex/OpenCode 是否進入可接收輸入狀態。
  - 注入重試：sendText 後等待 raw log size 或 tail fingerprint 變化作弱 ACK；無 ACK 則有限次重試並記錄事件。
  - Events log：workflow 事件以 JSONL 落地（避免存完整 prompt）。
  - Poller 防重入：`workflowTick` 改為 async 並用 `tickBusy` 防止重入。
- `tools/vscode_terminal_orchestrator/package.json`
  - 新增 workflow 設定項：ready timeout / retry / ack timeout / retry delay / prime enter。
- `tools/vscode_terminal_orchestrator/README.md`
  - 補上 workflow events log 與 troubleshooting 指引。
  - 補上「QA PASS + log 存在後才清空 `.service/terminal_capture/`」的收尾流程。

---

## 🧪 驗證

- 靜態檢查：
  - `node --check tools/vscode_terminal_orchestrator/extension.js`（syntax OK）
  - `node -e "JSON.parse(fs.readFileSync('tools/vscode_terminal_orchestrator/package.json'))"`（JSON OK）

- 手動 smoke test（需要在 VS Code 內執行；本 log 先提供可重跑步驟）：
  1) 安裝 extension：`bash scripts/vscode/install_terminal_orchestrator.sh`
  2) VS Code：`Developer: Reload Window`
  3) Command Palette：`IvyHouse: Start Workflow Loop (Engineer→QA→Fix)`
     - Engineer terminal：`OpenCode CLI`
     - QA terminal：`Codex CLI`
     - 任務描述建議用「快測」：
       - 例：`請回覆一行 OK，然後在最後一行單獨輸出 [ENGINEER_DONE]。`
  4) 檢查 `.service/terminal_capture/workflow_<ts>_events.jsonl`：
     - 期望看到：`ready_ok` → `send_attempt` → `send_ack`
     - 若看到 `ready_wait_timeout`：提高 `ivyhouseTerminalOrchestrator.workflowReadyTimeoutMs`
     - 若看到 `send_no_ack` 連續：提高 `workflowSendAckTimeoutMs` 或 `workflowPrimeEnterCount`，或增加 `workflowSendRetryCount`

    5) （收尾）若 QA 已輸出 `QA_RESULT=PASS` 且此 log 檔已存在：
      - Command Palette → `IvyHouse: Clear .service/terminal_capture (after QA PASS + log)`
      - 輸入 `Idx-024`
      - 期望：命令會先檢查 `.agent/logs/Idx-024_log.md` 存在，並嘗試從最新的 `qa_<timestamp>_raw.log` 偵測 PASS；通過後才會清空 `.service/terminal_capture/`。

    6) （自動提示 Smoke Test）在 Workflow Loop 啟動時於「Associated Idx」填入 `Idx-024`：
      - 啟動 Workflow Loop 並以正常流程讓 QA 輸出 `[QA_DONE]` 與 `QA_RESULT=PASS`。
      - 期望：extension 自動彈出 modal 提示是否清空 `.service/terminal_capture/`（若 `.agent/logs/Idx-024_log.md` 可被找到）；選擇 `清空` 會顯示刪除數量的第二次確認，確認後會清空並在 events log 補上 `cleanup_done` 事件。

- 實測結果（2026-01-21）：
  - 已觸發 PASS 後自動提示清理流程，並完成清理。
  - events log：`.service/terminal_capture/workflow_20260121042916_events.jsonl`
    - `{"action":"cleanup_done","idx":"Idx-024","removed":9,...}`
    - `{"action":"workflow_stop","reason":"PASS",...}`
  - 注意：若選擇「清空」，會刪除 `.service/terminal_capture/` 內包含 events/raw logs 在內的檔案；因此 events 檔可能只保留清理後重新 append 的尾端事件（屬預期行為）。

---

## 🔍 風險與限制

- 本次在 chat 工具側無法直接觸發 VS Code Command Palette，因此無法在此 log 內直接附上「已實測 PASS」的證據；需依上述步驟在 VS Code 內跑一次。
- retry 可能造成 prompt 重送；已在重送 payload 末尾加上「若已開始處理請忽略」以降低重複工作風險。

## ✅ Implementation
- Code changes committed on branch `feature/idx-024-clear-on-pass` (commit `28ce69b`).
- Added config: `ivyhouseTerminalOrchestrator.workflowPromptClearCaptureOnPass` (default true).
- Added optional `Associated Idx` input when starting a workflow run and `idxName` tracking.
- Implemented auto prompt helper that appears when QA PASS is detected and `.agent/logs/<Idx>_log.md` exists; includes double-confirm flow and event logging.
- README updated to document behavior and setting.

---

[ENGINEER_DONE]
