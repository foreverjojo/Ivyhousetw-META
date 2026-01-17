# Agent Skills 技能清單

此檔案為艾薇 Dev-Team 的技能索引，供 Agent 或人類開發者查閱如何調用各項工具。

---

## 📦 可用技能一覽

| 技能名稱 | 用途 | 調用指令 |
|----------|------|----------|
| `code_reviewer` | 代碼品質審查 | `python .agent/skills/code_reviewer.py <file_path>` |
| `doc_generator` | 文件自動生成 | `python .agent/skills/doc_generator.py <file_path>` |
| `test_runner` | 測試執行器 | `python .agent/skills/test_runner.py [test_path]` |
| `github_explorer` | GitHub 技能搜尋與下載 | `python .agent/skills/github_explorer.py <command>` |
| `skill_converter` | 技能轉換流水線 | 由 github_explorer 內部調用 |
| `plan_validator` | Plan 格式驗證 | `python .agent/skills/plan_validator.py <plan_file_path>` |
| `git_stats_reporter` | Git 變更統計與 Gate 觸發 | `python .agent/skills/git_stats_reporter.py <diff_file_path>` |
| `manifest_updater` | Skills manifest 同步 | `python .agent/skills/manifest_updater.py --check` / `--sync` |
| `skills_evaluator` | Skills 執行統計與回饋 | `python .agent/skills/skills_evaluator.py <log_file_path> [--format json|markdown]` |

---

## 🔍 技能詳細說明

### 1. code_reviewer.py

**功能**：靜態分析 Python 檔案，檢查以下項目：
- API Key 洩漏偵測 (正規表達式辨識 `sk-`, `api_key=` 等)
- 檔案行數檢查 (超過 500 行發出警告)
- 中文註釋檢查 (檢查前五行是否包含中文)

**調用方式**：
```bash
python .agent/skills/code_reviewer.py <file_path>
```

**輸出格式**：JSON
```json
{
  "status": "pass | warning | fail",
  "file": "path/to/file.py",
  "line_count": 123,
  "issues": [
    {"type": "api_key_leak", "line": 10, "message": "..."}
  ],
  "summary": {
    "api_key_leak": 0,
    "file_too_long": 0,
    "missing_chinese_comment": 0
  }
}
```

---

### 2. doc_generator.py

**功能**：從 Python 檔案中提取 docstring，自動產生 Markdown 格式說明文件。

**調用方式**：
```bash
python .agent/skills/doc_generator.py <file_path>
```

**輸出格式**：Markdown 純文字

---

### 3. test_runner.py

**功能**：在專案根目錄執行 `pytest`，擷取結果並以 JSON 格式回報。

**調用方式**：
```bash
python .agent/skills/test_runner.py [test_path]
```

**輸出格式**：JSON
```json
{
  "status": "pass | fail | no_tests | error",
  "project_root": "/path/to/project",
  "passed": 5,
  "failed": 2,
  "errors": 0,
  "output": "..."
}
```

---

### 4. github_explorer.py

**功能**：從 GitHub 搜尋並下載外部技能，具備安全預覽機制。

**調用方式**：
```bash
# 搜尋技能
python .agent/skills/github_explorer.py search <keyword>

# 預覽技能內容 (下載前必做)
python .agent/skills/github_explorer.py preview <owner/repo> [skill_path]

# 下載技能 (需加 --confirm 確認)
python .agent/skills/github_explorer.py download <owner/repo> <file_path> --confirm

# 列出本地技能
python .agent/skills/github_explorer.py list
```

**安全機制**：
1. ⚠️ 下載前**必須**先執行 `preview` 查看內容
2. ⚠️ 下載時**必須**加上 `--confirm` 參數確認
3. ✅ 下載後自動執行 `code_reviewer.py` 安全掃描
4. 🚨 若掃描發現問題，已下載檔案會被自動刪除

**輸出格式**：JSON
```json
{
  "status": "success | error | blocked",
  "message": "操作結果說明",
  "results": []
}
```

---

### 5. plan_validator.py

**功能**：驗證 Plan 文件是否包含必要段落與 `EXECUTION_BLOCK` 關鍵欄位。

**調用方式**：
```bash
python .agent/skills/plan_validator.py doc/plans/Idx-XXX_*.md
```

**輸出格式**：JSON（status 小寫）
```json
{
  "status": "pass | fail | error",
  "plan_path": "doc/plans/Idx-XXX_*.md",
  "missing_sections": [],
  "format_errors": [],
  "summary": "Plan 驗證通過"
}
```

---

### 6. git_stats_reporter.py

**功能**：解析 `git diff --numstat` 輸出，產生變更統計並輸出 Gate 觸發建議（Maintainability / UI/UX）。

**調用方式**：
```bash
git diff --numstat > /tmp/diff_stats.txt
python .agent/skills/git_stats_reporter.py /tmp/diff_stats.txt
```

**輸出格式**：JSON（status 小寫）
```json
{
  "status": "pass | error",
  "total_files_changed": 3,
  "total_lines_added": 10,
  "total_lines_deleted": 2,
  "total_lines_changed": 12,
  "affected_paths": ["app.py", "ui/foo.py"],
  "triggers": { "maintainability_gate": false, "ui_ux_gate": true },
  "summary": "3 files, +10/-2 lines"
}
```

---

### 7. manifest_updater.py

**功能**：同步 `.agent/skills/skill_manifest.json` 的 builtin skills 清單，並保留 external/legacy 記錄（向後相容）。

**調用方式**：
```bash
# 僅檢查（不寫入）
python .agent/skills/manifest_updater.py --check

# 寫入更新
python .agent/skills/manifest_updater.py --sync
```

**輸出格式**：JSON（status 小寫）

---

### 8. skills_evaluator.py

**功能**：解析 Log 的 `## 🛠️ SKILLS_EXECUTION_REPORT` 表格，產生統計報告（執行次數、狀態分布、失敗清單、成功率）。

**調用方式**：
```bash
# JSON（預設）
python .agent/skills/skills_evaluator.py doc/logs/Idx-XXX_log.md

# Markdown
python .agent/skills/skills_evaluator.py doc/logs/Idx-XXX_log.md --format markdown
```

**輸出格式**：JSON（預設）或 Markdown（--format markdown）

---

## 🔒 Output Schema Validation（Phase 2）

本 repo 會在 `.agent/skills/schemas/` 內提供 JSON Schema 檔案，供對 skills 輸出做機械化驗證。

- Phase 1：建立 schema 檔案（不強制驗證）
- Phase 2：skills 會在輸出 JSON 前嘗試執行 **optional** schema 驗證（graceful degradation）
  - 若 `jsonschema` 不可用 → 跳過驗證（不影響執行）
  - 若 schema 檔案不存在 → 跳過驗證（不影響執行）
  - 若 schema 驗證失敗 → 在輸出 JSON 加上 `validation_errors` + `suggestion`（**不強制改動原本 status/exit code**）

---

## 🚧 未來技能 (規劃中)

| 技能名稱 | 用途 | 狀態 |
|----------|------|------|
| `security_scan` | 深度安全漏洞掃描 | ⏳ 規劃中 |
| `dependency_check` | 依賴套件版本與安全檢查 | ⏳ 規劃中 |

---

## 📜 使用規範

1. **資安紅線**：技能腳本本身絕對不能包含任何 API Key。
2. **獨立性**：技能腳本應盡量減少對專案核心代碼的依賴。
3. **繁體中文**：所有輸出訊息皆須為繁體中文。
