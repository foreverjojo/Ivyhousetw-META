# IvyHouse Terminal Orchestrator (local VS Code extension)

目的：
- 自動啟動並維持兩個「可見的互動 VS Code terminal」：
  - `Codex CLI`
  - `OpenCode CLI`
- **所有對這兩個 terminal 的啟動/指令下達都透過 `terminal.sendText()`**（避免 terminal collision 的覆寫問題）。

## 安裝（Dev Container / VS Code Server）

在 repo root 執行：

```bash
bash scripts/vscode/install_terminal_orchestrator.sh
```

完成後請在 VS Code 內執行「Developer: Reload Window」。

## 使用

Command Palette：
- `IvyHouse: Start Codex Terminal`
- `IvyHouse: Start OpenCode Terminal`
- `IvyHouse: Start Codex + OpenCode Terminals`
- `IvyHouse: Send Text to Codex Terminal`
- `IvyHouse: Send Text to OpenCode Terminal`

## 設定

Workspace Settings：
- `ivyhouseTerminalOrchestrator.autoStart`（預設 `true`）
- `ivyhouseTerminalOrchestrator.codexCommand`
- `ivyhouseTerminalOrchestrator.opencodeCommand`

## 注意

- 任何「在同一個 terminal」執行第二個命令，都可能導致長期服務退出；因此這個 extension 會把啟動與輸入統一走 `sendText`。
- 若你想把 git/pytest/ruff 等命令放到第三個 terminal，請使用一般 terminal（例如命名 `Project`）即可。
