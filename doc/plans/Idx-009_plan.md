# 計劃：Idx-009

**Index**: Idx-009
**Created**: 2026-01-12
**Planner**: @GitHub-Copilot

---

## 🎯 目標

實現完整的 Terminal 管理方案，確保 Codex CLI 執行時所有命令都發送到同一個 Terminal 會話，並整合 Role Selection Gate、Execution 欄位、分層 Rollback 策略及 Cross-QA 規則。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `.agent/scripts/terminal_manager.py` | 新增 | Terminal 會話管理核心腳本（Python 版） |
| `.agent/scripts/terminal_manager_tmux.sh` | 新增 | Terminal 會話管理替代方案（tmux 版） |
| `.agent/scripts/run_codex_template.sh` | 新增 | Codex CLI 執行包裝腳本，整合 Terminal Manager |
| `.agent/TERMINAL_MANAGEMENT.md` | 新增 | Terminal 管理規則與使用說明文檔 |
| `.agent/.terminal_session.json` | 新增 | Terminal 會話狀態追蹤檔（由腳本自動生成） |
| `.agent/workflows/dev-team.md` | 修改 | 加入 Role Selection Gate（Step 2.5）與 Terminal 管理規則 |
| `doc/plans/Idx-000_plan.template.md` | 修改 | 新增 `execution` 欄位與 `rollback` 策略區段 |
| `doc/logs/Idx-000_log.template.md` | 修改 | 新增執行工具、Terminal 資訊、Rollback 記錄區段 |
| `.agent/roles/qa.md` | 修改 | 補充 L3 Rollback SOP 與 Cross-QA 檢核規則 |
| `.gitignore` | 修改 | 加入 `.terminal_session.json` 忽略規則 |

---

## 📝 邏輯細節

### 1. `.agent/scripts/terminal_manager.py`

**目的**: 提供 Python 腳本來管理 Terminal 會話，確保所有 Codex CLI 命令發送到同一個 Terminal。

**核心功能**:
- `get_or_create_terminal()`: 從 `.terminal_session.json` 讀取現有 Terminal ID，若不存在則創建新的
- `send_command(terminal_id, command)`: 發送命令到指定 Terminal
- `close_terminal(terminal_id)`: 關閉 Terminal 並清理狀態檔
- 使用 VS Code API 或 `tmux` 進行 Terminal 管理

**實作指引**:
```python
import json
import os
import subprocess
from pathlib import Path

STATE_FILE = Path(".agent/.terminal_session.json")

def get_or_create_terminal():
    """獲取或創建 Codex 專用 Terminal"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            return state.get('terminal_id')

    # 創建新 Terminal（使用 tmux 或 VS Code API）
    terminal_id = create_new_terminal()
    save_state(terminal_id)
    return terminal_id

def send_command(terminal_id, command):
    """發送命令到指定 Terminal"""
    # 實作發送邏輯
    pass

def save_state(terminal_id):
    """保存 Terminal 狀態"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump({
            'terminal_id': terminal_id,
            'created_at': datetime.now().isoformat(),
            'last_used': datetime.now().isoformat()
        }, f, indent=2)
```

### 2. `.agent/scripts/terminal_manager_tmux.sh`

**目的**: 提供 tmux 版本的 Terminal 管理腳本（備用方案）。

**核心功能**:
- 使用 tmux 創建/附加到名為 `codex-session` 的會話
- 發送命令到 tmux 會話
- 清理 tmux 會話

**實作指引**:
```bash
#!/bin/bash
SESSION_NAME="codex-session"

get_or_create_session() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo "$SESSION_NAME"
    else
        tmux new-session -d -s "$SESSION_NAME"
        echo "$SESSION_NAME"
    fi
}

send_command() {
    local session=$1
    local cmd=$2
    tmux send-keys -t "$session" "$cmd" C-m
}
```

### 3. `.agent/scripts/run_codex_template.sh`

**目的**: Codex CLI 執行的包裝腳本，整合 Terminal Manager 與 L2 Rollback。

**核心功能**:
- 調用 `terminal_manager.py` 獲取 Terminal ID
- 發送 Codex CLI 命令到該 Terminal
- 執行失敗時觸發 L2 Rollback（`git restore`）
- 記錄執行結果到 `.agent/execution_log.json`

**實作指引**:
```bash
#!/bin/bash
set -e

PLAN_FILE=$1
TERMINAL_ID=$(python3 .agent/scripts/terminal_manager.py get-terminal)

# 讀取 plan.md 中的 execution 欄位
EXECUTION_TOOL=$(grep "^execution:" "$PLAN_FILE" | cut -d: -f2 | xargs)

if [[ "$EXECUTION_TOOL" == "codex-cli" ]]; then
    echo "🔧 使用 Codex CLI 執行，Terminal ID: $TERMINAL_ID"

    # 發送命令到 Terminal
    python3 .agent/scripts/terminal_manager.py send-command "$TERMINAL_ID" "codex --prompt-file $PLAN_FILE"

    # 檢查執行結果
    if [ $? -ne 0 ]; then
        echo "❌ 執行失敗，觸發 L2 Rollback"
        git restore .
        exit 1
    fi
else
    echo "ℹ️ 非 Codex CLI 執行，跳過 Terminal 管理"
fi
```

### 4. `.agent/TERMINAL_MANAGEMENT.md`

**目的**: 文檔化 Terminal 管理的規則與使用方式。

**內容包含**:
- Terminal 一致性原則
- 何時創建新 Terminal
- Terminal Manager 使用方法
- 故障排除指南

### 5. `.agent/workflows/dev-team.md` 更新

**新增**: Step 2.5 - Role Selection Gate

**位置**: 在 `Step 2: Meta Expert Review` 之後，`Step 3: Engineer Execute` 之前

**內容**:
```markdown
## Step 2.5: Role Selection Gate 🚦

**執行者**: Planner（暫時）或 Workflow Coordinator（未來）

**觸發條件**: Plan 通過 User Approval Gate

**選項**:
1. **GitHub Copilot**: 互動式開發，需要即時反饋
2. **Codex CLI**: 批次執行，明確的檔案操作

**決策因素**:
- 任務複雜度
- 是否需要即時反饋
- 檔案數量與操作類型

**輸出**: 在 `plan.md` 中填入 `execution: [copilot|codex-cli]`

**Terminal 規則**:
- Codex CLI 執行時，所有命令必須發送到同一個 Terminal
- 除非 Plan 明確要求，否則不得創建新 Terminal
- 使用 `terminal_manager.py` 管理 Terminal 會話
```

**新增**: Terminal 管理規則到 Engineer 職責

### 6. `doc/plans/Idx-000_plan.template.md` 更新

**新增欄位**:
```markdown
## 🔧 執行資訊

**execution**: [copilot|codex-cli]
**terminal**: [使用現有 Terminal | 需要新 Terminal（請說明原因）]

---

## 🔄 Rollback 策略

**L1 (自我修正)**: Engineer 發現錯誤，立即修正
**L2 (腳本回滾)**: 執行失敗時，自動執行 `git restore .`
**L3 (Copilot 建議)**: QA 不通過時，Copilot 提供 `git reset` 建議
**L4 (任務中止)**: User 執行 `git reset --hard` 或刪除 branch

**預期 Rollback Level**: [L1|L2|L3|L4]
```

### 7. `doc/logs/Idx-000_log.template.md` 更新

**新增區段**:
```markdown
## 🔧 執行資訊

**Execution Tool**: [GitHub Copilot | Codex CLI]
**Terminal ID**: [terminal-xxx | N/A]
**Execution Start**: YYYY-MM-DD HH:MM
**Execution End**: YYYY-MM-DD HH:MM

---

## 🔄 Rollback 記錄

| Level | Timestamp | Reason | Action | Result |
|-------|-----------|--------|--------|--------|
| L2 | 2026-01-12 14:30 | 語法錯誤 | `git restore utils/helper.py` | 成功 |

---

## ✅ Cross-QA 檢核

**Executor**: [GitHub Copilot | Codex CLI]
**QA Tool**: [Codex CLI | GitHub Copilot] *(必須與 Executor 不同)*
**QA Compliance**: [✅ PASS | ⚠️ 違規：說明]
```

### 8. `.agent/roles/qa.md` 更新

**新增**: L3 Rollback SOP

**位置**: QA 職責區段

**內容**:
```markdown
### L3 Rollback SOP

**觸發條件**: QA 結果為 FAIL

**執行步驟**:
1. 標記 Plan Status 為 `FAIL`
2. 使用 Copilot 分析 git log，找出需回滾的 commit
3. 提供回滾建議：`git reset --soft HEAD~N` 或 `git revert <commit>`
4. 等待 User 確認後執行
5. 記錄 Rollback 到 Log

**Copilot Prompt 範例**:
```
請分析最近 5 個 commits，找出與 Idx-009 相關的變更，
並建議回滾命令（保留工作區變更）。
```
```

**新增**: Cross-QA 規則

**內容**:
```markdown
### Cross-QA 規則

**原則**: Executor 與 QA 工具必須不同

**組合**:
- Copilot 執行 → Codex CLI QA
- Codex CLI 執行 → Copilot QA

**檢核點**:
1. 檢查 Plan 的 `execution` 欄位
2. 選擇不同的工具執行 QA
3. 在 Log 中記錄 Executor 與 QA Tool
4. 若違規，標記 `QA Compliance: ⚠️ 違規`
```

### 9. `.gitignore` 更新

**新增**:
```
# Agent Terminal 狀態
.agent/.terminal_session.json
```

---

## ⚠️ 注意事項

- **風險提示**:
  - Terminal Manager 依賴 Python 3.7+，需確認環境
  - tmux 版本需安裝 `tmux` 套件
  - VS Code API 版本可能需要特定版本的 VS Code
  - Terminal 會話異常關閉時，需手動清理 `.terminal_session.json`

- **資安考量**:
  - Terminal 命令可能包含敏感資訊，不應記錄到 Git
  - `.terminal_session.json` 已加入 `.gitignore`

- **相依性**:
  - 此 Plan 依賴 `Idx-007`（Plan Template）和 `Idx-008`（Log Template）
  - Terminal Manager 與 Codex CLI 執行流程緊密耦合
  - Cross-QA 規則需要 QA 角色理解並遵守

- **Codex CLI 安裝**:
  - 當前環境尚未安裝 Codex CLI
  - 需要先安裝 Codex CLI 才能測試 Terminal Manager
  - 建議先實作檔案與文檔，再進行整合測試

---

## 🔗 相關資源

- [Idx-007: Plan Template](doc/logs/Idx-007_log.md)
- [Idx-008: Log Template](doc/logs/Idx-008_log.md)
- [Terminal Management Doc](../.agent/TERMINAL_MANAGEMENT.md) *(待建立)*
- [VS Code Terminal API](https://code.visualstudio.com/api/references/vscode-api#Terminal)
- [tmux Documentation](https://github.com/tmux/tmux/wiki)

---

## 🔧 執行資訊

**execution**: github-copilot
**terminal**: 使用現有 Terminal（由 Terminal Manager 管理）

**Cross-QA 規範**:
- 執行工具: GitHub Copilot
- QA 工具: Codex CLI
- 符合 Cross-QA 規則: ✅

---

## 🔄 Rollback 策略

**L1 (自我修正)**: Codex CLI 執行過程中發現語法錯誤，立即修正
**L2 (腳本回滾)**: `run_codex_template.sh` 檢測到執行失敗，自動執行 `git restore .`
**L3 (Copilot 建議)**: QA 階段發現邏輯錯誤，Copilot 提供回滾建議
**L4 (任務中止)**: User 決定整個方案不可行，執行 `git reset --hard`

**預期 Rollback Level**: L1-L2（預期順利，僅需輕微修正）

---

## ✅ 用戶確認

> 🛑 **必要停頓點**：Planner 產出 Spec 後，必須等待用戶確認才能進入 Step 2。

- [ ] Spec 已確認，可進入 Step 2 (Meta Expert)
- [ ] 執行工具已選擇：`codex-cli`
- [ ] Terminal 管理策略已確認

---

**Template Version**: 2.0.0
**Last Updated**: 2026-01-12
**Plan Status**: NOT_STARTED
