"""
檔案用途：Schema 驗證
職責：
  - 載入 JSON Schema
  - 驗證 JSON 資料
  - 提供可讀的錯誤訊息
"""

import json
from pathlib import Path
from typing import List, Optional
from jsonschema import validators


class SchemaValidationError(RuntimeError):
    """給 pipeline_state.json 落盤用：保留可讀錯誤清單在 details"""

    def __init__(self, message: str, details: Optional[List[str]] = None):
        super().__init__(message)
        self.details: List[str] = details or []


def _load_schema(schema_filename: str, schemas_dir: Path) -> dict:
    """載入 JSON Schema 檔案"""
    sp = schemas_dir / schema_filename
    if not sp.exists():
        raise RuntimeError(f"找不到 schema 檔案：{sp}（請確認已放在 schemas/）")
    return json.loads(sp.read_text(encoding="utf-8"))


def validate_json(instance: dict, schema: dict, *, label: str = "") -> None:
    """
    使用 schema 的 $schema 自動選對 validator，並輸出可讀錯誤
    若驗證失敗，拋出 SchemaValidationError
    """
    ValidatorCls = validators.validator_for(schema)
    ValidatorCls.check_schema(schema)
    v = ValidatorCls(schema)

    errors = sorted(v.iter_errors(instance), key=lambda e: list(e.path))
    if not errors:
        return

    # 只列前 20 條，避免 UI / log 爆炸
    lines: List[str] = []
    for e in errors[:20]:
        path = ".".join(str(p) for p in e.path) or "(root)"
        lines.append(f"- {path}: {e.message}")

    hint = f"\n（還有 {len(errors) - 20} 條未顯示）" if len(errors) > 20 else ""
    name = f"[{label}] " if label else ""
    msg = name + "Schema validate 失敗：\n" + "\n".join(lines) + hint
    raise SchemaValidationError(msg, details=lines)


def validate_report_summary(rs: dict, schemas_dir: Path) -> None:
    """驗證 report_summary.json"""
    schema = _load_schema("report_summary.v1.json", schemas_dir)
    validate_json(rs, schema, label="report_summary.v1")
