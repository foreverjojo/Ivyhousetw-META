# 專案工具使用指南 (Tool Usage Guide)

> **用途**：記錄專案中常用工具的正確用法，避免重複試錯。

---

## 🤝 多工具協作模式

### 基本原則
1. **工具選擇分離（Cross-QA）**：`qa_tool` 必須與 `last_change_tool` 不同
2. **終端注入（固定）**：一律使用 IvyHouse Terminal Injector extension 的 command IDs 注入到固定終端（Codex/OpenCode）
   - `ivyhouseTerminalInjector.sendLiteralToCodex` / `ivyhouseTerminalInjector.sendLiteralToOpenCode`
3. **即時監控（主從）**：主路徑用 Proposed API；不可用時使用 IvyHouse Terminal Monitor extension 備援擷取
4. **記錄可追蹤**：工具選擇與結果寫入 plan 的 `EXECUTION_BLOCK`（含 `last_change_tool`）

> **Deprecated**：`ivyhouseTerminalOrchestrator.*` 為 legacy 相容套件；新流程只認 Injector + Monitor。

### 協作流程範例：Copilot 協調 Codex CLI（注入 + 監控）

**場景**：Engineer Tool = Codex CLI（VS Code Terminal），Copilot Chat 負責注入與監控

1. **啟動 Codex CLI 執行**
   - 用戶先在 VS Code 建立/選取固定終端（例如 terminal 名稱：`Codex CLI`），確保 Codex CLI 可接收指令。

2. **Copilot 注入 Plan/指令**
   - 固定使用 Injector extension 的 command IDs 注入（禁止用 bash 腳本代送，避免程序/TUI 退出）。
   - Codex：`ivyhouseTerminalInjector.sendLiteralToCodex`
   - OpenCode：`ivyhouseTerminalInjector.sendLiteralToOpenCode`

3. **監控完成**
   - 以 completion marker 作為完成條件（例如：`[ENGINEER_DONE]` / `[QA_DONE]` / `[FIX_DONE]`）
   - Coordinator 監測終端輸出直到偵測 marker 或 timeout

4. **Copilot 處理結果**
   - 更新 plan 的 `executor_end` 時間戳
   - 更新 `last_change_tool`（本輪最後修改程式碼的工具）
   - 通知用戶選擇 QA 工具（必須 ≠ last_change_tool）

### Cross-QA 工具選擇範例

| 情境 | Executor | QA Tool | 理由 |
|------|----------|---------|------|
| 批次修改/大量檔案 | Codex CLI | OpenCode | 交叉審查，避免同工具自審 |
| 互動式終端驗證 | OpenCode | Codex CLI | 交叉審查，避免同工具自審 |

### Cross-QA 例外情況處理

**允許同工具 QA 的情境**：
- 小修正：≤20 行程式碼變更
- 緊急修復：P0 級別 bug
- 文件修正：僅修改 .md/.txt

**記錄格式**：
```markdown
<!-- 例外情況記錄於 plan 的 EXECUTION_BLOCK -->
qa_compliance: ⚠️ 例外（小修正）- 變更：15 行 - 用戶：已確認
```

---

## 🔧 Codex CLI

### 基本資訊
- **版本**: v0.77.0+
- **文件**: 執行 `codex --help` 查看
- **預設模型**: gpt-5.2 (可透過 `-c model=...` 覆寫)

### 常用指令

#### 1. 執行任務 (exec)
```bash
# 基本用法
codex exec "請幫我審查 scripts/adapters/momo_adapter.py"

# 指定模型（-c 為 Codex CLI 專屬參數）
codex exec -c model="gpt-4o" "prompt"

# 指定配置（-c 為 Codex CLI 專屬參數）
codex exec -c 'sandbox_permissions=["disk-full-read-access"]' "prompt"
```

#### 2. 審查代碼 (review)
```bash
# 審查未提交的變更
codex review --uncommitted

# 審查與特定分支的差異
codex review --base main

# 審查特定 commit
codex review --commit abc123
```

#### 3. 使用 Pipeline 傳入檔案
```powershell
# PowerShell
Get-Content scripts/adapters/momo_adapter.py | codex exec "審查這段代碼"

# 或直接在 prompt 中指定路徑（Codex 可讀取工作目錄檔案）
codex exec "請審查 scripts/adapters/momo_adapter.py 的安全性"
```

> **注意**: 在 prompt 中指定路徑時，Codex 會嘗試讀取該檔案。
>
> **Sandbox 受限時的替代方案**：
> 1. **Pipeline 方式**：`Get-Content file.py | codex exec "prompt"`
> 2. **調整權限**：`codex exec -c 'sandbox_permissions=["disk-full-read-access"]' "prompt"`
> 3. **複製內容到 prompt**：手動將檔案內容貼入 prompt（適用於短檔案）

### ⚠️ 常見錯誤

| 錯誤指令 | 錯誤原因 | 正確方式 |
|---------|---------|---------|
| `codex exec --message "..."` | 無此參數 | `codex exec "..."` |
| `codex exec --context-file file.py` | 無此參數 | 在 prompt 指定路徑或用 pipeline |
| `codex review --uncommitted "prompt"` | review 不支援自訂 prompt | 使用 `codex exec` 替代 |
| `codex exec --model "gpt-4"` | 語法錯誤 | `codex exec -c model="gpt-4" "..."` |

---

## 🧪 pytest

### 基本用法

```bash
# 執行所有測試
python -m pytest tests/ -v

# 執行特定檔案
python -m pytest tests/test_momo_adapter_golden.py -v

# 執行特定測試函式
python -m pytest tests/test_momo_adapter_golden.py::test_momo_adapter_matches_golden -v

# 顯示詳細輸出
python -m pytest tests/ -v -s

# 只顯示失敗的測試
python -m pytest tests/ --tb=short
```

### 常用參數

| 參數 | 用途 |
|------|------|
| `-v` | 顯示詳細測試名稱 |
| `-s` | 顯示 print 輸出 |
| `--tb=short` | 簡化錯誤訊息 |
| `-x` | 遇到第一個失敗就停止 |
| `-k "pattern"` | 只執行名稱符合 pattern 的測試 |

---

## 🐍 Python Scripts

### 自動化技能腳本

#### 代碼審查
```bash
python .agent/skills/code_reviewer.py <file_path>
```
**輸出**：JSON 格式，包含資安風險、檔案長度、中文註釋檢查

#### 測試執行
```bash
python .agent/skills/test_runner.py [test_path]
```

#### 文件生成
```bash
python .agent/skills/doc_generator.py <file_or_dir>
```

---

## 📦 其他工具

### Git
```bash
# 查看未提交的變更
git status

# 查看差異
git diff

# 提交變更
git add .
git commit -m "message"
```

### PowerShell 常用指令
```powershell
# 讀取檔案
Get-Content file.txt

# 列出檔案
Get-ChildItem -Recurse -Filter "*.py"

# 搜尋內容
Select-String -Path "*.py" -Pattern "pattern"
```

---

## 📚 延伸閱讀

- [CLI 工具探索 SOP](.agent/skills/explore_cli_tool.md)
- [艾薇品管員角色](.agent/roles/qa.md)
