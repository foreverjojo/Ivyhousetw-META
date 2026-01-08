"""
檔案用途：檔案 I/O 工具函式
職責：
  - JSON 檔案讀寫
  - 文字檔案讀寫
  - CSV 讀取
  - DataFrame 預覽
"""

import json
from pathlib import Path
from typing import Optional
import io

import pandas as pd


def read_json_if_exists(p: Path) -> Optional[dict]:
    """讀取 JSON 檔案，若不存在則回傳 None"""
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def write_json(p: Path, obj: dict) -> None:
    """寫入 JSON 檔案，自動建立父目錄"""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def read_text_if_exists(p: Path) -> Optional[str]:
    """讀取文字檔案，若不存在則回傳 None"""
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None


def write_text(p: Path, s: str) -> None:
    """寫入文字檔案，自動建立父目錄"""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def read_csv(uploaded_file) -> pd.DataFrame:
    """
    讀取 CSV 檔案，自動偵測編碼
    支援：utf-8-sig, utf-8, cp950, big5
    """
    raw = uploaded_file.getvalue()
    for enc in ["utf-8-sig", "utf-8", "cp950", "big5"]:
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=enc)
        except Exception:
            continue
    return pd.read_csv(io.BytesIO(raw))
