# IvyHouse Terminal Monitor

專責 **終端輸出監測** 的 VS Code extension。

## 責任範圍

- 主路徑：使用 Proposed API（`onDidWriteTerminalData`）監測輸出。
- 備援：若 Proposed API 不可用，改用 shell integration stream 作 fallback capture。
- 不直接承擔一般注入職責；送指令預設呼叫 Injector extension 的命令。

## 換機快速落地（建議）

1. 安裝推薦 extensions（含 ivyhouse-local IDs）：
   - `bash scripts/portable/install_extensions.sh`
   - Windows：`powershell -ExecutionPolicy Bypass -File scripts/portable/install_extensions.ps1`
2. 在 Dev Container 內安裝 local extension symlink：
   - `bash scripts/vscode/install_terminal_orchestrator.sh`
3. VS Code 執行：`Developer: Reload Window`

## Required: argv.json 啟用 Proposed API

Monitor 主路徑依賴 `onDidWriteTerminalData`（Proposed API）。請在 runtime `argv.json` 加入：

- Windows Stable：`%APPDATA%\\Code\\User\\argv.json`
- Windows Insiders：`%APPDATA%\\Code - Insiders\\User\\argv.json`
- macOS Stable：`~/Library/Application Support/Code/User/argv.json`
- macOS Insiders：`~/Library/Application Support/Code - Insiders/User/argv.json`
- Linux Stable：`~/.config/Code/User/argv.json`
- Linux Insiders：`~/.config/Code - Insiders/User/argv.json`

```json
{
  "enable-proposed-api": [
    "ivyhouse-local.ivyhouse-terminal-monitor",
    "ivyhouse-local.ivyhouse-terminal-orchestrator"
  ]
}
```

> 可用 `Preferences: Configure Runtime Arguments` 開啟檔案；儲存後請完整關閉並重啟 VS Code。

## 主要命令

- `IvyHouse Monitor: Capture Codex Output`
- `IvyHouse Monitor: Auto-Capture Codex /status`
- `IvyHouse Monitor: Restart Codex + Auto-Capture /status`
- `IvyHouse Monitor: Verify Codex /status Injection`
- `IvyHouse Monitor: Open Last Codex Capture`
- `IvyHouse Monitor: Clear Codex Capture`
- `IvyHouse Monitor: Codex Capture Diagnostics`

## 依賴

- 建議與 `ivyhouse-terminal-injector` 一起安裝，Monitor 會呼叫：
  - `ivyhouseTerminalInjector.sendLiteralToCodex`
  - `ivyhouseTerminalInjector.restartCodex`

## 資料落地路徑（重要）

Monitor 會寫入工作區以下資料夾（預設）：

- `.service/terminal_capture/monitor_debug.jsonl`：啟用狀態與事件（含 `proposed_api true/false`）
- `.service/terminal_capture/codex_live.txt`：Codex rolling capture
- `.service/terminal_capture/opencode_live.txt`：OpenCode rolling capture
- `.service/terminal_capture/codex_last.txt`：單次 capture 暫存

建議把 `.service/` 視為 runtime 資料夾，不納入版本控管。

## 快速驗證

1. 命令面板執行 `IvyHouse Monitor: Ping`
2. 檢查 `monitor_debug.jsonl` 是否出現 `"type":"proposed_api","onDidWriteTerminalData":true`
3. 執行 `IvyHouse Monitor: Auto-Capture Codex /status` 檢查 capture 是否落檔

## 打包

在此資料夾執行：

```bash
npm -s exec --yes @vscode/vsce package -- --allow-missing-repository --skip-license
```
