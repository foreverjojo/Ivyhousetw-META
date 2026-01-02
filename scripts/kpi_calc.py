import io
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, Tuple, Optional

import pandas as pd


# =========================
# CSV / Excel IO
# =========================
def _read_csv_bytes(file_bytes: bytes) -> pd.DataFrame:
    # 支援 Meta 匯出常見編碼
    for enc in ["utf-8-sig", "utf-8", "cp950", "big5"]:
        try:
            return pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
        except Exception:
            continue
    return pd.read_csv(io.BytesIO(file_bytes))


def _clean_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


# =========================
# Numeric utils
# =========================
def _to_num(x) -> float:
    # 轉數字：把逗號、空白、% 去掉；空值 -> 0
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        try:
            if pd.isna(x):
                return 0.0
        except Exception:
            pass
        return float(x)

    s = str(x).strip().replace(",", "").replace("%", "")
    if s == "" or s.lower() == "nan":
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0


def _sum_col(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns or df.empty:
        return 0.0
    return float(df[col].apply(_to_num).sum())


def _first_str(df: pd.DataFrame, col: str) -> str:
    if col not in df.columns or df.empty:
        return ""
    v = df.iloc[0][col]
    return "" if pd.isna(v) else str(v).strip()


# =========================
# Meta CSV fixed cleaning rules
# - drop total/summary rows (name empty)
# =========================
def _drop_total_rows(df: pd.DataFrame, name_col: str) -> Tuple[pd.DataFrame, int]:
    if df.empty or name_col not in df.columns:
        return df, 0
    d = df.copy()
    name = d[name_col].astype(str).fillna("").str.strip()
    before = len(d)
    d = d[name.ne("") & name.ne("nan")]
    dropped = before - len(d)
    return d, dropped


# =========================
# Date range / week id
# =========================
def parse_date_range_from_meta(adset_df: pd.DataFrame) -> Tuple[str, str]:
    """
    以 Meta CSV 的「分析報告開始/結束」為準
    可能是 '2025-12-04' 或 '2025/12/04' 或含時間
    """
    start_raw = _first_str(adset_df, "分析報告開始")
    end_raw = _first_str(adset_df, "分析報告結束")

    def _parse(s: str) -> str:
        s = (s or "").replace("/", "-")
        s10 = s[:10]
        try:
            datetime.fromisoformat(s10)
            return s10
        except Exception:
            # 容錯：就回傳前 10 碼
            return s10

    return _parse(start_raw), _parse(end_raw)


def iso_week_id(date_start: str) -> str:
    # 用開始日推 ISO week，例如 2025-W49
    try:
        dt = datetime.fromisoformat(date_start)
        y, w, _ = dt.isocalendar()
        return f"{y}-W{int(w):02d}"
    except Exception:
        return ""


# =========================
# KPI calc (Truth = Website Direct)
# =========================
def calc_meta_kpis(adset_df: pd.DataFrame, ads_df: pd.DataFrame) -> Dict[str, Any]:
    """
    KPI 真值：網站直接（website_*）
    漂移偵測：平台購買（platform_*）+ delta_*
    """

    # spend (truth/platform share same spend)
    spend = _sum_col(adset_df, "花費金額 (TWD)")

    # Truth (website direct)
    website_purchases = _sum_col(adset_df, "網站直接購買次數")
    website_value = _sum_col(adset_df, "網站直接購買轉換值")

    # Platform (for drift watch)
    platform_purchases = _sum_col(adset_df, "購買次數")
    platform_value = _sum_col(adset_df, "購買轉換值")

    # Funnel (events)
    atc = _sum_col(adset_df, "加到購物車次數")
    ic = _sum_col(adset_df, "開始結帳次數")
    lpv = _sum_col(adset_df, "連結頁面瀏覽次數")
    link_clicks = _sum_col(adset_df, "連結點擊次數")

    # Truth ROAS/CPA
    roas_truth = (website_value / spend) if spend > 0 else 0.0
    cpa_truth = (spend / website_purchases) if website_purchases > 0 else 0.0

    # Platform ROAS/CPA (reference)
    roas_platform = (platform_value / spend) if spend > 0 else 0.0
    cpa_platform = (spend / platform_purchases) if platform_purchases > 0 else 0.0

    # Drift
    delta_value = platform_value - website_value
    delta_rate = (delta_value / website_value) if website_value > 0 else 0.0

    return {
        # ✅ legacy keys (now point to TRUTH, to keep downstream stable)
        "spend_twd": round(spend, 2),
        "purchase_value_twd": round(website_value, 2),   # legacy key, now truth
        "purchases": int(round(website_purchases)),      # legacy key, now truth
        "roas_calc": round(roas_truth, 4),               # legacy key, now truth
        "cpa_calc_twd": round(cpa_truth, 2),             # legacy key, now truth

        # ✅ explicit truth keys
        "website_purchases": int(round(website_purchases)),
        "website_purchase_value_twd": round(website_value, 2),

        # ✅ platform reference keys (drift watch)
        "platform_purchases": int(round(platform_purchases)),
        "platform_purchase_value_twd": round(platform_value, 2),
        "roas_platform_calc": round(roas_platform, 4),
        "cpa_platform_calc_twd": round(cpa_platform, 2),

        # ✅ drift metrics
        "delta_purchase_value_twd": round(delta_value, 2),
        "delta_purchase_value_rate": round(delta_rate, 4),

        "funnel": {
            "link_clicks": int(round(link_clicks)),
            "landing_page_views": int(round(lpv)),
            "add_to_cart": int(round(atc)),
            "initiate_checkout": int(round(ic)),
        },
        "ads_has_rankings": all(c in ads_df.columns for c in ["品質排名", "互動率排名", "轉換率排名"]),
    }


def calc_top_tables(adset_df: pd.DataFrame, ads_df: pd.DataFrame, top_n: int = 5) -> Dict[str, Any]:
    """
    Top/Worst tables:
    - 預設用「網站直接」作 ROAS 排序（與 KPI 真值一致）
    - 同時帶 platform/delta 欄位做漂移偵測
    - 補上 name，避免表格失去可讀性
    """

    def add_roas(df: pd.DataFrame, name_col: str) -> pd.DataFrame:
        d = df.copy()

        d["__name"] = d[name_col].astype(str).fillna("").str.strip()

        d["__spend"] = d.get("花費金額 (TWD)", 0).apply(_to_num)

        # truth
        if "網站直接購買轉換值" in d.columns:
            d["__value_truth"] = d["網站直接購買轉換值"].apply(_to_num)
        else:
            d["__value_truth"] = d.get("購買轉換值", 0).apply(_to_num)

        if "網站直接購買次數" in d.columns:
            d["__purchases_truth"] = d["網站直接購買次數"].apply(_to_num)
        else:
            d["__purchases_truth"] = d.get("購買次數", 0).apply(_to_num)

        # platform reference
        d["__value_platform"] = d.get("購買轉換值", 0).apply(_to_num)
        d["__purchases_platform"] = d.get("購買次數", 0).apply(_to_num)

        # truth metrics
        d["__roas_truth"] = d.apply(lambda r: (r["__value_truth"] / r["__spend"]) if r["__spend"] > 0 else 0.0, axis=1)
        d["__cpa_truth"] = d.apply(lambda r: (r["__spend"] / r["__purchases_truth"]) if r["__purchases_truth"] > 0 else 0.0, axis=1)

        # platform metrics
        d["__roas_platform"] = d.apply(lambda r: (r["__value_platform"] / r["__spend"]) if r["__spend"] > 0 else 0.0, axis=1)

        # drift
        d["__delta_value"] = d["__value_platform"] - d["__value_truth"]
        d["__delta_rate"] = d.apply(lambda r: (r["__delta_value"] / r["__value_truth"]) if r["__value_truth"] > 0 else 0.0, axis=1)

        keep = [
            "__name",
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
            "頻率",
        ]
        keep = [c for c in keep if c in d.columns]
        return d[keep]

    adset = add_roas(adset_df, "廣告組合名稱")
    ads = add_roas(ads_df, "廣告名稱")

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
            out.append({
                "name": str(r.get("__name", "")).strip(),

                # truth (aligned with KPI)
                "spend_twd": round(_sf(r.get("__spend", 0)), 2),
                "purchase_value_twd": round(_sf(r.get("__value_truth", 0)), 2),
                "purchases": _si(r.get("__purchases_truth", 0)),
                "roas": round(_sf(r.get("__roas_truth", 0)), 4),
                "cpa_twd": round(_sf(r.get("__cpa_truth", 0)), 2),

                # platform reference + drift
                "platform_purchase_value_twd": round(_sf(r.get("__value_platform", 0)), 2),
                "platform_purchases": _si(r.get("__purchases_platform", 0)),
                "roas_platform": round(_sf(r.get("__roas_platform", 0)), 4),
                "delta_purchase_value_twd": round(_sf(r.get("__delta_value", 0)), 2),
                "delta_purchase_value_rate": round(_sf(r.get("__delta_rate", 0)), 4),

                "frequency": round(_sf(r.get("頻率", 0)), 2) if "頻率" in df.columns else None
            })
        return out

    return {
        "top_adsets_by_roas": to_records(top_adset),
        "worst_adsets_by_roas": to_records(worst_adset),
        "top_ads_by_roas": to_records(top_ads),
        "worst_ads_by_roas": to_records(worst_ads),
    }


# =========================
# Web KPI
# =========================
def calc_web_kpis(web_df: pd.DataFrame) -> Dict[str, Any]:
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
# Build report_summary (v1)
# =========================
def build_report_summary(
    meta_adset_bytes: bytes,
    meta_ads_bytes: bytes,
    web_excel_bytes: bytes,
) -> Dict[str, Any]:
    adset_df = _clean_cols(_read_csv_bytes(meta_adset_bytes))
    ads_df = _clean_cols(_read_csv_bytes(meta_ads_bytes))
    web_df = pd.read_excel(io.BytesIO(web_excel_bytes))
    web_df = _clean_cols(web_df)

    # ✅ drop total/summary rows (must)
    adset_df, dropped_adset = _drop_total_rows(adset_df, "廣告組合名稱")
    ads_df, dropped_ads = _drop_total_rows(ads_df, "廣告名稱")

    date_start, date_end = parse_date_range_from_meta(adset_df)
    week_id = iso_week_id(date_start)

    meta_kpi = calc_meta_kpis(adset_df, ads_df)
    tables = calc_top_tables(adset_df, ads_df, top_n=5)
    web_kpi = calc_web_kpis(web_df)

    return {
        "schema_version": "report_summary.v1",
        "generated_at": datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds"),
        "week_id": week_id,
        "date_range": f"{date_start}~{date_end}",

        # schema locked
        "kpi_truth_source": "meta_adset_csv",
        "ad_diagnostics_source": "meta_ad_csv",

        "kpi": {
            "meta": meta_kpi,
            "web": web_kpi,
        },
        "tables": tables,

        # 非必要，但很實用：可追溯清洗規則是否生效
        "data_cleaning": {
            "dropped_total_rows": {
                "meta_adset": int(dropped_adset),
                "meta_ads": int(dropped_ads),
            }
        },

        "missing_data": {
            "meta_unavailable_fields": ["optimization_goal", "billing_event", "buying_type"],
            "note": "這三欄匯出拿不到：用命名規則 tag 或 inputs.json 快照補。"
        }
    }
