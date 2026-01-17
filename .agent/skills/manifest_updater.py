# -*- coding: utf-8 -*-
"""
.agent/skills/manifest_updater.py
=====================================
用途：Skills Manifest 自動同步工具
職責：掃描 .agent/skills/*.py，更新 skill_manifest.json 的 builtin 清單並保留 external/legacy 記錄
=====================================

使用方式：
    python .agent/skills/manifest_updater.py --check
    python .agent/skills/manifest_updater.py --sync

輸出：
    JSON 格式報告（status: pass|error）
退出碼：
    0 = pass
    2 = error
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SKILLS_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = SKILLS_DIR / "skill_manifest.json"
SCHEMAS_DIR = SKILLS_DIR / "schemas"


EXTERNAL_MARKERS = ("source_repo", "sha256_hash", "downloaded_at", "file_path", "commit_sha")


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


def is_external_record(record: Dict[str, Any]) -> bool:
    if record.get("type") == "external":
        return True
    return any(k in record for k in EXTERNAL_MARKERS)


def is_builtin_record(record: Dict[str, Any]) -> bool:
    if record.get("type") == "builtin":
        return True
    path = record.get("path")
    if isinstance(path, str) and path.startswith(".agent/skills/") and not is_external_record(record):
        return True
    return False


def should_preserve_record(record: Dict[str, Any]) -> bool:
    return not is_builtin_record(record)


def read_first_purpose_line(py_file: Path) -> str:
    try:
        head = py_file.read_text(encoding="utf-8").splitlines()[:40]
    except Exception:
        return "（無法讀取用途）"
    for line in head:
        stripped = line.strip()
        if stripped.startswith("用途："):
            return stripped.replace("用途：", "").strip() or "（未提供用途）"
    return "（未提供用途）"


def scan_builtin_skills(exclude_names: Iterable[str]) -> List[Dict[str, Any]]:
    exclude = set(exclude_names)
    skills: List[Dict[str, Any]] = []

    for py_file in sorted(SKILLS_DIR.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        skill_name = py_file.stem
        if skill_name in exclude:
            continue

        schema_file = SCHEMAS_DIR / f"{skill_name}_output.schema.json"
        schema_path = f".agent/skills/schemas/{schema_file.name}" if schema_file.exists() else None

        skills.append(
            {
                "name": skill_name,
                "type": "builtin",
                "version": "1.0.0",
                "path": f".agent/skills/{py_file.name}",
                "description": read_first_purpose_line(py_file),
                "schema": schema_path,
                "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

    return skills


def load_manifest() -> Dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return {"version": "1.0", "skills": []}
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(manifest: Dict[str, Any]) -> None:
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def build_manifest(existing: Dict[str, Any]) -> Tuple[Dict[str, Any], int, int, int]:
    existing_skills = existing.get("skills", [])
    if not isinstance(existing_skills, list):
        existing_skills = []

    preserved = [s for s in existing_skills if isinstance(s, dict) and s.get("name") and should_preserve_record(s)]
    external_names = [s.get("name") for s in preserved if isinstance(s, dict) and s.get("name") and is_external_record(s)]

    builtin_skills = scan_builtin_skills(exclude_names=external_names)

    builtin_names = {s["name"] for s in builtin_skills}
    preserved_filtered = [s for s in preserved if s.get("name") not in builtin_names]

    manifest = {
        "version": existing.get("version", "1.0"),
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "skills": builtin_skills + preserved_filtered,
    }

    return manifest, len(builtin_skills), len(preserved_filtered), len(builtin_skills) + len(preserved_filtered)


def main(argv: List[str]) -> int:
    if "--sync" not in argv and "--check" not in argv:
        result = {
            "status": "error",
            "manifest_path": str(MANIFEST_PATH),
            "message": "缺少參數（--sync 或 --check）",
            "usage": "python .agent/skills/manifest_updater.py [--sync|--check]",
            "suggestion": "請使用 --check（不寫入）或 --sync（寫入更新）。",
        }
        result = validate_output_schema(result, "manifest_updater")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    dry_run = "--check" in argv and "--sync" not in argv

    try:
        existing = load_manifest()
        new_manifest, builtin_count, preserved_count, total_count = build_manifest(existing)
    except Exception as exc:
        result = {
            "status": "error",
            "manifest_path": str(MANIFEST_PATH),
            "message": f"更新 manifest 失敗：{exc}",
            "usage": "python .agent/skills/manifest_updater.py [--sync|--check]",
            "suggestion": "請確認 skill_manifest.json 格式正確，且 .agent/skills 目錄可讀取。",
        }
        result = validate_output_schema(result, "manifest_updater")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    if not dry_run:
        try:
            save_manifest(new_manifest)
        except Exception as exc:
            result = {
                "status": "error",
                "manifest_path": str(MANIFEST_PATH),
                "message": f"寫入 manifest 失敗：{exc}",
                "suggestion": "請確認檔案權限可寫入，或改用 --check 先檢視更新結果。",
            }
            result = validate_output_schema(result, "manifest_updater")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2

    result = {
        "status": "pass",
        "manifest_path": str(MANIFEST_PATH),
        "dry_run": dry_run,
        "builtin_count": builtin_count,
        "preserved_count": preserved_count,
        "total_count": total_count,
        "summary": "已同步 builtin skills 並保留 external/legacy 記錄" if not dry_run else "Dry run：已計算 manifest 更新結果",
    }
    result = validate_output_schema(result, "manifest_updater")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
