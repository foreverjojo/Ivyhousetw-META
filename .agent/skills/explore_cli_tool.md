---
description: CLI 工具探索標準作業流程 - 避免臆測參數導致失敗
---

# CLI 工具探索標準作業流程 (SOP)

> **用途**：當 AI Agent 首次使用新的 CLI 工具時，必須遵循此流程，避免因「臆測參數」導致執行失敗。

---

## 📋 必要步驟 (不可跳過)

### Step 1️⃣ 執行基礎 Help

```bash
<tool> --help
```

**目的**：
- 確認工具是否已安裝
- 瞭解有哪些子命令 (subcommands)
- 查看全域參數 (global flags)

**範例**：
```bash
codex --help
# 輸出會列出: exec, review, login, logout 等
```

---

### Step 2️⃣ 執行子命令 Help

```bash
<tool> <subcommand> --help
```

**目的**：
- 確認「實際支援的參數」
- 瞭解參數的正確語法與用途

**範例**：
```bash
codex exec --help
# 會顯示支援 -c, --config 等，但沒有 --context-file
```

⚠️ **紅線原則**：絕對不可臆測參數名稱（如 `--message`, `--context-file`）

---

### Step 3️⃣ 最小可行測試 (MVT)

先用**最簡單的語法**測試工具是否可執行：

```bash
<tool> <subcommand> "minimal prompt"
```

**範例**：
```bash
# ✅ 正確：先測試最基本用法
codex exec "Hello"

# ❌ 錯誤：直接加一堆未驗證的參數
codex exec --model "gpt-4" --context-file "file.py" "prompt"
```

---

### Step 4️⃣ 逐步加參數

確認基本可行後，**逐一**新增參數：

```bash
# 範例：逐步測試參數（以通用格式為例）
<tool> <subcommand> --option1 value1 "prompt"

# 驗證成功後再加第二個
<tool> <subcommand> --option1 value1 --option2 value2 "prompt"
```

> ⚠️ **注意**: 每個工具的參數格式可能不同。例如：
> - Codex CLI 使用 `-c key=value` 格式
> - 其他工具可能使用 `--key value` 或 `--key=value`
>
> **務必**依照該工具 `--help` 顯示的格式使用參數。

---

## 🚫 禁止行為清單

| 禁止行為 | 原因 | 正確做法 |
|---------|------|---------|
| ❌ 跳過 `--help` 直接憑經驗構建指令 | 不同工具語法差異大 | 執行 Step 1-2 |
| ❌ 使用未在 help 出現的參數 | 會直接報錯 | 只用 help 列出的參數 |
| ❌ 一次加多個未驗證的參數 | 無法定位問題 | 逐步加參數 (Step 4) |
| ❌ 假設所有 CLI 工具語法相同 | 每個工具設計不同 | 獨立探索每個工具 |

---

## 💡 進階技巧

### 使用 stdin/pipeline 傳遞內容

若工具不支援 `--file` 或 `--context-file`：

```powershell
# PowerShell pipeline
Get-Content file.py | <tool> <subcommand> "prompt"

# Bash pipeline
cat file.py | <tool> <subcommand> "prompt"
```

### 查看詳細錯誤訊息

```bash
<tool> <subcommand> --verbose "prompt"
# 或
<tool> <subcommand> --debug "prompt"
```

---

## 📝 記錄與分享

探索完成後，請將結果記錄至 [`doc/TOOL_USAGE.md`](doc/TOOL_USAGE.md)，方便後續使用。
