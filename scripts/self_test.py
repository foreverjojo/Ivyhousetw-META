#!/usr/bin/env python3
# scripts/self_test.py
"""
Regression self-test for Ivy House Meta weekly MVP.

What it checks (minimum, deterministic):
1) report_summary.v1 schema: const locks + required fields are present in schema
2) Step-2 schemas validate: inputs_snapshot(meta_adset/meta_ad), report_insights, consultant_notes, workflow_state
3) Total-row drop must happen (names cannot be empty after drop)
4) Attribution setting must be const
5) Language drift guard: missing required Chinese raw columns triggers a clear error message (simulated)

Run:
  python scripts/self_test.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except Exception:
    print("ERROR: jsonschema is required. Install it first (pip install jsonschema).")
    raise


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


# ---------------------------
# Helpers
# ---------------------------


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def must_exist(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")


def validate_instance(instance: Any, schema: dict[str, Any]) -> list[str]:
    v = Draft202012Validator(schema)
    errors = sorted(v.iter_errors(instance), key=lambda e: list(e.path))
    out: list[str] = []
    for e in errors:
        p = "$"
        for seg in e.path:
            p += f".{seg}" if isinstance(seg, str) else f"[{seg}]"
        out.append(f"{p}: {e.message}")
    return out


def expect_pass(name: str, instance: Any, schema_path: Path) -> None:
    schema = load_json(schema_path)
    errs = validate_instance(instance, schema)
    if errs:
        raise AssertionError(f"[FAIL] {name} should PASS but got errors:\n- " + "\n- ".join(errs))
    print(f"[PASS] {name}")


def expect_fail(
    name: str, instance: Any, schema_path: Path, must_contain: str | None = None
) -> None:
    schema = load_json(schema_path)
    errs = validate_instance(instance, schema)
    if not errs:
        raise AssertionError(f"[FAIL] {name} should FAIL but passed")
    if must_contain and not any(must_contain in e for e in errs):
        raise AssertionError(
            f"[FAIL] {name} failed but error did not contain '{must_contain}'.\nErrors:\n- "
            + "\n- ".join(errs)
        )
    print(f"[PASS] {name} (expected fail)")


def assert_schema_const(schema: dict[str, Any], prop: str, expected: str) -> None:
    props = schema.get("properties", {})
    if prop not in props:
        raise AssertionError(f"Schema missing property: {prop}")
    const = props[prop].get("const")
    if const != expected:
        raise AssertionError(
            f"Schema property {prop}.const mismatch: expected '{expected}', got '{const}'"
        )


def assert_schema_required(schema: dict[str, Any], field: str) -> None:
    req = schema.get("required", [])
    if field not in req:
        raise AssertionError(f"Schema required[] missing: {field}")


# ---------------------------
# Simulated language drift guard (unit test target)
# ---------------------------

META_REQUIRED_ZH_ADSET = [
    "分析報告開始",
    "分析報告結束",
    "廣告組合名稱",
    "廣告組合投遞",
    "廣告組合預算",
    "廣告組合預算類型",
    "花費金額 (TWD)",
    "觸及人數",
    "頻率",
    "歸因設定",
    "結束時間",
    "開始",
    "曝光次數",
    "CPM（每千次廣告曝光成本） (TWD)",
    "連結點擊次數",
    "CPC（單次連結點擊成本） (TWD)",
    "CTR（連結點閱率）",
    "連結頁面瀏覽次數",
    "每次連結頁面瀏覽成本 (TWD)",
    "購買次數",
    "每次購買的成本 (TWD)",
    "加到購物車次數",
    "帳號名稱",
    "行銷活動名稱",
    "購買轉換值",
    "網站直接購買次數",
    "網站直接購買轉換值",
    "開始結帳次數",
]

META_REQUIRED_ZH_AD = [
    "分析報告開始",
    "分析報告結束",
    "廣告名稱",
    "廣告投遞",
    "廣告組合預算",
    "廣告組合預算類型",
    "花費金額 (TWD)",
    "觸及人數",
    "頻率",
    "歸因設定",
    "結束時間",
    "品質排名",
    "互動率排名",
    "轉換率排名",
    "曝光次數",
    "CPM（每千次廣告曝光成本） (TWD)",
    "連結點擊次數",
    "CPC（單次連結點擊成本） (TWD)",
    "CTR（連結點閱率）",
    "連結頁面瀏覽次數",
    "每次連結頁面瀏覽成本 (TWD)",
    "購買次數",
    "每次購買的成本 (TWD)",
    "加到購物車次數",
    "帳號名稱",
    "目標",
    "行銷活動名稱",
    "購買轉換值",
    "網站直接購買次數",
    "網站直接購買轉換值",
    "開始結帳次數",
    "廣告組合名稱",
]


def detect_lang_drift(headers: list[str], required_zh: list[str]) -> tuple[bool, list[str]]:
    missing = [c for c in required_zh if c not in headers]
    return (len(missing) > 0, missing)


# ---------------------------
# Minimal fixtures for Step-2 schemas
# ---------------------------

ATTR_CONST = "點擊後 7 天、瀏覽後 1 天或互動觀看後 1 天"


def fixture_inputs_snapshot_adset() -> dict[str, Any]:
    return {
        "version": "inputs_snapshot.meta_adset.v1",
        "source": "meta_adset_csv",
        "timezone": "Asia/Taipei",
        "attribution_setting": ATTR_CONST,
        "report_start": "2025-12-04",
        "report_end": "2025-12-09",
        "currency": "TWD",
        "dropped_rows": {"total_rows_dropped": 1},
        "rows": [
            {
                "adset_name": "測試廣告組合",
                "adset_delivery": "active",
                "account_name": "102796323413794， TWD",
                "campaign_name": "測試 - 2025-常態影片廣告",
                "spend_twd": 100.0,
                "impressions": 1000,
                "reach": 800,
                "link_clicks": 10,
                "lpv": 8,
                "add_to_cart": 2,
                "initiate_checkout": 1,
                "website_purchases": 1,
                "website_purchase_value": 500.0,
                "purchases": 1,
                "purchase_value": 500.0,
                "adset_budget": 300,
                "adset_budget_type": "每日",
                "frequency": 1.2,
                "ctr_link": None,
                "cpc_link_twd": None,
                "cpm_twd": None,
                "cost_per_lpv_twd": None,
                "cpp_twd": None,
                "end_time": None,
                "start_date": None,
                "attribution_setting": ATTR_CONST,
            }
        ],
    }


def fixture_inputs_snapshot_ad() -> dict[str, Any]:
    return {
        "version": "inputs_snapshot.meta_ad.v1",
        "source": "meta_ad_csv",
        "timezone": "Asia/Taipei",
        "attribution_setting": ATTR_CONST,
        "report_start": "2025-12-04",
        "report_end": "2025-12-09",
        "currency": "TWD",
        "dropped_rows": {"total_rows_dropped": 1},
        "rows": [
            {
                "ad_name": "測試廣告",
                "ad_delivery": "active",
                "adset_name": "測試廣告組合",
                "campaign_name": "測試 - 2025-常態影片廣告",
                "account_name": "102796323413794， TWD",
                "objective": "銷售",
                "spend_twd": 50.0,
                "impressions": 500,
                "reach": 400,
                "frequency": 1.1,
                "link_clicks": 5,
                "lpv": 4,
                "add_to_cart": 1,
                "initiate_checkout": 1,
                "website_purchases": 1,
                "website_purchase_value": 300.0,
                "purchases": 1,
                "purchase_value": 300.0,
                "cpp_twd": None,
                "ctr_link": None,
                "cpc_link_twd": None,
                "cpm_twd": None,
                "cost_per_lpv_twd": None,
                "quality_ranking": None,
                "engagement_ranking": None,
                "conversion_ranking": None,
                "end_time": None,
                "attribution_setting": ATTR_CONST,
            }
        ],
    }


def fixture_inputs_snapshot_v3() -> dict[str, Any]:
    # Metadata-only snapshot (MVP route A)
    return {
        "schema_version": "inputs_snapshot.v3",
        "created_at": "2025-12-10T10:00:00+08:00",
        "week_id": "2025-W49",
        "date_range": "2025-12-04~2025-12-09",
        "uploaded_files": {
            "meta_adset": "ivyhouse_meta_adset_2025-W49.csv",
            "meta_ads": "ivyhouse_meta_ad_2025-W49.csv",
            "web_excel": "web.xlsx",
        },
        "fingerprint": {
            "schema_version": "inputs_fingerprint.v2",
            "generated_at": "2025-12-10T10:00:00+08:00",
            "config": {"detail_level": "adset+ads"},
            "files": {
                "meta_adset": {"name": "a.csv", "size": 1, "sha256": "0" * 64},
                "meta_ads": {"name": "b.csv", "size": 1, "sha256": "1" * 64},
                "web_excel": {"name": "c.xlsx", "size": 1, "sha256": "2" * 64},
            },
        },
        "fp_short": "abcdef12",
        "manual_inputs": {
            "schema_version": "manual_inputs.v1",
            "updated_at": "2025-12-10T10:00:00+08:00",
            "buying_type": "UNKNOWN",
            "optimization_goal": "",
            "billing_event": "",
            "weekly_changes": "",
            "note_for_consultants": "",
        },
        "prev_week": {"week_id": "2025-W48"},
    }


def fixture_report_insights() -> dict[str, Any]:
    return {
        "version": "report_insights.meta.v1",
        "week_id": "2025-W49",
        "timezone": "Asia/Taipei",
        "generated_at": "2025-12-10 10:00:00",
        "date_range": {"start": "2025-12-04", "end": "2025-12-09"},
        "kpi": {
            "spend_twd": 150.0,
            "website_purchases": 2,
            "website_purchase_value": 800.0,
            "roas": 5.3333,
            "purchases": 2,
            "purchase_value": 800.0,
        },
        "creative_diagnostics": {"top_ads": [], "bottom_ads": []},
        "anomalies": [],
        "next_actions": [{"owner": "Marketing", "action": "Test", "kpi": "ROAS"}],
    }


def fixture_consultant_notes() -> dict[str, Any]:
    return {
        "version": "consultant_notes.meta.v1",
        "week_id": "2025-W49",
        "timezone": "Asia/Taipei",
        "generated_at": "2025-12-10 10:00:00",
        "notes": {
            "performance_marketing": ["A"],
            "ecommerce": ["B"],
            "finance": ["C"],
            "fulfillment": ["D"],
            "gm_coo": ["E"],
        },
    }


def fixture_workflow_state() -> dict[str, Any]:
    return {
        "version": "workflow_state.meta_weekly.v1",
        "week_id": "2025-W49",
        "timezone": "Asia/Taipei",
        "date_range": {"start": "2025-12-04", "end": "2025-12-09"},
        "kpi": {
            "meta_spend": 150.0,
            "meta_website_purchases": 2,
            "meta_website_purchase_value": 800.0,
            "meta_roas": 5.3333,
        },
        "guardrail_check": {"tier1": {}, "tier2": {}},
        "department_actions": {
            "gm_coo": [{"task": "t"}],
            "finance": [{"task": "t"}],
            "ecommerce": [{"task": "t"}],
            "marketing": [{"task": "t"}],
            "fulfillment": [{"task": "t"}],
        },
        "risks": [{"risk": "r"}],
        "validation_plan": {"day3": {}, "day7": {}, "day14": {}},
    }


# ---------------------------
# Tests
# ---------------------------


def test_report_summary_schema_locks() -> None:
    schema_path = SCHEMAS / "report_summary.v1.json"
    must_exist(schema_path)
    schema = load_json(schema_path)

    # const locks
    assert_schema_const(schema, "kpi_truth_source", "meta_adset_csv")
    assert_schema_const(schema, "ad_diagnostics_source", "meta_ad_csv")

    # required locks
    assert_schema_required(schema, "generated_at")

    print("[PASS] report_summary.v1 schema locks (const + required)")


def test_step2_schemas_pass_fail() -> None:
    # Step-2 schemas we validate in the MVP pipeline
    p_inputs = SCHEMAS / "inputs_snapshot.v3.json"
    p_insights = SCHEMAS / "report_insights.v1.json"
    p_notes = SCHEMAS / "consultant_notes.v1.json"
    p_ws = SCHEMAS / "workflow_state.v1.json"

    for p in [p_inputs, p_insights, p_notes, p_ws]:
        must_exist(p)

    # PASS (pipeline artifacts)
    expect_pass("inputs_snapshot.v3 PASS", fixture_inputs_snapshot_v3(), p_inputs)
    expect_pass("report_insights PASS", fixture_report_insights(), p_insights)
    expect_pass("consultant_notes PASS", fixture_consultant_notes(), p_notes)
    expect_pass("workflow_state PASS", fixture_workflow_state(), p_ws)

    # FAIL (common drift): missing required field
    bad = fixture_report_insights()
    bad.pop("week_id", None)
    expect_fail("report_insights missing week_id FAIL", bad, p_insights, must_contain="required")

    bad2 = fixture_workflow_state()
    bad2.pop("week_id", None)
    expect_fail("workflow_state missing week_id FAIL", bad2, p_ws, must_contain="required")

    # Optional: row-level input schemas (only if you keep them in schemas/)
    p_adset = SCHEMAS / "inputs_snapshot.meta_adset.v1.json"
    p_ad = SCHEMAS / "inputs_snapshot.meta_ad.v1.json"
    if p_adset.exists() and p_ad.exists():
        expect_pass("inputs_snapshot adset PASS", fixture_inputs_snapshot_adset(), p_adset)
        expect_pass("inputs_snapshot ad PASS", fixture_inputs_snapshot_ad(), p_ad)

        # FAIL: attribution const mismatch
        bad3 = fixture_inputs_snapshot_adset()
        bad3["rows"][0]["attribution_setting"] = "點擊後 1 天"
        expect_fail(
            "inputs_snapshot adset attribution const FAIL", bad3, p_adset, must_contain="expected"
        )

        # FAIL: total row not dropped (name empty after drop)
        bad4 = fixture_inputs_snapshot_ad()
        bad4["rows"][0]["ad_name"] = ""
        expect_fail("inputs_snapshot ad empty name FAIL", bad4, p_ad, must_contain="minLength")
    else:
        print("[SKIP] row-level input snapshot schemas not found (ok for metadata-only MVP)")


def test_language_drift_guard() -> None:
    # Simulate English headers (missing Chinese required)
    english_headers = ["Reporting Starts", "Reporting Ends", "Ad Name", "Amount Spent (TWD)"]
    drift, missing = detect_lang_drift(english_headers, META_REQUIRED_ZH_AD)
    if not drift:
        raise AssertionError("[FAIL] language drift guard should detect missing Chinese headers")
    if len(missing) < 10:
        raise AssertionError(
            "[FAIL] language drift guard missing list too small; required list may be wrong"
        )
    print("[PASS] language drift guard detects missing Chinese headers")


def main() -> int:
    try:
        test_report_summary_schema_locks()
        test_step2_schemas_pass_fail()
        test_language_drift_guard()
    except Exception as e:
        print(str(e))
        return 1

    print("\nALL SELF-TESTS PASSED ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
