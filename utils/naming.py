"""
檔案用途：命名與檔名正規化工具
職責：
  - 產生可跨平台保存的安全檔名
  - 依素材類型與時間戳建立一致的素材命名規則
  - 從 Meta CSV 內容辨識日期範圍與 Week ID（報告命名）
  - （選用）加入內容雜湊，協助去重與追蹤
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from utils.week_utils import normalize_week_id


# =========================
# 報告自動命名 (Report Naming)
# =========================

def _normalize_date_str(s: str) -> Optional[str]:
    """
    將日期字串正規化為 YYYY-MM-DD 格式。
    支援 'YYYY-MM-DD', 'YYYY/MM/DD', 含時間的格式。
    """
    if not isinstance(s, str):
        s = str(s)
    s = s.strip().replace("/", "-")[:10]
    if not s or s.lower() in ("nan", "none", ""):
        return None
    try:
        datetime.fromisoformat(s)
        return s
    except Exception:
        return None


def extract_date_range_from_csv(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """
    從 Meta CSV 的「分析報告開始/結束」欄位辨識日期範圍。

    改進：掃描整欄找第一個有效日期（避免首列為空或異常）。

    回傳:
        (start_date, end_date) 格式 YYYY-MM-DD，若無法解析則為 None
    """
    start_col = "分析報告開始"
    end_col = "分析報告結束"

    if start_col not in df.columns or end_col not in df.columns:
        return None, None

    if len(df) == 0:
        return None, None

    def _find_first_valid(col_name: str) -> Optional[str]:
        for val in df[col_name]:
            parsed = _normalize_date_str(str(val))
            if parsed:
                return parsed
        return None

    return _find_first_valid(start_col), _find_first_valid(end_col)


def infer_week_id_from_date(date_str: str) -> Optional[str]:
    """
    從日期字串推算 ISO Week ID (YYYY-Www)。

    改進：先正規化日期格式，支援 YYYY/MM/DD。

    範例: '2025/12/04' -> '2025-W49'
    """
    normalized = _normalize_date_str(date_str)
    if not normalized:
        return None
    try:
        dt = datetime.fromisoformat(normalized)
        y, w, _ = dt.isocalendar()
        return f"{y}-W{w:02d}"
    except Exception:
        return None


def generate_report_filename(
    week_id: str,
    report_type: str = "meta",
    suffix: str = ".json",
) -> str:
    """
    產生標準化報告檔名。

    改進：強制 suffix 以 '.' 開頭並進行基本清理。

    範例: generate_report_filename("2025-W49", "meta", "json")
          -> "2025-W49_meta_report_summary.json"
    """
    normalized = normalize_week_id(week_id) or week_id
    safe_type = re.sub(r"[^a-zA-Z0-9_]", "_", report_type.lower())

    # 保護 suffix 格式
    if suffix and not suffix.startswith("."):
        suffix = f".{suffix}"
    suffix = re.sub(r"[^a-zA-Z0-9.]", "", suffix or ".json")

    return f"{normalized}_{safe_type}_report_summary{suffix}"



# =========================
# 素材命名 (Media Naming)
# =========================



# Windows 不允許的檔名字元：<>:"/\|?*，同時避免控制字元
_INVALID_FILENAME_CHARS_RE = re.compile(r'[<>:"/\\\\|?*\\x00-\\x1F]')
_WHITESPACE_RE = re.compile(r"\\s+")
_DOTS_RE = re.compile(r"\\.+")


@dataclass(frozen=True)
class MediaNamingResult:
    """素材命名結果（保留可追溯資訊，方便上傳與回寫 manifest）。"""

    original_name: str
    material_type: str
    timestamp: str
    sha256_8: Optional[str]
    filename: str


def _now_taipei() -> datetime:
    """
    取得台北時間的當前時間。
    注意：避免在此層強依賴 core.config（其 import 可能觸發其他初始化），因此採用 zoneinfo 自行處理。
    """
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Taipei"))
    except Exception:
        return datetime.now()


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """將時間轉成檔名友善的時間戳（YYYYMMDD_HHMMSS）。"""
    dt = dt or _now_taipei()
    return dt.strftime("%Y%m%d_%H%M%S")


def sanitize_filename(name: str, *, max_length: int = 160) -> str:
    """
    將檔名正規化為「安全檔名」：
    - 移除路徑分隔符與 Windows 不允許字元
    - 連續空白轉為單一底線
    - 避免前後句點/空白（Windows 會出問題）
    - 控制長度，避免雲端與檔案系統限制
    """
    if not isinstance(name, str):
        name = str(name)

    name = name.strip()
    name = _INVALID_FILENAME_CHARS_RE.sub("_", name)
    name = _WHITESPACE_RE.sub("_", name)

    # 避免連續句點造成隱藏副檔名/路徑混淆
    name = _DOTS_RE.sub(".", name)

    # Windows：檔名不可用句點或空白結尾
    name = name.strip(" .")

    if not name:
        name = "unnamed"

    if len(name) > max_length:
        # 盡量保留副檔名
        p = Path(name)
        stem = p.stem[: max(1, max_length - len(p.suffix) - 1)]
        name = f"{stem}{p.suffix}"

    return name


def infer_material_type(path: Path) -> str:
    """依副檔名推斷素材類型（IMG/VID/ASSET）。"""
    suf = path.suffix.lower()
    if suf in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return "IMG"
    if suf in {".mp4", ".mov"}:
        return "VID"
    return "ASSET"


def compute_sha256_8_from_file(path: Path) -> str:
    """計算檔案內容 SHA256（前 8 碼），用於去重與追蹤。"""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()[:8]


def build_media_filename(
    *,
    original_name: str,
    material_type: str,
    timestamp: Optional[str] = None,
    sha256_8: Optional[str] = None,
    suffix: Optional[str] = None,
) -> MediaNamingResult:
    """
    建立一致的素材檔名：
      <TYPE>_<YYYYMMDD_HHMMSS>_<SHA8>.<ext>

    - TYPE：IMG/VID/ASSET（或自訂字串，會自動正規化）
    - SHA8：可選；若未提供則省略該段
    """
    original_name = sanitize_filename(original_name)
    material_type = sanitize_filename(material_type.upper(), max_length=24)
    timestamp = timestamp or format_timestamp()

    if suffix is None:
        suffix = Path(original_name).suffix
    if suffix and not suffix.startswith("."):
        suffix = f".{suffix}"

    parts = [material_type, timestamp]
    if sha256_8:
        parts.append(sha256_8)
    filename = sanitize_filename("_".join(parts) + (suffix or ""))

    return MediaNamingResult(
        original_name=original_name,
        material_type=material_type,
        timestamp=timestamp,
        sha256_8=sha256_8,
        filename=filename,
    )

