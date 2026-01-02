"""
scripts/validator.py

Centralized JSONSchema validation helpers for Ivy House weekly MVP.
- Uses schemas/ as the single source of truth.
- On validation error, records an ERROR event into vdir/pipeline_state.json
  via scripts.pipeline_state.write_pipeline_state, then raises.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from jsonschema import validators

from scripts.pipeline_state import write_pipeline_state


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT / "schemas"


class SchemaValidationError(RuntimeError):
    """Validation error carrying human-readable details for UI/logging."""

    def __init__(self, message: str, details: Optional[List[str]] = None):
        super().__init__(message)
        self.details: List[str] = details or []


def schema_path(schema_filename: str) -> Path:
    return SCHEMAS_DIR / schema_filename


def schema_exists(schema_filename: str) -> bool:
    return schema_path(schema_filename).exists()


def load_schema(schema_filename: str) -> Dict[str, Any]:
    sp = schema_path(schema_filename)
    if not sp.exists():
        raise FileNotFoundError(f"找不到 schema 檔案：{sp}（請確認已放在 schemas/）")
    return json.loads(sp.read_text(encoding="utf-8"))


def _format_errors(errors: List[Any], *, limit: int = 20) -> List[str]:
    lines: List[str] = []
    for e in errors[:limit]:
        path = ".".join(str(p) for p in e.path) or "(root)"
        lines.append(f"- {path}: {e.message}")
    if len(errors) > limit:
        lines.append(f"- ...（還有 {len(errors)-limit} 條未顯示）")
    return lines


def validate_jsonschema(instance: Dict[str, Any], schema: Dict[str, Any], *, label: str = "") -> None:
    """
    Validate instance against schema (auto-choose validator from $schema).
    Raises SchemaValidationError with `.details` (list[str]).
    """
    ValidatorCls = validators.validator_for(schema)
    ValidatorCls.check_schema(schema)
    v = ValidatorCls(schema)

    errors = sorted(v.iter_errors(instance), key=lambda e: list(e.path))
    if not errors:
        return

    details = _format_errors(errors)
    prefix = f"[{label}] " if label else ""
    msg = prefix + "Schema validate 失敗：\n" + "\n".join(details)
    raise SchemaValidationError(msg, details=details)


def validate_file(
    instance: Dict[str, Any],
    *,
    schema_filename: str,
    label: str = "",
) -> None:
    schema = load_schema(schema_filename)
    validate_jsonschema(instance, schema, label=label or schema_filename)


def validate_or_record(
    *,
    instance: Dict[str, Any],
    schema_filename: str,
    label: str,
    vdir: Path,
    mode: str,
    step_on_error: str,
    skip_if_missing_schema: bool = True,
) -> None:
    """
    Validate instance with schema file.
    - If schema missing and skip_if_missing_schema=True: do nothing (MVP-friendly).
    - If invalid: record pipeline_state ERROR event, then raise.
    """
    if not schema_exists(schema_filename):
        if skip_if_missing_schema:
            return
        raise FileNotFoundError(f"缺少 schema：schemas/{schema_filename}")

    try:
        validate_file(instance, schema_filename=schema_filename, label=label)
    except SchemaValidationError as e:
        write_pipeline_state(
            vdir,
            step_on_error,
            mode,
            status="error",
            error=str(e),
            details=e.details,
        )
        raise
    except Exception as e:
        write_pipeline_state(
            vdir,
            step_on_error,
            mode,
            status="error",
            error=str(e),
            details=[str(e)],
        )
        raise
