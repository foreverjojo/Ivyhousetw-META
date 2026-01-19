"""
檔案用途：Meta/Web KPI 計算與 `report_summary` 生成（供 UI 與後續 LLM/技能流程使用）。
支援雙語（英文/繁體中文）Meta CSV 欄位名稱，欄位別名由 `schemas/column_aliases.json` 驅動。
"""

import io
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from scripts.daily_aggregation import (
    _aggregate_daily_to_weekly,
    _clean_cols,
    _drop_total_rows,
    _get_alias,
    _is_daily_data,
    _read_csv_bytes,
    _resolve_col_name,
    _sum_col,
    _to_num,
    iso_week_id,
    parse_date_range_from_meta,
)
from utils.week_utils import normalize_week_id


# =========================
# KPI 計算（真值 = Website Direct）
# =========================
def calc_meta_kpis(adset_df: pd.DataFrame, ads_df: pd.DataFrame) -> dict[str, Any]:
    """
    KPI 真值：網站直接（website_*）
    漂移偵測：平台購買（platform_*）+ delta_*
    使用 column_aliases.json 支援雙語欄位名稱。
    """

    # 使用 alias key 取得欄位值
    spend = _sum_col(adset_df, "spend")
    impressions = _sum_col(adset_df, "impressions")

    # 真值（Website Direct）
    website_purchases = _sum_col(adset_df, "purchases_website")
    website_value = _sum_col(adset_df, "purchases_value_website")

    # Platform (for drift watch)
    platform_purchases = _sum_col(adset_df, "purchases_platform")
    platform_value = _sum_col(adset_df, "purchases_value_platform")

    # Funnel (events)
    atc = _sum_col(adset_df, "atc")
    ic = _sum_col(adset_df, "ic")
    lpv = _sum_col(adset_df, "lpv")
    link_clicks = _sum_col(adset_df, "link_clicks")

    # 真值 ROAS/CPA
    roas_truth = (website_value / spend) if spend > 0 else 0.0
    cpa_truth = (spend / website_purchases) if website_purchases > 0 else 0.0

    # Platform ROAS/CPA (reference)
    roas_platform = (platform_value / spend) if spend > 0 else 0.0
    cpa_platform = (spend / platform_purchases) if platform_purchases > 0 else 0.0

    # Drift
    delta_value = platform_value - website_value
    delta_rate = (delta_value / website_value) if website_value > 0 else 0.0

    # Cost / traffic diagnostics (derived, deterministic)
    cpm_twd = (spend / (impressions / 1000.0)) if impressions > 0 else 0.0
    ctr_link_pct = ((link_clicks / impressions) * 100.0) if impressions > 0 else 0.0
    cpc_twd = (spend / link_clicks) if link_clicks > 0 else 0.0

    aov_truth = (website_value / website_purchases) if website_purchases > 0 else 0.0
    aov_platform = (platform_value / platform_purchases) if platform_purchases > 0 else 0.0

    return {
        # ✅ 相容舊鍵（目前指向真值，避免下游 schema 破壞）
        "spend_twd": round(spend, 2),
        "purchase_value_twd": round(website_value, 2),  # legacy key, now truth
        "purchases": int(round(website_purchases)),  # legacy key, now truth
        "roas_calc": round(roas_truth, 4),  # legacy key, now truth
        "cpa_calc_twd": round(cpa_truth, 2),  # legacy key, now truth
        # ✅ explicit truth keys
        "website_purchases": int(round(website_purchases)),
        "website_purchase_value_twd": round(website_value, 2),
        "aov_twd_calc": round(aov_truth, 2),
        # ✅ 平台參考鍵（漂移監控）
        "platform_purchases": int(round(platform_purchases)),
        "platform_purchase_value_twd": round(platform_value, 2),
        "roas_platform_calc": round(roas_platform, 4),
        "cpa_platform_calc_twd": round(cpa_platform, 2),
        "aov_platform_twd_calc": round(aov_platform, 2),
        # ✅ drift metrics
        "delta_purchase_value_twd": round(delta_value, 2),
        "delta_purchase_value_rate": round(delta_rate, 4),
        # ✅ traffic diagnostics (derived)
        "impressions": int(round(impressions)),
        "cpm_calc_twd": round(cpm_twd, 2),
        "ctr_link_pct_calc": round(ctr_link_pct, 4),
        "cpc_calc_twd": round(cpc_twd, 2),
        "funnel": {
            "link_clicks": int(round(link_clicks)),
            "landing_page_views": int(round(lpv)),
            "add_to_cart": int(round(atc)),
            "initiate_checkout": int(round(ic)),
        },
        # 使用 alias 判斷 rankings 欄位是否存在（支援英文/中文）
        "ads_has_rankings": all(
            _resolve_col_name(ads_df, _get_alias(k)) in ads_df.columns
            for k in ["quality_ranking", "engagement_ranking", "conversion_ranking"]
        ),
    }


def calc_top_tables(adset_df: pd.DataFrame, ads_df: pd.DataFrame, top_n: int = 5) -> dict[str, Any]:
    """
    Top/Worst 表格：
    - 預設用「網站直接」作 ROAS 排序（與 KPI 真值一致）
    - 同時帶 platform/delta 欄位做漂移偵測
    - 補上 name，避免表格失去可讀性
    """

    def add_roas(df: pd.DataFrame, name_col: str) -> pd.DataFrame:
        d = df.copy()

        d["__name"] = d[name_col].astype(str).fillna("").str.strip()

        # 使用 alias-aware 欄位解析
        spend_col = _resolve_col_name(d, _get_alias("spend"))
        impressions_col = _resolve_col_name(d, _get_alias("impressions"))
        link_clicks_col = _resolve_col_name(d, _get_alias("link_clicks"))
        lpv_col = _resolve_col_name(d, _get_alias("lpv"))
        frequency_col = _resolve_col_name(d, _get_alias("frequency"))

        d["__spend"] = d[spend_col].apply(_to_num) if spend_col in d.columns else 0
        d["__impressions"] = (
            d[impressions_col].apply(_to_num) if impressions_col in d.columns else 0
        )
        d["__link_clicks"] = (
            d[link_clicks_col].apply(_to_num) if link_clicks_col in d.columns else 0
        )
        d["__lpv"] = d[lpv_col].apply(_to_num) if lpv_col in d.columns else 0
        d["__frequency"] = d[frequency_col].apply(_to_num) if frequency_col in d.columns else 0

        # truth (website direct)
        value_truth_col = _resolve_col_name(d, _get_alias("purchases_value_website"))
        purchases_truth_col = _resolve_col_name(d, _get_alias("purchases_website"))
        value_platform_col = _resolve_col_name(d, _get_alias("purchases_value_platform"))
        purchases_platform_col = _resolve_col_name(d, _get_alias("purchases_platform"))

        if value_truth_col in d.columns:
            d["__value_truth"] = d[value_truth_col].apply(_to_num)
        elif value_platform_col in d.columns:
            d["__value_truth"] = d[value_platform_col].apply(_to_num)
        else:
            d["__value_truth"] = 0

        if purchases_truth_col in d.columns:
            d["__purchases_truth"] = d[purchases_truth_col].apply(_to_num)
        elif purchases_platform_col in d.columns:
            d["__purchases_truth"] = d[purchases_platform_col].apply(_to_num)
        else:
            d["__purchases_truth"] = 0

        # 平台參考（漂移監控）
        d["__value_platform"] = (
            d[value_platform_col].apply(_to_num) if value_platform_col in d.columns else 0
        )
        d["__purchases_platform"] = (
            d[purchases_platform_col].apply(_to_num) if purchases_platform_col in d.columns else 0
        )

        # truth metrics
        d["__roas_truth"] = d.apply(
            lambda r: (r["__value_truth"] / r["__spend"]) if r["__spend"] > 0 else 0.0, axis=1
        )
        d["__cpa_truth"] = d.apply(
            lambda r: (r["__spend"] / r["__purchases_truth"])
            if r["__purchases_truth"] > 0
            else 0.0,
            axis=1,
        )

        # platform metrics
        d["__roas_platform"] = d.apply(
            lambda r: (r["__value_platform"] / r["__spend"]) if r["__spend"] > 0 else 0.0, axis=1
        )

        # traffic diagnostics
        d["__ctr_link_pct_calc"] = d.apply(
            lambda r: ((r["__link_clicks"] / r["__impressions"]) * 100.0)
            if r["__impressions"] > 0
            else 0.0,
            axis=1,
        )

        # drift
        d["__delta_value"] = d["__value_platform"] - d["__value_truth"]
        d["__delta_rate"] = d.apply(
            lambda r: (r["__delta_value"] / r["__value_truth"]) if r["__value_truth"] > 0 else 0.0,
            axis=1,
        )

        keep = [
            "__name",
            "__impressions",
            "__link_clicks",
            "__ctr_link_pct_calc",
            "__lpv",
            "__spend",
            "__value_truth",
            "__purchases_truth",
            "__roas_truth",
            "__cpa_truth",
            "__value_platform",
            "__purchases_platform",
            "__roas_platform",
            "__delta_value",
            "__delta_rate",
            "__frequency",  # 使用 alias-aware 欄位
        ]
        keep = [c for c in keep if c in d.columns]

        return d[keep]

    adset_name_col = _resolve_col_name(adset_df, _get_alias("adset_name"))
    ads_name_col = _resolve_col_name(ads_df, _get_alias("ad_name"))

    adset = add_roas(adset_df, adset_name_col)
    ads = add_roas(ads_df, ads_name_col)

    # 排序用 truth ROAS
    top_adset = adset.sort_values("__roas_truth", ascending=False).head(top_n)
    worst_adset = adset.sort_values("__roas_truth", ascending=True).head(top_n)
    top_ads = ads.sort_values("__roas_truth", ascending=False).head(top_n)
    worst_ads = ads.sort_values("__roas_truth", ascending=True).head(top_n)

    def to_records(df: pd.DataFrame):
        import math

        def _sf(x, default=0.0):
            try:
                if x is None:
                    return default
                if isinstance(x, float) and math.isnan(x):
                    return default
                return float(x)
            except Exception:
                return default

        def _si(x, default=0):
            v = _sf(x, default=float(default))
            if isinstance(v, float) and math.isnan(v):
                return default
            return int(round(v))

        out = []
        for _, r in df.iterrows():
            out.append(
                {
                    "name": str(r.get("__name", "")).strip(),
                    "impressions": _si(r.get("__impressions", 0)),
                    "link_clicks": _si(r.get("__link_clicks", 0)),
                    "ctr_link_pct_calc": round(_sf(r.get("__ctr_link_pct_calc", 0)), 4),
                    "landing_page_views": _si(r.get("__lpv", 0)),
                    # truth (aligned with KPI)
                    "spend_twd": round(_sf(r.get("__spend", 0)), 2),
                    "purchase_value_twd": round(_sf(r.get("__value_truth", 0)), 2),
                    "purchases": _si(r.get("__purchases_truth", 0)),
                    "roas": round(_sf(r.get("__roas_truth", 0)), 4),
                    "cpa_twd": round(_sf(r.get("__cpa_truth", 0)), 2),
                    # 平台參考 + 漂移
                    "platform_purchase_value_twd": round(_sf(r.get("__value_platform", 0)), 2),
                    "platform_purchases": _si(r.get("__purchases_platform", 0)),
                    "roas_platform": round(_sf(r.get("__roas_platform", 0)), 4),
                    "delta_purchase_value_twd": round(_sf(r.get("__delta_value", 0)), 2),
                    "delta_purchase_value_rate": round(_sf(r.get("__delta_rate", 0)), 4),
                    "frequency": round(_sf(r.get("__frequency", 0)), 2)
                    if "__frequency" in df.columns
                    else None,
                }
            )

        return out

    return {
        "top_adsets_by_roas": to_records(top_adset),
        "worst_adsets_by_roas": to_records(worst_adset),
        "top_ads_by_roas": to_records(top_ads),
        "worst_ads_by_roas": to_records(worst_ads),
    }


# =========================
# 網站 KPI
# =========================
def calc_web_kpis(web_df: pd.DataFrame) -> dict[str, Any]:
    d = web_df.copy()
    d.columns = [str(c).strip() for c in d.columns]

    orders_col = "訂單量"
    revenue_col = "營業額"

    orders = _sum_col(d, orders_col) if orders_col in d.columns else 0.0
    revenue = _sum_col(d, revenue_col) if revenue_col in d.columns else 0.0
    aov = (revenue / orders) if orders > 0 else 0.0

    return {
        "orders": int(round(orders)),
        "revenue_twd": round(revenue, 2),
        "aov_twd_calc": round(aov, 2),
        "columns": list(d.columns),
    }


# =========================
# 產生 report_summary（v1）
# =========================


def build_report_summary(
    meta_adset_bytes: bytes,
    meta_ads_bytes: bytes,
    web_excel_bytes: bytes,
) -> dict[str, Any]:
    adset_df = _clean_cols(_read_csv_bytes(meta_adset_bytes))
    ads_df = _clean_cols(_read_csv_bytes(meta_ads_bytes))
    web_df = pd.read_excel(io.BytesIO(web_excel_bytes))
    web_df = _clean_cols(web_df)

    # ✅ 移除總計/摘要列（必須）- 使用 alias 支援雙語
    adset_name_candidates = _get_alias("adset_name")
    ads_name_candidates = _get_alias("ad_name")

    adset_df, dropped_adset = _drop_total_rows(adset_df, adset_name_candidates)
    ads_df, dropped_ads = _drop_total_rows(ads_df, ads_name_candidates)

    # ✅ P1：保存原始日資料供 Skill 2/3 使用
    adset_daily_df = adset_df.copy() if _is_daily_data(adset_df) else None
    _ads_daily_df = ads_df.copy() if _is_daily_data(ads_df) else None
    is_daily = adset_daily_df is not None

    # ✅ P1：若為日資料，聚合為週彙總供 KPI 計算
    aggregation_methods = {}
    if is_daily:
        adset_name_col = _resolve_col_name(adset_df, adset_name_candidates)
        ads_name_col = _resolve_col_name(ads_df, ads_name_candidates)
        adset_df, adset_agg_methods = _aggregate_daily_to_weekly(adset_df, adset_name_col)
        ads_df, ads_agg_methods = _aggregate_daily_to_weekly(ads_df, ads_name_col)
        aggregation_methods = adset_agg_methods or ads_agg_methods

    date_start, date_end = parse_date_range_from_meta(
        adset_daily_df if adset_daily_df is not None else adset_df
    )
    week_id_raw = iso_week_id(date_start)
    week_id = normalize_week_id(week_id_raw) or week_id_raw  # 確保格式為 YYYY-Www

    meta_kpi = calc_meta_kpis(adset_df, ads_df)
    tables = calc_top_tables(adset_df, ads_df, top_n=5)
    web_kpi = calc_web_kpis(web_df)

    result = {
        "schema_version": "report_summary.v1",
        "generated_at": datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds"),
        "week_id": week_id,
        "date_range": f"{date_start}~{date_end}",
        # schema 固定欄位
        "kpi_truth_source": "meta_adset_csv",
        "ad_diagnostics_source": "meta_ad_csv",
        "kpi": {
            "meta": meta_kpi,
            "web": web_kpi,
        },
        "tables": tables,
        # 非必要但實用：可追溯清洗/彙總規則是否生效
        "data_cleaning": {
            "dropped_total_rows": {
                "meta_adset": int(dropped_adset),
                "meta_ads": int(dropped_ads),
            },
            "daily_aggregation": {
                "is_daily_data": is_daily,
                "aggregation_methods": aggregation_methods,
            }
            if is_daily
            else None,
        },
        # 這些欄位已透過 UI manual inputs 補充，不再視為缺失
        "missing_data": {
            "meta_unavailable_fields": [],
            "note": "optimization_goal, billing_event, buying_type 由使用者在 UI 輸入，存於 inputs.json",
        },
    }

    return result
