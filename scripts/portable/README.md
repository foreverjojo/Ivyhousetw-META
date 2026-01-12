# Portable Setup（一鍵復原）

這個資料夾提供「在全新電腦上快速復原開發環境」的腳本。

重點：
- 會嘗試安裝：VS Code / Docker / Git / Python（依作業系統與可用的套件管理工具而定）
- 會下載（clone 或 zip）本 repo 到本機
- 會依照本 repo 的 `.vscode/extensions.json` 一鍵安裝建議的 VS Code extensions

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
