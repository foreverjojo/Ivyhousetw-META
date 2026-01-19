"""
檔案用途：雜湊與指紋碼計算工具
職責：
  - SHA256 雜湊計算
  - 檔案指紋碼生成
  - 輸入資料指紋碼計算
"""

import hashlib
from typing import Any


def sha256_bytes(b: bytes) -> str:
    """計算 bytes 的 SHA256 雜湊值"""
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def sha256_str(s: str) -> str:
    """計算字串的 SHA256 雜湊值"""
    return sha256_bytes(s.encode("utf-8"))


def compute_file_fp(uploaded_file) -> dict:
    """計算上傳檔案的指紋碼"""
    b = uploaded_file.getvalue()
    return {"sha256": sha256_bytes(b), "size": len(b)}


def compute_inputs_fingerprint(
    meta_adset_file, meta_ads_file, web_excel_file, detail_level: str
) -> dict:
    """
    計算輸入檔案的整體指紋碼
    包含：3個檔案的 sha256、size，以及 detail_level
    """
    return {
        "meta_adset": compute_file_fp(meta_adset_file),
        "meta_ads": compute_file_fp(meta_ads_file),
        "web_excel": compute_file_fp(web_excel_file),
        "detail_level": detail_level,
    }


def fingerprint_key_for_version(current_fp: dict) -> str:
    """
    從 fingerprint dict 產生版本用的 key（deterministic）
    只取 sha256 + size + detail_level，不含 generated_at
    """

    def fget(k: str) -> Any:
        return current_fp.get(k, {})

    parts = [
        fget("meta_adset").get("sha256", ""),
        str(fget("meta_adset").get("size", 0)),
        fget("meta_ads").get("sha256", ""),
        str(fget("meta_ads").get("size", 0)),
        fget("web_excel").get("sha256", ""),
        str(fget("web_excel").get("size", 0)),
        current_fp.get("detail_level", "default"),
    ]
    combined = "|".join(parts)
    return sha256_str(combined)


def fp_short(current_fp: dict) -> str:
    """取得指紋碼的短版本（前8碼）"""
    return fingerprint_key_for_version(current_fp)[:8]
