#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Callable

from jsonschema import validators

try:
    from zoneinfo import ZoneInfo
    TAIPEI_TZ = ZoneInfo("Asia/Taipei")
except Exception:
    TAIPEI_TZ = None


def now_iso() -> str:
    if TAIPEI_TZ:
        return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")
    return datetime.now().isoformat(timespec="seconds")


def read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


# ---- schema validate ----
SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "schemas"


def _load_schema(schema_filename: str) -> dict:
    sp = SCHEMAS_DIR / schema_filename
    if not sp.exists():
        raise RuntimeError(f"Schema file not found: {sp}")
    return json.loads(sp.read_text(encoding="utf-8"))


class SchemaValidationError(RuntimeError):
    def __init__(self, message: str, details: Optional[List[str]] = None):
        super().__init__(message)
        self.details: List[str] = details or []


def validate_json(instance: dict, schema: dict, *, label: str = "") -> None:
    ValidatorCls = validators.validator_for(schema)
    ValidatorCls.check_schema(schema)
    v = ValidatorCls(schema)

    errors = sorted(v.iter_errors(instance), key=lambda e: list(e.path))
    if not errors:
        return

    lines: List[str] = []
    for e in errors[:20]:
        path = ".".join(str(p) for p in e.path) or "(root)"
        lines.append(f"- {path}: {e.message}")

    prefix = f"[{label}] " if label else ""
    msg = prefix + "Schema validate failed:\n" + "\n".join(lines)
    raise SchemaValidationError(msg, details=lines)


def validate_report_summary(rs: dict) -> None:
    schema = _load_schema("report_summary.v1.json")
    validate_json(rs, schema, label="report_summary.v1")


# ---- pipeline_state writer (minimal) ----
def write_pipeline_state(
    vdir: Path,
    step: str,
    *,
    mode: str = "self_test",
    status: str = "ok",
    error: Optional[str] = None,
    details: Optional[List[str]] = None,
) -> None:
    p = vdir / "pipeline_state.json"
    state = read_json(p) if p.exists() else {
        "schema_version": "pipeline_state.v1",
        "created_at": now_iso(),
        "events": [],
    }

    state["updated_at"] = now_iso()
    state["last_completed_step"] = step
    state["last_mode"] = mode

    ev = {"at": now_iso(), "mode": mode, "step": step, "status": status}
    if error:
        ev["error"] = error
    if details:
        ev["details"] = details

    state["events"].append(ev)
    write_json(p, state)


# ---- fixtures ----
def make_valid_report_summary() -> dict:
    return {
        "schema_version": "report_summary.v1",
        "generated_at": now_iso(),
        "week_id": "2025-W49",
        "date_range": "2025-12-04~2025-12-09",
        "kpi_truth_source": "meta_adset_csv",
        "ad_diagnostics_source": "meta_ad_csv",
        "kpi": {
            "meta": {
                "spend_twd": 1.0,
                "purchase_value_twd": 2.0,
                "purchases": 1,
                "roas_calc": 2.0,
                "cpa_calc_twd": 1.0,
                "funnel": {
                    "link_clicks": 1,
                    "landing_page_views": 1,
                    "add_to_cart": 0,
                    "initiate_checkout": 0
                },
                "ads_has_rankings": False
            },
            "web": {
                "orders": 1,
                "revenue_twd": 100.0,
                "aov_twd_calc": 100.0,
                "columns": ["訂單量", "營業額"]
            }
        },
        "tables": {
            "top_adsets_by_roas": [],
            "worst_adsets_by_roas": [],
            "top_ads_by_roas": [],
            "worst_ads_by_roas": []
        },
        "missing_data": {
            "meta_unavailable_fields": ["optimization_goal", "billing_event", "buying_type"],
            "note": "test"
        }
    }


def expect_validate_error_and_event(rs: dict, vdir: Path) -> None:
    try:
        validate_report_summary(rs)
        raise AssertionError("Expected SchemaValidationError, but validation passed.")
    except SchemaValidationError as e:
        write_pipeline_state(
            vdir,
            "B(validate_error)",
            status="error",
            error=str(e),
            details=e.details,
        )
        ps = read_json(vdir / "pipeline_state.json")
        last = ps["events"][-1]
        assert last["step"] == "B(validate_error)"
        assert last["status"] == "error"
        assert isinstance(last.get("details"), list) and len(last["details"]) > 0


# ---- 4 cases ----
def case_1_valid_should_pass():
    validate_report_summary(make_valid_report_summary())


def case_2_wrong_kpi_truth_source_should_fail_and_log():
    rs = make_valid_report_summary()
    rs["kpi_truth_source"] = "WRONG_VALUE"
    with tempfile.TemporaryDirectory() as d:
        expect_validate_error_and_event(rs, Path(d))


def case_3_wrong_ad_diagnostics_source_should_fail_and_log():
    rs = make_valid_report_summary()
    rs["ad_diagnostics_source"] = "WRONG_VALUE"
    with tempfile.TemporaryDirectory() as d:
        expect_validate_error_and_event(rs, Path(d))


def case_4_missing_required_field_should_fail_and_log():
    rs = make_valid_report_summary()
    rs["kpi"]["meta"].pop("spend_twd", None)
    with tempfile.TemporaryDirectory() as d:
        expect_validate_error_and_event(rs, Path(d))


@dataclass
class Case:
    name: str
    fn: Callable[[], None]


def main():
    cases = [
        Case("case_1_valid_should_pass", case_1_valid_should_pass),
        Case("case_2_wrong_kpi_truth_source_should_fail_and_log", case_2_wrong_kpi_truth_source_should_fail_and_log),
        Case("case_3_wrong_ad_diagnostics_source_should_fail_and_log", case_3_wrong_ad_diagnostics_source_should_fail_and_log),
        Case("case_4_missing_required_field_should_fail_and_log", case_4_missing_required_field_should_fail_and_log),
    ]

    print("Running self tests...")
    for c in cases:
        c.fn()
        print(f"[PASS] {c.name}")
    print(f"All passed: {len(cases)}/{len(cases)}")


if __name__ == "__main__":
    main()
