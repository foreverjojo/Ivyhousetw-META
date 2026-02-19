# -*- coding: utf-8 -*-
"""
.agent/skills/git_stats_reporter.py
=====================================
用途：Git 變更統計工具（numstat 解析）
職責：解析 git diff --numstat 輸出，計算變更統計並輸出 Gate 觸發建議
=====================================

使用方式：
    python .agent/skills/git_stats_reporter.py <diff_file_path>

輸入：
    <diff_file_path> 內容需為 git diff --numstat 的輸出

輸出：
    JSON 格式報告（status: pass|error）
退出碼：
    0 = pass
    2 = error
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


MAINTAINABILITY_THRESHOLD = 50
MAINTAINABILITY_CORE_PATHS = ("core/", "utils/", "config.py")

UI_UX_PATH_PREFIXES = ("pages/", "ui/")
UI_UX_ENTRY_FILES = ("app.py", "main.py")
UI_UX_NAME_SUFFIXES = ("_page.py", "_ui.py", "_component.py")


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


@dataclass(frozen=True)
class NumstatRow:
    added: int
    deleted: int
    path: str
    is_binary: bool = False


def _parse_int_or_dash(value: str) -> Tuple[int, bool]:
    if value.strip() == "-":
        return 0, True
    return int(value), False


def parse_numstat_lines(lines: Iterable[str]) -> List[NumstatRow]:
    rows: List[NumstatRow] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added_s, deleted_s, path = parts[0], parts[1], "\t".join(parts[2:])
        try:
            added, added_bin = _parse_int_or_dash(added_s)
            deleted, deleted_bin = _parse_int_or_dash(deleted_s)
        except ValueError:
            continue
        rows.append(NumstatRow(added=added, deleted=deleted, path=path, is_binary=added_bin or deleted_bin))
    return rows


def compute_triggers(affected_paths: List[str], total_lines_changed: int) -> Dict[str, bool]:
    maintainability_gate = False
    ui_ux_gate = False

    if total_lines_changed > MAINTAINABILITY_THRESHOLD:
        maintainability_gate = True

    for p in affected_paths:
        if any(p.startswith(prefix) for prefix in MAINTAINABILITY_CORE_PATHS if prefix.endswith("/")):
            maintainability_gate = True
        if p == "config.py":
            maintainability_gate = True

        if p.startswith(UI_UX_PATH_PREFIXES) or p in UI_UX_ENTRY_FILES or p.endswith(UI_UX_NAME_SUFFIXES):
            ui_ux_gate = True

    return {"maintainability_gate": maintainability_gate, "ui_ux_gate": ui_ux_gate}


def generate_report(diff_content: str) -> Dict[str, Any]:
    rows = parse_numstat_lines(diff_content.splitlines())
    affected_paths = sorted({r.path for r in rows})
    total_lines_added = sum(r.added for r in rows)
    total_lines_deleted = sum(r.deleted for r in rows)
    total_lines_changed = total_lines_added + total_lines_deleted

    triggers = compute_triggers(affected_paths, total_lines_changed)

    return {
        "status": "pass",
        "total_files_changed": len(affected_paths),
        "total_lines_added": total_lines_added,
        "total_lines_deleted": total_lines_deleted,
        "total_lines_changed": total_lines_changed,
        "affected_paths": affected_paths,
        "triggers": triggers,
        "summary": f"{len(affected_paths)} files, +{total_lines_added}/-{total_lines_deleted} lines",
    }


def error_result(summary: str, suggestion: str | None = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "status": "error",
        "total_files_changed": 0,
        "total_lines_added": 0,
        "total_lines_deleted": 0,
        "total_lines_changed": 0,
        "affected_paths": [],
        "triggers": {"maintainability_gate": False, "ui_ux_gate": False},
        "summary": summary,
        "usage": "python .agent/skills/git_stats_reporter.py <diff_file_path>",
    }
    if suggestion:
        result["suggestion"] = suggestion
    return result


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print(
            json.dumps(
                validate_output_schema(
                    error_result(
                    "缺少 diff 檔案路徑參數",
                    suggestion="請先產生 diff 檔案，例如：\n"
                    "  git diff --cached --numstat > /tmp/diff_stats.txt  # staged changes\n"
                    "  git diff HEAD --numstat > /tmp/diff_stats.txt      # all uncommitted\n"
                    "  git diff --numstat > /tmp/diff_stats.txt           # unstaged changes",
                    ),
                    "git_stats_reporter",
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    diff_path = Path(argv[1])
    if not diff_path.exists():
        print(
            json.dumps(
                validate_output_schema(
                    error_result(
                    f"Diff 檔案不存在：{diff_path}",
                    suggestion="請先產生 diff 檔案，例如：\n"
                    "  git diff --cached --numstat > /tmp/diff_stats.txt  # staged changes\n"
                    "  git diff HEAD --numstat > /tmp/diff_stats.txt      # all uncommitted\n"
                    "  git diff --numstat > /tmp/diff_stats.txt           # unstaged changes",
                    ),
                    "git_stats_reporter",
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    try:
        diff_content = diff_path.read_text(encoding="utf-8")
    except Exception as exc:
        result = error_result(f"讀取 Diff 檔案失敗：{exc}")
        result = validate_output_schema(result, "git_stats_reporter")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    report = generate_report(diff_content)
    report = validate_output_schema(report, "git_stats_reporter")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
