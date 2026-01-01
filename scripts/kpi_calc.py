import io
import json
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, Tuple

import pandas as pd


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


def _to_num(s):
    # 轉數字：把逗號、空白、% 去掉
    if s is None:
        return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip().replace(",", "")
    s = s.replace("%", "")
    if s == "" or s.lower() == "nan":
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0


def _sum_col(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns:
        return 0.0
    return float(df[col].apply(_to_num).sum())


def _first_str(df: pd.DataFrame, col: str) -> str:
    if col not in df.columns or df.empty:
        return ""
    v = df.iloc[0][col]
    return "" if pd.isna(v) else str(v).strip()


def parse_date_range_from_meta(adset_df: pd.DataFrame) -> Tuple[str, str]:
    """
    以你現有 Meta CSV 的「分析報告開始/結束」為準
    可能是 '2025-12-04' 或 '2025/12/04' 或含時間
    """
    start_raw = _first_str(adset_df, "分析報告開始")
    end_raw = _first_str(adset_df, "分析報告結束")

    def _parse(s: str) -> str:
        s = s.replace("/", "-")
        # 只取前 10 碼 YYYY-MM-DD
        s10 = s[:10]
        # 容錯
        try:
            datetime.fromisoformat(s10)
            return s10
        except Exception:
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


def calc_meta_kpis(adset_df: pd.DataFrame, ads_df: pd.DataFrame) -> Dict[str, Any]:
    # Adset 層總覽（拍板用）
    spend = _sum_col(adset_df, "花費金額 (TWD)")
    purchases = _sum_col(adset_df, "購買次數")
    purchase_value = _sum_col(adset_df, "購買轉換值")  # 你報表欄位是「購買轉換值」
    atc = _sum_col(adset_df, "加到購物車次數")
    ic = _sum_col(adset_df, "開始結帳次數")
    lpv = _sum_col(adset_df, "連結頁面瀏覽次數")
    link_clicks = _sum_col(adset_df, "連結點擊次數")

    roas = (purchase_value / spend) if spend > 0 else 0.0
    cpa = (spend / purchases) if purchases > 0 else 0.0

    return {
        "spend_twd": round(spend, 2),
        "purchase_value_twd": round(purchase_value, 2),
        "purchases": int(purchases),
        "roas_calc": round(roas, 4),
        "cpa_calc_twd": round(cpa, 2),
        "funnel": {
            "link_clicks": int(link_clicks),
            "landing_page_views": int(lpv),
            "add_to_cart": int(atc),
            "initiate_checkout": int(ic),
        },
        "ads_has_rankings": all(
            c in ads_df.columns for c in ["品質排名", "互動率排名", "轉換率排名"]
        ),
    }


def calc_top_tables(adset_df: pd.DataFrame, ads_df: pd.DataFrame, top_n: int = 5) -> Dict[str, Any]:
    # 用腳本算 ROAS，避免看 Meta 的欄位四捨五入
    def add_roas(df: pd.DataFrame, name_col: str) -> pd.DataFrame:
        d = df.copy()
        d["__spend"] = d["花費金額 (TWD)"].apply(_to_num)
        d["__value"] = d["購買轉換值"].apply(_to_num)
        d["__purchases"] = d["購買次數"].apply(_to_num)
        d["__roas"] = d.apply(lambda r: (r["__value"] / r["__spend"]) if r["__spend"] > 0 else 0.0, axis=1)
        d["__cpa"] = d.apply(lambda r: (r["__spend"] / r["__purchases"]) if r["__purchases"] > 0 else 0.0, axis=1)
        keep = [name_col, "__spend", "__value", "__purchases", "__roas", "__cpa", "頻率"]
        keep = [c for c in keep if c in d.columns]
        return d[keep]

    adset = add_roas(adset_df, "廣告組合名稱")
    ads = add_roas(ads_df, "廣告名稱")

    top_adset = adset.sort_values("__roas", ascending=False).head(top_n)
    worst_adset = adset.sort_values("__roas", ascending=True).head(top_n)

    top_ads = ads.sort_values("__roas", ascending=False).head(top_n)
    worst_ads = ads.sort_values("__roas", ascending=True).head(top_n)

    def to_records(df: pd.DataFrame, name_col: str):
        import math

        def _safe_float(x, default=0.0):
            try:
                if x is None:
                    return default
                if isinstance(x, float) and math.isnan(x):
                    return default
                return float(x)
            except Exception:
                return default

        def _safe_int(x, default=0):
            v = _safe_float(x, default=float(default))
            # v 仍可能是 nan（極少數狀況），再保險一次
            if isinstance(v, float) and math.isnan(v):
                return default
            return int(round(v))

        out = []
        for _, r in df.iterrows():
            out.append({
                "spend_twd": round(_safe_float(r.get("__spend", 0)), 2),
                "purchase_value_twd": round(_safe_float(r.get("__value", 0)), 2),
                "purchases": _safe_int(r.get("__purchases", 0)),
                "roas": round(_safe_float(r.get("__roas", 0)), 4),
                "cpa_twd": round(_safe_float(r.get("__cpa", 0)), 2),
                "frequency": round(_safe_float(r.get("頻率", 0)), 2) if "頻率" in df.columns else None
            })
        return out

    return {
        "top_adsets_by_roas": to_records(top_adset, "廣告組合名稱"),
        "worst_adsets_by_roas": to_records(worst_adset, "廣告組合名稱"),
        "top_ads_by_roas": to_records(top_ads, "廣告名稱"),
        "worst_ads_by_roas": to_records(worst_ads, "廣告名稱"),
    }


def calc_web_kpis(web_df: pd.DataFrame) -> Dict[str, Any]:
    # 這份官網 Excel 是彙總表：日期、訂單量、營業額、毛利…（欄位有尾巴空白，要先 strip）
    d = web_df.copy()
    d.columns = [str(c).strip() for c in d.columns]

    orders_col = "訂單量"
    revenue_col = "營業額"  # 預設用營業額（你若要改成交額，下一步我幫你切換）

    orders = _sum_col(d, orders_col) if orders_col in d.columns else 0.0
    revenue = _sum_col(d, revenue_col) if revenue_col in d.columns else 0.0
    aov = (revenue / orders) if orders > 0 else 0.0

    return {
        "orders": int(orders),
        "revenue_twd": round(revenue, 2),
        "aov_twd_calc": round(aov, 2),
        "columns": list(d.columns),
    }


def build_report_summary(
    meta_adset_bytes: bytes,
    meta_ads_bytes: bytes,
    web_excel_bytes: bytes,
) -> Dict[str, Any]:
    adset_df = _clean_cols(_read_csv_bytes(meta_adset_bytes))
    ads_df = _clean_cols(_read_csv_bytes(meta_ads_bytes))
    web_df = pd.read_excel(io.BytesIO(web_excel_bytes))
    web_df = _clean_cols(web_df)

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
        "missing_data": {
            "meta_unavailable_fields": ["optimization_goal", "billing_event", "buying_type"],
            "note": "這三欄匯出拿不到：用命名規則 tag 或 inputs.json 快照補。"
        }
    }
