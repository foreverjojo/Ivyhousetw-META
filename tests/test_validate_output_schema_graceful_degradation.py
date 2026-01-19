"""tests/test_validate_output_schema_graceful_degradation.py
=====================================
用途：覆蓋 skills 的 validate_output_schema graceful-degradation 行為
職責：確保缺少 jsonschema 或缺少 schema 檔案時，不會阻擋技能輸出/流程
=====================================
"""

from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = PROJECT_ROOT / ".agent" / "skills"


def _load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"無法載入 module：{module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "module_path, skill_name",
    [
        (SKILLS_DIR / "plan_validator.py", "plan_validator"),
        (SKILLS_DIR / "code_reviewer.py", "code_reviewer"),
        (SKILLS_DIR / "manifest_updater.py", "manifest_updater"),
    ],
)
def test_validate_output_schema_graceful_degradation_when_jsonschema_missing(
    monkeypatch: pytest.MonkeyPatch, module_path: Path, skill_name: str
):
    module = _load_module(f"skill_{skill_name}", module_path)
    assert hasattr(module, "validate_output_schema")

    original: dict[str, Any] = {"status": "pass"}

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "jsonschema" or name.startswith("jsonschema."):
            raise ImportError("mocked jsonschema missing")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    out = module.validate_output_schema(original, skill_name)
    assert out is original
    assert "validation_errors" not in out


def test_validate_output_schema_graceful_degradation_when_schema_file_missing():
    module = _load_module("skill_plan_validator", SKILLS_DIR / "plan_validator.py")

    original: dict[str, Any] = {"status": "pass"}
    out = module.validate_output_schema(original, "definitely_missing_schema_for_test")

    assert out is original
    assert "validation_errors" not in out


def test_validate_output_schema_adds_validation_errors_when_schema_validation_fails():
    module = _load_module("skill_plan_validator_for_validation", SKILLS_DIR / "plan_validator.py")

    # plan_validator schema 會要求多個必填欄位；此處刻意提供不完整輸出
    bad_output: dict[str, Any] = {"status": "pass"}
    out = module.validate_output_schema(bad_output, "plan_validator")

    assert out is bad_output
    assert "validation_errors" in out
    assert isinstance(out["validation_errors"], list)
    assert out["validation_errors"], "應至少包含一筆 validation error"
