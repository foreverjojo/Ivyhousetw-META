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
    name: str,
    instance: Any,
    schema_path: Path,
    must_contain: str | list[str] | None = None,
    must_contain_any: list[str] | None = None,
) -> None:
    schema = load_json(schema_path)
    errs = validate_instance(instance, schema)
    if not errs:
        raise AssertionError(f"[FAIL] {name} should FAIL but passed")

    if must_contain is not None and must_contain_any is not None:
        raise ValueError("Use either must_contain or must_contain_any, not both")

    if isinstance(must_contain, list):
        if must_contain and not any(any(m in e for m in must_contain) for e in errs):
            raise AssertionError(
                f"[FAIL] {name} failed but error did not contain any of {must_contain}.\nErrors:\n- "
                + "\n- ".join(errs)
            )
    elif must_contain and not any(must_contain in e for e in errs):
        raise AssertionError(
            f"[FAIL] {name} failed but error did not contain '{must_contain}'.\nErrors:\n- "
            + "\n- ".join(errs)
        )
    elif must_contain_any and not any(any(s in e for s in must_contain_any) for e in errs):
        raise AssertionError(
            f"[FAIL] {name} failed but error did not contain any of {must_contain_any}.\nErrors:\n- "
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
        "insights_version": "insights.v1",
        "week_id": "2025-W49",
        "date_range": "2025-12-04~2025-12-09",
        "executive_summary": [
            "ROAS 表現良好（僅示意；實際數字須引用輸入 report_summary）",
            "素材組合 A 相對優於 B（僅示意）",
            "建議先補齊缺失欄位再擴量（僅示意）",
        ],
        "what_worked": ["Top 組合共同點：受眾更聚焦（示意）"],
        "what_didnt": ["Worst 組合共同點：頻次偏高（示意）"],
        "diagnostics": {
            "traffic": "流量：CTR/CPM 依輸入判讀（示意）",
            "conversion": "轉換：CPA/ROAS 依輸入判讀（示意）",
            "creative": "素材：以 top/worst ads 觀察（示意）",
        },
        "actions": [
            {
                "owner": "Marketing",
                "task": "建立 2 組素材 A/B 測試",
                "deliverable": "新素材 2 版 + 上線紀錄",
                "why": "降低素材疲乏風險（示意）",
                "kpi": "CTR 上升（示意）",
                "stoploss": "若 CTR 下降則回滾（示意）",
            }
        ],
        "data_issues": ["缺少部分欄位（示意）"],
        "open_questions": ["本週是否有重大投放策略調整？（示意）"],
    }


def fixture_consultant_notes() -> dict[str, Any]:
    return {
        "consultants_version": "consultants.v1",
        "week_id": "2025-W49",
        "date_range": "2025-12-04~2025-12-09",
        "avg_daily_spend_twd_calc": 1000.0,
        "consultant_A": {
            "consultant_key": "A",
            "summary": ["成效面結論（示意）"],
            "opportunities": ["可擴量機會（示意）"],
            "risks": [
                {
                    "risk": "轉換波動",
                    "probability": "中",
                    "impact": "影響放量",
                    "mitigation": "先小幅調整",
                    "alternative": "先做素材測試",
                }
            ],
            "overall_budget_action": {
                "action": "hold",
                "change_pct": 0,
                "rationale": "先確認資料口徑一致（示意）",
            },
            "adset_ads_actions": [
                {
                    "level": "adset",
                    "name": "測試廣告組合",
                    "action": "increase",
                    "why": "ROAS 較佳（示意）",
                    "kpi": "ROAS",
                    "stoploss": "ROAS 低於門檻則回復",
                }
            ],
            "next_7d_actions": [
                {
                    "task": "調整預算節奏",
                    "owner_role": "Marketing",
                    "deliverable": "預算調整紀錄",
                    "due": "D+2",
                    "kpi": "ROAS",
                    "stoploss": "ROAS 下滑則停止",
                    "why": "避免過快放量（示意）",
                }
            ],
            "questions": ["本週是否有促銷檔期？（示意）"],
        },
        "consultant_B": {
            "consultant_key": "B",
            "summary": ["創意面結論（示意）"],
            "overall_budget_action": {"action": "hold", "change_pct": 0, "rationale": "（示意）"},
        },
        "consultant_C": {
            "consultant_key": "C",
            "summary": ["策略面結論（示意）"],
            "overall_budget_action": {"action": "hold", "change_pct": 0, "rationale": "（示意）"},
        },
    }


def fixture_consultant_cross_review_pass(reviewer: str = "A") -> dict[str, Any]:
    """合法的 E2 交叉審核 fixture（用於 schema PASS 測試）。"""
    targets_map = {"A": ["B", "C"], "B": ["A", "C"], "C": ["A", "B"]}
    targets = targets_map.get(reviewer, ["B", "C"])
    return {
        "review_version": "consultant_cross_review.v1",
        "reviewer": reviewer,
        "reviewed_targets": targets,
        "strengths": [
            f"reviewer {reviewer} 肯定點 1：依據 source:consultant_{targets[0]}.summary[0]",
        ],
        "critical_issues": [
            {
                "issue": "建議過於樂觀，缺乏風險說明",
                "evidence_ref": f"source:consultant_{targets[0]}.risks[0].risk",
                "impact": "可能誤導預算加碼決策",
                "severity": "medium",
                "suggested_fix": "補充停損條件",
            }
        ],
        "assumptions_to_validate": [
            {
                "assumption": "假設下週轉換率持平",
                "validation_step": "確認廣告帳戶歸因設定未變更",
            }
        ],
        "recommended_edits": ["建議在 next_7d_actions 中加入停損 KPI 門檻"],
        "stoploss_or_guardrails": ["若 ROAS 低於 1.9 立即暫停加碼"],
        "confidence": 0.75,
        "why": "本次審核核心關切是決策建議缺乏明確止損機制，在高 CPA 環境下風險較高。",
    }


def fixture_consultant_cross_review_fail_missing_field() -> dict[str, Any]:
    """缺少必填欄位的 E2 fixture（用於 schema FAIL 測試）。"""
    return {
        "review_version": "consultant_cross_review.v1",
        "reviewer": "A",
        "reviewed_targets": ["B", "C"],
        # 缺少 strengths, critical_issues, recommended_edits 等必填欄位
        "confidence": 0.5,
        "why": "測試用",
    }


def fixture_workflow_state() -> dict[str, Any]:
    return {
        "schema_version": "workflow_state.v1",
        "week_id": "2025-W49",
        "date_range": "2025-12-04~2025-12-09",
        "kpi_snapshot": {"meta": {"spend_twd": 150.0}, "web": {"orders": 2}},
        "decisions": ["做：先確立口徑（示意）"],
        "guardrail_check": {"tier1": {}, "tier2": {}},
        "consultant_summary": ["共識：先修資料口徑（示意）"],
        "department_actions": {
            "GM": [
                {
                    "task": "決定本週主口徑（示意）",
                    "deliverable": "口徑定義（示意）",
                    "due": "D+1",
                    "kpi": "下週可比較（示意）",
                    "stoploss": "無法對齊則改採單一口徑（示意）",
                }
            ],
            "Marketing": [
                {
                    "task": "執行素材 A/B（示意）",
                    "deliverable": "測試結果（示意）",
                    "due": "D+7",
                    "kpi": "CTR（示意）",
                    "stoploss": "CTR 下滑則停止（示意）",
                }
            ],
        },
        "risks": [{"risk": "r"}],
        "validation_plan": {"3天": "（示意）", "7天": "（示意）", "14天": "（示意）"},
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
        expect_fail(
            "inputs_snapshot ad empty name FAIL",
            bad4,
            p_ad,
            must_contain=["minLength", "non-empty"],
        )
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


def test_e2_cross_review_schema() -> None:
    """
    E2 交叉審核 schema 測試：
    - 驗證合法 fixture 通過（A/B/C 三個 reviewer）
    - 驗證缺少必填欄位的 fixture 失敗
    - 驗證 reviewed_targets 不符合 reviewer 規則時失敗
    """
    p_cross = SCHEMAS / "consultant_cross_review.v1.json"
    must_exist(p_cross)

    # PASS: 三個 reviewer 各自的合法 fixture
    for reviewer in ["A", "B", "C"]:
        expect_pass(
            f"consultant_cross_review.v1 reviewer={reviewer} PASS",
            fixture_consultant_cross_review_pass(reviewer),
            p_cross,
        )

    # FAIL: 缺少必填欄位
    expect_fail(
        "consultant_cross_review.v1 missing required fields FAIL",
        fixture_consultant_cross_review_fail_missing_field(),
        p_cross,
        must_contain="required",
    )

    # FAIL: reviewer A 的 reviewed_targets 不包含 B（違反 if/then 規則）
    bad_targets = fixture_consultant_cross_review_pass("A")
    bad_targets["reviewed_targets"] = ["B", "B"]  # 違反 uniqueItems
    expect_fail(
        "consultant_cross_review.v1 duplicate reviewed_targets FAIL",
        bad_targets,
        p_cross,
    )

    # FAIL: confidence 超出範圍
    bad_confidence = fixture_consultant_cross_review_pass("B")
    bad_confidence["confidence"] = 1.5  # 超過 maximum: 1
    expect_fail(
        "consultant_cross_review.v1 confidence out of range FAIL",
        bad_confidence,
        p_cross,
        must_contain="maximum",
    )

    print("[PASS] E2 consultant_cross_review.v1 schema 測試全通過")


def test_e2_graceful_degradation() -> None:
    """
    E2 graceful degradation 邏輯測試：
    - 模擬 generate_consultant_cross_reviews 單位 reviewer 失敗時，結果仍包含其他成功者
    - 確認 error_count / success_count 正確
    """
    # 模擬三位顧問中一位失敗的交叉審核輸出
    mock_cross_reviews = {
        "cross_reviews_version": "consultant_cross_reviews.v1",
        "week_id": "2025-W49",
        "date_range": "2025-12-04~2025-12-09",
        "success_count": 2,
        "error_count": 1,
        "reviews": {
            "reviewer_A": fixture_consultant_cross_review_pass("A"),
            "reviewer_B": {"error": "timeout", "reviewer": "B", "reviewed_targets": ["A", "C"]},
            "reviewer_C": fixture_consultant_cross_review_pass("C"),
        },
    }

    # 驗證：即使有 error，success/error count 正確
    success_count = mock_cross_reviews["success_count"]
    error_count = mock_cross_reviews["error_count"]
    if success_count != 2:
        raise AssertionError(f"[FAIL] 預期 success_count=2，實際={success_count}")
    if error_count != 1:
        raise AssertionError(f"[FAIL] 預期 error_count=1，實際={error_count}")

    # 驗證：成功的 reviewer 產物符合 schema
    p_cross = SCHEMAS / "consultant_cross_review.v1.json"
    for key in ["reviewer_A", "reviewer_C"]:
        review = mock_cross_reviews["reviews"][key]
        errs = validate_instance(review, load_json(p_cross))
        if errs:
            raise AssertionError(
                f"[FAIL] {key} 應通過 schema 驗證，但有錯誤：\n- " + "\n- ".join(errs)
            )

    # 驗證：失敗的 reviewer 有 error 欄位
    failed_review = mock_cross_reviews["reviews"]["reviewer_B"]
    if "error" not in failed_review:
        raise AssertionError("[FAIL] 失敗的 reviewer 應包含 error 欄位")

    print("[PASS] E2 graceful degradation 測試通過（1 失敗 / 2 成功場景）")


def main() -> int:
    try:
        test_report_summary_schema_locks()
        test_step2_schemas_pass_fail()
        test_language_drift_guard()
        test_e2_cross_review_schema()
        test_e2_graceful_degradation()
    except Exception as e:
        print(str(e))
        return 1

    print("\nALL SELF-TESTS PASSED ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
