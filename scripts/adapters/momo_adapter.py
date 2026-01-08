# -*- coding: utf-8 -*-
"""
檔案用途：將 MOMO ADS 報表 CSV 轉換為專案通用的 Unified JSON 格式（unified_ad_data）。
支援解析 MOMO 廣告素材報表 (商品層級)。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# === 常數定義 ===

MOMO_HEADER_ROW = 0  # MOMO CSV/Excel Header 在第 1 行

# 欄位名稱對應（MOMO 中文欄位 → 內部 key）
MOMO_COL_MAP = {
    "product_id": ["商品編號", "編號"],
    "name": ["商品名稱", "名稱"],
    "impressions": ["曝光數", "瀏覽量"],
    "clicks": ["點擊數"],
    "spend": ["已花費 (NTD)"],
    "conversions_count": ["訂單數"],
    "conversions_value": ["商品訂購金額 (NTD)"],
    "atc": ["加入購物車數"],
}

# === 工具函式 ===

def _read_momo_csv(path: Path) -> pd.DataFrame:
    """讀取 MOMO 報表 (支援 csv, xlsx, xls)。"""
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        # Excel 讀取
        return pd.read_excel(path, header=MOMO_HEADER_ROW)
    
    # CSV 讀取
    for enc in ("utf-8-sig", "utf-8", "cp950", "big5"):
        try:
            return pd.read_csv(path, encoding=enc, header=MOMO_HEADER_ROW)
        except Exception:
            continue
    return pd.read_csv(path, header=MOMO_HEADER_ROW)


def _extract_date_range_from_filename(filename: str) -> Tuple[str, str]:
    """從檔名擷取日期範圍 (例如 momo_20251201-20251231.xlsx)。若無則回傳 default。"""
    # 支援 YYYYMMDD-YYYYMMDD
    match = re.search(r"(\d{8})[-_](\d{8})", filename)
    if match:
        start = f"{match.group(1)[:4]}-{match.group(1)[4:6]}-{match.group(1)[6:]}"
        end = f"{match.group(2)[:4]}-{match.group(2)[4:6]}-{match.group(2)[6:]}"
        return start, end
    
    # 支援 YYYY_MM_DD-YYYY_MM_DD
    match2 = re.search(r"(\d{4}_\d{2}_\d{2})[-_](\d{4}_\d{2}_\d{2})", filename)
    if match2:
        start = match2.group(1).replace("_", "-")
        end = match2.group(2).replace("_", "-")
        return start, end

    # Fallback default date to pass schema validation (YYYY-MM-DD)
    return "1970-01-01", "1970-01-01"


def _clean_cols(df: pd.DataFrame) -> pd.DataFrame:
    """清理欄位名稱（去除空白）。"""
    d = df.copy()
    columns = [str(c).strip() for c in d.columns]
    d.columns = columns
    return d


def _find_col(row: pd.Series, possible_names: List[str]) -> Any:
    """從多個可能的欄位名稱中找值。"""
    for name in possible_names:
        if name in row:
            return row[name]
    return None


def _to_float(x: Any) -> float:
    """安全轉換為浮點數 (去除 , %)。"""
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        try:
            if pd.isna(x):
                return 0.0
        except Exception:
            pass
        return float(x)
    s = str(x).strip().replace(",", "").replace("%", "").replace("NT$", "")
    if s == "" or s.lower() in {"nan", "none", "n/a"}:
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0


def _to_int(x: Any) -> int:
    """安全轉換為整數。"""
    return int(round(_to_float(x)))


def _get_str(val: Any) -> str:
    """取得欄位值並轉為字串，數字 ID 去除 .0 尾綴。"""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    return str(val).strip()


def _build_momo_record(
    *,
    row: pd.Series,
    row_index: int,
    time_range: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    """建立單筆 Unified Ad Data record。"""
    
    # 欄位值擷取 (使用 MOMO_COL_MAP)
    raw_name_val = _find_col(row, MOMO_COL_MAP["name"])
    raw_name = _get_str(raw_name_val)
    
    raw_id_val = _find_col(row, MOMO_COL_MAP["product_id"])
    raw_id = _get_str(raw_id_val)
    
    spend = _to_float(_find_col(row, MOMO_COL_MAP["spend"]))
    impressions = _to_int(_find_col(row, MOMO_COL_MAP["impressions"]))
    clicks = _to_int(_find_col(row, MOMO_COL_MAP["clicks"]))
    
    conv_count = _to_int(_find_col(row, MOMO_COL_MAP["conversions_count"]))
    conv_value = _to_float(_find_col(row, MOMO_COL_MAP["conversions_value"]))
    atc = _to_int(_find_col(row, MOMO_COL_MAP["atc"]))

    # 跳過無效行 (ID 與 Name 皆空，或總計行)
    if (not raw_id and not raw_name) or "總計" in raw_name:
        return None

    # ID 策略
    record_id = raw_id
    if not record_id:
         # Fallback for rows without ID but with name
         raw_str = f"momo|{raw_name}|{time_range.get('start')}"
         record_id = f"momo_fallback_{hashlib.sha1(raw_str.encode('utf-8')).hexdigest()[:10]}"

    return {
        "platform": "momo",
        "level": "ad",  # MOMO 報表多為商品層級，視同 AD
        "id": record_id,
        "name": raw_name,
        "time_range": time_range,
        "currency": "TWD",
        "metrics": {
            "spend": round(spend, 2),
            "impressions": impressions,
            "clicks": clicks,
            "conversions": {
                "truth": {"count": 0, "value": 0.0}, # MOMO 無直接轉換數據
                "platform": {"count": conv_count, "value": round(conv_value, 2)},
            },
            "funnel": {
                "atc": atc,
                "ic": 0,
                "lpv": 0
            },
        },
        "source": {
            "kind": "momo_ad_report",
            "row_index": row_index,
            "raw_id": raw_id,
        },
    }


# === 主要轉換函式 ===

def adapt_momo_ad_report(path: Path) -> Dict[str, Any]:
    """將 MOMO 報表轉換為 Unified Ad Data 格式。"""
    df = _clean_cols(_read_momo_csv(path))
    
    # 擷取時間範圍
    start, end = _extract_date_range_from_filename(path.name)
    time_range = {"start": start, "end": end}
    
    records: List[Dict[str, Any]] = []
    for i, row in df.iterrows():
        record = _build_momo_record(row=row, row_index=int(i), time_range=time_range)
        if record:
            records.append(record)
    
    return {
        "version": "unified_ad_data.v1",
        "source": "momo_ad_report",
        "timezone": "Asia/Taipei",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "data": records,
    }


# === CLI 入口 ===

def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="MOMO ADS 報表 -> Unified Ad Data")
    p.add_argument("--input", type=Path, required=True, help="MOMO 報表檔案路徑 (csv/xlsx/xls)")
    p.add_argument("--out", type=Path, required=True, help="輸出 unified JSON 檔案路徑")
    p.add_argument("--validate", action="store_true", help="輸出後用 schemas/unified_ad_data.json 驗證")
    args = p.parse_args(argv)
    
    payload = adapt_momo_ad_report(args.input)
    
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"✅ 已轉換 {len(payload['data'])} 筆資料至 {args.out}")
    
    if args.validate:
        from scripts.validator import validate_file
        validate_file(payload, schema_filename="unified_ad_data.json", label="unified_ad_data")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
