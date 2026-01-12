# Terminal Management Guide

## 🎯 目的

確保 Codex CLI 執行時，所有命令都發送到同一個 Terminal 會話，避免為每個任務創建新的 Terminal，提高執行效率與一致性。

---

## 📋 核心原則

### 1. Terminal 一致性原則

**規則**: 在同一個開發會話中，所有 Codex CLI 命令必須發送到同一個 Terminal。

**理由**:
- 保持環境變數一致性
- 避免多個 Terminal 造成的混亂
- 方便追蹤命令歷史
- 降低資源消耗

### 2. 何時創建新 Terminal

**允許創建新 Terminal 的情況**:
- Plan 中明確要求（例如：需要同時運行 server 和 client）
- 前一個 Terminal 會話已意外關閉
- 開始新的開發會話（例如：重啟 VS Code）
- 需要隔離的執行環境（例如：測試不同的環境變數）

**禁止創建新 Terminal 的情況**:
- 僅僅為了執行下一個 Plan
- Terminal 中有錯誤訊息（應該在同一個 Terminal 中修正）
- 覺得 Terminal 「看起來亂」（應該使用 `clear` 命令）

---

## 🔧 使用方法

### Option 1: Python Terminal Manager (推薦)

#### 安裝需求
```bash
# Python 3.7+
python3 --version

# tmux (用於 Terminal 會話管理)
sudo apt-get install tmux  # Debian/Ubuntu
brew install tmux          # macOS
```

#### 基本用法

**獲取或創建 Terminal**:
```bash
python3 .agent/scripts/terminal_manager.py get-terminal
```

**發送命令到 Terminal**:
```bash
python3 .agent/scripts/terminal_manager.py send-command codex-session "ls -la"
```

**查看 Terminal 資訊**:
```bash
python3 .agent/scripts/terminal_manager.py info
```

**關閉 Terminal**:
```bash
python3 .agent/scripts/terminal_manager.py close-terminal codex-session
```

#### 整合到工作流程

使用 `run_codex_template.sh` 包裝腳本，自動處理 Terminal 管理：

```bash
.agent/scripts/run_codex_template.sh doc/plans/Idx-009_plan.md
```

### Option 2: Bash Terminal Manager (tmux)

#### 基本用法

**獲取或創建 Terminal**:
```bash
.agent/scripts/terminal_manager_tmux.sh get-or-create
```

**發送命令到 Terminal**:
```bash
.agent/scripts/terminal_manager_tmux.sh send-command codex-session "npm test"
```

**查看 Terminal 資訊**:
```bash
.agent/scripts/terminal_manager_tmux.sh info
```

**關閉 Terminal**:
```bash
.agent/scripts/terminal_manager_tmux.sh close codex-session
```

---

## 📁 狀態管理

### 狀態檔: `.agent/.terminal_session.json`

**位置**: 專案根目錄 `.agent/.terminal_session.json`

**格式**:
```json
{
  "terminal_id": "codex-session",
  "session_name": "codex-session",
  "created_at": "2026-01-12T10:30:00+08:00",
  "last_used": "2026-01-12T14:45:00+08:00",
  "command_count": 23
}
```

**說明**:
- `terminal_id`: Terminal 識別符（tmux session name）
- `session_name`: 人類可讀的會話名稱
- `created_at`: Terminal 創建時間
- `last_used`: 最後一次使用時間
- `command_count`: 已發送的命令數量

**注意**: 此檔案已加入 `.gitignore`，不會提交到 Git。

---

## 🔄 與 Workflow 整合

### Step 2.5: Role Selection Gate

在 Plan 通過 User Approval 後，Planner 會詢問執行工具：

```markdown
## 🔧 執行資訊

**execution**: [copilot|codex-cli]
**terminal**: [使用現有 Terminal | 需要新 Terminal（請說明原因）]
```

### Step 3: Engineer Execute

如果 `execution: codex-cli`，則：

1. **檢查 Terminal 狀態**:
   ```bash
   python3 .agent/scripts/terminal_manager.py info
   ```

2. **執行 Plan**:
   ```bash
   .agent/scripts/run_codex_template.sh doc/plans/Idx-XXX_plan.md
   ```

3. **腳本自動處理**:
   - 獲取或創建 Terminal
   - 發送 Codex CLI 命令
   - 監控執行結果
   - 失敗時觸發 L2 Rollback

### Step 4: QA

QA 工具必須與 Executor 不同（Cross-QA 規則）：
- Executor: Codex CLI → QA: GitHub Copilot
- Executor: GitHub Copilot → QA: Codex CLI

---

## 🚨 故障排除

### 問題 1: Terminal 會話不存在

**症狀**:
```
❌ Session 'codex-session' does not exist
```

**解決方案**:
```bash
# 清理狀態檔
rm .agent/.terminal_session.json

# 重新創建 Terminal
python3 .agent/scripts/terminal_manager.py get-terminal
```

### 問題 2: tmux 未安裝

**症狀**:
```
❌ tmux is not installed
```

**解決方案**:
```bash
# Debian/Ubuntu
sudo apt-get update && sudo apt-get install tmux

# macOS
brew install tmux
```

### 問題 3: 狀態檔損壞

**症狀**:
```
⚠️  Failed to load state: ...
```

**解決方案**:
```bash
# 刪除損壞的狀態檔
rm .agent/.terminal_session.json

# Terminal Manager 會自動重建
python3 .agent/scripts/terminal_manager.py get-terminal
```

### 問題 4: 需要手動附加到 Terminal

**使用 tmux attach**:
```bash
# 列出所有 tmux 會話
tmux list-sessions

# 附加到 Codex 會話
tmux attach-session -t codex-session
```

**分離 tmux 會話**:
```
按 Ctrl+B，然後按 D
```

---

## 📊 最佳實踐

### 1. 開發會話開始

```bash
# 查看是否有現存的 Terminal
python3 .agent/scripts/terminal_manager.py info

# 如果沒有，會自動創建
python3 .agent/scripts/terminal_manager.py get-terminal
```

### 2. 執行多個 Plan

```bash
# Plan 1
.agent/scripts/run_codex_template.sh doc/plans/Idx-009_plan.md

# Plan 2 (使用同一個 Terminal)
.agent/scripts/run_codex_template.sh doc/plans/Idx-010_plan.md
```

### 3. 開發會話結束

```bash
# 可選：關閉 Terminal（下次會自動重建）
python3 .agent/scripts/terminal_manager.py close-terminal codex-session
```

### 4. 檢查 Terminal 狀態

```bash
# 查看狀態
python3 .agent/scripts/terminal_manager.py info

# 查看 tmux 會話
tmux list-sessions
```

---

## 🔐 安全考量

1. **狀態檔隱私**:
   - `.terminal_session.json` 已加入 `.gitignore`
   - 不包含敏感資訊（僅有 session ID 和時間戳）

2. **命令記錄**:
   - Terminal 命令可能包含敏感參數
   - 不要在腳本中 echo 完整的命令
   - 使用 tmux 的 history 功能時注意安全

3. **多用戶環境**:
   - 每個用戶有獨立的 tmux session
   - 使用 `tmux list-sessions` 確認不會干擾其他用戶

---

## 📚 參考資源

- [tmux Documentation](https://github.com/tmux/tmux/wiki)
- [tmux Cheat Sheet](https://tmuxcheatsheet.com/)
- [Python subprocess Module](https://docs.python.org/3/library/subprocess.html)
- [VS Code Terminal API](https://code.visualstudio.com/api/references/vscode-api#Terminal)

---

## 📝 更新日誌

| 版本 | 日期 | 變更說明 |
|------|------|----------|
| 1.0.0 | 2026-01-12 | 初版：Terminal Manager 核心功能 |

---

**維護者**: @GitHub-Copilot
**最後更新**: 2026-01-12
