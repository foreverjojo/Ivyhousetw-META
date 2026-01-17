"""
Metric Tree Diagnostic Skill (Deterministic)

目的：
  - 解決「只知道變貴，不知道壞在哪」：用全漏斗指標樹拆解問題點
  - 在資料不足時，明確標示「未提供」，避免臆測

輸入：
  - report_summary（report_summary.v1 的 dict）

輸出（dict）：
  - skill_version, triggered, roas_primary, funnel_rates, suspected_bottleneck, recommendations
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from scripts.skills import build_standard_skill_contract


def _to_float(x: Any) -> float:
    try:
        if x is None:
            return 0.0
        return float(x)
    except Exception:
        return 0.0


def _safe_div(num: float, den: float) -> Optional[float]:
    if den <= 0:
        return None
    return num / den


@dataclass(frozen=True)
class Thresholds:
    roas_trigger: float = 2.5
    ctr_link_pct_min: float = 1.0
    cvr_purchase_per_click_min: float = 1.0
    lpv_per_click_min: float = 0.6
    atc_per_lpv_min: float = 0.08
    ic_per_atc_min: float = 0.35
    purchase_per_ic_min: float = 0.25


def run_metric_tree_diagnostic(
    report_summary: Dict[str, Any], thresholds: Thresholds | None = None
) -> Dict[str, Any]:
    thresholds = thresholds or Thresholds()

    meta = (report_summary.get("kpi") or {}).get("meta") or {}
    web = (report_summary.get("kpi") or {}).get("web") or {}
    funnel = meta.get("funnel") or {}

    spend = _to_float(meta.get("spend_twd"))
    purchase_value_truth = _to_float(meta.get("purchase_value_twd"))
    purchases_truth = _to_float(meta.get("purchases"))
    roas_truth = _to_float(meta.get("roas_calc"))

    purchase_value_platform = _to_float(meta.get("platform_purchase_value_twd"))
    purchases_platform = _to_float(meta.get("platform_purchases"))
    roas_platform = _to_float(meta.get("roas_platform_calc"))

    # 主 ROAS：若 truth purchase value 為 0 但 platform 有值，避免把追蹤異常當成「成效很差」
    use_platform = (purchase_value_truth <= 0.0) and (purchase_value_platform > 0.0)
    roas_primary = roas_platform if use_platform else roas_truth
    roas_basis = "platform" if use_platform else "truth"

    link_clicks = _to_float(funnel.get("link_clicks"))
    lpv = _to_float(funnel.get("landing_page_views"))
    atc = _to_float(funnel.get("add_to_cart"))
    ic = _to_float(funnel.get("initiate_checkout"))
    impressions_raw = meta.get("impressions", None)
    impressions = _to_float(impressions_raw) if impressions_raw is not None else None

    # 以主口徑選擇 purchases/value（只作判讀，不重算 KPI）
    purchases_primary = purchases_platform if use_platform else purchases_truth
    purchase_value_primary = purchase_value_platform if use_platform else purchase_value_truth

    aov_primary = _safe_div(purchase_value_primary, purchases_primary)
    cpa_primary = _safe_div(spend, purchases_primary)

    cpm_raw = meta.get("cpm_calc_twd", None)
    ctr_raw = meta.get("ctr_link_pct_calc", None)
    cpm_twd = _to_float(cpm_raw) if cpm_raw is not None else None
    ctr_link_pct = _to_float(ctr_raw) if ctr_raw is not None else None
    if cpm_twd is None and impressions is not None and impressions > 0:
        cpm_twd = _safe_div(spend * 1000.0, impressions)
    if ctr_link_pct is None and impressions is not None and impressions > 0:
        ctr_link_pct = _safe_div(link_clicks * 100.0, impressions)
    cvr_purchase_per_click_pct = (
        (_safe_div(purchases_primary * 100.0, link_clicks)) if link_clicks > 0 else None
    )

    rates = {
        "lpv_per_click": _safe_div(lpv, link_clicks),
        "atc_per_lpv": _safe_div(atc, lpv),
        "ic_per_atc": _safe_div(ic, atc),
        "purchase_per_ic": _safe_div(purchases_primary, ic),
        "purchase_per_lpv": _safe_div(purchases_primary, lpv),
    }

    costs = {
        "cpc_twd_calc": _safe_div(spend, link_clicks),
        "cplpv_twd_calc": _safe_div(spend, lpv),
        "cpatc_twd_calc": _safe_div(spend, atc),
        "cpic_twd_calc": _safe_div(spend, ic),
        "cpa_twd_calc": _safe_div(spend, purchases_primary),
    }

    triggered = (roas_primary > 0.0) and (roas_primary < thresholds.roas_trigger)
    # 若 roas_primary=0 但 purchase_value_truth=0（追蹤異常），仍視為需要診斷（資料鏈路優先）
    if roas_primary == 0.0 and purchase_value_truth == 0.0 and purchase_value_platform > 0.0:
        triggered = True

    suspected = []
    metric_tree_notes: list[str] = []
    if roas_primary < thresholds.roas_trigger:
        metric_tree_notes.append(
            f"Level1：ROAS={roas_primary:.4f} 未達目標 {thresholds.roas_trigger}。"
        )
    else:
        metric_tree_notes.append(
            f"Level1：ROAS={roas_primary:.4f} 達標（目標 {thresholds.roas_trigger}）。"
        )

    if cpa_primary is not None and aov_primary is not None:
        metric_tree_notes.append(
            f"Level2：ROAS ≈ AOV/CPA；AOV≈{aov_primary:.2f}、CPA≈{cpa_primary:.2f}（basis={roas_basis}）。"
        )
    else:
        metric_tree_notes.append(
            "Level2：缺少 purchases/value，無法計算 AOV/CPA（可能是追蹤異常或資料缺失）。"
        )

    cpm_note = f"{cpm_twd:.2f}" if cpm_twd is not None else "未提供"
    ctr_note = f"{ctr_link_pct:.2f}%" if ctr_link_pct is not None else "未提供"
    cvr_note = (
        f"{cvr_purchase_per_click_pct:.2f}%" if cvr_purchase_per_click_pct is not None else "未提供"
    )
    metric_tree_notes.append(
        f"Level3：CPA ≈ CPM / (CTR×CVR)。CPM≈{cpm_note}、CTR≈{ctr_note}、CVR≈{cvr_note}。"
    )

    if ctr_link_pct is not None and ctr_link_pct > 0 and ctr_link_pct < thresholds.ctr_link_pct_min:
        suspected.append(
            f"CTR 偏低（{ctr_link_pct:.2f}% < {thresholds.ctr_link_pct_min}%）：偏向『素材/受眾訊息』問題"
        )
    if (
        cvr_purchase_per_click_pct is not None
        and cvr_purchase_per_click_pct > 0
        and cvr_purchase_per_click_pct < thresholds.cvr_purchase_per_click_min
    ):
        suspected.append(
            f"CVR 偏低（{cvr_purchase_per_click_pct:.2f}% < {thresholds.cvr_purchase_per_click_min}%）：偏向『落地頁/產品/結帳』問題"
        )

    if rates["lpv_per_click"] is not None and rates["lpv_per_click"] < thresholds.lpv_per_click_min:
        suspected.append("點擊→到站（LPV）落差：可能是落地頁速度/追蹤/跳出")
    if rates["atc_per_lpv"] is not None and rates["atc_per_lpv"] < thresholds.atc_per_lpv_min:
        suspected.append("到站→加車轉換偏低：商品頁訊息/價格/信任元素/CTA")
    if rates["ic_per_atc"] is not None and rates["ic_per_atc"] < thresholds.ic_per_atc_min:
        suspected.append("加車→結帳啟動偏低：運費/優惠/結帳入口/流程摩擦")
    if (
        rates["purchase_per_ic"] is not None
        and rates["purchase_per_ic"] < thresholds.purchase_per_ic_min
    ):
        suspected.append("結帳→購買偏低：付款方式/錯誤率/折扣碼/庫存/表單摩擦")

    if not suspected:
        if purchase_value_truth == 0.0 and purchase_value_platform > 0.0:
            suspected.append("追蹤/歸因鏈路異常：Meta（網站）purchase value 為 0，但平台有值")
        else:
            suspected.append("未找到明顯漏斗斷點（或資料不足），建議補齊 CTR/曝光/事件品質後再判讀")

    recs: list[str] = []
    if purchase_value_truth == 0.0 and purchase_value_platform > 0.0:
        recs.append(
            "先修復 Pixel/CAPI 的 Purchase value/currency 與去重，否則 ROAS（truth）全面失真。"
        )
    recs.append(
        "指標樹順序：先看 ROAS → 拆 AOV/CPA → 再拆 CPM/CTR/CVR → 最後用漏斗事件定位（LPV/ATC/IC/Purchase）。"
    )
    if rates["lpv_per_click"] is None:
        recs.append(
            "缺少 LPV/Clicks 無法判斷點擊→到站，請確認匯出含「連結頁面瀏覽次數」「連結點擊次數」。"
        )
    if rates["purchase_per_ic"] is None:
        recs.append(
            "缺少 initiate_checkout 或 purchases，無法定位結帳段問題，請確認匯出含「開始結帳次數」「購買次數」。"
        )
    recs.append(
        f"若主 ROAS（{roas_basis}）低於 {thresholds.roas_trigger}，依序檢查：LPV/Click → ATC/LPV → IC/ATC → Purchase/IC。"
    )
    recs.append(
        "把最弱的一段做成 1~2 個最小改動 A/B（例如商品頁信任元素、運費/到貨資訊、結帳流程）。"
    )

    output: Dict[str, Any] = {
        "skill_version": "metric_tree_diagnostic.v1",
        "trigger_rule": {"roas_lt": thresholds.roas_trigger},
        "triggered": triggered,
        "metric_tree_summary": metric_tree_notes[:10],
        "roas_primary": {"value": round(roas_primary, 4), "basis": roas_basis},
        "kpi_primary": {
            "spend_twd": round(spend, 2),
            "purchases": int(round(purchases_primary)),
            "purchase_value_twd": round(purchase_value_primary, 2),
            "web_revenue_twd": _to_float(web.get("revenue_twd")),
        },
        "level2_decomposition": {
            "aov_twd_calc": (round(aov_primary, 2) if aov_primary is not None else None),
            "cpa_twd_calc": (round(cpa_primary, 2) if cpa_primary is not None else None),
        },
        "level3_decomposition": {
            "impressions": (int(round(impressions)) if impressions is not None else None),
            "cpm_calc_twd": (round(cpm_twd, 2) if cpm_twd is not None else None),
            "ctr_link_pct_calc": (round(ctr_link_pct, 4) if ctr_link_pct is not None else None),
            "cvr_purchase_per_click_pct_calc": (
                round(cvr_purchase_per_click_pct, 4)
                if cvr_purchase_per_click_pct is not None
                else None
            ),
        },
        "funnel_counts": {
            "link_clicks": int(round(link_clicks)),
            "landing_page_views": int(round(lpv)),
            "add_to_cart": int(round(atc)),
            "initiate_checkout": int(round(ic)),
        },
        "funnel_rates": {k: (round(v, 4) if v is not None else None) for k, v in rates.items()},
        "costs": {k: (round(v, 2) if v is not None else None) for k, v in costs.items()},
        "suspected_bottlenecks": suspected[:5],
        "recommendations": recs[:8],
    }

    contract = build_standard_skill_contract(
        schema_version="skill_metric_tree_diagnostic_output.v1",
        inputs={
            "week_id": report_summary.get("week_id"),
            "kpi_truth_source": report_summary.get("kpi_truth_source"),
        },
        thresholds={
            "roas_trigger": thresholds.roas_trigger,
            "ctr_link_pct_min": thresholds.ctr_link_pct_min,
            "cvr_purchase_per_click_min": thresholds.cvr_purchase_per_click_min,
            "lpv_per_click_min": thresholds.lpv_per_click_min,
            "atc_per_lpv_min": thresholds.atc_per_lpv_min,
            "ic_per_atc_min": thresholds.ic_per_atc_min,
            "purchase_per_ic_min": thresholds.purchase_per_ic_min,
        },
        results={
            "triggered": output.get("triggered"),
            "roas_primary": output.get("roas_primary"),
            "suspected_bottlenecks": output.get("suspected_bottlenecks"),
            "recommendations": output.get("recommendations"),
        },
        warnings=[],
    )
    output.update(contract)
    return output
