"""
檔案用途：提供 Meta CSV 讀取、雙語欄位別名解析、日期解析、與日資料聚合（週彙總）等共用工具。
供 `scripts/kpi_calc.py` 與後續確定性技能模組重用。
"""

import io
import json
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
from dateutil import parser


# =========================
# Column Aliases（雙語欄位對應）
# =========================
_ALIASES_CACHE: Dict[str, List[str]] = {}


def _load_aliases() -> Dict[str, List[str]]:
    """載入 `schemas/column_aliases.json`，支援英文與繁體中文欄位名稱對應。"""
    global _ALIASES_CACHE
    if _ALIASES_CACHE:
        return _ALIASES_CACHE

    aliases_path = Path(__file__).parent.parent / "schemas" / "column_aliases.json"
    if aliases_path.exists():
        with open(aliases_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            _ALIASES_CACHE = {k: v for k, v in data.items() if not k.startswith("$")}
    return _ALIASES_CACHE


def _get_alias(key: str) -> List[str]:
    """取得指定 alias key 的候選欄位清單；若不存在則回傳 [key]。"""
    aliases = _load_aliases()
    return aliases.get(key, [key])


# =========================
# CSV / 欄位清洗
# =========================
def _read_csv_bytes(file_bytes: bytes) -> pd.DataFrame:
    """讀取 Meta 匯出 CSV（支援常見編碼）。"""
    for enc in ["utf-8-sig", "utf-8", "cp950", "big5"]:
        try:
            return pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
        except Exception:
            continue
    return pd.read_csv(io.BytesIO(file_bytes))


def _clean_cols(df: pd.DataFrame) -> pd.DataFrame:
    """欄位名稱去前後空白。"""
    d = df.copy()
    d.columns = [str(c).strip() for c in d.columns]
    return d


def _resolve_col_name(df: pd.DataFrame, candidates: List[str]) -> str:
    """嘗試從候選清單中找出存在的欄位名稱。"""
    for col in candidates:
        if col in df.columns:
            return col
    return candidates[0] if candidates else ""


def _drop_total_rows(df: pd.DataFrame, name_candidates: List[str]) -> Tuple[pd.DataFrame, int]:
    """
    移除 Meta 匯出中的「總計/摘要列」：通常 name 欄位為空字串。
    """
    name_col = _resolve_col_name(df, name_candidates)
    if df.empty or not name_col or name_col not in df.columns:
        return df, 0

    d = df.copy()
    name = d[name_col].astype(str).fillna("").str.strip()
    before = len(d)
    d = d[name.ne("") & name.ne("nan")]
    return d, before - len(d)


# =========================
# 數值/欄位取值工具
# =========================
def _to_num(x) -> float:
    """轉數字：把逗號、空白、% 去掉；空值 -> 0。"""
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


def _first_str(df: pd.DataFrame, col: str) -> str:
    """取第一列字串值（不存在或空表則回傳空字串）。"""
    if not col or col not in df.columns or df.empty:
        return ""
    v = df.iloc[0][col]
    return "" if pd.isna(v) else str(v).strip()


def _sum_col(df: pd.DataFrame, candidates: List[str] | str) -> float:
    """
    欄位加總。candidates 可以是：
    - 單一 alias key（如 "spend"）：自動查詢 `column_aliases.json`
    - 欄位名稱清單（如 ["花費金額", "Amount spent"]）：直接使用
    """
    if isinstance(candidates, str):
        alias_candidates = _get_alias(candidates)
        candidates = alias_candidates if alias_candidates != [candidates] else [candidates]

    col = _resolve_col_name(df, candidates)
    if not col or col not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


# =========================
# 日期區間 / 週別
# =========================
def parse_date_range_from_meta(adset_df: pd.DataFrame) -> Tuple[str, str]:
    """
    以 Meta CSV 的「分析報告開始/結束」為準（支援英文/繁體中文欄位名稱）。
    v2 匯出多為日資料：不可用第一列推斷，需以全列 min/max 推導區間。
    """
    start_col = _resolve_col_name(adset_df, _get_alias("date_start"))
    end_col = _resolve_col_name(adset_df, _get_alias("date_end"))
    if adset_df.empty or start_col not in adset_df.columns or end_col not in adset_df.columns:
        return "", ""

    def _parse_dt(v) -> pd.Timestamp | None:
        s = ("" if v is None else str(v)).strip()
        if not s or s.lower() == "nan":
            return None
        try:
            return pd.Timestamp(parser.parse(s))
        except Exception:
            try:
                return pd.Timestamp(s.replace("/", "-")[:10])
            except Exception:
                return None

    starts = [_parse_dt(v) for v in adset_df[start_col].tolist()]
    ends = [_parse_dt(v) for v in adset_df[end_col].tolist()]
    starts = [d for d in starts if d is not None]
    ends = [d for d in ends if d is not None]
    if not starts or not ends:
        return "", ""

    date_start = min(starts).strftime("%Y-%m-%d")
    date_end = max(ends).strftime("%Y-%m-%d")
    return date_start, date_end


def iso_week_id(date_start: str) -> str:
    """用開始日推 ISO week，例如 2025-W49（格式：YYYY-Www）。"""
    try:
        dt = parser.parse(date_start)
        y, w, _ = dt.isocalendar()
        return f"{y}-W{int(w):02d}"
    except Exception:
        return ""


# =========================
# 日資料聚合（週彙總）
# =========================
def _is_daily_data(df: pd.DataFrame) -> bool:
    """
    判斷 DataFrame 是否為日資料格式。
    日資料特徵：每列的 Reporting starts == Reporting ends（同一天）。
    """
    start_col = _resolve_col_name(df, _get_alias("date_start"))
    end_col = _resolve_col_name(df, _get_alias("date_end"))
    if not start_col or not end_col or start_col not in df.columns or end_col not in df.columns:
        return False
    if df.empty:
        return False

    sample = df.head(5)
    same_day_count = sum(
        str(row[start_col]).strip() == str(row[end_col]).strip()
        for _, row in sample.iterrows()
        if pd.notna(row[start_col]) and pd.notna(row[end_col])
    )
    return same_day_count >= len(sample) * 0.8  # 80% 以上是同一天即判定為日資料


def _aggregate_daily_to_weekly(df: pd.DataFrame, name_col: str) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    將日資料按 name_col 聚合為週彙總。

    聚合規則：
    - Additive（可加總）：sum()
    - Reach：max()（累計去重值）
    - Frequency：impressions / max(reach)
    """
    if df.empty or name_col not in df.columns:
        return df, {}

    additive_keys = [
        "spend",
        "impressions",
        "link_clicks",
        "lpv",
        "atc",
        "ic",
        "purchases_platform",
        "purchases_value_platform",
        "purchases_website",
        "purchases_value_website",
        "video_3s",
        "thruplays",
        "video_25",
        "video_50",
        "video_75",
        "video_95",
        "video_100",
    ]

    agg_dict: Dict[str, str] = {}
    for key in additive_keys:
        col = _resolve_col_name(df, _get_alias(key))
        if col and col in df.columns:
            agg_dict[col] = "sum"

    reach_col = _resolve_col_name(df, _get_alias("reach"))
    if reach_col and reach_col in df.columns:
        agg_dict[reach_col] = "max"

    if not agg_dict:
        return df, {}

    grouped = df.groupby(name_col, as_index=False).agg(agg_dict)

    impressions_col = _resolve_col_name(grouped, _get_alias("impressions"))
    if reach_col in grouped.columns and impressions_col in grouped.columns:
        grouped["__frequency_calc"] = grouped.apply(
            lambda r: r[impressions_col] / r[reach_col] if r[reach_col] > 0 else 0,
            axis=1,
        )
        frequency_col = _resolve_col_name(df, _get_alias("frequency"))
        if frequency_col and frequency_col not in grouped.columns:
            grouped[frequency_col] = grouped["__frequency_calc"]

    return grouped, {
        "additive": "sum",
        "reach": "max",
        "frequency": "impressions / max(reach)",
    }

