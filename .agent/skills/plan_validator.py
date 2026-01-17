# -*- coding: utf-8 -*-
"""
.agent/skills/plan_validator.py
=====================================
用途：Plan 格式驗證工具
職責：驗證 doc/plans/Idx-XXX_*.md 是否包含必要段落與 EXECUTION_BLOCK 關鍵欄位
=====================================

使用方式：
    python .agent/skills/plan_validator.py <plan_file_path>

輸出：
    JSON 格式報告（status: pass|fail|error）
退出碼：
    0 = pass
    1 = fail
    2 = error
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_SECTIONS = [
    "## 📋 SPEC",
    "## 🔍 RESEARCH & ASSUMPTIONS",
    "## 🔒 SCOPE & CONSTRAINTS",
    "## 📁 檔案變更",
    "<!-- EXECUTION_BLOCK_START -->",
    "<!-- EXECUTION_BLOCK_END -->",
]

REQUIRED_EXECUTION_FIELDS = [
    "executor_tool:",
    "qa_tool:",
    "last_change_tool:",
]


def validate_output_schema(result: Dict[str, Any], skill_name: str) -> Dict[str, Any]:
    """可選 JSON Schema 驗證（graceful degradation）"""
    try:
        import jsonschema
    except ImportError:
        return result

    schema_path = Path(__file__).resolve().parent / "schemas" / f"{skill_name}_output.schema.json"
    if not schema_path.exists():
        return result

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(result, schema)
        return result
    except jsonschema.ValidationError as exc:
        result["validation_errors"] = [
            {"message": exc.message, "path": list(exc.path), "schema_path": list(exc.schema_path)}
        ]
        result.setdefault(
            "suggestion",
            f"輸出格式不符合 schema 規範。請檢查 {skill_name}_output.schema.json 並確認欄位正確性。",
        )
        return result
    except Exception:
        return result


def _extract_execution_block(content: str) -> str | None:
    start = "<!-- EXECUTION_BLOCK_START -->"
    end = "<!-- EXECUTION_BLOCK_END -->"
    if start not in content or end not in content:
        return None
    return content.split(start, 1)[1].split(end, 1)[0]


def validate_plan(plan_path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "status": "pass",
        "plan_path": str(plan_path),
        "missing_sections": [],
        "format_errors": [],
        "summary": "Plan 驗證通過",
    }

    if not plan_path.exists():
        return {
            "status": "error",
            "plan_path": str(plan_path),
            "missing_sections": [],
            "format_errors": [],
            "summary": f"Plan 檔案不存在：{plan_path}",
            "usage": "python .agent/skills/plan_validator.py <plan_file_path>",
            "suggestion": "請確認路徑正確，或先由 Planner 產生/更新 Plan 檔案。",
        }

    try:
        content = plan_path.read_text(encoding="utf-8")
    except Exception as exc:
        return {
            "status": "error",
            "plan_path": str(plan_path),
            "missing_sections": [],
            "format_errors": [f"讀取檔案失敗：{exc}"],
            "summary": "Plan 驗證失敗（讀取檔案錯誤）",
            "usage": "python .agent/skills/plan_validator.py <plan_file_path>",
        }

    for section in REQUIRED_SECTIONS:
        if section not in content:
            result["missing_sections"].append(section)

    if "research_required:" not in content:
        result["format_errors"].append("缺少 research_required: true/false（位於 RESEARCH & ASSUMPTIONS 段落）")

    exec_block = _extract_execution_block(content)
    if exec_block is None:
        result["format_errors"].append("缺少 EXECUTION_BLOCK（請確認包含 START/END 註解）")
    else:
        for field in REQUIRED_EXECUTION_FIELDS:
            if field not in exec_block:
                result["format_errors"].append(f"EXECUTION_BLOCK 缺少欄位：{field}")

    if result["missing_sections"] or result["format_errors"]:
        result["status"] = "fail"
        result["summary"] = (
            f"Plan 驗證未通過：缺少 {len(result['missing_sections'])} 個段落，"
            f"{len(result['format_errors'])} 個格式問題"
        )

    return result


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        result = {
            "status": "error",
            "plan_path": "",
            "missing_sections": [],
            "format_errors": [],
            "summary": "缺少 Plan 檔案路徑參數",
            "usage": "python .agent/skills/plan_validator.py <plan_file_path>",
            "suggestion": "請提供 Plan 檔案路徑，例如：python .agent/skills/plan_validator.py doc/plans/Idx-012_*.md",
        }
        result = validate_output_schema(result, "plan_validator")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    plan_path = Path(argv[1])
    result = validate_plan(plan_path)
    result = validate_output_schema(result, "plan_validator")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] == "pass":
        return 0
    if result["status"] == "fail":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
