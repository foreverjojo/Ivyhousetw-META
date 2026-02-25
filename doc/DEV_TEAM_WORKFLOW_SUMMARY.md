# Dev-Team Workflow — 精簡流程

觸發 : 使用者輸入 `/dev`（或相容別名 `/dev-team`）或請求「啟動開發團隊」。

流程總覽：

Planner -> Meta Expert -> (Execution Gate) -> Engineer -> QA -> 完成

簡要步驟：

- Step 1 Planner
  - 掃描專案並撰寫 Spec（`doc/plans/Idx-NNN_plan.md`）。
  - 必須等待使用者確認後才進入下一步。

- Step 2 Meta Expert
  - 若含數據或 Meta API：檢核公式與串接建議；否則可跳過。

- Step 2.5 執行工具選擇（Execution Gate）
  - 由 GitHub Copilot Chat（Coordinator）詢問用戶選擇：
    - Engineer Tool：`codex-cli` 或 `opencode`
    - QA Tool：`codex-cli` 或 `opencode`（必須 ≠ last_change_tool）
    - Execution Backend Policy：`extension-sendtext-required`（固定）
    - Monitor Backend Policy：`proposed-primary-with-extension-fallback`（預設）
  - 在 Plan 的 `EXECUTION_BLOCK` 記錄：工具/操作者/時間戳/結果/last_change_tool。

- Step 3 Engineer
  - 由用戶指定的終端工具（Codex CLI / OpenCode CLI）執行 Plan。
  - Coordinator 透過 extension sendText 注入指令/Plan 文字（禁止以 bash/TTY 代送，避免 overlay 或工具退出）。
  - 注入命令（Command IDs）：`ivyhouseTerminalInjector.sendLiteralToCodex` / `ivyhouseTerminalInjector.sendLiteralToOpenCode`。
  - 監控主路徑使用 Proposed API；若不可用，切換 extension 監測模式備援。
  - 監測命令（Command IDs）：`ivyhouseTerminalMonitor.autoCaptureCodexStatus` / `ivyhouseTerminalMonitor.verifyCodexStatusInjection`。
  - 通用規範：中文註解、單檔 ≤500 行、無硬編 API Key、遵守 `ivy_house_rules.md`。

- Step 4 QA（Cross‑QA）
  - QA 工具必須與 **last_change_tool** 不同（Codex CLI ⇄ OpenCode CLI）。
  - 執行 checklist（安全、註解、規範、邏輯正確性等）。
  - 若不通過：允許 QA 工具提出修正建議並修正，但修正後必須更新 `last_change_tool`，並交叉改用另一工具再 QA（可重入迴圈，建議最多 3 輪）。

產出與交付：

- Spec: `doc/plans/Idx-XXX_plan.md`（待用戶確認）
- 實作紀錄: `.agent/execution_log.jsonl`
- 完成後: Coordinator 產生 `doc/logs/Idx-XXX_log.md`，並**保留** `doc/plans/Idx-XXX_plan.md`（不刪除）。

監控與回滾：

- 監控：Coordinator 使用 VS Code Proposed API 監測終端輸出（completion marker + timeout）。
- 備援：若 Proposed API 不可用，先走 `ivyhouse_monitor_extension_fallback`；仍不可用才改人工回報。
- 架構：允許拆分成兩個 extension（Injector 負責 sendText；Monitor 負責監測 fallback）。
- Deprecated：Orchestrator（`ivyhouseTerminalOrchestrator.*`）為 legacy，相容用途以外不得依賴。
- 回滾：任何破壞性 git 操作（reset/clean）必須先取得用戶明確確認。

快速 checklist（分享用）

- 確認 Spec 已由使用者核准。
- 在 Plan 的 `EXECUTION_BLOCK` 指定 executor_tool/qa_tool/last_change_tool。
- 在 Plan 的 `EXECUTION_BLOCK` 指定 execution_backend_policy/executor_backend/monitor_backend。
- 確認命令注入固定使用 extension sendText，監測採 Proposed API 主路徑 + extension fallback。
- QA 工具必須與 last_change_tool 不同。
- 無硬編 API Key，且檔案有中文用途註解。

參考原始流程檔案：`.agent/workflows/dev-team.md`
