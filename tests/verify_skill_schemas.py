"""tests/verify_skill_schemas.py
=====================================
用途：驗證 .agent/skills/schemas/ 下的 JSON Schema 檔案可被解析且本身符合 Draft-07 規範
職責：作為 CI 前置檢查；任何 schema 格式/結構錯誤即以非 0 退出碼失敗
=====================================

使用方式：
    python tests/verify_skill_schemas.py

退出碼：
    0 = 全部通過
    1 = 有 schema 解析/結構錯誤
    2 = 執行環境缺少必要依賴（例如 jsonschema）
"""

import json
from pathlib import Path
from typing import Any


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _schemas_dir() -> Path:
    return _project_root() / ".agent" / "skills" / "schemas"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    schemas_dir = _schemas_dir()
    if not schemas_dir.exists():
        print(f"❌ 找不到 schemas 目錄：{schemas_dir}")
        return 1

    try:
        from jsonschema import Draft7Validator
    except ImportError:
        print("❌ 缺少 jsonschema，無法檢查 schema 結構；請先安裝 requirements.txt")
        return 2

    schema_files = sorted(schemas_dir.glob("*_output.schema.json"))
    if not schema_files:
        print(f"⚠️ 未找到任何 schema 檔案：{schemas_dir}")
        return 1

    errors: list[str] = []

    for schema_path in schema_files:
        try:
            schema = _load_json(schema_path)
        except Exception as exc:
            errors.append(f"{schema_path}: JSON 解析失敗：{exc}")
            continue

        try:
            Draft7Validator.check_schema(schema)
        except Exception as exc:
            errors.append(f"{schema_path}: schema 結構不合法：{exc}")

    if errors:
        print("❌ Skills schemas 檢查失敗：")
        for e in errors:
            print(f"- {e}")
        return 1

    print(f"✅ Skills schemas 檢查通過，共 {len(schema_files)} 個檔案")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
