# Idx-020 Plan: Auto-start Codex/OpenCode in visible interactive terminals via sendText

> 本 Plan 屬於 **workflow / dev environment** 類型，Index 應登記於 `.agent/Workflow_Plan_index.md`。

## Goal / Objective

- 讓 `codex` 與 `opencode` 能 **自動啟動**
- 並且各自佔住一個 **可見的互動 VS Code terminal**
- 且對這兩個 terminal 的啟動與後續指令下達 **只允許使用 VS Code 的 `terminal.sendText()` 方式**
- 其他一般命令（git/pytest/ruff/ps…）統一在第三個 terminal（例如 `Project`）執行

## Acceptance Criteria

1. 開啟 workspace 後（Reload Window 或重新 attach devcontainer），會看到：
   - `Codex CLI` terminal（已送出 `codex` 啟動指令）
   - `OpenCode CLI` terminal（已送出 `opencode --port 35103` 啟動指令）
2. 啟動與後續輸入都透過 `sendText`，不再依賴復用 terminal 來跑 shell command
3. 有手動指令可重新啟動/重新送出命令
4. 有安裝腳本可在 devcontainer 環境安裝本地 extension
5. 既有 tests 仍可通過（pytest）

## Implementation

- 新增一個 **local VS Code extension**（純 JS，無 build step）：
  - autoStart：onStartupFinished 時建立/找回兩個 terminal，並用 `terminal.sendText` 啟動
  - commands：Start Codex / Start OpenCode / Start All / Send Text
  - 防重複：用 workspaceState 記錄本次 session 是否已送過 start 指令
- 新增安裝腳本：將 extension symlink 到 `$HOME/.vscode-server/extensions/`

## Files to Change (Allowlist)

- `tools/vscode_terminal_orchestrator/**`
- `scripts/vscode/install_terminal_orchestrator.sh`
- `.agent/Workflow_Plan_index.md`
- `.agent/plans/Idx-020_terminal_autostart_sendtext_plan.md`
- `.agent/logs/Idx-020_log.md`
- （可選）`doc/*`（說明文件）

## Risks / Notes

- extension 需安裝一次；完成後 Reload Window 才會生效。
- autoStart 只保證「送出啟動命令」，若 CLI 本身因環境/權限退出，需再補診斷。
