"""
檔案用途：將 Meta 匯出的 Adset/Ad CSV 轉換為專案通用的 Unified JSON 格式（unified_ad_data）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from utils import naming


@dataclass(frozen=True)
class MetaCsvSpec:
    level: str
    name_col: str
    id_cols: tuple[str, ...]


META_ADSET_SPEC = MetaCsvSpec(
    level="adset",
    name_col="廣告組合名稱",
    id_cols=("廣告組合 ID", "廣告組合ID", "廣告組合編號", "Ad Set ID"),
)
META_AD_SPEC = MetaCsvSpec(
    level="ad",
    name_col="廣告名稱",
    id_cols=("廣告 ID", "廣告ID", "廣告編號", "Ad ID"),
)


def _read_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp950", "big5"):
        try:
            return pd.read_csv(path, encoding=enc, comment="#")
        except Exception:
            continue
    return pd.read_csv(path, comment="#")


def _clean_cols(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d.columns = [str(c).strip() for c in d.columns]
    return d


def _first_existing_col(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _to_float(x: Any) -> float:
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
    if s == "" or s.lower() in {"nan", "none"}:
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0


def _to_int(x: Any) -> int:
    return int(round(_to_float(x)))


def _normalize_date_yyyy_mm_dd(s: Any) -> str | None:
    if s is None:
        return None
    ss = str(s).strip().replace("/", "-")[:10]
    if ss == "" or ss.lower() in {"nan", "none"}:
        return None
    try:
        datetime.fromisoformat(ss)
        return ss
    except Exception:
        return None


def _drop_total_rows(df: pd.DataFrame, name_col: str) -> tuple[pd.DataFrame, int]:
    if df.empty or name_col not in df.columns:
        return df, 0
    d = df.copy()
    name = d[name_col].astype(str).fillna("").str.strip()
    before = len(d)
    d = d[name.ne("") & name.ne("nan")]
    return d, before - len(d)


def _stable_fallback_id(
    *, platform: str, level: str, name: str, time_range: dict[str, str], salt: str = ""
) -> str:
    raw = f"{platform}|{level}|{name}|{time_range.get('start', '')}|{time_range.get('end', '')}|{salt}"
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"{platform}_{level}_{h}"


def _extract_time_range(df: pd.DataFrame) -> dict[str, str]:
    start, end = naming.extract_date_range_from_csv(df)
    start_n = _normalize_date_yyyy_mm_dd(start) or ""
    end_n = _normalize_date_yyyy_mm_dd(end) or ""
    return {"start": start_n, "end": end_n}


def _row_time_range(row: pd.Series, fallback: dict[str, str]) -> dict[str, str]:
    start = _normalize_date_yyyy_mm_dd(row.get("分析報告開始"))
    end = _normalize_date_yyyy_mm_dd(row.get("分析報告結束"))
    return {
        "start": start or fallback.get("start", ""),
        "end": end or fallback.get("end", ""),
    }


def _get_str(row: pd.Series, col: str) -> str:
    """取得欄位值並轉為字串，數字 ID 去除 .0 尾綴（如 2380001.0 → 2380001）。"""
    v = row.get(col)
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    # 處理浮點數 ID：若為整數浮點值 (如 2380001.0)，去除 .0
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _get_metric(row: pd.Series, col: str) -> float:
    if col not in row.index:
        return 0.0
    return _to_float(row.get(col))


def _build_record(
    *,
    spec: MetaCsvSpec,
    row: pd.Series,
    row_index: int,
    time_range: dict[str, str],
) -> dict[str, Any]:
    name = _get_str(row, spec.name_col)
    id_col = _first_existing_col(pd.DataFrame([row]), spec.id_cols)
    raw_id = _get_str(row, id_col) if id_col else ""

    record_id = raw_id or _stable_fallback_id(
        platform="meta",
        level=spec.level,
        name=name,
        time_range=time_range,
        salt=_get_str(row, "行銷活動名稱") or _get_str(row, "廣告組合名稱"),
    )

    spend = _get_metric(row, "花費金額 (TWD)")
    impressions = _to_int(row.get("曝光次數")) if "曝光次數" in row.index else 0
    clicks = _to_int(row.get("連結點擊次數")) if "連結點擊次數" in row.index else 0

    truth_count = _to_int(row.get("網站直接購買次數")) if "網站直接購買次數" in row.index else 0
    truth_value = _get_metric(row, "網站直接購買轉換值")
    platform_count = _to_int(row.get("購買次數")) if "購買次數" in row.index else 0
    platform_value = _get_metric(row, "購買轉換值")

    atc = _to_int(row.get("加到購物車次數")) if "加到購物車次數" in row.index else 0
    ic = _to_int(row.get("開始結帳次數")) if "開始結帳次數" in row.index else 0
    lpv = _to_int(row.get("連結頁面瀏覽次數")) if "連結頁面瀏覽次數" in row.index else 0

    return {
        "platform": "meta",
        "level": spec.level,
        "id": record_id,
        "name": name,
        "time_range": time_range,
        "currency": "TWD",
        "metrics": {
            "spend": round(float(spend), 6),
            "impressions": int(impressions),
            "clicks": int(clicks),
            "conversions": {
                "truth": {"count": int(truth_count), "value": round(float(truth_value), 6)},
                "platform": {
                    "count": int(platform_count),
                    "value": round(float(platform_value), 6),
                },
            },
            "funnel": {"atc": int(atc), "ic": int(ic), "lpv": int(lpv)},
        },
        "source": {
            "kind": f"meta_{spec.level}_csv",
            "row_index": int(row_index),
            "raw_id": raw_id or None,
            "account_name": _get_str(row, "帳號名稱") or None,
            "campaign_name": _get_str(row, "行銷活動名稱") or None,
            "adset_name": _get_str(row, "廣告組合名稱") or None,
        },
    }


def adapt_meta_csv(path: Path, *, spec: MetaCsvSpec) -> dict[str, Any]:
    df = _clean_cols(_read_csv(path))
    df, _ = _drop_total_rows(df, spec.name_col)

    base_time_range = _extract_time_range(df)
    out: list[dict[str, Any]] = []
    for i, row in df.iterrows():
        name = _get_str(row, spec.name_col)
        if name == "":
            continue
        tr = _row_time_range(row, base_time_range)
        out.append(_build_record(spec=spec, row=row, row_index=int(i), time_range=tr))

    return {
        "version": "unified_ad_data.v1",
        "source": f"meta_{spec.level}_csv",
        "timezone": "Asia/Taipei",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "data": out,
    }


def adapt_meta_adset_csv(path: Path) -> dict[str, Any]:
    return adapt_meta_csv(path, spec=META_ADSET_SPEC)


def adapt_meta_ad_csv(path: Path) -> dict[str, Any]:
    return adapt_meta_csv(path, spec=META_AD_SPEC)


def adapt_meta_adset_and_ad_csv(*, adset_csv: Path | None, ad_csv: Path | None) -> dict[str, Any]:
    chunks: list[dict[str, Any]] = []
    if adset_csv:
        chunks.append(adapt_meta_adset_csv(adset_csv))
    if ad_csv:
        chunks.append(adapt_meta_ad_csv(ad_csv))

    merged: list[dict[str, Any]] = []
    for c in chunks:
        merged.extend(c.get("data", []))

    return {
        "version": "unified_ad_data.v1",
        "source": "meta_csv",
        "timezone": "Asia/Taipei",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "data": merged,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Meta CSV -> Unified Ad Data")
    p.add_argument("--adset", type=Path, help="Meta Adset CSV 檔案路徑")
    p.add_argument("--ad", type=Path, help="Meta Ad CSV 檔案路徑")
    p.add_argument("--out", type=Path, required=True, help="輸出 unified JSON 檔案路徑")
    p.add_argument(
        "--validate", action="store_true", help="輸出後用 schemas/unified_ad_data.json 驗證"
    )
    args = p.parse_args(argv)

    payload = adapt_meta_adset_and_ad_csv(adset_csv=args.adset, ad_csv=args.ad)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.validate:
        from scripts.validator import validate_file

        validate_file(payload, schema_filename="unified_ad_data.json", label="unified_ad_data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
