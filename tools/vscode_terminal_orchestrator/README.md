# IvyHouse Terminal Orchestrator（DEPRECATED）

此 extension 已棄用，改由兩個實體套件取代：

- `tools/vscode_terminal_injector/`（Injector：只負責 sendText 注入）
- `tools/vscode_terminal_monitor/`（Monitor：只負責輸出監測與 capture）

> ✅ 新流程：命令注入固定走 Injector；監測優先 Proposed API，失敗才走 Monitor fallback。

> ℹ️ 仍保留本套件的原因：
> - legacy workflow loop 相容
> - HTTP SendText Bridge（`/healthz`, `/send`）在特定場景仍可用

---

## 新命令（請改用）

### Injector（命令注入）

- `IvyHouse Injector: Start Codex Terminal`
- `IvyHouse Injector: Restart Codex Terminal`
- `IvyHouse Injector: Start OpenCode Terminal`
- `IvyHouse Injector: Start Codex + OpenCode Terminals`
- `IvyHouse Injector: Send Text to Codex Terminal`
- `IvyHouse Injector: Send Text to OpenCode Terminal`
- `IvyHouse Injector: Reset Session State`

### Monitor（監測與擷取）

- `IvyHouse Monitor: Capture Codex Output`
- `IvyHouse Monitor: Auto-Capture Codex /status`
- `IvyHouse Monitor: Restart Codex + Auto-Capture /status`
- `IvyHouse Monitor: Open Last Codex Capture`
- `IvyHouse Monitor: Clear Codex Capture`
- `IvyHouse Monitor: Codex Capture Diagnostics`

---

## 安裝方式（目前建議）

1. 打包 Injector：

```bash
cd tools/vscode_terminal_injector
npm -s exec --yes @vscode/vsce package -- --allow-missing-repository --skip-license
```

2. 打包 Monitor：

```bash
cd tools/vscode_terminal_monitor
npm -s exec --yes @vscode/vsce package -- --allow-missing-repository --skip-license
```

3. 安裝兩個 VSIX：

```bash
code-insiders --install-extension tools/vscode_terminal_injector/ivyhouse-terminal-injector-<version>.vsix --force
code-insiders --install-extension tools/vscode_terminal_monitor/ivyhouse-terminal-monitor-<version>.vsix --force
```

4. 若不再使用舊套件，可移除舊 extension：

```bash
code-insiders --uninstall-extension ivyhouse-local.ivyhouse-terminal-orchestrator
```

## 換機時的關鍵設定（argv.json）

若要使用 Proposed API 監測（含 legacy 模式），請設定 runtime `argv.json`：

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

> 使用 `Preferences: Configure Runtime Arguments` 開啟檔案；儲存後請完整關閉並重啟 VS Code。

## Bridge / Capture 相關資料夾（若啟用）

- `.service/sendtext_bridge/token`：Bridge 驗證 token
- `.service/terminal_capture/sendtext_bridge_events.jsonl`：Bridge `/send` 事件紀錄
- `.service/terminal_capture/codex_live.txt` / `opencode_live.txt`：rolling capture
- `.service/terminal_capture/monitor_debug.jsonl`：Proposed API 可用性事件

Bridge 健康檢查：

```bash
curl http://127.0.0.1:8765/healthz
```

---

## 相容性說明

- 舊 Orchestrator 保留僅為相容，不建議新流程繼續使用。
- 若你看到 `IvyHouse Legacy` 前綴的命令，代表它們是 deprecated 命令。
