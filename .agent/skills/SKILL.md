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
