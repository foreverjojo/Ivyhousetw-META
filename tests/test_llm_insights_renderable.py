from __future__ import annotations

from scripts.llm_insights import is_report_insights_renderable


def test_is_report_insights_renderable_requires_nonempty_executive_summary() -> None:
    assert is_report_insights_renderable({"executive_summary": ["洞察一"]}) is True

    assert is_report_insights_renderable({"executive_summary": []}) is False
    assert is_report_insights_renderable({"executive_summary": ["", "  "]}) is False

    # 常見的 error payload（合法 JSON 但不是 insights.v1）
    assert (
        is_report_insights_renderable(
            {"status": "error", "code": "MISSING_INPUT_JSON", "message": "未收到投放資料"}
        )
        is False
    )

    assert is_report_insights_renderable(None) is False
    assert is_report_insights_renderable([]) is False
