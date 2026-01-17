# -*- coding: utf-8 -*-
"""
檔案用途：將蝦皮廣告報表 CSV 轉換為專案通用的 Unified JSON 格式（unified_ad_data）。
支援解析蝦皮廣告總體報表與關鍵字版位報表。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# === 常數定義 ===

SHOPEE_HEADER_SKIP_ROWS = 7  # 蝦皮 CSV 前 7 行是 metadata

# 欄位名稱對應（蝦皮中文欄位 → 內部 key）
SHOPEE_COL_MAP = {
    "廣告名稱": "name",
    "商品 ID": "product_id",
    "商品ID": "product_id",
    "廣告類型": "ad_type",
    "狀態": "status",
    "版位": "placement",
    "開始日期": "start_date",
    "結束日期": "end_date",
    "瀏覽數": "impressions",
    "點擊數": "clicks",
    "點擊率": "ctr",
    "轉換數": "conversions_platform_count",
    "直接轉換數": "conversions_truth_count",
    "轉換率": "cvr",
    "直接轉換率": "direct_cvr",
    "銷售金額": "conversions_platform_value",
    "直接銷售金額": "conversions_truth_value",
    "花費": "spend",
    "投入產出比": "roas",
    "直接投入產出比": "direct_roas",
    "每一筆轉換的成本": "cpa",
    "每一筆直接轉換的成本": "direct_cpa",
    "銷售數": "sales_count",
    "直接銷售數": "direct_sales_count",
}


# === 工具函式 ===


def _read_shopee_csv(path: Path) -> pd.DataFrame:
    """讀取蝦皮 CSV，自動跳過 metadata 行。"""
    for enc in ("utf-8-sig", "utf-8", "cp950", "big5"):
        try:
            return pd.read_csv(path, encoding=enc, skiprows=SHOPEE_HEADER_SKIP_ROWS)
        except Exception:
            continue
    return pd.read_csv(path, skiprows=SHOPEE_HEADER_SKIP_ROWS)


def _extract_date_range_from_filename(filename: str) -> Tuple[Optional[str], Optional[str]]:
    """從檔名擷取日期範圍 (例如 2025_12_04-2025_12_09)。"""
    match = re.search(r"(\d{4}_\d{2}_\d{2})-(\d{4}_\d{2}_\d{2})", filename)
    if match:
        start = match.group(1).replace("_", "-")
        end = match.group(2).replace("_", "-")
        return start, end
    return None, None


def _extract_metadata_from_csv(path: Path) -> Dict[str, str]:
    """從蝦皮 CSV 前幾行擷取 metadata（賣場名稱、期間等）。"""
    metadata = {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            lines = [f.readline().strip() for _ in range(7)]
        for line in lines:
            if "," in line:
                parts = line.split(",", 1)
                if len(parts) == 2:
                    key, val = parts[0].strip(), parts[1].strip()
                    if key and val:
                        metadata[key] = val
    except Exception:
        pass
    return metadata


def _clean_cols(df: pd.DataFrame) -> pd.DataFrame:
    """清理欄位名稱（去除空白）。"""
    d = df.copy()
    d.columns = [str(c).strip() for c in d.columns]
    return d


def _to_float(x: Any) -> float:
    """安全轉換為浮點數。"""
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        try:
            if pd.isna(x):
                return 0.0
        except Exception:
            pass
        return float(x)
    s = str(x).strip().replace(",", "").replace("%", "").replace("-", "")
    if s == "" or s.lower() in {"nan", "none", "n/a"}:
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0


def _to_int(x: Any) -> int:
    """安全轉換為整數。"""
    return int(round(_to_float(x)))


def _get_str(row: pd.Series, col: str) -> str:
    """取得欄位值並轉為字串，數字 ID 去除 .0 尾綴。"""
    v = row.get(col)
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _stable_fallback_id(
    *, platform: str, level: str, name: str, time_range: Dict[str, str], salt: str = ""
) -> str:
    """產生穩定的 fallback ID（當無原生 ID 時使用）。"""
    raw = f"{platform}|{level}|{name}|{time_range.get('start', '')}|{time_range.get('end', '')}|{salt}"
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"{platform}_{level}_{h}"


def _build_shopee_record(
    *,
    row: pd.Series,
    row_index: int,
    time_range: Dict[str, str],
) -> Dict[str, Any]:
    """建立單筆 Unified Ad Data record。"""
    name = _get_str(row, "廣告名稱")
    product_id = _get_str(row, "商品 ID") or _get_str(row, "商品ID")

    # ID 策略：優先用商品 ID，否則用 fallback
    record_id = product_id or _stable_fallback_id(
        platform="shopee",
        level="ad",
        name=name,
        time_range=time_range,
        salt=_get_str(row, "廣告類型"),
    )

    # 指標
    spend = _to_float(row.get("花費"))
    impressions = _to_int(row.get("瀏覽數"))
    clicks = _to_int(row.get("點擊數"))

    # 轉換 (platform = 歸因口徑, truth = 直接口徑)
    conv_platform_count = _to_int(row.get("轉換數"))
    conv_platform_value = _to_float(row.get("銷售金額"))
    conv_truth_count = _to_int(row.get("直接轉換數"))
    conv_truth_value = _to_float(row.get("直接銷售金額"))

    return {
        "platform": "shopee",
        "level": "ad",
        "id": record_id,
        "name": name,
        "time_range": time_range,
        "currency": "TWD",
        "metrics": {
            "spend": round(float(spend), 2),
            "impressions": int(impressions),
            "clicks": int(clicks),
            "conversions": {
                "truth": {
                    "count": int(conv_truth_count),
                    "value": round(float(conv_truth_value), 2),
                },
                "platform": {
                    "count": int(conv_platform_count),
                    "value": round(float(conv_platform_value), 2),
                },
            },
            "funnel": {"atc": 0, "ic": 0, "lpv": 0},  # 蝦皮無漏斗欄位
        },
        "source": {
            "kind": "shopee_ad_csv",
            "row_index": int(row_index),
            "raw_id": product_id or None,
            "product_id": product_id or None,
            "ad_type": _get_str(row, "廣告類型") or None,
            "status": _get_str(row, "狀態") or None,
            "placement": _get_str(row, "版位") or None,
        },
    }


def _drop_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    """移除空白行（廣告名稱為空）。"""
    if df.empty or "廣告名稱" not in df.columns:
        return df
    d = df.copy()
    name_col = d["廣告名稱"].astype(str).fillna("").str.strip()
    return d[name_col.ne("") & name_col.ne("nan")]


# === 主要轉換函式 ===


def adapt_shopee_ad_csv(path: Path) -> Dict[str, Any]:
    """將蝦皮廣告 CSV 轉換為 Unified Ad Data 格式。"""
    df = _clean_cols(_read_shopee_csv(path))
    df = _drop_empty_rows(df)

    # 擷取時間範圍
    start, end = _extract_date_range_from_filename(path.name)
    time_range = {"start": start or "", "end": end or ""}

    # 轉換每一筆資料
    records: List[Dict[str, Any]] = []
    for i, row in df.iterrows():
        name = _get_str(row, "廣告名稱")
        if not name:
            continue
        records.append(_build_shopee_record(row=row, row_index=int(i), time_range=time_range))

    return {
        "version": "unified_ad_data.v1",
        "source": "shopee_ad_csv",
        "timezone": "Asia/Taipei",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "data": records,
    }


# === CLI 入口 ===


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="蝦皮廣告 CSV -> Unified Ad Data")
    p.add_argument("--input", type=Path, required=True, help="蝦皮廣告 CSV 檔案路徑")
    p.add_argument("--out", type=Path, required=True, help="輸出 unified JSON 檔案路徑")
    p.add_argument(
        "--validate", action="store_true", help="輸出後用 schemas/unified_ad_data.json 驗證"
    )
    args = p.parse_args(argv)

    payload = adapt_shopee_ad_csv(args.input)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ 已轉換 {len(payload['data'])} 筆資料至 {args.out}")

    if args.validate:
        from scripts.validator import validate_file

        validate_file(payload, schema_filename="unified_ad_data.json", label="unified_ad_data")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
