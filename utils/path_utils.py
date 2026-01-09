"""
檔案用途：路徑管理工具
職責：
  - Week 相關路徑生成
  - Version 目錄管理
  - Latest 指標讀寫
  - Week info 寫入
"""

from pathlib import Path
from typing import Optional
from datetime import datetime


def now_iso() -> str:
    """
    產生當前時間的 ISO 格式字串（台北時間）
    注意：需要從 core.config 取得 TAIPEI_TZ
    """
    try:
        from zoneinfo import ZoneInfo
        taipei_tz = ZoneInfo("Asia/Taipei")
        return datetime.now(taipei_tz).isoformat(timespec="seconds")
    except Exception:
        return datetime.now().isoformat(timespec="seconds")


def week_meta_dir(week_id: str, history_root: Path) -> Path:
    """取得 week 的 meta 目錄路徑"""
    return history_root / week_id / "meta"


def versions_root(week_id: str, history_root: Path) -> Path:
    """取得 week 的 versions 根目錄"""
    return week_meta_dir(week_id, history_root) / "versions"


def version_dir(week_id: str, fp_code: str, history_root: Path) -> Path:
    """取得特定 fingerprint 的版本目錄"""
    return versions_root(week_id, history_root) / f"fp-{fp_code}"


def latest_ptr_path(week_id: str, history_root: Path) -> Path:
    """取得 latest.json 的路徑"""
    return week_meta_dir(week_id, history_root) / "latest.json"


def read_latest_ptr(week_id: str, history_root: Path) -> Optional[dict]:
    """讀取 latest.json"""
    from utils.file_io import read_json_if_exists
    return read_json_if_exists(latest_ptr_path(week_id, history_root))


def write_latest_ptr(week_id: str, fp_code: str, history_root: Path) -> None:
    """
    寫入 latest.json（使用相對路徑）
    避免搬環境時路徑失效
    """
    from utils.file_io import write_json

    rel = f"versions/fp-{fp_code}"
    write_json(
        latest_ptr_path(week_id, history_root),
        {
            "schema_version": "latest_ptr.v2",
            "updated_at": now_iso(),
            "week_id": week_id,
            "fp": fp_code,
            "rel_path": rel,
        },
    )


def write_week_info(week_id: str, date_range: str, history_root: Path) -> None:
    """寫入 week_info.json，確保保留或初始化 created_at"""
    from utils.file_io import read_json_if_exists, write_json

    path = week_meta_dir(week_id, history_root) / "week_info.json"
    existing = read_json_if_exists(path) or {}

    # 保留現有的 created_at，若無則用當前時間初始化
    created_at = existing.get("created_at") or existing.get("updated_at") or now_iso()

    write_json(
        path,
        {
            "schema_version": "week_info.v1",
            "created_at": created_at,
            "updated_at": now_iso(),
            "week_id": week_id,
            "date_range": date_range,
        },
    )


def ensure_week_meta_dirs(week_id: str, history_root: Path) -> None:
    """確保 week 的 meta 目錄結構存在"""
    week_meta_dir(week_id, history_root).mkdir(parents=True, exist_ok=True)
    versions_root(week_id, history_root).mkdir(parents=True, exist_ok=True)


def staging_version_dir(fp_code: str, history_root: Path) -> Path:
    """
    取得 staging 版本目錄（用於 Step B 執行前的錯誤記錄）
    結構：history/_staging/<timestamp>/meta/versions/fp-<code>
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return history_root / "_staging" / stamp / "meta" / "versions" / f"fp-{fp_code}"
