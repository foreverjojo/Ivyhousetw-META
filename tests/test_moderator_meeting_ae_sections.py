from __future__ import annotations

from scripts.moderator_meeting import build_meeting_markdown


def test_meeting_md_contains_ae_sections_and_key_metrics() -> None:
    ws = {
        "week_id": "2025-W49",
        "date_range": "2025-12-04~2025-12-10",
        "guardrail_check": {"tier1": {}, "tier2": {}},
        "department_actions": {},
        "risks": [],
        "validation_plan": {},
        "consultant_summary": [],
    }

    report_summary = {
        "week_id": "2025-W49",
        "date_range": "2025-12-04~2025-12-10",
        "kpi": {
            "meta": {
                "spend_twd": 1000,
                "website_purchases": 3,
                "website_purchase_value_twd": 9000,
                "roas_calc": 9.0,
                "platform_purchases": 4,
                "platform_purchase_value_twd": 9500,
                "roas_platform_calc": 9.5,
                "cpa_calc_twd": 333.33,
                "ctr_link_pct_calc": 3.2,
                "cpc_calc_twd": 6.25,
                "aov_platform_twd_calc": 2400,
                "delta_purchase_value_twd": 500,
                "delta_purchase_value_rate": 0.0555,
                "funnel": {
                    "link_clicks": 100,
                    "landing_page_views": 95,
                },
            },
            "web": {
                "revenue_twd": 8800,
                "orders": 3,
                "aov_twd_calc": 2933.33,
            },
        },
        "tables": {
            "top_adsets_by_roas": [
                {
                    "name": "組合A",
                    "spend_twd": 600,
                    "purchases": 2,
                    "roas": 10.0,
                    "roas_platform": 10.2,
                    "ctr_link_pct_calc": 3.5,
                    "link_clicks": 60,
                    "landing_page_views": 57,
                    "platform_purchases": 3,
                    "frequency": 1.8,
                }
            ],
            "worst_adsets_by_roas": [
                {
                    "name": "組合B",
                    "spend_twd": 400,
                    "purchases": 1,
                    "roas": 2.0,
                    "roas_platform": 2.1,
                    "ctr_link_pct_calc": 2.0,
                    "link_clicks": 40,
                    "landing_page_views": 32,
                    "platform_purchases": 1,
                    "frequency": 2.2,
                }
            ],
            "top_ads_by_roas": [
                {
                    "name": "素材A-1",
                    "adset_name": "組合A",
                    "roas": 12.0,
                    "roas_platform": 12.3,
                    "ctr_link_pct_calc": 3.9,
                }
            ],
            "worst_ads_by_roas": [
                {
                    "name": "素材B-1",
                    "adset_name": "組合B",
                    "roas": 0.5,
                    "roas_platform": 0.6,
                    "ctr_link_pct_calc": 1.8,
                }
            ],
        },
    }

    report_insights = {
        "executive_summary": ["洞察一"],
        "actions": [
            {
                "task": "先做對帳欄位定義",
                "why": "避免口徑混淆",
                "kpi": "下週週會能對齊平台/官網",
                "stoploss": "若 7 天仍無法對齊，固定以平台口徑決策",
            }
        ],
    }

    md = build_meeting_markdown(ws, report_summary, report_insights)

    for heading in [
        "## A. 這週先講重點（1 分鐘版）",
        "## B. Ad Set 表現對比",
        "## B+. Ad（素材）表現（按 adset）",
        "## B2. 損益平衡點（CPP vs 客單）",
        "## C. 今天立刻要做的調整（照做就好）",
        "## D. 下次回來我看這 5 個數字（驗收門檻）",
        "## E. 風險檢查（必做 2 件事）",
    ]:
        assert heading in md

    assert "LPV/Click" in md
    assert "損益平衡點" in md
    assert "### 組合A" in md
