import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from scripts.skills.creative_fatigue import run_creative_fatigue_diagnostic
from scripts.skills.budget_rules import run_budget_rules


def test_creative_fatigue():
    print("Testing Creative Fatigue...")
    report_summary = {"week_id": "TEST"}

    # Case 1: Empty
    res = run_creative_fatigue_diagnostic(report_summary, [])
    print(f"Empty input result: {res['triggered']}")

    # Case 2: Fatigued Ad
    # Freq > 2.5, CTR < Avg * 0.8
    # Let's say Avg CTR is 1.0%
    ads = [
        {
            "ad_name": "Fatigued Ad",
            "impressions": 5000,
            "frequency": 3.0,
            "link_clicks": 20,  # CTR 0.4%
            "video_3s": 1000,
            "thruplays": 200,
            "spend": 1000,
        },
        {
            "ad_name": "Normal Ad",
            "impressions": 5000,
            "frequency": 1.5,
            "link_clicks": 100,  # CTR 2.0%
            "video_3s": 2000,
            "thruplays": 500,
            "spend": 1000,
        },
    ]
    # Avg CTR = (0.4 + 2.0) / 2 = 1.2%
    # Threshold = 1.2 * 0.8 = 0.96%
    # Ad 1 CTR 0.4% < 0.96%, Freq 3.0 > 2.5 -> Should trigger

    res = run_creative_fatigue_diagnostic(report_summary, ads)
    print(f"Fatigued case triggered: {res['triggered']}")
    if res["triggered"]:
        print(f"Fatigue Ads found: {len(res['fatigue_ads'])}")
        print(f"Reason: {res['fatigue_ads'][0]['reason']}")
    else:
        print("FAILED: Should detect fatigue")


def test_budget_rules():
    print("\nTesting Budget Rules...")
    report_summary = {"kpi": {"meta": {"spend_twd": 5000, "purchases": 0, "purchase_value_twd": 0}}}
    manual_inputs = {"target_cpa": 500, "breakeven_roas": 2.0}

    # Case 1: KILL (Spend 5000 > 1.5*500=750, Purchases 0)
    res = run_budget_rules(report_summary, manual_inputs)

    actions = {a["level"]: a["action"] for a in res["actions"]}
    print(f"KILL case action: {actions.get('overall')}")

    # Case 2: SCALE UP
    report_summary["kpi"]["meta"]["purchases"] = 10
    report_summary["kpi"]["meta"]["purchase_value_twd"] = 20000  # ROAS 4.0
    # ROAS 4.0 > 2.0 * 1.2 = 2.4 -> Scale Up

    res = run_budget_rules(report_summary, manual_inputs)
    actions = {a["level"]: a["action"] for a in res["actions"]}
    print(f"SCALE UP case action: {actions.get('overall')}")


if __name__ == "__main__":
    try:
        test_creative_fatigue()
        test_budget_rules()
        print("\n✅ Verification Complete")
    except Exception as e:
        print(f"\n❌ Verification Failed: {e}")
        import traceback

        traceback.print_exc()
