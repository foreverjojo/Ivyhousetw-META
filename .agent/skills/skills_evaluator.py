# -*- coding: utf-8 -*-
"""
.agent/skills/skills_evaluator.py
=====================================
用途：解析 Log 中的 SKILLS_EXECUTION_REPORT，產生統計報告
職責：
  - 解析 Log 表格並彙整狀態分布與技能執行次數
  - 輸出 JSON（預設）或 Markdown（--format markdown）
=====================================

使用方式：
    python .agent/skills/skills_evaluator.py <log_file_path> [--format json|markdown]

輸出（JSON）：
    JSON 格式報告（status: pass|warning|error）
退出碼：
    0 = pass|warning
    2 = error
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


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


def _strip_ticks(value: str) -> str:
    v = value.strip()
    if v.startswith("`") and v.endswith("`") and len(v) >= 2:
        return v[1:-1].strip()
    return v


def parse_skills_execution_report(log_content: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    lines = log_content.splitlines()

    header_index = None
    for i, line in enumerate(lines):
        if line.strip().startswith("## 🛠️ SKILLS_EXECUTION_REPORT"):
            header_index = i
            break

    if header_index is None:
        return records

    section_lines: List[str] = []
    for line in lines[header_index + 1 :]:
        if line.startswith("## "):
            break
        section_lines.append(line)

    for raw in section_lines:
        row = raw.strip()
        if not row.startswith("|"):
            continue
        parts = [p.strip() for p in row.strip("|").split("|")]
        if len(parts) < 5:
            continue
        skill, target, status, summary, timestamp = parts[:5]
        if skill.strip().lower() in {"skill", "---", ""}:
            continue
        if re.fullmatch(r"-{3,}", _strip_ticks(skill)):
            continue

        records.append(
            {
                "skill": _strip_ticks(skill),
                "target": _strip_ticks(target),
                "status": _strip_ticks(status).lower(),
                "summary": summary.strip(),
                "timestamp": timestamp.strip(),
            }
        )

    return records


def compute_statistics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {
            "total_executions": 0,
            "success_rate": 0.0,
            "status_distribution": {},
            "skill_counts": {},
            "failed_skills": [],
            "summary": "未找到 skills 執行記錄",
        }

    status_counter = Counter(r.get("status", "") for r in records)
    skill_counter = Counter(r.get("skill", "") for r in records)

    failed_skills = [
        {"skill": r.get("skill", ""), "target": r.get("target", ""), "summary": r.get("summary", "")}
        for r in records
        if r.get("status") in {"fail", "error"}
    ]

    success_count = (
        status_counter.get("pass", 0) + status_counter.get("warning", 0) + status_counter.get("no_tests", 0)
    )
    total_count = len(records)
    success_rate = (success_count / total_count * 100.0) if total_count else 0.0

    return {
        "total_executions": total_count,
        "success_rate": round(success_rate, 2),
        "status_distribution": dict(status_counter),
        "skill_counts": dict(skill_counter.most_common()),
        "failed_skills": failed_skills,
        "summary": f"{total_count} 次執行，成功率 {success_rate:.1f}%",
    }


def generate_markdown_report(stats: Dict[str, Any]) -> str:
    md_lines: List[str] = []
    md_lines.append("# Skills Evaluation Report")
    md_lines.append("")
    md_lines.append(f"**總執行次數**: {stats.get('total_executions', 0)}")
    md_lines.append(f"**成功率**: {stats.get('success_rate', 0.0)}%")
    md_lines.append("")

    md_lines.append("## Status 分布")
    md_lines.append("")
    md_lines.append("| Status | Count |")
    md_lines.append("|--------|-------|")
    for status, count in (stats.get("status_distribution") or {}).items():
        md_lines.append(f"| {status} | {count} |")
    md_lines.append("")

    md_lines.append("## Skills 執行次數")
    md_lines.append("")
    md_lines.append("| Skill | Count |")
    md_lines.append("|-------|-------|")
    for skill, count in (stats.get("skill_counts") or {}).items():
        md_lines.append(f"| {skill} | {count} |")
    md_lines.append("")

    failed = stats.get("failed_skills") or []
    if failed:
        md_lines.append("## 失敗的 Skills")
        md_lines.append("")
        md_lines.append("| Skill | Target | Summary |")
        md_lines.append("|-------|--------|----------|")
        for item in failed:
            md_lines.append(f"| {item.get('skill','')} | {item.get('target','')} | {item.get('summary','')} |")
        md_lines.append("")

    return "\n".join(md_lines).rstrip() + "\n"


def _parse_format(argv: List[str]) -> str:
    if "--format" not in argv:
        return "json"
    try:
        idx = argv.index("--format")
        return argv[idx + 1].strip().lower()
    except Exception:
        return "json"


def main(argv: List[str]) -> int:
    usage = "python .agent/skills/skills_evaluator.py <log_file_path> [--format json|markdown]"

    if len(argv) < 2:
        result = {
            "status": "error",
            "log_path": "",
            "statistics": {},
            "message": "缺少 Log 檔案路徑參數",
            "suggestion": "請提供 Log 檔案路徑，例如：python .agent/skills/skills_evaluator.py .agent/logs/Idx-012_log.md（workflow/治理）或 doc/logs/Idx-012_log.md（專案功能）",
            "usage": usage,
        }
        result = validate_output_schema(result, "skills_evaluator")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    log_path = Path(argv[1])
    output_format = _parse_format(argv)

    if not log_path.exists():
        result = {
            "status": "error",
            "log_path": str(log_path),
            "statistics": {},
            "message": f"Log 檔案不存在：{log_path}",
            "suggestion": "請確認路徑正確，workflow/治理任務的 Log 通常在 .agent/logs；專案功能任務的 Log 通常在 doc/logs。",
            "usage": usage,
        }
        result = validate_output_schema(result, "skills_evaluator")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    try:
        log_content = log_path.read_text(encoding="utf-8")
    except Exception as exc:
        result = {
            "status": "error",
            "log_path": str(log_path),
            "statistics": {},
            "message": f"無法讀取 Log 檔案：{exc}",
            "suggestion": "請確認檔案權限正確，或改用文字編輯器檢查檔案內容。",
            "usage": usage,
        }
        result = validate_output_schema(result, "skills_evaluator")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    records = parse_skills_execution_report(log_content)
    if not records:
        result = {
            "status": "warning",
            "log_path": str(log_path),
            "statistics": {
                "total_executions": 0,
                "success_rate": 0.0,
                "status_distribution": {},
                "skill_counts": {},
                "failed_skills": [],
                "summary": "未找到 skills 執行記錄",
            },
            "message": "Log 中未找到 SKILLS_EXECUTION_REPORT 段落",
            "suggestion": "請確認 Log 檔案格式正確，或補上 SKILLS_EXECUTION_REPORT 表格後再執行。",
            "usage": usage,
        }
        result = validate_output_schema(result, "skills_evaluator")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    stats = compute_statistics(records)

    if output_format == "markdown":
        print(generate_markdown_report(stats), end="")
        return 0

    result = {"status": "pass", "log_path": str(log_path), "statistics": stats, "summary": stats.get("summary", "")}
    result = validate_output_schema(result, "skills_evaluator")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
