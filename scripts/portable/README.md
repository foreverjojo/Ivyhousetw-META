# Portable Setup（一鍵復原）

這個資料夾提供「在全新電腦上快速復原開發環境」的腳本。

重點：
- 會嘗試安裝：VS Code / Docker / Git / Python（依作業系統與可用的套件管理工具而定）
- 會下載（clone 或 zip）本 repo 到本機
- 會依照本 repo 的 `.vscode/extensions.json` 一鍵安裝建議的 VS Code extensions
- 另外，本 repo 有兩個 local VS Code extensions（Injector / Monitor）：
	- `tools/vscode_terminal_injector/`
	- `tools/vscode_terminal_monitor/`
	- `tools/vscode_terminal_orchestrator/`（legacy 相容）
	若需要可手動打包後用 `code-insiders --install-extension <vsix>` 安裝。

> 目前 `install_extensions.sh` / `install_extensions.ps1` 已支援自動打包並安裝上述 `ivyhouse-local.*` local extensions（best-effort）。

## Proposed API（argv.json）

若要啟用 Monitor 的 Proposed API 主路徑，請在 VS Code runtime `argv.json` 加入：

```json
{
  "enable-proposed-api": [
    "ivyhouse-local.ivyhouse-terminal-monitor",
    "ivyhouse-local.ivyhouse-terminal-orchestrator"
  ]
}
```

常見路徑：
- Windows Insiders：`%APPDATA%\\Code - Insiders\\User\\argv.json`
- Windows Stable：`%APPDATA%\\Code\\User\\argv.json`
- macOS Insiders：`~/Library/Application Support/Code - Insiders/User/argv.json`
- Linux Insiders：`~/.config/Code - Insiders/User/argv.json`

儲存後請完整關閉並重啟 VS Code。

## 快速開始（建議）

請優先參考文件：`doc/ENVIRONMENT_RECOVERY.md`（有包含一行指令版）。

## 目錄

- `bootstrap.sh`：macOS/Linux 一鍵入口（自動偵測 OS）
- `bootstrap_windows.ps1`：Windows 一鍵安裝（winget）
- `bootstrap_macos.sh`：macOS 一鍵安裝（Homebrew）
- `bootstrap_linux.sh`：Debian/Ubuntu 一鍵安裝（apt）
- `install_extensions.ps1`：Windows 安裝 VS Code extensions
- `install_extensions.sh`：macOS/Linux 安裝 VS Code extensions

## 安全提醒

這些腳本可能需要系統管理權限（例如安裝 Docker Desktop）。
若你使用「一行指令從網路下載並執行」的方式，請務必先打開 GitHub 上的腳本內容確認無誤再執行。
