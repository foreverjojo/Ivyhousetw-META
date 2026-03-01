"""
檔案用途：Google Drive 週備份上傳器
職責：
  - 將指定版本資料夾（vdir）的白名單產物上傳至 Google Drive
  - 在 Drive 建立 weekly_backups/<week_id>/<fp>/ 資料夾結構
  - 寫入本機備份 manifest（backup_manifest.gdrive.json），不含任何敏感資訊
  - 失敗不中斷主流程（呼叫方需自行包 try/except）
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from core.cloud_config import CloudConfig, load_cloud_config
from scripts.media_uploader import ensure_gdrive_folder, get_gdrive_access_token

# ===========================
# 常數設定
# ===========================

# 備份白名單（相對於 vdir 的路徑，支援 glob）
_BACKUP_WHITELIST_FILES = [
    "meeting.md",
    "workflow_state.json",
    "report_summary.json",
    "report_insights.json",
    "consultant_notes.json",
    "pipeline_state.json",
    "inputs.json",
]

# Drive 備份根資料夾名稱（在 GOOGLE_DRIVE_FOLDER_ID 之下）
_DRIVE_BACKUP_ROOT = "weekly_backups"


# ===========================
# 內部輔助函式
# ===========================


def _sha256_8_bytes(data: bytes) -> str:
    """計算 bytes 的 SHA256 前 8 碼"""
    return hashlib.sha256(data).hexdigest()[:8]


def _sha256_8_file(path: Path) -> str:
    """計算檔案的 SHA256 前 8 碼"""
    return _sha256_8_bytes(path.read_bytes())


def _now_utc_iso() -> str:
    """回傳目前 UTC 時間的 ISO 字串（以 Z 結尾）"""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _collect_whitelist_files(vdir: Path) -> list[Path]:
    """
    從 vdir 收集白名單產物（靜態檔名 + inputs/raw/ 之下所有檔案）
    回傳：存在的 Path 列表
    """
    collected: list[Path] = []

    # 靜態白名單檔案
    for fname in _BACKUP_WHITELIST_FILES:
        p = vdir / fname
        if p.exists() and p.is_file():
            collected.append(p)

    # inputs/raw/ 之下的所有檔案（子目錄遞迴）
    raw_dir = vdir / "inputs" / "raw"
    if raw_dir.exists() and raw_dir.is_dir():
        for p in sorted(raw_dir.rglob("*")):
            if p.is_file():
                collected.append(p)

    return collected


def _drive_upload_bytes(
    *,
    token: str,
    folder_id: str,
    data: bytes,
    filename: str,
    timeout: int = 120,
) -> dict[str, Any]:
    """將 bytes 直接上傳至 Google Drive 指定資料夾"""
    metadata: dict[str, Any] = {"name": filename, "parents": [folder_id]}
    url = (
        "https://www.googleapis.com/upload/drive/v3/files"
        "?uploadType=multipart"
        "&supportsAllDrives=true"
        "&fields=id,name,webViewLink"
    )
    headers = {"Authorization": f"Bearer {token}"}
    files = {
        "metadata": (
            "metadata",
            json.dumps(metadata, ensure_ascii=False),
            "application/json; charset=utf-8",
        ),
        "file": (filename, data, "application/octet-stream"),
    }
    resp = requests.post(url, headers=headers, files=files, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"Drive 上傳失敗（{resp.status_code}）：{resp.text[:300]}")
    return resp.json()


def _ensure_drive_backup_path(
    token: str,
    root_folder_id: str,
    week_id: str,
    fp_code: str,
    timeout: int,
) -> str:
    """
    確保 Drive 上 weekly_backups/<week_id>/<fp_code>/ 路徑存在
    回傳：fp_code 資料夾的 Drive ID
    """
    backup_root_id = ensure_gdrive_folder(
        token, _DRIVE_BACKUP_ROOT, parent_id=root_folder_id, timeout=timeout
    )
    week_folder_id = ensure_gdrive_folder(token, week_id, parent_id=backup_root_id, timeout=timeout)
    fp_folder_id = ensure_gdrive_folder(token, fp_code, parent_id=week_folder_id, timeout=timeout)
    return fp_folder_id


def _ensure_drive_subfolder(
    token: str,
    parent_id: str,
    subfolder_name: str,
    timeout: int,
) -> str:
    """確保 Drive 上的子資料夾存在，回傳 ID"""
    return ensure_gdrive_folder(token, subfolder_name, parent_id=parent_id, timeout=timeout)


# ===========================
# 主要公開 API
# ===========================


def upload_version_to_drive(
    *,
    week_id: str,
    vdir: Path,
    fp_code: str,
    cfg: CloudConfig | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    將 vdir（版本資料夾）的白名單產物備份到 Google Drive。

    參數：
        week_id: 週次 ID（例如 2026-W08）
        vdir: 版本資料夾路徑（history/<week_id>/meta/versions/fp-<code>）
        fp_code: fingerprint 短碼（8 碼）
        cfg: CloudConfig（預設從環境變數載入）
        dry_run: True 時僅列出計畫，不實際上傳

    回傳：
        manifest dict（含 entries 與整體統計）
    """
    cfg = cfg or load_cloud_config()
    timestamp = _now_utc_iso()

    def _is_sa_quota_error(exc: Exception) -> bool:
        msg = str(exc)
        return "Service Accounts do not have storage quota" in msg

    # 收集待備份檔案
    files_to_upload = _collect_whitelist_files(vdir)

    if dry_run:
        entries = []
        for p in files_to_upload:
            rel = str(p.relative_to(vdir))
            entries.append(
                {
                    "timestamp": timestamp,
                    "local_rel_path": rel,
                    "sha256_8": _sha256_8_file(p),
                    "size": p.stat().st_size,
                    "status": "dry_run",
                    "remote_id": None,
                    "remote_url": None,
                }
            )
        manifest = _build_manifest(
            timestamp=timestamp,
            week_id=week_id,
            fp_code=fp_code,
            entries=entries,
            dry_run=True,
        )
        _write_manifest(vdir, manifest)
        return manifest

    # === 實際上傳模式 ===
    try:
        token = get_gdrive_access_token(cfg)
        root_folder_id = cfg.google_drive_folder_id
        if not root_folder_id:
            raise RuntimeError("缺少 GOOGLE_DRIVE_FOLDER_ID，無法備份至 Drive。")

        # 確保 Drive 資料夾結構存在
        fp_folder_id = _ensure_drive_backup_path(
            token, root_folder_id, week_id, fp_code, cfg.http_timeout_s
        )
    except Exception as exc:

        def _sa_email_from_json(path: str) -> str | None:
            try:
                p = Path(path)
                data = json.loads(p.read_text(encoding="utf-8"))
                email = data.get("client_email")
                return str(email).strip() if isinstance(email, str) and email.strip() else None
            except Exception:
                return None

        msg = str(exc)
        hints: list[str] = []
        # 404 notFound on parent folder almost always means the folder isn't visible
        # (not shared to the credential) or the folder_id is wrong.
        if "File not found:" in msg:
            if cfg.google_application_credentials:
                sa_email = _sa_email_from_json(cfg.google_application_credentials)
                if sa_email:
                    hints.append(
                        f"請確認 GOOGLE_DRIVE_FOLDER_ID 已分享給 Service Account：{sa_email}"
                    )
                    hints.append("若目標在 Shared Drive，請確認 SA 已加入該 Shared Drive 成員")
            hints.append("也請確認 GOOGLE_DRIVE_FOLDER_ID 正確且未被刪除")

        # 401 on token-based path usually indicates an expired/invalid access token.
        if "Invalid Credentials" in msg or "invalid authentication" in msg.lower():
            hints.append(
                "若使用 GOOGLE_DRIVE_ACCESS_TOKEN，請更新為有效的 OAuth access token（短效，過期需刷新）"
            )

        if "Service Accounts do not have storage quota" in msg:
            hints.append(
                "此錯誤代表 Service Account 在 My Drive 無配額：請改用 OAuth token 或把備份根資料夾放在 Shared Drive"
            )

        error_text = msg
        if hints:
            # 把 hints 放前面，避免 300 字截斷後看不到可行動資訊。
            error_text = "；".join(hints) + " | " + msg

        # 重要：即使初始化失敗（例如 parent folder 權限/不存在），也要落盤一份 manifest
        # 讓 UI/使用者可以在不看 console log 的情況下回溯原因。
        entries: list[dict[str, Any]] = []
        for p in files_to_upload:
            rel = str(p.relative_to(vdir))
            try:
                sha8 = _sha256_8_file(p)
                size = p.stat().st_size
            except Exception:
                sha8 = None
                size = None
            entries.append(
                {
                    "timestamp": timestamp,
                    "local_rel_path": rel,
                    "sha256_8": sha8,
                    "size": size,
                    "status": "error",
                    "remote_id": None,
                    "remote_url": None,
                    "error": error_text[:300],
                }
            )

        manifest = _build_manifest(
            timestamp=timestamp,
            week_id=week_id,
            fp_code=fp_code,
            entries=entries,
            dry_run=False,
        )
        _write_manifest(vdir, manifest)
        raise

    # 建立 inputs/raw/ 對應的 Drive 子資料夾 cache
    subfolder_cache: dict[str, str] = {}
    oauth_fallback_enabled = False
    oauth_fallback_attempted = False

    def _get_or_create_subfolder(rel_parts: tuple[str, ...]) -> str:
        """遞迴確保子資料夾存在，回傳最終 folder ID"""
        if not rel_parts:
            return fp_folder_id
        key = "/".join(rel_parts)
        if key in subfolder_cache:
            return subfolder_cache[key]
        # 從根往下逐層建立
        parent_id = fp_folder_id
        for i, part in enumerate(rel_parts):
            partial_key = "/".join(rel_parts[: i + 1])
            if partial_key not in subfolder_cache:
                fid = _ensure_drive_subfolder(token, parent_id, part, cfg.http_timeout_s)
                subfolder_cache[partial_key] = fid
            parent_id = subfolder_cache[partial_key]
        subfolder_cache[key] = parent_id
        return parent_id

    entries: list[dict[str, Any]] = []
    for p in files_to_upload:
        rel = str(p.relative_to(vdir))
        rel_path = Path(rel)
        sha8 = _sha256_8_file(p)
        size = p.stat().st_size

        try:
            # 決定上傳目標資料夾
            parts = rel_path.parts
            if len(parts) > 1:
                parent_parts = parts[:-1]
                target_folder_id = _get_or_create_subfolder(parent_parts)
            else:
                target_folder_id = fp_folder_id

            data = p.read_bytes()
            result = _drive_upload_bytes(
                token=token,
                folder_id=target_folder_id,
                data=data,
                filename=rel_path.name,
                timeout=cfg.http_timeout_s,
            )
            entries.append(
                {
                    "timestamp": timestamp,
                    "local_rel_path": rel,
                    "sha256_8": sha8,
                    "size": size,
                    "status": "uploaded",
                    "remote_id": result.get("id"),
                    "remote_url": result.get("webViewLink"),
                }
            )
        except Exception as exc:
            # 特例：SA 上傳被 Drive quota 規則擋下（403），自動切到 OAuth token 重試一次。
            if (
                (not oauth_fallback_enabled)
                and (not oauth_fallback_attempted)
                and _is_sa_quota_error(exc)
            ):
                oauth_fallback_attempted = True
                original_token = token
                try:
                    oauth_token = get_gdrive_access_token(cfg, auth_mode="oauth")
                    # 切換成功後才污染全域狀態。
                    # 重要：為避免同一次 run 產生兩套同名資料夾結構，這裡沿用既有 folder IDs
                    # （初始已成功 ensure 出 fp_folder_id），不要再用新 token 重新 ensure 一次。
                    token = oauth_token
                    oauth_fallback_enabled = True

                    # 重新計算 target folder（沿用既有 cache；若缺少會用 OAuth token 補建）
                    parts = rel_path.parts
                    if len(parts) > 1:
                        parent_parts = parts[:-1]
                        target_folder_id = _get_or_create_subfolder(parent_parts)
                    else:
                        target_folder_id = fp_folder_id

                    data = p.read_bytes()
                    result = _drive_upload_bytes(
                        token=token,
                        folder_id=target_folder_id,
                        data=data,
                        filename=rel_path.name,
                        timeout=cfg.http_timeout_s,
                    )
                    entries.append(
                        {
                            "timestamp": timestamp,
                            "local_rel_path": rel,
                            "sha256_8": sha8,
                            "size": size,
                            "status": "uploaded",
                            "remote_id": result.get("id"),
                            "remote_url": result.get("webViewLink"),
                        }
                    )
                    continue
                except Exception as oauth_exc:
                    token = original_token
                    err = str(oauth_exc)
                    if (
                        "invalid authentication credentials" in err.lower()
                        or "Invalid Credentials" in err
                    ):
                        err = (
                            "偵測到 Service Account 無配額（403）；已嘗試切換 OAuth token 但 token 無效/過期（401）。"
                            "請更新 GOOGLE_DRIVE_ACCESS_TOKEN（或確認 Secret Manager 的 GOOGLE_DRIVE_ACCESS_TOKEN 為最新且執行身分有讀取權限）"
                            f" | {oauth_exc}"
                        )
                    else:
                        err = (
                            "偵測到 Service Account 無配額（403）；已嘗試切換 OAuth token 仍失敗"
                            f"：{oauth_exc}"
                        )
                    entries.append(
                        {
                            "timestamp": timestamp,
                            "local_rel_path": rel,
                            "sha256_8": sha8,
                            "size": size,
                            "status": "error",
                            "remote_id": None,
                            "remote_url": None,
                            "error": err[:300],
                        }
                    )
                    continue

            entries.append(
                {
                    "timestamp": timestamp,
                    "local_rel_path": rel,
                    "sha256_8": sha8,
                    "size": size,
                    "status": "error",
                    "remote_id": None,
                    "remote_url": None,
                    "error": str(exc)[:300],
                }
            )

    manifest = _build_manifest(
        timestamp=timestamp,
        week_id=week_id,
        fp_code=fp_code,
        entries=entries,
        dry_run=False,
    )
    _write_manifest(vdir, manifest)
    return manifest


def _build_manifest(
    *,
    timestamp: str,
    week_id: str,
    fp_code: str,
    entries: list[dict[str, Any]],
    dry_run: bool,
) -> dict[str, Any]:
    """
    組裝 manifest dict。
    安全規則：不包含任何 token、SA JSON 路徑、環境變數內容。
    """
    uploaded = sum(1 for e in entries if e.get("status") == "uploaded")
    errors = sum(1 for e in entries if e.get("status") == "error")
    skipped = sum(1 for e in entries if e.get("status") == "dry_run")
    return {
        "schema_version": "backup_manifest.gdrive.v1",
        "timestamp": timestamp,
        "week_id": week_id,
        "fp_code": fp_code,
        "dry_run": dry_run,
        "total_files": len(entries),
        "uploaded": uploaded,
        "errors": errors,
        "skipped_dry_run": skipped,
        "entries": entries,
    }


def _write_manifest(vdir: Path, manifest: dict[str, Any]) -> None:
    """將 manifest 寫入 vdir/backup_manifest.gdrive.json"""
    out_path = vdir / "backup_manifest.gdrive.json"
    out_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ===========================
# CLI 入口
# ===========================


def main() -> None:
    """CLI 入口：可單獨呼叫上傳特定週次的版本資料夾"""
    import argparse

    from core import HISTORY_ROOT
    from core.env_loader import load_environment_variables
    from utils.path_utils import read_latest_ptr, version_dir

    parser = argparse.ArgumentParser(
        description="Google Drive 週備份上傳器\n"
        "用法：python -m scripts.gdrive_weekly_backup --week 2026-W08\n"
        "或：  python -m scripts.gdrive_weekly_backup --week 2026-W08 --fp <fp_code>"
    )
    parser.add_argument("--week", required=True, help="週次 ID，例如：2026-W08")
    parser.add_argument("--fp", default=None, help="fingerprint 短碼（預設讀取 latest.json）")
    parser.add_argument("--dry-run", action="store_true", help="乾跑模式：不實際上傳，只列出計畫")
    args = parser.parse_args()

    # 與 Streamlit 執行路徑一致：先載入 ifp.env/.env +（若有）Secret Manager。
    # 讓 CLI 測試不需要手動 export 一堆環境變數。
    try:
        load_environment_variables()
    except Exception as exc:
        print(f"[WARN] 環境變數載入失敗（仍會嘗試用目前環境繼續）：{exc}")

    week_id = args.week
    fp_code = args.fp

    # 若未指定 fp，嘗試從 latest.json 讀取
    if not fp_code:
        ptr = read_latest_ptr(week_id, HISTORY_ROOT)
        if not ptr or "fp" not in ptr:
            print(f"[ERROR] 找不到 {week_id} 的 latest.json，請明確指定 --fp 參數。")
            return
        fp_code = ptr["fp"]

    vdir = version_dir(week_id, fp_code, HISTORY_ROOT)
    if not vdir.exists():
        print(f"[ERROR] 版本資料夾不存在：{vdir}")
        return

    print(f"[INFO] 準備備份：week={week_id}  fp={fp_code}  dry_run={args.dry_run}")
    print(f"[INFO] vdir={vdir}")

    try:
        manifest = upload_version_to_drive(
            week_id=week_id,
            vdir=vdir,
            fp_code=fp_code,
            dry_run=args.dry_run,
        )
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"[ERROR] 備份失敗：{exc}")


if __name__ == "__main__":
    main()
