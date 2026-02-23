from __future__ import annotations

from scripts.moderator_meeting import build_meeting_markdown


def test_consultant_summary_week_focus_renders_in_meeting_md() -> None:
    ws = {
        "week_id": "2025-W49",
        "date_range": "2025-12-04~2025-12-10",
        "guardrail_check": {"tier1": {}, "tier2": {}},
        "department_actions": {},
        "risks": [],
        "validation_plan": {},
        "consultant_summary": {
            "week_focus": [
                "先修復歸因回傳，避免 ROAS 誤判。",
                "預算先 hold，僅對高效組合做條件式擴量。",
            ],
            "key_observations": [
                "Meta 端 purchase value 異常為 0。",
            ],
        },
    }

    report_summary = {
        "week_id": "2025-W49",
        "date_range": "2025-12-04~2025-12-10",
        "kpi": {"meta": {}, "web": {}},
    }
    report_insights = {"executive_summary": ["洞察一"]}

    md = build_meeting_markdown(ws, report_summary, report_insights)

    assert "## 三顧問摘要（共識 / 分歧）" in md

    # 只檢查「三顧問摘要」區塊，避免其他章節的 placeholder 影響判斷
    start = md.index("## 三顧問摘要（共識 / 分歧）")
    end = md.find("## Department Actions（核心 5 主管）", start)
    assert end != -1
    block = md[start:end]

    assert "- （待補）" not in block
    assert "共識：先修復歸因回傳" in block
    assert "觀察：Meta 端 purchase value" in block
