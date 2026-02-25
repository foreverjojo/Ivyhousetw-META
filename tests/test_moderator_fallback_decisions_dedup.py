from __future__ import annotations

from scripts.moderator_fallback import build_deterministic_workflow_state


def test_deterministic_decisions_do_not_copy_executive_summary() -> None:
    report_summary = {
        "week_id": "2025-W49",
        "date_range": "2025-12-04~2025-12-10",
        "kpi": {"meta": {}, "web": {}},
    }
    report_insights = {
        "executive_summary": ["洞察：本週 ROAS 走弱，需先修正追蹤再決策。"],
        "actions": [
            {
                "owner": "Finance",
                "task": "建立平台回傳 vs 官網營收對帳欄位",
                "kpi": "下週週會可追溯差異原因",
                "stoploss": "若差異仍大，短期固定以平台口徑決策並註記限制",
            }
        ],
        "data_issues": ["官網回傳 purchase value 為 0"],
    }

    ws = build_deterministic_workflow_state(
        report_summary=report_summary,
        report_insights=report_insights,
        consultant_notes=None,
        guardrails={},
    )

    decisions = ws.get("decisions")
    assert isinstance(decisions, list)

    decision_texts: list[str] = []
    for d in decisions:
        if isinstance(d, dict):
            decision_texts.append(str(d.get("decision", "")))
        else:
            decision_texts.append(str(d))

    assert all("洞察：本週 ROAS 走弱" not in t for t in decision_texts)
