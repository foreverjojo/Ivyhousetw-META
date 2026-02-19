# Idx-009 第三輪 QA 執行指引

## 背景
由於 Codex CLI 的互動模式設計（需要 TTY），自動化輸入方式（tmux send-keys / exec / PowerShell）都不穩定。

## 建議執行方式

### 選項 1：手動在 Terminal 執行（最可靠）

1. 開啟新的 VS Code Terminal
2. 執行 `codex`
3. 貼上以下 prompt：

```
請針對本 repo 的 Idx-009（Terminal Management）做第三輪 QA，特別檢查以下一致性：

1) execution 欄位允許值與 doc/plans/Idx-009_plan.md 實填一致（允許值是 copilot/codex-cli）
2) Rollback L2 的文件描述需與 .agent/scripts/run_codex_template.sh 的實作一致（使用 .agent/.pre_execution_backup.patch 還原）
3) .agent/scripts/terminal_manager_tmux.sh 若需要 jq，需有清楚的依賴說明或 graceful fallback

請審查以下檔案：
- doc/plans/Idx-009_plan.md
- .agent/TERMINAL_MANAGEMENT.md
- .agent/scripts/run_codex_template.sh
- .agent/scripts/terminal_manager_tmux.sh
- .agent/scripts/codex_tmux_send.sh

請輸出完整 QA 報告（Markdown 格式），並在最後給出明確的最終判定：PASS 或 FAIL。
```

4. 等待 Codex 完成後，把結果存到 `.agent/.qa_round3_report.md`

### 選項 2：改用 GitHub Copilot（更快但不符合 Cross-QA）

如果接受 Copilot 自 QA（雖然 Executor 也是 Copilot），可以在 Chat 中執行：

```
@workspace 請依照 .agent/roles/qa.md 審查 Idx-009，重點檢查：
1. execution 欄位一致性（Plan vs 文件）
2. L2 rollback 描述與實作一致
3. jq 依賴有 fallback

給出 PASS/FAIL。
```

## 已修正的問題（本輪）

為通過第三輪 QA，已修正：
- ✅ Idx-009 Plan execution 欄位改為 `copilot`（符合允許值）
- ✅ L2 rollback 描述與 run_codex_template.sh 實作一致（patch + reset）
- ✅ terminal_manager_tmux.sh 對 jq 加入 graceful fallback
- ✅ TERMINAL_MANAGEMENT.md 補充 jq 為可選依賴
- ✅ 新增 codex_tmux_send.sh 輔助腳本（使用 tmux paste-buffer）

## 技術發現

**Codex CLI 自動化限制**（基於 2026-01-12 v0.80.0 實測）：
- `codex` 互動模式無法從 stdin 讀取（要求 TTY）
- `codex exec` 雖號稱非互動，但仍會偵測 TTY 並可能失敗
- `tmux send-keys` 對大量輸入不穩定（Codex 有自己的 TUI 狀態）
- `script` + `codex` 會遇到 cursor position 錯誤

**結論**：Codex CLI 就是設計給「人類在真實 terminal 使用」，強行自動化會碰到各種 TTY/TUI 問題。
