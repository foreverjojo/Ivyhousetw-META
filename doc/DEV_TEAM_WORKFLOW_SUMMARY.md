# Dev-Team Workflow — 精簡流程

觸發 : 使用者輸入 `/dev-team` 或請求「啟動開發團隊」。

流程總覽：

Planner -> Meta Expert -> (Execution Gate) -> Engineer -> QA -> 完成

簡要步驟：

- Step 1 Planner
  - 掃描專案並撰寫 Spec（`doc/plans/Idx-NNN_plan.md`）。
  - 必須等待使用者確認後才進入下一步。

- Step 2 Meta Expert
  - 若含數據或 Meta API：檢核公式與串接建議；否則可跳過。

- Step 2.5 執行工具選擇（Execution Gate）
  - 在 Plan 中寫入 `execution: [copilot|codex-cli]`。
  - 選擇依任務複雜度與即時性決定執行工具。

- Step 3 Engineer
  - 模式 A (Copilot)：小規模變更、IDE 即時互動。
  - 模式 B (Codex CLI)：批次處理、大量檔案、使用 `.agent/scripts/run_codex_template.sh`。
  - 通用規範：中文註解、單檔 ≤500 行、無硬編 API Key、遵守 `ivy_house_rules.md`。

- Step 4 QA（Cross‑QA）
  - QA 工具必須與 Executor 不同（Copilot ⇄ Codex CLI）。
  - 執行 checklist（安全、註解、規範、邏輯正確性等）。
  - 若不通過，回到 Step 3 修正並重審。

產出與交付：

- Spec: `doc/plans/Idx-XXX_plan.md`（待用戶確認）
- 實作紀錄: `.agent/execution_log.jsonl`
- 完成後: 轉為 `doc/logs/Idx-XXX_log.md` 並刪除 plans 檔，執行 `git commit`。

監控與回滾：

- 支援 Terminal Bridge Server `/wait` 以監控 git 狀態。
- 失敗時可觸發 L2 Rollback（需乾淨 worktree）。

快速 checklist（分享用）

- 確認 Spec 已由使用者核准。
- 在 Plan 中指定 `execution`（copilot 或 codex-cli）。
- Executor 與 QA 工具不得相同。
- 無硬編 API Key，且檔案有中文用途註解。

參考原始流程檔案：`.agent/workflows/dev-team.md`
