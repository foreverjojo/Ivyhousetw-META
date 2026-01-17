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
  - 在 Plan 的 `EXECUTION_BLOCK` 記錄：工具/操作者/時間戳/結果/last_change_tool。

- Step 3 Engineer
  - 由用戶指定的終端工具（Codex CLI / OpenCode CLI）執行 Plan。
  - Coordinator 透過 VS Code 內建 `terminal.sendText` 注入指令/Plan 文字（禁止以 bash 腳本代送，避免工具退出）。
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
- 回滾：任何破壞性 git 操作（reset/clean）必須先取得用戶明確確認。

快速 checklist（分享用）

- 確認 Spec 已由使用者核准。
- 在 Plan 的 `EXECUTION_BLOCK` 指定 executor_tool/qa_tool/last_change_tool。
- QA 工具必須與 last_change_tool 不同。
- 無硬編 API Key，且檔案有中文用途註解。

參考原始流程檔案：`.agent/workflows/dev-team.md`
