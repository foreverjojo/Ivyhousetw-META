# Idx-020 執行記錄

**Plan**: `.agent/plans/Idx-020_terminal_autostart_sendtext_plan.md`

**Plan Version**: 2026-01-20-v1
**Priority**: P1
**Status**: ENGINEER_DONE
**Date**: 2026-01-20

## Summary

- 新增 local VS Code extension：自動建立/啟動 `Codex CLI` 與 `OpenCode CLI` 兩個互動 terminal。
- 所有啟動與後續指令下達皆使用 `terminal.sendText()`，避免 terminal collision 導致長期服務退出。
- 提供安裝腳本：在 devcontainer / vscode-server 環境以 symlink 方式安裝。

## Files

- `tools/vscode_terminal_orchestrator/package.json`
- `tools/vscode_terminal_orchestrator/extension.js`
- `tools/vscode_terminal_orchestrator/README.md`
- `scripts/vscode/install_terminal_orchestrator.sh`

## Verification

- `pytest -q`（既有測試全數通過；golden file 測試依原狀 skip）

## Manual Steps

1. `bash scripts/vscode/install_terminal_orchestrator.sh`
2. VS Code: `Developer: Reload Window`
3. Terminal panel 會出現 `Codex CLI` / `OpenCode CLI`
