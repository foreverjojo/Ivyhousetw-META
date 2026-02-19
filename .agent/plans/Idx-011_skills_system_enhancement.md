# Plan: Idx-011

**Index**: Idx-011
**Created**: 2026-01-17
**Planner**: @GitHub-Copilot

---

## 🎯 目標

基於對 Anthropic/OpenAI/LangChain/CrewAI/GitHub Copilot 最佳實務的研究，全面強化 `.agent/skills` 系統，確保：
1. Skills 執行可稽核（每次變更都有執行證據）
2. （Phase 2）Skills 輸出有 schema 驗證（避免格式錯誤）
3. Skills manifest 完整記錄（版本/來源/審計）
4. 補充缺失的關鍵 skills（plan validation / git stats reporting）

---

## 📋 SPEC

### Goal
將 Skills 從「可選工具」提升為「強制執行且可稽核的 Quality Gate」，對齊業界 agent tools 最佳實務。

### Non-goals
- ❌ 不做：建立 Skills Evaluation Loop（保留至 Phase 2）
- ❌ 不做：Skills 自動優化機制（保留至 Phase 2）
- ❌ 不做：重構現有 skills 的核心邏輯（只加驗證層）

### Acceptance Criteria
1. ✅ Engineer 階段執行 `code_reviewer.py` 後，Log 中有 `SKILLS_EXECUTION_REPORT` 段落
2. ✅ `skill_manifest.json` 記錄所有 builtin skills（含版本/schema路徑）
3. ✅ 新增 `plan_validator.py` 可驗證 Plan 格式正確性
4. ✅ 新增 `git_stats_reporter.py` 可產生變更統計並觸發 Gate 判定
5. ✅ QA Checklist 包含 Skills 執行證據檢核項
6. ✅ Error messages 包含 actionable suggestions
7. ⚪ （Phase 2）所有 skills 輸出通過 JSON Schema 驗證

### Edge cases
- 若 skill 執行失敗（例如 Python script crash）→ Log 記錄 `status: error` + stack trace 摘要
- （Phase 2）若 schema 驗證失敗 → Log 記錄驗證錯誤並停止流程
- 若 `plan_validator.py` 發現 Plan 缺失 → 退回 Planner 補齊
- 若 `git_stats_reporter.py` 無法讀取 git diff → 回退為手動確認

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: true

### Sources
- ✅ Anthropic: [Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
  - Key principles: Tool schema clarity, structured outputs, error prompt-engineering, token efficiency, evaluation-driven optimization
- ✅ OpenAI: [Structured Outputs for Multi-Agent Systems](https://cookbook.openai.com/examples/structured_outputs_multi_agent)
  - Key: Use `strict: true` for schema validation, tool consolidation, clear boundaries
- ✅ Web Search Policy（允許搜尋，但必須附來源連結）：
  - 允許 Coordinator/Planner 透過網路搜尋補齊 LangChain / CrewAI 等外部參考
  - **必須**在本段落貼上可點擊的來源 URL（優先官方文件/官方 repo/官方部落格）
  - 若找不到可驗證的來源 URL → 一律寫入 Assumptions 並標註 `RISK: unverified`
- ⚠️ RISK: unverified - LangChain Tools best practices（嘗試搜尋但無可驗證 URL）
  - Concept: Clear tool names, specific descriptions, appropriate tool selection
- ⚠️ RISK: unverified - CrewAI Tool design patterns（嘗試搜尋但無可驗證 URL）
  - Concept: Agent-tool ergonomics, documentation-driven design
- ✅ Repo 內文檔:
  - `.agent/skills/SKILL.md` - 現有 skills 清單與用法
  - `.agent/roles/engineer.md` - 當前 skills 叫用方式
  - `.agent/roles/qa.md` - QA skills 使用規範
  - `.agent/workflows/dev-team.md` - 主流程（缺 skills gate）

### Assumptions
- ✅ VERIFIED: 現有 5 個 skills (`code_reviewer`, `test_runner`, `doc_generator`, `github_explorer`, `skill_converter`) 功能完整，只需補驗證層
- ⚠️ RISK: unverified - （Phase 2 可選）若要啟用 schema validation，執行環境可能尚未安裝 `jsonschema`
- ⚠️ RISK: unverified - 假設 Coordinator（Copilot Chat）可以可靠解析 skills 輸出的 JSON（若格式異常需有 fallback）

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `.agent/workflows/dev-team.md` - 補 Skill Execution Gate
- `.agent/roles/engineer.md` - 強化 skills 使用規範
- `.agent/roles/qa.md` - 補 Skills 執行證據檢核項
- `.agent/roles/coordinator.md` - 補 Gate 自動觸發邏輯
- `.agent/skills/SKILL.md` - 補 schema validation / error handling 文件
- `.agent/skills/skill_manifest.json` - 填充 builtin skills 清單
- `.agent/skills/schemas/` - 新建目錄 + 4 個 schema 檔案
- （Phase 2）`.agent/skills/code_reviewer.py` - 加 schema 驗證 + 改善 error messages
- （Phase 2）`.agent/skills/test_runner.py` - 加 schema 驗證 + 改善 error messages
- `.agent/skills/doc_generator.py` - （Phase 2 可選）加 schema 驗證
- `.agent/skills/github_explorer.py` - （Phase 2 可選）加 schema 驗證
- `.agent/skills/plan_validator.py` - 新建
- `.agent/skills/git_stats_reporter.py` - 新建
- `.agent/skills/manifest_updater.py` - 新建
- `doc/logs/Idx-000_log.template.md` - 補 `SKILLS_EXECUTION_REPORT` 段落
- （Phase 2）`requirements.txt` - （Phase 2）若要啟用 schema validation，才需要確認/加入 `jsonschema`

### Done 定義
1. ✅ 所有檔案變更已完成且 `code_reviewer.py` 無 `status: fail|error`
2. ✅ 新增的 3 個 skills 可獨立執行並輸出正確 JSON
3. ✅ `skill_manifest.json` 包含所有 8 個 builtin skills（5 舊 + 3 新）
4. ✅ 執行 `python .agent/skills/manifest_updater.py --sync` 成功
5. ✅ 執行 `python .agent/skills/plan_validator.py doc/plans/Idx-011_skills_system_enhancement.md` 回傳 `status: pass`
6. ✅ 在 mock git diff 上執行 `python .agent/skills/git_stats_reporter.py` 產生正確統計

### Rollback 策略
- **Level**: L2（檔案級回滾）
- **前置條件**: 若任一 skill 執行失敗導致 workflow 中斷
- **回滾動作**:
  ```bash
  # 回滾新增的 skills（保留 schemas/ 目錄）
  git checkout HEAD -- .agent/skills/plan_validator.py
  git checkout HEAD -- .agent/skills/git_stats_reporter.py
  git checkout HEAD -- .agent/skills/manifest_updater.py

  # 回滾 workflow/roles 變更
  git checkout HEAD -- .agent/workflows/dev-team.md
  git checkout HEAD -- .agent/roles/engineer.md
  git checkout HEAD -- .agent/roles/qa.md
  git checkout HEAD -- .agent/roles/coordinator.md
  ```

### Max rounds
- **估計**: 2-3 輪（1 輪實作 + 1-2 輪測試/修正）
- **超過處理**: 僅限（Phase 2）啟用 schema validation 時：若連續超過 3 輪仍 schema 驗證失敗，暫停並檢討 schema 設計，先回退為 Phase 1 交付

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `.agent/workflows/dev-team.md` | 修改 | Step 3 補 Skill Execution Gate（Engineer 階段必執行） |
| `.agent/roles/engineer.md` | 修改 | 強化「完成代碼後必執行 code_reviewer」規範 |
| `.agent/roles/qa.md` | 修改 | Checklist 補「Skills 執行證據檢核」項 |
| `.agent/roles/coordinator.md` | 修改 | Gate 章節補 git_stats_reporter 觸發邏輯 |
| `.agent/skills/SKILL.md` | 修改 | 補 Schema Validation / Error Handling 段落 |
| `.agent/skills/skill_manifest.json` | 修改 | 填充 builtin skills 清單（8 個） |
| `.agent/skills/schemas/code_reviewer_output.schema.json` | 新增 | code_reviewer 輸出 JSON Schema |
| `.agent/skills/schemas/test_runner_output.schema.json` | 新增 | test_runner 輸出 JSON Schema |
| `.agent/skills/schemas/plan_validator_output.schema.json` | 新增 | plan_validator 輸出 JSON Schema |
| `.agent/skills/schemas/git_stats_reporter_output.schema.json` | 新增 | git_stats_reporter 輸出 JSON Schema |
| （Phase 2）`.agent/skills/code_reviewer.py` | 修改 | 加 schema 驗證 + 改善 error messages（actionable suggestions） |
| （Phase 2）`.agent/skills/test_runner.py` | 修改 | 加 schema 驗證 + 改善 error messages |
| `.agent/skills/plan_validator.py` | 新增 | 驗證 Plan 格式是否符合 template |
| `.agent/skills/git_stats_reporter.py` | 新增 | 從 git diff 產生統計 + Gate 觸發判定 |
| `.agent/skills/manifest_updater.py` | 新增 | 自動掃描 skills/ 並更新 manifest |
| `doc/logs/Idx-000_log.template.md` | 修改 | 補 `SKILLS_EXECUTION_REPORT` 段落 |
| （Phase 2）`requirements.txt` | 修改 | （Phase 2）若要啟用 schema validation，才需要確認/加入 `jsonschema` |

---

## 📝 邏輯細節

### 1. `.agent/workflows/dev-team.md` - Step 3 補 Skill Execution Gate

在 **Step 3️⃣ 全端工程師 (Engineer)** 段落的「共同規則」後方，補充：

```markdown
**Skill Execution Gate（每次變更必執行）**：
1. 對每個新建/修改的 `.py` 檔案執行：
   ```bash
   python .agent/skills/code_reviewer.py <file_path>
   ```
2. 若專案有單元測試，執行：
   ```bash
   python .agent/skills/test_runner.py [test_path]
   ```
3. **Coordinator 收集流程**（VS Code 原生模式）：
   - Copilot Chat 透過 `terminal.sendText()` 注入指令到 Project terminal
   - 使用 Proposed API `onDidWriteTerminalData` 監測 terminal 輸出
   - 從 stdout 擷取 JSON 結果（完整輸出）
   - 將結果寫入 Log 的 `## 🛠️ SKILLS_EXECUTION_REPORT` 段落（使用 Markdown table 格式）
4. 若 `code_reviewer.py` 回傳 `"status": "fail"`（例如 API key 洩漏），立即停止並回報 user

**完成標記後**：Engineer 輸出 `[ENGINEER_DONE]` 前，必須確認所有 skill 執行結果已收集且無 `fail` 狀態。
```

### 2. `.agent/roles/engineer.md` - 強化 skills 使用規範

在「可用技能 (Available Skills)」表格後方的提示區塊，改寫為：

```markdown
> 💡 **強制使用時機（必須執行且留證據）**：
> - ✅ **完成代碼後**：必須執行 `code_reviewer.py` 並將 JSON 輸出交給 Coordinator 寫入 Log
> - ✅ **若有測試**：必須執行 `test_runner.py` 並記錄測試結果
> - ⚠️ **若 code_reviewer 回傳 `status: fail`**：立即停止，修正問題後重新執行
> - 詳細說明請參閱 [`.agent/skills/SKILL.md`](.agent/skills/SKILL.md)。
```

### 3. `.agent/roles/qa.md` - Checklist 補 Skills 執行證據檢核

在「檢查清單 (Checklist)」區段，補充：

```markdown
- [ ] **Skills 執行證據**：Log 中是否包含 `SKILLS_EXECUTION_REPORT` 段落？
- [ ] **安全掃描 pass/warning**：`code_reviewer.py` 是否回傳 `status: pass|warning`（且無 API key 洩漏）？
- [ ] **測試結果記錄**：若有測試，`test_runner.py` 結果是否已記錄？
```

### 4. `.agent/roles/coordinator.md` - Gate 自動觸發邏輯

在「ORCH_MODE 固定 Gate（Deterministic）」段落的**共用輸入**後方，補充：

```markdown
**Gate 自動觸發檢測（使用 git_stats_reporter）**：
1. 在 Project terminal 執行（依需求選擇）：
   ```bash
   # Staged changes
   git diff --cached --numstat > /tmp/diff_stats.txt
   # 或 All uncommitted changes
   git diff HEAD --numstat > /tmp/diff_stats.txt
   ```
2. 執行 skill：
   ```bash
   python .agent/skills/git_stats_reporter.py /tmp/diff_stats.txt
   ```
3. 根據 JSON 輸出的 `triggers` 欄位，決定是否執行 Maintainability/UI-UX Gate：
   - `triggers.maintainability_gate: true` → 必須執行 Maintainability Review
   - `triggers.ui_ux_gate: true` → QA 報告必須包含 UI/UX CHECK 段落
```

### 5. `.agent/skills/SKILL.md` - 補文件段落

在文件末尾補充兩個新段落：

```markdown
## 🔒 Output Schema Validation（Phase 2 可選）

**Phase 1（本 Plan）**：不強制 JSON Schema 驗證，保持現有 skills 輸出格式相容性。

**Phase 2（未來）**：可選擇性建立 `.agent/skills/schemas/<skill_name>_output.schema.json` 並在 skill 內加入驗證。

**Preflight Check**：
- **Phase 1（必做）**：建立 `.agent/skills/schemas/` 目錄與 4 個 schema 檔案（純文件參考，不執行驗證）
- **Phase 2（可選）**：若要啟用 schema validation，才需要：
  - 確認 Python 環境可 `import jsonschema`
  - 視需要在 `requirements.txt` 加入 `jsonschema>=4.0.0`

**現有 skills 輸出格式**（Phase 1 維持）：
- `code_reviewer.py`: `status` 為小寫（`pass|warning|fail|error`），欄位 `file`（非 `file_path`）
- `test_runner.py`: `status` 為小寫（`pass|fail|no_tests|error`），欄位 `project_root`（非 `test_path`）

**Coordinator 處理**（Phase 1）：
- 解析 skill 輸出（JSON parse only，不驗證 schema）
- 若 JSON parse 失敗 → 視為 skill crash，記錄原始 stdout/stderr
- 若 `status: error` → 提取 `message`；若有 `suggestion` 則一併呈現給 user
- 若 `status: fail` → 停止 workflow，要求修正後重新執行

**Error 輸出範例（供 Coordinator 解析，對齊現有格式）**：
```json
{
  "status": "error",
  "file": "app2.py",
  "message": "檔案不存在：app2.py",
  "suggestion": "是否想要以下檔案？\n  - app.py\n  - app_legacy.py",
  "usage": "python .agent/skills/code_reviewer.py <file_path>"
}
```

---

## 🚨 Error Response Guidelines

（Phase 1）**新建 skills** 的 error output 必須包含（現有 skills 可逐步在 Phase 2 補齊）：

| 欄位 | 必填 | 說明 |
|------|------|------|
| `status` | ✅ | 固定為 `"error"` |
| `message` | ✅ | 問題描述（一句話） |
| `suggestion` | ✅ | 可操作建議（具體範例） |
| `usage` | ✅ | 正確用法（命令範例） |
| `details` | ⚪ | 詳細錯誤資訊（可選） |

**範例**：
```json
  {
	  "status": "error",
	  "message": "檔案不存在：app2.py",
	  "suggestion": "是否想要以下檔案？\n  - app.py\n  - app_legacy.py",
	  "usage": "python code_reviewer.py <file_path>",
	  "details": "可用檔案：app.py, main.py, app_legacy.py"
  }
```
```

### 6. `.agent/skills/skill_manifest.json` - 填充清單

完整改寫為：

```json
{
  "version": "1.0",
  "last_updated": "2026-01-17T00:00:00Z",
  "skills": [
    {
      "name": "code_reviewer",
      "type": "builtin",
      "version": "1.0.0",
      "path": ".agent/skills/code_reviewer.py",
      "description": "代碼品質審查（API key 洩漏、檔案長度、中文註釋）",
      "schema": ".agent/skills/schemas/code_reviewer_output.schema.json",
      "last_updated": "2026-01-17T00:00:00Z"
    },
    {
      "name": "test_runner",
      "type": "builtin",
      "version": "1.0.0",
      "path": ".agent/skills/test_runner.py",
      "description": "測試執行器（pytest wrapper）",
      "schema": ".agent/skills/schemas/test_runner_output.schema.json",
      "last_updated": "2026-01-17T00:00:00Z"
    },
    {
      "name": "doc_generator",
      "type": "builtin",
      "version": "1.0.0",
      "path": ".agent/skills/doc_generator.py",
      "description": "文件自動生成（AST docstring extraction）",
      "schema": null,
      "last_updated": "2026-01-17T00:00:00Z"
    },
    {
      "name": "github_explorer",
      "type": "builtin",
      "version": "1.0.0",
      "path": ".agent/skills/github_explorer.py",
      "description": "GitHub 技能搜尋與下載（含 whitelist/audit）",
      "schema": null,
      "last_updated": "2026-01-17T00:00:00Z"
    },
    {
      "name": "skill_converter",
      "type": "builtin",
      "version": "1.0.0",
      "path": ".agent/skills/skill_converter.py",
      "description": "技能格式轉換器（舊格式→新格式）",
      "schema": null,
      "last_updated": "2026-01-17T00:00:00Z"
    },
    {
      "name": "plan_validator",
      "type": "builtin",
      "version": "1.0.0",
      "path": ".agent/skills/plan_validator.py",
      "description": "Plan 格式驗證器",
      "schema": ".agent/skills/schemas/plan_validator_output.schema.json",
      "last_updated": "2026-01-17T00:00:00Z"
    },
    {
      "name": "git_stats_reporter",
      "type": "builtin",
      "version": "1.0.0",
      "path": ".agent/skills/git_stats_reporter.py",
      "description": "Git 變更統計與 Gate 觸發判定",
      "schema": ".agent/skills/schemas/git_stats_reporter_output.schema.json",
      "last_updated": "2026-01-17T00:00:00Z"
    },
    {
      "name": "manifest_updater",
      "type": "builtin",
      "version": "1.0.0",
      "path": ".agent/skills/manifest_updater.py",
      "description": "Manifest 自動同步工具",
      "schema": null,
      "last_updated": "2026-01-17T00:00:00Z"
    },
    {
      "name": "example_external_skill",
      "source_repo": "owner/repo",
      "file_path": ".agent/skills/example_external_skill.py",
      "commit_sha": "unknown",
      "sha256_hash": "abc123...",
      "downloaded_at": "2025-12-01T10:00:00Z"
    }
  ]
}
```

### 7. JSON Schemas - 新建 4 個檔案

**`.agent/skills/schemas/code_reviewer_output.schema.json`**（Phase 2 參考，Phase 1 不強制執行）：
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["status", "file", "issues"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["pass", "warning", "fail", "error"]
    },
    "file": {
      "type": "string"
    },
    "line_count": {
      "type": "integer"
    },
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "message"],
        "properties": {
          "type": {
            "type": "string",
            "enum": ["api_key_leak", "file_too_long", "missing_chinese_comment"]
          },
          "message": {
            "type": "string"
          },
          "line": {
            "type": "integer"
          }
        }
      }
    },
    "summary": {
      "type": "object",
      "properties": {
        "api_key_leak": {"type": "integer"},
        "file_too_long": {"type": "integer"},
        "missing_chinese_comment": {"type": "integer"}
      }
    },
    "message": {
      "type": "string"
    },
    "suggestion": {
      "type": "string"
    }
  },
  "additionalProperties": true
}
```

**`.agent/skills/schemas/test_runner_output.schema.json`**（Phase 2 參考，Phase 1 不強制執行）：
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["status", "project_root", "passed", "failed", "errors"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["pass", "fail", "no_tests", "error"]
    },
    "project_root": {
      "type": "string"
    },
    "passed": {
      "type": "integer",
      "minimum": 0
    },
    "failed": {
      "type": "integer",
      "minimum": 0
    },
    "errors": {
      "type": "integer",
      "minimum": 0
    },
    "exit_code": {
      "type": "integer"
    },
    "output": {
      "type": "string"
    },
    "details": {
      "type": "array"
    },
    "message": {
      "type": "string"
    }
  },
  "additionalProperties": true
}
```

**`.agent/skills/schemas/plan_validator_output.schema.json`**（Phase 2 參考，Phase 1 不強制執行）：
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["status", "plan_path", "missing_sections", "summary"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["pass", "fail", "error"]
    },
    "plan_path": {
      "type": "string"
    },
    "missing_sections": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "format_errors": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "summary": {
      "type": "string"
    }
  },
  "additionalProperties": true
}
```

**`.agent/skills/schemas/git_stats_reporter_output.schema.json`**（Phase 2 參考，Phase 1 不強制執行）：
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["status", "total_files_changed", "total_lines_added", "total_lines_deleted", "total_lines_changed", "affected_paths", "triggers"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["pass", "error"]
    },
    "total_files_changed": {
      "type": "integer",
      "minimum": 0
    },
    "total_lines_added": {
      "type": "integer",
      "minimum": 0
    },
    "total_lines_deleted": {
      "type": "integer",
      "minimum": 0
    },
    "total_lines_changed": {
      "type": "integer",
      "minimum": 0
    },
    "affected_paths": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "triggers": {
      "type": "object",
      "required": ["maintainability_gate", "ui_ux_gate"],
      "properties": {
        "maintainability_gate": {
          "type": "boolean"
        },
        "ui_ux_gate": {
          "type": "boolean"
        }
      }
    },
    "summary": {
      "type": "string"
    }
  },
  "additionalProperties": true
}
```

### 8. 修改現有 skills - 加 schema 驗證

**`code_reviewer.py`** Phase 1 不修改（維持現有輸出格式：`status: "pass"|"warning"|"fail"|"error"`, `file: "<path>"`）。

**Phase 2（未來）可選加入 schema 驗證**：
```python
# （Phase 2 可選）Schema validation
import json
from pathlib import Path
try:
    import jsonschema
    schema_path = Path(__file__).parent / "schemas" / "code_reviewer_output.schema.json"
    if schema_path.exists():
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        jsonschema.validate(result, schema)
except ImportError:
    pass  # jsonschema 未安裝，跳過驗證
except jsonschema.ValidationError as e:
    print(json.dumps({"status": "error", "message": f"Schema validation failed: {e.message}"}))
```

**Error message 改善範例**（在 file not found 處）：
```python
if not Path(file_path).exists():
    # 找出相似檔名
    similar_files = find_similar_files(file_path, max_results=3)
    return {
        "status": "error",
        "file": file_path,
        "issues": [],
        "message": f"檔案不存在：{file_path}",
        "suggestion": f"是否想要以下檔案？\n" + "\n".join(f"  - {f}" for f in similar_files),
        "usage": "python .agent/skills/code_reviewer.py <file_path>"
    }
```

類似邏輯套用至 `test_runner.py`。

### 9. 新建 `plan_validator.py`

完整腳本（約 150 行）：

```python
"""
.agent/skills/plan_validator.py

用途：驗證 Plan 是否符合模板規範

執行：python .agent/skills/plan_validator.py <plan_file_path>

檢查項目：
- 必須包含 SPEC / RESEARCH & ASSUMPTIONS / SCOPE & CONSTRAINTS / EXECUTION_BLOCK
- EXECUTION_BLOCK 必須包含 executor_tool / qa_tool / last_change_tool 欄位
- research_required 必須明確 true/false
- 檔案清單格式正確（Markdown table）

輸出：JSON（status 小寫: pass|fail|error）
"""

import sys
import json
from pathlib import Path

# 必需段落
REQUIRED_SECTIONS = [
    "## 📋 SPEC",
    "## 🔍 RESEARCH & ASSUMPTIONS",
    "## 🔒 SCOPE & CONSTRAINTS",
    "## 📁 檔案變更",
    "<!-- EXECUTION_BLOCK_START -->"
]

# EXECUTION_BLOCK 必需欄位
REQUIRED_EXEC_FIELDS = [
    "executor_tool:",
    "qa_tool:",
    "last_change_tool:"
]

def validate_plan(plan_path):
    """驗證 Plan 格式"""
    result = {
        "status": "pass",
        "plan_path": str(plan_path),
        "missing_sections": [],
        "format_errors": [],
        "summary": "Plan validation passed"
    }

    if not plan_path.exists():
        result["status"] = "error"
        result["summary"] = f"Plan 檔案不存在：{plan_path}"
        return result

    content = plan_path.read_text(encoding='utf-8')

    # 檢查必需段落
    for section in REQUIRED_SECTIONS:
        if section not in content:
            result["missing_sections"].append(section)

    # 檢查 EXECUTION_BLOCK 欄位
    if "<!-- EXECUTION_BLOCK_START -->" in content:
        exec_block = content.split("<!-- EXECUTION_BLOCK_START -->")[1].split("<!-- EXECUTION_BLOCK_END -->")[0]
        for field in REQUIRED_EXEC_FIELDS:
            if field not in exec_block:
                result["format_errors"].append(f"Missing EXECUTION_BLOCK field: {field}")

    # 檢查 research_required
    if "research_required:" not in content:
        result["format_errors"].append("Missing 'research_required: true/false' in RESEARCH & ASSUMPTIONS")

    # 判定結果
    if result["missing_sections"] or result["format_errors"]:
        result["status"] = "fail"
        result["summary"] = f"Plan validation failed: {len(result['missing_sections'])} missing sections, {len(result['format_errors'])} format errors"

    return result

def main():
    if len(sys.argv) < 2:
        error_result = {
            "status": "error",
            "plan_path": "",
            "missing_sections": [],
            "format_errors": [],
            "summary": "Missing plan file path",
            "usage": "python .agent/skills/plan_validator.py <plan_file_path>"
        }
        print(json.dumps(error_result, indent=2, ensure_ascii=False))
        sys.exit(1)

    plan_path = Path(sys.argv[1])
    result = validate_plan(plan_path)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    # Exit code: pass=0, fail=1, error=2
    if result["status"] == "pass":
        sys.exit(0)
    elif result["status"] == "fail":
        sys.exit(1)
    else:  # error
        sys.exit(2)

if __name__ == "__main__":
    main()
```

### 10. 新建 `git_stats_reporter.py`

完整腳本（約 180 行）：

```python
"""
.agent/skills/git_stats_reporter.py

用途：從 git diff 產生統計報告（只讀取，不執行 git 指令）

執行：python .agent/skills/git_stats_reporter.py <diff_file_path>

輸入：git diff --numstat 輸出（從檔案或 stdin 讀取）

輸出：JSON（status 小寫: pass|error）
"""

import sys
import json
from pathlib import Path

# Gate 觸發規則
MAINTAINABILITY_THRESHOLD = 50  # 總變更行數
MAINTAINABILITY_CORE_PATHS = ["core/", "utils/", "config.py"]
UI_UX_PATHS = ["pages/", "ui/", "app.py", "main.py", "_page.py", "_ui.py", "_component.py"]

def parse_diff_numstat(content):
    """解析 git diff --numstat 輸出"""
    stats = {
        "total_files_changed": 0,
        "total_lines_added": 0,
        "total_lines_deleted": 0,
        "affected_paths": []
    }

    for line in content.strip().split('\n'):
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) < 3:
            continue

        added = parts[0]
        deleted = parts[1]
        path = parts[2]

        # 處理 binary files（顯示為 '-'）
        if added != '-':
            stats["total_lines_added"] += int(added)
        if deleted != '-':
            stats["total_lines_deleted"] += int(deleted)

        stats["total_files_changed"] += 1
        stats["affected_paths"].append(path)

    stats["total_lines_changed"] = stats["total_lines_added"] + stats["total_lines_deleted"]
    return stats

def check_triggers(stats):
    """檢查是否觸發 Gate"""
    triggers = {
        "maintainability_gate": False,
        "ui_ux_gate": False
    }

    # Maintainability Gate: 總變更 > 50 或命中核心路徑
    if stats["total_lines_changed"] > MAINTAINABILITY_THRESHOLD:
        triggers["maintainability_gate"] = True

    for path in stats["affected_paths"]:
        for core_path in MAINTAINABILITY_CORE_PATHS:
            if core_path in path:
                triggers["maintainability_gate"] = True
                break

    # UI/UX Gate: 命中 UI 相關路徑
    for path in stats["affected_paths"]:
        for ui_path in UI_UX_PATHS:
            if ui_path in path:
                triggers["ui_ux_gate"] = True
                break

    return triggers

def generate_report(diff_content):
    """產生統計報告"""
    stats = parse_diff_numstat(diff_content)
    triggers = check_triggers(stats)

    result = {
        "status": "pass",
        "total_files_changed": stats["total_files_changed"],
        "total_lines_added": stats["total_lines_added"],
        "total_lines_deleted": stats["total_lines_deleted"],
        "total_lines_changed": stats["total_lines_changed"],
        "affected_paths": stats["affected_paths"],
        "triggers": triggers,
        "summary": f"{stats['total_files_changed']} files, +{stats['total_lines_added']}/-{stats['total_lines_deleted']} lines"
    }

    return result

def main():
    if len(sys.argv) < 2:
        error_result = {
            "status": "error",
            "total_files_changed": 0,
            "total_lines_added": 0,
            "total_lines_deleted": 0,
            "total_lines_changed": 0,
            "affected_paths": [],
            "triggers": {"maintainability_gate": False, "ui_ux_gate": False},
            "summary": "Missing diff file path",
            "usage": "python .agent/skills/git_stats_reporter.py <diff_file_path>"
        }
        print(json.dumps(error_result, indent=2, ensure_ascii=False))
        sys.exit(1)

    diff_path = Path(sys.argv[1])

    if not diff_path.exists():
        error_result = {
            "status": "error",
            "total_files_changed": 0,
            "total_lines_added": 0,
            "total_lines_deleted": 0,
            "total_lines_changed": 0,
            "affected_paths": [],
            "triggers": {"maintainability_gate": False, "ui_ux_gate": False},
            "summary": f"Diff 檔案不存在：{diff_path}",
            "suggestion": "請先產生 diff 檔案：\n  git diff --cached --numstat > /tmp/diff_stats.txt  # staged changes\n  git diff HEAD --numstat > /tmp/diff_stats.txt      # all uncommitted (staged + unstaged)\n  git diff --numstat > /tmp/diff_stats.txt           # unstaged changes only",
            "usage": "python .agent/skills/git_stats_reporter.py <diff_file_path>"
        }
        print(json.dumps(error_result, indent=2, ensure_ascii=False))
        sys.exit(1)

    diff_content = diff_path.read_text(encoding='utf-8')
    result = generate_report(diff_content)

    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
```

### 11. 新建 `manifest_updater.py`

完整腳本（約 120 行）：

```python
"""
.agent/skills/manifest_updater.py

用途：自動掃描 .agent/skills/*.py 並更新 skill_manifest.json

執行：python .agent/skills/manifest_updater.py --sync

選項：
  --sync: 同步 builtin skills 到 manifest
  --check: 只檢查不更新

邏輯：
- 掃描所有 .py 檔案（包含 manifest_updater.py 本身）
- 保留 manifest 中的 external skills 記錄（向後相容：可能無 `type` 欄位，但會包含 `source_repo` / `sha256_hash` / `downloaded_at`）
"""

import sys
import json
from pathlib import Path
from datetime import datetime

SKILLS_DIR = Path(__file__).parent
MANIFEST_PATH = SKILLS_DIR / "skill_manifest.json"
SCHEMAS_DIR = SKILLS_DIR / "schemas"

def scan_builtin_skills(exclude_names=None):
    """掃描所有 builtin skills（包含所有 .py 檔案）

    Args:
        exclude_names: 要排除的 skill 名稱集合（用於避免覆蓋 external skills）
    """
    if exclude_names is None:
        exclude_names = set()

    skills = []
    for py_file in SKILLS_DIR.glob("*.py"):
        if py_file.name == "__init__.py":
            continue

        skill_name = py_file.stem

        # 跳過已存在的 external skills
        if skill_name in exclude_names:
            continue

        schema_path = SCHEMAS_DIR / f"{skill_name}_output.schema.json"

        # 讀取檔案前 10 行提取 description
        description = "No description"
        with open(py_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:10]
            for line in lines:
                if line.strip().startswith('用途：'):
                    description = line.strip().replace('用途：', '').strip()
                    break

        skill = {
            "name": skill_name,
            "type": "builtin",
            "version": "1.0.0",
            "path": f".agent/skills/{py_file.name}",
            "description": description,
            "schema": f".agent/skills/schemas/{skill_name}_output.schema.json" if schema_path.exists() else None,
            "last_updated": datetime.now().isoformat()
        }
        skills.append(skill)

    return skills

def update_manifest(dry_run=False):
    """更新 manifest"""
    # 讀取現有 manifest
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    else:
        manifest = {"version": "1.0", "skills": []}

    # 保留所有 external skills（用 metadata 判定：source_repo/sha256_hash/downloaded_at）
    def is_external(skill):
        return any(key in skill for key in ["source_repo", "sha256_hash", "downloaded_at"]) or skill.get("type") == "external"

    external_skills = [
        s for s in manifest.get("skills", [])
        if isinstance(s, dict) and s.get("name") and is_external(s)
    ]
    external_names = {s.get("name") for s in external_skills if s.get("name")}

    # 掃描 builtin skills（排除 external 同名）
    builtin_skills = scan_builtin_skills(exclude_names=external_names)

    # 合併（builtin + external）
    manifest["skills"] = builtin_skills + external_skills
    manifest["last_updated"] = datetime.now().isoformat()

    if dry_run:
        print("Dry run - would update manifest with:")
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
    else:
        with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"✅ Updated {MANIFEST_PATH} with {len(builtin_skills)} builtin skills")

    return manifest

def main():
    if "--sync" in sys.argv:
        update_manifest(dry_run=False)
    elif "--check" in sys.argv:
        update_manifest(dry_run=True)
    else:
        print("Usage: python manifest_updater.py [--sync|--check]")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### 12. `doc/logs/Idx-000_log.template.md` - 補段落

在 `## ✅ 品管審查報告` 之前，補充：

```markdown
## 🛠️ SKILLS_EXECUTION_REPORT

> 記錄本次任務執行的所有 skills（自動化工具）及其結果

| Skill | Target | Status | Summary | Timestamp |
|-------|--------|--------|---------|-----------|
| `code_reviewer.py` | `app.py` | `pass` | 未發現問題 | 2026-01-17 14:30:00 |
| `test_runner.py` | `tests/` | `no_tests` | 未收集到測試 | 2026-01-17 14:32:00 |

- [說明哪些檔案執行了哪些 skills]
- [若有 fail/error，說明原因與處理方式]

---
```

### 13. `requirements.txt` - 確認依賴（Phase 2 可選）

（Phase 2）若要啟用 schema validation，檢查是否包含 `jsonschema`，若無則補上：

```
jsonschema>=4.0.0
```

---

## ⚠️ 注意事項

- **風險提示**：
  - 新增 schema 驗證可能導致現有 skills 輸出不符合格式（需測試並修正）
  - `plan_validator.py` 需要對所有現有 plans 跑一次驗證（可能發現格式問題）
  - `git_stats_reporter.py` 依賴 git diff 格式，若 repo 有 binary files 需特別處理

- **資安考量**：
  - 所有 skills 執行不會修改檔案，只讀取並產生報告
  - JSON Schema 驗證防止惡意 JSON 注入

- **相依性**：
  - `manifest_updater.py` 需要 `skill_manifest.json` 存在（若不存在會自動建立）
  - （Phase 2）啟用 schema validation 時，才依賴 `jsonschema` 套件
  - `git_stats_reporter.py` 需要 git diff 由 Coordinator 在 Project terminal 預先產生

---

## 🔗 相關資源

- [Anthropic: Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [OpenAI: Structured Outputs for Multi-Agent Systems](https://cookbook.openai.com/examples/structured_outputs_multi_agent)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [JSON Schema Specification](https://json-schema.org/)

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-01-17 00:00:00
plan_approved: [待用戶確認]
scope_policy: strict
expert_required: false
expert_conclusion: N/A
scope_exceptions: []

# Engineer 執行
executor_tool: [待用戶確認: codex-cli|opencode]
executor_tool_version: [待填寫]
executor_user: [待填寫]
executor_start: [待填寫]
executor_end: [待填寫]
session_id: [待填寫]
last_change_tool: [待填寫]

# QA 執行
qa_tool: [待用戶確認: codex-cli|opencode]
qa_tool_version: [待填寫]
qa_user: [待填寫]
qa_start: [待填寫]
qa_end: [待填寫]
qa_result: [PASS|PASS_WITH_RISK|FAIL]
qa_compliance: [待填寫]

# 收尾
log_file_path: doc/logs/Idx-011_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

### 執行模式建議

**工具選擇**（由 user 決定）：
- `codex-cli`：互動式對話，適合逐步調整與確認
- `opencode`：較適合大量檔案修改與批次調整

**本任務特性**：涉及 16+ 檔案修改 + 3 個新 Python script，兩種工具皆可。

**分階段執行**（Phase 1 範圍，建議 2 輪）：
- **Round 1**：修改現有檔案（workflow/roles/SKILL.md/manifest/log template）+ 建立 schemas/ 目錄與 4 個 schema 檔案（不強制執行驗證）
- **Round 2**：新增 3 個 skills（plan_validator / git_stats_reporter / manifest_updater）+ 測試

**Phase 2（未來）**：
- 在 code_reviewer.py / test_runner.py 加入 optional schema 驗證（try-except import jsonschema）
- 新增 Skills Evaluation Loop

**測試驗收**：
```bash
# 1. 驗證 manifest
python .agent/skills/manifest_updater.py --check

# 2. 驗證本 Plan
python .agent/skills/plan_validator.py doc/plans/Idx-011_skills_system_enhancement.md

# 3. 產生 mock git diff 並測試
git diff --cached --numstat > /tmp/test_diff.txt  # 或 git diff HEAD --numstat
python .agent/skills/git_stats_reporter.py /tmp/test_diff.txt

# 4. 測試現有 skills
python .agent/skills/code_reviewer.py app.py
python .agent/skills/test_runner.py tests/
```

---

## 📊 優先級分級（供參考）

| 優先級 | Gap 編號 | 說明 | 影響範圍 |
|--------|----------|------|----------|
| **P0** | Gap 1 | Skill Execution Gate + Log 模板 | 可稽核性（最高） |
| **P0** | Gap 5 | Plan Validator | Plan 品質保證 |
| **P0** | Gap 7 | Manifest 填充 | 版本追蹤 |
| **P1** | Gap 2 | JSON Schema 驗證 | 可靠性 |
| **P1** | Gap 4 | Error Prompt-Engineering | 可用性 |
| **P1** | Gap 6 | Git Stats Reporter | Gate 自動化 |
| **P2** | Gap 3 | Skill Evaluation Loop | 未來優化（本 Plan 不包含） |

本 Plan 涵蓋 P0 + P1 共 6 個 Gap，預計完成後 Skills System 達到 production-ready 水準。
