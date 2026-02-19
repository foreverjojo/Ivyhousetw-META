# Plan: Idx-012

**Index**: Idx-012
**Created**: 2026-01-17
**Planner**: @Claude-Sonnet-4.5
**Predecessor**: Idx-011 (Skills System Enhancement - Phase 1)

---

## 🎯 目標

基於 Idx-011 Phase 1 的基礎建設（3 個新 skills + 4 個 JSON Schema），啟用 **Phase 2 可選功能**：
1. 在現有 skills 中加入 **optional** JSON Schema 驗證（graceful degradation）
2. 改善 error messages 為 actionable suggestions
3. 新增 **Skills Evaluation Loop**（追蹤 skills 執行歷史並提供優化建議）

---

## 📋 SPEC

### Goal
將 Skills 從「手動執行工具」提升為「自我驗證、可追蹤、可優化」的智能 Quality Gate。

### Non-goals
- ❌ 不做：強制 schema 驗證（若 jsonschema 不可用，仍需正常執行）
- ❌ 不做：修改 skills 核心邏輯（只加驗證層與 evaluation loop）
- ❌ 不做：自動修復 schema 驗證錯誤（僅報告，由人工修正）
- ❌ 不做：Skills 自動優化機制（Evaluation Loop 只追蹤，不自動改寫 skills）

### Acceptance Criteria
1. ✅ `code_reviewer.py` / `test_runner.py` 加入 optional schema 驗證（try-except import jsonschema）
2. ✅ Schema 驗證失敗時，輸出包含 `validation_errors`（含 message/path/schema_path）+ suggestion（不強制改動原本的 `status`）
3. ✅ 所有 skills error messages 包含 actionable suggestions（例如：檔案不存在 → 建議相似檔名）
4. ✅ 新增 `skills_evaluator.py` 可解析 Log 中的 SKILLS_EXECUTION_REPORT，產生統計報告
5. ✅ QA Checklist 包含 Skills Evaluation 檢核項
6. ✅ 若 `jsonschema` 不可用，skills 仍可正常執行（graceful degradation）
7. ✅ Log template 補充 SKILLS_EVALUATION 段落（記錄 skills 執行統計）

### Edge cases
- 若 `jsonschema` 未安裝 → skills 跳過 schema 驗證，輸出正常 JSON（不影響執行）
- 若 schema 驗證失敗 → 輸出包含 `validation_errors` 欄位（不影響原本 exit code 規則）
- 若 `skills_evaluator.py` 找不到 Log 檔案 → 回傳空報告 + warning message
- 若 Log 中無 SKILLS_EXECUTION_REPORT 段落 → 回傳 warning: "No skills execution data found"

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- ✅ Idx-011 Plan 已完成 Phase 1 research（Anthropic/OpenAI/GitHub 最佳實務）
- ✅ Repo 內文檔:
  - `doc/logs/Idx-000_log.template.md` - Log 格式（含 SKILLS_EXECUTION_REPORT）
  - `doc/logs/Idx-010_log.md` - 既有 Log 範例
  - `.agent/skills/schemas/*.json` - 已建立的 4 個 schema 檔案
  - `.agent/skills/SKILL.md` - Phase 1 已補充 schema validation 說明
  - `requirements.txt` - 已包含 `jsonschema>=4.20.0`

### Assumptions
- ✅ VERIFIED: `jsonschema>=4.20.0` 已在 requirements.txt 中，執行環境應可 import
- ⚠️ RISK: minor - 若某些環境（例如 docker/codespace）未正確安裝依賴，schema 驗證可能失敗（但有 graceful degradation）
- ✅ VERIFIED: Phase 1 已建立 4 個 schema 檔案 (code_reviewer, test_runner, plan_validator, git_stats_reporter)
- ⚠️ ASSUMPTION: Coordinator（Copilot Chat）可解析 validation_errors 欄位並呈現給用戶

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `.agent/skills/code_reviewer.py` - 加 optional schema 驗證 + 改善 error messages
- `.agent/skills/test_runner.py` - 加 optional schema 驗證 + 改善 error messages
- `.agent/skills/github_explorer.py` - 加 optional schema 驗證（可選；JSON-output）
- `.agent/skills/plan_validator.py` - 加 optional schema 驗證
- `.agent/skills/git_stats_reporter.py` - 加 optional schema 驗證
- `.agent/skills/manifest_updater.py` - 加 optional schema 驗證
- `.agent/skills/skills_evaluator.py` - 新建（解析 Log 並產生統計報告）
- `.agent/skills/schemas/github_explorer_output.schema.json` - 新建（可選）
- `.agent/skills/schemas/manifest_updater_output.schema.json` - 新建
- `.agent/skills/schemas/skills_evaluator_output.schema.json` - 新建
- `.agent/skills/SKILL.md` - 補充 skills_evaluator 說明
- `.agent/skills/__init__.py` - AVAILABLE_SKILLS 更新為 9 個（加 skills_evaluator）
- `.agent/skills/skill_manifest.json` - 更新（執行 manifest_updater --sync）
- `.agent/roles/qa.md` - 補充 Skills Evaluation 檢核項
- `.agent/workflows/dev-team.md` - 補充 Skills Evaluation 執行時機
- `doc/logs/Idx-000_log.template.md` - 補充 SKILLS_EVALUATION 段落

### Done 定義
1. ✅ 所有 JSON-output skills 加入 optional schema 驗證（try-except import jsonschema）
2. ✅ Schema 驗證失敗時，輸出包含 validation_errors 欄位
3. ✅ 新增 `skills_evaluator.py` 可獨立執行並輸出正確 JSON
4. ✅ 以 sample log 驗證 evaluator 可解析 SKILLS_EXECUTION_REPORT（`/tmp/idx012_sample_log.md`）
5. ✅ 執行 `python .agent/skills/manifest_updater.py --sync` 更新 manifest 為 9 個 skills
6. ✅ 所有 skills 通過 py_compile + code_reviewer.py
7. ✅ 若 `jsonschema` 不可用，skills 仍可正常執行（測試：使用 `python -S` 執行不依賴第三方套件的 skills）

### Scope Gate 規範
- **Research Gate**: ❌ 不觸發（research_required: false，依賴 Idx-011 研究成果）
- **Maintainability Gate**: ✅ 觸發（修改 6 個 JSON-output skills + 新增 1 個 skills_evaluator，總行數預計 > 200）
- **UI/UX Gate**: ❌ 不觸發（無 UI 變更）
- **Evidence Gate**: ⚠️ 僅在需要貼大量輸出/完整 diff 時才觸發（依 repo 的 deterministic 規則）

### 變更控制
- **影響範圍**: 僅限 `.agent/skills/` 目錄與相關文檔，不影響 core/ 或 app.py
- **回滾方案**: 若 schema 驗證導致 skills 無法執行 → 移除 validation 程式碼，回退為 Phase 1（純文件參考）
- **測試覆蓋**: 每個 skill 需測試「有 jsonschema」與「無 jsonschema」兩種情境

---

## 📝 EXECUTION_BLOCK

> 本段落僅描述工具選擇原則；實際欄位回填請使用文件末尾的 `EXECUTION_BLOCK_START/END`。

### executor_tool
- **工具選擇**: 由 user 決定（`codex-cli` 或 `opencode` 皆可）
- **理由**: 涉及 7+ 檔案修改 + 1 個新 skill，兩種工具皆適合

### qa_tool
- **工具選擇**: 與 executor_tool **不同**（Cross-QA compliance）
- **QA 範圍**:
  1. Schema 驗證程式碼正確性（try-except 邏輯）
  2. Graceful degradation 測試（不卸載套件；改用 `python -S` 模擬 ImportError）
  3. Error messages 包含 actionable suggestions
  4. skills_evaluator.py 輸出正確性

### last_change_tool
- **預期值**: 與 executor_tool 相同
- **驗證**: 由 Coordinator 回填 Plan 的 `EXECUTION_BLOCK.last_change_tool`

---

## 📁 檔案變更

| 檔案路徑 | 類型 | 變更說明 | 預估行數 |
|---------|------|----------|---------|
| `.agent/skills/code_reviewer.py` | 修改 | 加 optional schema 驗證 + 改善 error messages | +30 |
| `.agent/skills/test_runner.py` | 修改 | 加 optional schema 驗證 + 改善 error messages | +30 |
| `.agent/skills/github_explorer.py` | 修改 | 加 optional schema 驗證 | +25 |
| `.agent/skills/plan_validator.py` | 修改 | 加 optional schema 驗證 | +25 |
| `.agent/skills/git_stats_reporter.py` | 修改 | 加 optional schema 驗證 | +25 |
| `.agent/skills/manifest_updater.py` | 修改 | 加 optional schema 驗證 | +25 |
| `.agent/skills/skills_evaluator.py` | 新建 | 解析 Log 中的 SKILLS_EXECUTION_REPORT，產生統計報告 | ~200 |
| `.agent/skills/schemas/manifest_updater_output.schema.json` | 新建 | manifest_updater.py 輸出規範 | ~50 |
| `.agent/skills/schemas/skills_evaluator_output.schema.json` | 新建 | skills_evaluator.py 輸出規範 | ~80 |
| `.agent/skills/schemas/github_explorer_output.schema.json` | 新建 | github_explorer.py 輸出規範（可選） | ~70 |
| `.agent/skills/SKILL.md` | 修改 | 補充 skills_evaluator 說明 + schema 驗證執行範例 | +40 |
| `.agent/skills/__init__.py` | 修改 | AVAILABLE_SKILLS 更新為 9 個 | +1 |
| `.agent/skills/skill_manifest.json` | 修改 | 執行 manifest_updater --sync | 自動更新 |
| `.agent/roles/qa.md` | 修改 | 補充 Skills Evaluation 檢核項 | +15 |
| `.agent/workflows/dev-team.md` | 修改 | 補充 Skills Evaluation 執行時機 | +20 |
| `doc/logs/Idx-000_log.template.md` | 修改 | 補充 SKILLS_EVALUATION 段落 | +15 |

---

## 🛠️ 實作規格

### 1. Optional Schema 驗證模板（JSON-output skills 通用）

在每個 skill 的 main() 函數結尾，輸出 JSON 前加入：

```python
def validate_output_schema(result: dict, skill_name: str) -> dict:
    """
    用途：可選的 JSON Schema 驗證（graceful degradation）

    Args:
        result: skill 輸出的 dict
        skill_name: skill 名稱（例如 "code_reviewer"）

    Returns:
        dict: 若驗證通過或跳過，回傳原始 result；若驗證失敗，回傳包含 validation_errors 的 result
    """
    try:
        import json
        import jsonschema
        from pathlib import Path

        schema_path = Path(__file__).parent / "schemas" / f"{skill_name}_output.schema.json"
        if not schema_path.exists():
            # Schema 檔案不存在，跳過驗證（不影響執行）
            return result

        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)

        jsonschema.validate(result, schema)
        return result

    except ImportError:
        # jsonschema 未安裝，跳過驗證（graceful degradation）
        return result

    except jsonschema.ValidationError as e:
        # Schema 驗證失敗：不強制改動原本 status（避免破壞既有 exit code 行為），但提供可機械化的 validation_errors
        result["validation_errors"] = [
            {
                "message": e.message,
                "path": list(e.path),
                "schema_path": list(e.schema_path),
            }
        ]
        result["suggestion"] = (
            f"輸出格式不符合 schema 規範。請檢查 {schema_path.name} 並確認欄位正確性。\n"
            f"驗證錯誤：{e.message}"
        )
        return result

    except Exception as e:
        # 其他錯誤（例如 schema 格式錯誤），不影響執行
        return result


def main(argv: List[str]) -> int:
    # ... 原有邏輯 ...

    # 在輸出 JSON 前加入 schema 驗證
    result = validate_output_schema(result, "code_reviewer")  # skill_name 依檔案名稱調整

	    print(json.dumps(result, ensure_ascii=False, indent=2))
	    # Exit code 必須維持各 skill 既有邏輯（本段落不提供統一規則）
```

**套用至**:
- `code_reviewer.py` (skill_name="code_reviewer")
- `test_runner.py` (skill_name="test_runner")
- `github_explorer.py` (skill_name="github_explorer")
- `plan_validator.py` (skill_name="plan_validator")
- `git_stats_reporter.py` (skill_name="git_stats_reporter")
- `manifest_updater.py` (skill_name="manifest_updater")

---

### 2. 改善 Error Messages（以 code_reviewer.py 為例）

**現有問題**:
- 檔案不存在時，僅輸出 `"message": "檔案不存在：<path>"`

**改善方案**:
```python
def find_similar_files(target_path: str, project_root: str = ".") -> List[str]:
    """
    用途：找出與目標檔案名稱相似的檔案（用於 error suggestion）

    Args:
        target_path: 目標檔案路徑
        project_root: 專案根目錄

    Returns:
        List[str]: 相似檔案清單（最多 5 個）
    """
    from pathlib import Path
    import difflib

    target_name = Path(target_path).name
    all_py_files = [str(p) for p in Path(project_root).rglob("*.py")]
    all_file_names = [Path(p).name for p in all_py_files]

    # 使用 difflib 找出相似檔名
    similar = difflib.get_close_matches(target_name, all_file_names, n=5, cutoff=0.6)
    similar_paths = [p for p in all_py_files if Path(p).name in similar]

    return similar_paths[:5]


# main() 內會用到
import os

# 在 main() 中，檔案不存在時：
if not os.path.exists(file_path):
    similar_files = find_similar_files(file_path)
    suggestion = ""
    if similar_files:
        suggestion = f"是否想要以下檔案？\n" + "\n".join(f"  - {f}" for f in similar_files)
    else:
        suggestion = f"請確認檔案路徑正確，或使用 `find . -name '*.py'` 列出所有 Python 檔案。"

    result = {
        "status": "error",
        "file": file_path,
        "line_count": 0,
        "issues": [],
        "message": f"檔案不存在：{file_path}",
        "suggestion": suggestion,
        "usage": "python .agent/skills/code_reviewer.py <file_path>"
    }
    result = validate_output_schema(result, "code_reviewer")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2
```

**套用至**: `code_reviewer.py`, `test_runner.py`

---

### 3. 新增 `skills_evaluator.py`

完整腳本（約 200 行）：

```python
#!/usr/bin/env python3
"""
.agent/skills/skills_evaluator.py

用途：解析 Log 中的 SKILLS_EXECUTION_REPORT，產生統計報告

執行：python .agent/skills/skills_evaluator.py <log_file_path> [--format json|markdown]

輸出：
- JSON 格式（預設）：統計報告
- Markdown 格式：人類可讀的表格

檢查項目：
- Skills 執行次數統計
- Status 分布（pass/fail/error/warning/no_tests）
- 平均執行時間（若 Log 包含 timestamp）
- 最常失敗的 skills
"""

import sys
import json
import re
from typing import List, Dict, Any
from pathlib import Path
from collections import defaultdict, Counter


def parse_skills_execution_report(log_content: str) -> List[Dict[str, Any]]:
    """
    用途：從 Log 內容中解析 SKILLS_EXECUTION_REPORT 表格

    Args:
        log_content: Log 檔案內容

    Returns:
        List[Dict]: 解析出的 skills 執行記錄
    """
    records = []

    # 找到 SKILLS_EXECUTION_REPORT 段落
    match = re.search(
        r'##\s+🛠️\s+SKILLS_EXECUTION_REPORT\s+(.*?)(?=\n##|\Z)',
        log_content,
        re.DOTALL | re.IGNORECASE
    )

    if not match:
        return records

    report_section = match.group(1)

    # 解析表格（格式：| Skill | Target | Status | Summary | Timestamp |）
    table_pattern = r'\|\s*`?([^|`]+?)`?\s*\|\s*`?([^|`]+?)`?\s*\|\s*`?([^|`]+?)`?\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|'

    for match in re.finditer(table_pattern, report_section):
        skill, target, status, summary, timestamp = match.groups()

        # 跳過表頭
        if skill.strip().lower() in ['skill', '---', '']:
            continue

        records.append({
            "skill": skill.strip(),
            "target": target.strip(),
            "status": status.strip().lower(),
            "summary": summary.strip(),
            "timestamp": timestamp.strip()
        })

    return records


def compute_statistics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    用途：計算 skills 執行統計

    Args:
        records: 解析出的 skills 執行記錄

    Returns:
        Dict: 統計報告
    """
    if not records:
        return {
            "total_executions": 0,
            "status_distribution": {},
            "skill_counts": {},
            "failed_skills": [],
            "summary": "未找到 skills 執行記錄"
        }

    status_counter = Counter(r["status"] for r in records)
    skill_counter = Counter(r["skill"] for r in records)

    # 找出失敗的 skills
    failed_skills = [
        {"skill": r["skill"], "target": r["target"], "summary": r["summary"]}
        for r in records
        if r["status"] in ["fail", "error"]
    ]

    # 計算成功率
    success_count = status_counter.get("pass", 0) + status_counter.get("warning", 0) + status_counter.get("no_tests", 0)
    total_count = len(records)
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0.0

    return {
        "total_executions": total_count,
        "success_rate": round(success_rate, 2),
        "status_distribution": dict(status_counter),
        "skill_counts": dict(skill_counter.most_common()),
        "failed_skills": failed_skills,
        "summary": f"{total_count} 次執行，成功率 {success_rate:.1f}%"
    }


def generate_markdown_report(stats: Dict[str, Any]) -> str:
    """
    用途：產生 Markdown 格式的統計報告

    Args:
        stats: 統計報告

    Returns:
        str: Markdown 格式報告
    """
    md = "# Skills Evaluation Report\n\n"

    md += f"**總執行次數**: {stats['total_executions']}\n"
    md += f"**成功率**: {stats['success_rate']}%\n\n"

    md += "## Status 分布\n\n"
    md += "| Status | Count |\n"
    md += "|--------|-------|\n"
    for status, count in stats["status_distribution"].items():
        md += f"| {status} | {count} |\n"
    md += "\n"

    md += "## Skills 執行次數\n\n"
    md += "| Skill | Count |\n"
    md += "|-------|-------|\n"
    for skill, count in stats["skill_counts"].items():
        md += f"| {skill} | {count} |\n"
    md += "\n"

    if stats["failed_skills"]:
        md += "## 失敗的 Skills\n\n"
        md += "| Skill | Target | Summary |\n"
        md += "|-------|--------|----------|\n"
        for failed in stats["failed_skills"]:
            md += f"| {failed['skill']} | {failed['target']} | {failed['summary']} |\n"
        md += "\n"

    return md


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        result = {
            "status": "error",
            "log_path": "",
            "statistics": {},
            "message": "缺少 Log 檔案路徑參數",
            "suggestion": "請提供 Log 檔案路徑，例如：python .agent/skills/skills_evaluator.py doc/logs/Idx-011_log.md",
            "usage": "python .agent/skills/skills_evaluator.py <log_file_path> [--format json|markdown]"
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    log_path = argv[1]
    output_format = "json"

    # 解析 --format 參數
    if len(argv) > 2 and argv[2] == "--format" and len(argv) > 3:
        output_format = argv[3]

    # 檢查檔案是否存在
    if not Path(log_path).exists():
        result = {
            "status": "error",
            "log_path": log_path,
            "statistics": {},
            "message": f"Log 檔案不存在：{log_path}",
            "suggestion": f"請確認路徑正確，或使用 `find doc/logs -name '*.md'` 列出所有 Log 檔案。",
            "usage": "python .agent/skills/skills_evaluator.py <log_file_path> [--format json|markdown]"
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    # 讀取 Log 檔案
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
    except Exception as e:
        result = {
            "status": "error",
            "log_path": log_path,
            "statistics": {},
            "message": f"無法讀取 Log 檔案：{str(e)}",
            "suggestion": "請確認檔案權限正確，或使用 `cat <log_path>` 手動檢查檔案內容。",
            "usage": "python .agent/skills/skills_evaluator.py <log_file_path> [--format json|markdown]"
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    # 解析 SKILLS_EXECUTION_REPORT
    records = parse_skills_execution_report(log_content)

    if not records:
        result = {
            "status": "warning",
            "log_path": log_path,
            "statistics": {
                "total_executions": 0,
                "status_distribution": {},
                "skill_counts": {},
                "failed_skills": []
            },
            "message": "Log 中未找到 SKILLS_EXECUTION_REPORT 段落",
            "suggestion": "請確認 Log 檔案格式正確，或檢查是否有 skills 執行記錄。",
            "usage": "python .agent/skills/skills_evaluator.py <log_file_path> [--format json|markdown]"
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0  # warning 不算錯誤

    # 計算統計
    stats = compute_statistics(records)

    # 輸出結果
    if output_format == "markdown":
        print(generate_markdown_report(stats))
    else:
        result = {
            "status": "pass",
            "log_path": log_path,
            "statistics": stats,
            "summary": stats["summary"]
        }
        result = validate_output_schema(result, "skills_evaluator")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


def validate_output_schema(result: dict, skill_name: str) -> dict:
    """（同上述模板）"""
    try:
        import json
        import jsonschema
        from pathlib import Path

        schema_path = Path(__file__).parent / "schemas" / f"{skill_name}_output.schema.json"
        if not schema_path.exists():
            return result

        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)

        jsonschema.validate(result, schema)
        return result

    except ImportError:
        return result

    except jsonschema.ValidationError as e:
        # 不強制改動原本 status（避免破壞既有 exit code 行為），但提供可機械化的 validation_errors
        result["validation_errors"] = [
            {
                "message": e.message,
                "path": list(e.path),
                "schema_path": list(e.schema_path)
            }
        ]
        result["suggestion"] = (
            f"輸出格式不符合 schema 規範。請檢查 {schema_path.name} 並確認欄位正確性。\n"
            f"驗證錯誤：{e.message}"
        )
        return result

    except Exception as e:
        return result


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

---

### 4. 新增 Schema 檔案

#### 4.1 `manifest_updater_output.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["pass", "error"]
    },
    "manifest_path": {
      "type": "string"
    },
    "builtin_count": {
      "type": "integer"
    },
    "preserved_count": {
      "type": "integer"
    },
    "total_count": {
      "type": "integer"
    },
    "dry_run": {
      "type": "boolean"
    },
    "suggestion": {
      "type": "string"
    },
    "summary": {
      "type": "string"
    },
    "validation_errors": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "message": {"type": "string"},
          "path": {"type": "array"},
          "schema_path": {"type": "array"}
        }
      }
    }
  },
  "required": ["status", "manifest_path", "summary", "builtin_count", "preserved_count", "total_count", "dry_run"],
  "additionalProperties": true
}
```

#### 4.2 `skills_evaluator_output.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["pass", "warning", "error"]
    },
    "log_path": {
      "type": "string"
    },
    "statistics": {
      "type": "object",
      "properties": {
        "total_executions": {"type": "integer"},
        "success_rate": {"type": "number"},
        "status_distribution": {"type": "object"},
        "skill_counts": {"type": "object"},
        "failed_skills": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "skill": {"type": "string"},
              "target": {"type": "string"},
              "summary": {"type": "string"}
            }
          }
        },
        "summary": {"type": "string"}
      }
    },
    "message": {
      "type": "string"
    },
    "suggestion": {
      "type": "string"
    },
    "summary": {
      "type": "string"
    },
    "validation_errors": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "message": {"type": "string"},
          "path": {"type": "array"},
          "schema_path": {"type": "array"}
        }
      }
    }
  },
  "required": ["status", "log_path", "statistics", "summary"],
  "additionalProperties": true
}
```

#### 4.3 `github_explorer_output.schema.json` (可選)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
	"properties": {
	  "status": {
	    "type": "string",
	    "enum": ["success", "warning", "blocked", "error"]
	  },
	  "results": {
	    "type": ["array", "object"]
	  },
	  "message": {
	    "type": "string"
	  },
    "suggestion": {
      "type": "string"
    },
    "summary": {
      "type": "string"
    },
    "validation_errors": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "message": {"type": "string"},
          "path": {"type": "array"},
          "schema_path": {"type": "array"}
        }
      }
    }
  },
	  "required": ["status", "message"],
	  "additionalProperties": true
	}
```

---

### 5. 更新 SKILL.md

補充 skills_evaluator 說明：

```markdown
### 8. skills_evaluator.py

**功能**：解析 Log 中的 SKILLS_EXECUTION_REPORT，產生統計報告（Skills 執行次數、Status 分布、失敗記錄）。

**調用方式**：
```bash
# JSON 格式（預設）
python .agent/skills/skills_evaluator.py doc/logs/Idx-XXX_log.md

# Markdown 格式
python .agent/skills/skills_evaluator.py doc/logs/Idx-XXX_log.md --format markdown
```

**輸出格式**：JSON (status 小寫)
```json
{
  "status": "pass | warning | error",
  "log_path": "doc/logs/Idx-XXX_log.md",
  "statistics": {
    "total_executions": 2,
    "success_rate": 100.0,
    "status_distribution": {"pass": 1, "no_tests": 1},
    "skill_counts": {"code_reviewer.py": 1, "test_runner.py": 1},
    "failed_skills": [],
    "summary": "2 次執行，成功率 100.0%"
  },
  "summary": "2 次執行，成功率 100.0%"
}
```

---

## 🔒 Schema 驗證執行範例

**有 jsonschema 環境**：
```bash
python -c "import jsonschema; print(jsonschema.__version__)"
python .agent/skills/code_reviewer.py app.py
```

**無 jsonschema 環境**（不卸載套件；用 python -S 模擬 ImportError）：
```bash
python -S .agent/skills/code_reviewer.py app.py
```

**Schema 驗證失敗**：
```bash
# 用 schema 驗證一份「故意錯誤」的輸出（不修改程式碼、不修改 schema 檔）
python - <<'PY'
import json
from pathlib import Path
import jsonschema

schema = json.loads(Path(".agent/skills/schemas/code_reviewer_output.schema.json").read_text(encoding="utf-8"))
bad = {"status": "PASS", "file": "x.py", "line_count": 1, "issues": [], "summary": {"api_key_leak": 0, "file_too_long": 0, "missing_chinese_comment": 0}}
try:
    jsonschema.validate(bad, schema)
except jsonschema.ValidationError as e:
    print("message:", e.message)
    print("path:", list(e.path))
    print("schema_path:", list(e.schema_path))
PY
```
```

---

### 6. 更新 qa.md

補充 Skills Evaluation 檢核項：

```markdown
### Skills Evaluation 檢核

**執行時機**: 每個 Idx Log 完成後（建議在 QA 階段執行）

**執行指令**:
```bash
python .agent/skills/skills_evaluator.py doc/logs/Idx-XXX_log.md
```

**檢核項目**:
1. ✅ 所有 skills 執行記錄都包含在 SKILLS_EXECUTION_REPORT 段落
2. ✅ Success rate ≥ 80%（若 < 80%，需檢討 skills 設計或執行流程）
3. ✅ Failed skills 列表為空（若有失敗，需補上原因說明）
4. ✅ 若有 validation_errors，需確認 schema 設計是否合理
```

---

### 7. 更新 dev-team.md

補充 Skills Evaluation 執行時機：

```markdown
### Step 5: Skills Evaluation (可選)

**觸發條件**: Log 包含 SKILLS_EXECUTION_REPORT 段落

**執行指令**:
```bash
python .agent/skills/skills_evaluator.py doc/logs/Idx-XXX_log.md --format markdown
```

**輸出範例**:
```
# Skills Evaluation Report

**總執行次數**: 6
**成功率**: 100.0%

## Status 分布

| Status | Count |
|--------|-------|
| pass | 6 |

## Skills 執行次數

| Skill | Count |
|-------|-------|
| code_reviewer.py | 1 |
| test_runner.py | 1 |
```

**QA 檢核**: 若 success_rate < 80%，需檢討失敗原因
```

---

### 8. 更新 log template

補充 SKILLS_EVALUATION 段落：

```markdown
## 📊 SKILLS_EVALUATION

> 記錄本次任務的 skills 執行統計（由 skills_evaluator.py 自動產生）

**執行指令**: `python .agent/skills/skills_evaluator.py doc/logs/Idx-XXX_log.md`

**統計報告**:
- **總執行次數**: 2
- **成功率**: 100.0%
- **Status 分布**: {"pass": 1, "no_tests": 1}
- **最常執行 skill**: code_reviewer.py (示例)
- **失敗記錄**: 無

**評估**: ✅ 所有 skills 執行成功，無需改善
```

---

## 🧪 測試驗收

### 測試案例 1: Optional Schema 驗證（有 jsonschema）
```bash
python -c "import jsonschema; print(jsonschema.__version__)"

# 執行 code_reviewer.py
python .agent/skills/code_reviewer.py app.py

# 預期: 輸出正常 JSON + schema 驗證通過（無 validation_errors）
```

### 測試案例 2: Graceful Degradation（無 jsonschema）
```bash
# 不卸載套件，改用 python -S 模擬 ImportError（僅適用於不依賴第三方套件的 skills）
python -S .agent/skills/code_reviewer.py app.py

# 預期: 輸出正常 JSON（跳過 schema 驗證，不影響執行）
```

### 測試案例 3: Schema 驗證失敗
```bash
# 直接以 schema 驗證一份「故意錯誤」的輸出（不修改程式碼、不修改 schema 檔）
python - <<'PY'
import json
from pathlib import Path
import jsonschema

schema = json.loads(Path(".agent/skills/schemas/code_reviewer_output.schema.json").read_text(encoding="utf-8"))
bad = {"status": "PASS", "file": "x.py", "line_count": 1, "issues": [], "summary": {"api_key_leak": 0, "file_too_long": 0, "missing_chinese_comment": 0}}
try:
    jsonschema.validate(bad, schema)
except jsonschema.ValidationError as e:
    print("message:", e.message)
    print("path:", list(e.path))
    print("schema_path:", list(e.schema_path))
PY
```

### 測試案例 4: Skills Evaluator
```bash
cat > /tmp/idx012_sample_log.md <<'EOF'
## 🛠️ SKILLS_EXECUTION_REPORT

| Skill | Target | Status | Summary | Timestamp |
|-------|--------|--------|---------|-----------|
| `code_reviewer.py` | `app.py` | `pass` | 未發現問題 | 2026-01-17 14:30:00 |
| `test_runner.py` | `tests/` | `no_tests` | 未收集到測試 | 2026-01-17 14:32:00 |
EOF

python .agent/skills/skills_evaluator.py /tmp/idx012_sample_log.md

# 預期: 輸出 JSON，包含統計報告（total_executions, success_rate, status_distribution, skill_counts）
```

### 測試案例 5: Skills Evaluator (Markdown 格式)
```bash
python .agent/skills/skills_evaluator.py /tmp/idx012_sample_log.md --format markdown

# 預期: 輸出 Markdown 表格
```

### 測試案例 6: Error Message 改善
```bash
# 執行 code_reviewer.py 並故意提供不存在的檔案
python .agent/skills/code_reviewer.py non_existent_file.py

# 預期: 輸出包含 suggestion（相似檔案建議）
```

---

## 📊 優先級分級

| 優先級 | 任務 | 說明 | 影響範圍 |
|--------|------|------|----------|
| **P0** | Optional Schema 驗證 | 加入 try-except import jsonschema | 可靠性（最高） |
| **P0** | Error Message 改善 | 加入 actionable suggestions | 可用性（最高） |
| **P1** | Skills Evaluator | 產生統計報告 | 追蹤性 |
| **P1** | Schema 檔案補齊 | manifest_updater, skills_evaluator | 完整性 |
| **P2** | Markdown 格式輸出 | skills_evaluator --format markdown | 可讀性 |

本 Plan 涵蓋 P0 + P1，預計完成後 Skills System 達到 **自我驗證、可追蹤、可優化** 水準。

---

## 🔄 回滾方案

**若 Schema 驗證導致 skills 無法執行**:
1. 移除 validate_output_schema() 函數調用
2. 回退為 Phase 1（純文件參考，不執行驗證）
3. 檢討 schema 設計是否過於嚴格

**若 skills_evaluator.py 無法解析 Log**:
1. 檢查 Log 格式是否符合模板
2. 更新正規表達式（parse_skills_execution_report）
3. 若無法修復，暫時跳過 evaluation 功能

---

## 📝 注意事項

1. **Graceful Degradation**: 所有 skills 必須在無 jsonschema 環境下仍可正常執行
2. **Exit Code 不變**: 不新增/改寫既有 exit code 映射；schema 驗證失敗僅提供 `validation_errors`（預設不強制改 `status`）
3. **Validation Errors 格式**: 必須包含 message, path, schema_path 三個欄位
4. **Actionable Suggestions**: 所有 error messages 必須包含 suggestion 欄位（具體可操作建議）
5. **Cross-QA**: QA 工具必須與 executor_tool 不同（例如 opencode 執行 → codex-cli 審核）

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
log_file_path: doc/logs/Idx-012_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

---

**Plan End**
