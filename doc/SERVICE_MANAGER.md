# Service Manager (tmux/nohup) — 使用說明

本腳本用於管理開發時候的長期服務（例如 `opencode`, `codex`），避免意外把命令發送到錯誤的 Shared terminal 而導致服務被取代。

位置：`scripts/service_manager.sh`

主要特性：
- 優先使用 `tmux` 建立專屬 session（推薦）。
- 若沒有 `tmux`，則使用 `nohup` + pidfile 作背景執行。
- 會把 logs 與 pid/session 訊息存放於 `.service/` 目錄（預設被 .gitignore 忽略）。

快速範例：

- 啟動 opencode（預設參數）：

```bash
scripts/service_manager.sh start opencode
```

- 啟動 codex 並指定自訂指令：

```bash
scripts/service_manager.sh start codex --cmd 'codex --some-arg'
```

- 停止服務：

```bash
scripts/service_manager.sh stop opencode
```

- 檢查狀態：

```bash
scripts/service_manager.sh status opencode
```

- 查看日誌：

```bash
scripts/service_manager.sh tail opencode
```

- 附加到 tmux session（互動）：

```bash
scripts/service_manager.sh attach opencode
```

建議：
- 建議每個長期服務都透過此腳本啟動/停止。Agent 發送啟動/關閉指令前，請先查 `scripts/service_manager.sh status <svc>`。
- 若要更穩定（自動重啟、保護、system integration），請考慮在目標機器建立 systemd unit 或容器化運行。
