from __future__ import annotations

from scripts.moderator_meeting import build_meeting_markdown


def test_key_insights_renders_actionable_warning_on_error_payload() -> None:
    ws = {
        "week_id": "2025-W49",
        "date_range": "2025-12-04~2025-12-10",
        "guardrail_check": {"tier1": {}, "tier2": {}},
        "department_actions": {},
        "risks": [],
        "validation_plan": {},
        "decisions": [],
        "consultant_summary": [],
    }

    report_summary = {
        "week_id": "2025-W49",
        "date_range": "2025-12-04~2025-12-10",
        "kpi": {"meta": {}, "web": {}},
    }

    report_insights = {
        "status": "error",
        "code": "MISSING_INPUT_JSON",
        "message": "未收到投放資料 JSON，請確認 Step B 產物是否存在。",
    }

    md = build_meeting_markdown(ws, report_summary, report_insights)

    start = md.index("## Key Insights（來自 report_insights.json）")
    end = md.index("## 三顧問摘要（共識 / 分歧）", start)
    block = md[start:end]

    assert "- （待補）" not in block
    assert "洞察產物格式異常" in block
    assert "code=MISSING_INPUT_JSON" in block
