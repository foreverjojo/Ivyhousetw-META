"""
檔案用途：Google Drive 週備份 Retention（保留）管理器
職責：
  - 掃描 Drive 上 weekly_backups/ 之下的「週資料夾」
  - 依照 YYYY-Www 格式解析與排序，只保留最近 KEEP_WEEKS 週（預設 12）
  - 預設 dry-run：列出將被移到 Trash 的週資料夾清單
  - 需要 --apply 且 --confirm TRASH_OLDER_THAN_12_WEEKS 才會真正執行
  - 只移到 Trash（trashed=true），絕不永久刪除
  - 只處理本任務建立的 weekly_backups/ 之下的資料夾，不觸碰其他路徑
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

import requests

from core.cloud_config import load_cloud_config
from scripts.media_uploader import get_gdrive_access_token

# ===========================
# 常數
# ===========================

# Drive 備份根資料夾名稱（與 gdrive_weekly_backup.py 一致）
_DRIVE_BACKUP_ROOT = "weekly_backups"

# 週次 ID 正則（YYYY-Www 格式）
_WEEK_RE = re.compile(r"^(?P<y>\d{4})-W(?P<w>\d{2})$")

# Retention 的預設保留週數
DEFAULT_KEEP_WEEKS = 12

# 執行 Retention 需要的確認字串（防誤刪）
CONFIRM_STRING = "TRASH_OLDER_THAN_12_WEEKS"


# ===========================
# 週次解析輔助
# ===========================


def parse_week_folder_name(name: str) -> tuple[int, int] | None:
    """
    解析資料夾名稱是否符合 YYYY-Www 格式。
    回傳 (year, week) tuple；無法解析回傳 None。
    """
    m = _WEEK_RE.match(name.strip())
    if not m:
        return None
    return (int(m.group("y")), int(m.group("w")))


def sort_week_folders(
    week_entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    依照週次時間順序排序（舊 -> 新）。
    無法解析的資料夾排到最後（不刪）。
    """

    def sort_key(entry: dict[str, Any]) -> tuple[int, int, int, int]:
        parsed = parse_week_folder_name(entry.get("name", ""))
        if parsed is None:
            return (9999, 99, 0, 0)  # 無法解析的排到最後
        return (parsed[0], parsed[1], 0, 0)

    return sorted(week_entries, key=sort_key)


def compute_weeks_to_trash(
    sorted_entries: list[dict[str, Any]],
    keep_weeks: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    計算哪些週資料夾需要移到 Trash（保留最近 keep_weeks 週）。

    規則：
    - 只針對可解析的週資料夾（YYYY-Www）
    - 無法解析的資料夾：不刪除（預設保留）
    - 最新的 keep_weeks 個可解析週資料夾：保留
    - 超出的舊週資料夾：移到 Trash

    回傳：(to_trash_list, to_keep_list)
    """
    parseable = [e for e in sorted_entries if parse_week_folder_name(e.get("name", "")) is not None]
    unparseable = [e for e in sorted_entries if parse_week_folder_name(e.get("name", "")) is None]

    # 依時間排序後，保留最後 keep_weeks 個（最新的）
    parseable_sorted = sort_week_folders(parseable)
    if len(parseable_sorted) <= keep_weeks:
        to_trash: list[dict[str, Any]] = []
        to_keep = parseable_sorted + unparseable
    else:
        to_trash = parseable_sorted[:-keep_weeks]
        to_keep = parseable_sorted[-keep_weeks:] + unparseable

    return to_trash, to_keep


# ===========================
# Drive API 呼叫
# ===========================


def _list_drive_children(
    token: str,
    parent_id: str,
    timeout: int = 60,
) -> list[dict[str, Any]]:
    """
    列出 Drive 資料夾下的直接子項目（資料夾，非 trashed）
    回傳每個項目的 {id, name} dict。
    """
    items: list[dict[str, Any]] = []
    query = (
        f"'{parent_id}' in parents"
        " and mimeType='application/vnd.google-apps.folder'"
        " and trashed=false"
    )
    page_token: str | None = None

    while True:
        params: dict[str, str] = {
            "q": query,
            "fields": "nextPageToken, files(id, name)",
            "pageSize": "100",
        }
        if page_token:
            params["pageToken"] = page_token

        headers = {"Authorization": f"Bearer {token}"}
        url = "https://www.googleapis.com/drive/v3/files"
        resp = requests.get(url, headers=headers, params=params, timeout=timeout)

        if resp.status_code != 200:
            raise RuntimeError(f"Drive 列舉資料夾失敗（{resp.status_code}）：{resp.text[:300]}")

        data = resp.json()
        items.extend(data.get("files", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return items


def _find_folder_by_name(
    token: str,
    folder_name: str,
    parent_id: str,
    timeout: int = 60,
) -> str | None:
    """
    在 parent_id 資料夾下尋找名稱為 folder_name 的子資料夾。
    找到回傳 ID，找不到回傳 None。
    """
    safe_name = folder_name.replace("'", "\\'")
    query = (
        f"name='{safe_name}'"
        " and mimeType='application/vnd.google-apps.folder'"
        " and trashed=false"
        f" and '{parent_id}' in parents"
    )
    url = f"https://www.googleapis.com/drive/v3/files?q={requests.utils.quote(query)}&fields=files(id,name)"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, timeout=timeout)
    if resp.status_code == 200:
        files = resp.json().get("files", [])
        if files:
            return files[0]["id"]
    return None


def _trash_folder(token: str, folder_id: str, timeout: int = 60) -> dict[str, Any]:
    """
    將 Drive 資料夾移到 Trash（trashed=true）。
    不做永久刪除（不呼叫 DELETE）。
    回傳 API 回應 dict。
    """
    url = f"https://www.googleapis.com/drive/v3/files/{folder_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"trashed": True}
    resp = requests.patch(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"移入 Trash 失敗（{resp.status_code}）：{resp.text[:300]}")
    return resp.json()


# ===========================
# 主要公開 API
# ===========================


def run_retention(
    *,
    keep_weeks: int = DEFAULT_KEEP_WEEKS,
    apply: bool = False,
    confirm: str = "",
) -> dict[str, Any]:
    """
    執行 Drive 端 Retention（只對 weekly_backups/ 之下的週資料夾）。

    參數：
        keep_weeks: 保留最近幾週（預設 12）
        apply: True 才會真正移到 Trash
        confirm: 必須傳入固定字串 TRASH_OLDER_THAN_12_WEEKS 才允許執行

    回傳：
        retention_report dict（含 to_trash、to_keep 清單）
    """
    cfg = load_cloud_config()
    root_folder_id = cfg.google_drive_folder_id
    if not root_folder_id:
        raise RuntimeError("缺少 GOOGLE_DRIVE_FOLDER_ID，無法執行 Retention。")

    token = get_gdrive_access_token(cfg)

    # 尋找 weekly_backups/ 資料夾
    backup_root_id = _find_folder_by_name(
        token, _DRIVE_BACKUP_ROOT, root_folder_id, cfg.http_timeout_s
    )
    if not backup_root_id:
        return {
            "status": "skipped",
            "reason": f"Drive 上找不到 '{_DRIVE_BACKUP_ROOT}' 資料夾，可能尚未備份過。",
            "keep_weeks": keep_weeks,
            "to_trash": [],
            "to_keep": [],
            "executed": False,
        }

    # 列出週資料夾
    week_entries = _list_drive_children(token, backup_root_id, cfg.http_timeout_s)

    # 計算保留/刪除清單
    sorted_entries = sort_week_folders(week_entries)
    to_trash, to_keep = compute_weeks_to_trash(sorted_entries, keep_weeks)

    # 組裝報告（dry-run 結果）
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    report: dict[str, Any] = {
        "schema_version": "gdrive_retention.v1",
        "timestamp": timestamp,
        "keep_weeks": keep_weeks,
        "backup_root_folder_id": backup_root_id,
        "total_week_folders": len(week_entries),
        "to_trash_count": len(to_trash),
        "to_keep_count": len(to_keep),
        "to_trash": [{"id": e["id"], "name": e["name"]} for e in to_trash],
        "to_keep": [{"id": e["id"], "name": e["name"]} for e in to_keep],
        "executed": False,
        "execution_results": [],
    }

    if not apply:
        report["mode"] = "dry_run"
        report["note"] = (
            f"Dry-run 模式：以上 {len(to_trash)} 個週資料夾將被移到 Trash。"
            f" 若要執行，請加上 --apply --confirm {CONFIRM_STRING}"
        )
        return report

    # === apply 模式 ===
    if confirm != CONFIRM_STRING:
        report["mode"] = "apply_rejected"
        report["note"] = f"--confirm 字串不符（需要：{CONFIRM_STRING}），已拒絕執行。"
        return report

    # 二次確認通過，實際執行
    execution_results: list[dict[str, Any]] = []
    for entry in to_trash:
        folder_id = entry["id"]
        folder_name = entry["name"]
        try:
            _trash_folder(token, folder_id, cfg.http_timeout_s)
            execution_results.append(
                {
                    "id": folder_id,
                    "name": folder_name,
                    "status": "trashed",
                }
            )
        except Exception as exc:
            execution_results.append(
                {
                    "id": folder_id,
                    "name": folder_name,
                    "status": "error",
                    "error": str(exc)[:300],
                }
            )

    trashed_ok = sum(1 for r in execution_results if r["status"] == "trashed")
    trashed_err = sum(1 for r in execution_results if r["status"] == "error")

    report["mode"] = "apply"
    report["executed"] = True
    report["execution_results"] = execution_results
    report["trashed_ok"] = trashed_ok
    report["trashed_error"] = trashed_err
    report["note"] = (
        f"執行完成：{trashed_ok} 個週資料夾已移到 Trash，{trashed_err} 個失敗。"
        " 可至 Google Drive > 垃圾桶 還原。"
    )

    return report


# ===========================
# CLI 入口
# ===========================


def main() -> None:
    """
    CLI 入口。

    使用範例：
      # Dry-run（只列出，不執行）
      python -m scripts.gdrive_retention

      # 執行（需要 --apply 且 --confirm 固定字串）
      python -m scripts.gdrive_retention --apply --confirm TRASH_OLDER_THAN_12_WEEKS

      # 自訂保留週數
      python -m scripts.gdrive_retention --keep-weeks 8
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Google Drive 週備份 Retention 管理器\n"
        "預設只做 dry-run，需要 --apply --confirm 才會實際移到 Trash。\n"
        "只針對 weekly_backups/ 之下的週資料夾，不觸碰其他路徑。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--keep-weeks",
        type=int,
        default=DEFAULT_KEEP_WEEKS,
        help=f"保留最近幾週（預設 {DEFAULT_KEEP_WEEKS}）",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="實際執行（移到 Trash）；預設只 dry-run",
    )
    parser.add_argument(
        "--confirm",
        default="",
        help=f"二次確認字串（需傳入：{CONFIRM_STRING}）",
    )
    args = parser.parse_args()

    try:
        report = run_retention(
            keep_weeks=args.keep_weeks,
            apply=args.apply,
            confirm=args.confirm,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"[ERROR] Retention 執行失敗：{exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
