# IvyHouse Terminal Injector

專責 **sendText 注入** 的 VS Code extension。

## 責任範圍

- 只負責建立/啟動 `Codex CLI` 與 `OpenCode CLI` terminal。
- 只負責對上述 terminal 注入文字（`sendText`）。
- 送出提交鍵（Enter）統一使用 `sendSequence("\r")`（Codex / OpenCode 相同）。
- 不負責終端輸出監測與 capture。

## 換機快速落地（建議）

1. 安裝推薦 extensions（含 ivyhouse-local IDs）：
	- `bash scripts/portable/install_extensions.sh`
	- Windows：`powershell -ExecutionPolicy Bypass -File scripts/portable/install_extensions.ps1`
2. 在 Dev Container 內安裝 local extension symlink：
	- `bash scripts/vscode/install_terminal_orchestrator.sh`
3. VS Code 執行：`Developer: Reload Window`

> `install_terminal_orchestrator.sh` 目前會同時安裝：Injector / Monitor / Orchestrator（legacy）。

## 主要命令

- `IvyHouse Injector: Start Codex Terminal`
- `IvyHouse Injector: Restart Codex Terminal`
- `IvyHouse Injector: Start OpenCode Terminal`
- `IvyHouse Injector: Start Codex + OpenCode Terminals`
- `IvyHouse Injector: Send Text to Codex Terminal`
- `IvyHouse Injector: Send Text to OpenCode Terminal`
- `IvyHouse Injector: Reset Session State`

## 供其他 extension 呼叫的命令

- `ivyhouseTerminalInjector.sendLiteralToCodex`（參數：`{ text, submit }`）
- `ivyhouseTerminalInjector.sendLiteralToOpenCode`（參數：`{ text, submit }`）

## 重要設定

- `ivyhouseTerminalInjector.submitDelayMs`
	- 作用：送出文字後，延遲多少毫秒再送 Enter（使用 `sendSequence("\r")`）
	- 適用：Codex / OpenCode
	- 預設：`350`
- `ivyhouseTerminalInjector.codexSubmitDelayMs`
	- 舊版相容鍵，建議改用 `ivyhouseTerminalInjector.submitDelayMs`

## argv.json（Proposed API）說明

Injector 本身不依賴 Proposed API；但若你要搭配 Monitor 的 Proposed API 監測，建議同機設定 runtime `argv.json`：

- Windows Stable：`%APPDATA%\\Code\\User\\argv.json`
- Windows Insiders：`%APPDATA%\\Code - Insiders\\User\\argv.json`
- macOS Stable：`~/Library/Application Support/Code/User/argv.json`
- macOS Insiders：`~/Library/Application Support/Code - Insiders/User/argv.json`
- Linux Stable：`~/.config/Code/User/argv.json`
- Linux Insiders：`~/.config/Code - Insiders/User/argv.json`

建議內容（至少包含 Monitor；若仍需 legacy 也可保留 orchestrator）：

```json
{
	"enable-proposed-api": [
		"ivyhouse-local.ivyhouse-terminal-monitor",
		"ivyhouse-local.ivyhouse-terminal-orchestrator"
	]
}
```

> 可用 `Preferences: Configure Runtime Arguments` 開啟檔案；儲存後請完整關閉並重啟 VS Code。

## 打包

在此資料夾執行：

```bash
npm -s exec --yes @vscode/vsce package -- --allow-missing-repository --skip-license
```
