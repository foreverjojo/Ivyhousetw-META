"""
檔案用途：媒體素材與報表雲端上傳器（Stage 3 整合版）
職責：
  - 支援 Google Drive Service Account (JSON) 認證
  - 自動在雲端建立/維護子資料夾結構 (`reports/`, `assets/images/`, `assets/videos/`)
  - 掃描 `attached_assets/` 並執行命名、上傳、記錄
  - 上傳後寫入 upload_manifest.json 供回滾與追蹤
  - 雲端環境（GOOGLE_CLOUD_PROJECT）下優先從 Secret Manager 取最新 Access Token
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from core.cloud_config import CloudConfig, load_cloud_config
from core.config import MEDIA_ASSETS_DIR
from scripts.media_scanner import scan_media_assets
from utils.naming import build_media_filename, compute_sha256_8_from_file, infer_material_type

logger = logging.getLogger(__name__)

# Manifest 路徑
UPLOAD_MANIFEST_PATH = Path("upload_manifest.json")


@dataclass(frozen=True)
class UploadResult:
    """單一檔案的上傳結果。"""

    local_path: str
    upload_name: str
    provider: str
    status: str
    sha256_8: str | None = None
    size: int | None = None
    remote_id: str | None = None
    remote_url: str | None = None
    error: str | None = None


def get_gdrive_access_token(cfg: CloudConfig, *, auth_mode: str = "auto") -> str:
    """
    取得 Google Drive Access Token。

    auth_mode：
    - auto（預設）：維持原本流程（SA JSON 優先）。
    - oauth：忽略 SA JSON，強制走 OAuth Access Token 路徑（Secret Manager / env）。
    - service_account：強制要求 SA JSON；若缺少則 raise。

    優先序（auto）：
    1. SA JSON（google_application_credentials）：最穩定，維持原本流程。
    2. 雲端環境（GOOGLE_CLOUD_PROJECT 存在）且未使用 SA JSON：
       每次優先從 Secret Manager 取最新 access_token（確保 Idx-044 刷新的 token 立即生效）。
       若讀取失敗（含權限不足 403）：輸出可行動 warning，fallback 至環境變數 token。
    3. 環境變數 token（cfg.google_drive_access_token）：本機 / fallback 路徑。
    4. 若三者皆無：raise RuntimeError。

    資安要求：任何 log 絕不輸出 token 值。
    """
    mode = (auth_mode or "auto").strip().lower()
    if mode not in {"auto", "oauth", "service_account"}:
        raise ValueError(f"不支援的 Drive auth_mode：{auth_mode}")

    # 路徑 1：SA JSON（最穩定，不需 Secret Manager）
    if mode in {"auto", "service_account"} and cfg.google_application_credentials:
        scopes = ["https://www.googleapis.com/auth/drive.file"]
        creds = service_account.Credentials.from_service_account_file(
            cfg.google_application_credentials, scopes=scopes
        )
        creds.refresh(Request())
        return creds.token

    if mode == "service_account":
        raise RuntimeError("缺少 GOOGLE_APPLICATION_CREDENTIALS（指定 service_account 模式需要）。")

    def _extract_project_id_from_sa_json(path: str) -> str | None:
        try:
            p = Path(path)
            data = json.loads(p.read_text(encoding="utf-8"))
            pid = data.get("project_id")
            return str(pid).strip() if isinstance(pid, str) and pid.strip() else None
        except Exception:
            return None

    # 路徑 2：雲端/本機（只要有 project_id）→ 優先從 Secret Manager 取最新 token
    # 注意：本 repo 其他模組常用 GCP_PROJECT_ID，因此此處也一併支援，避免本機環境拿到過期 env token。
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT_ID")
    if (not project_id) and cfg.google_application_credentials:
        # 即使 auth_mode="oauth" 會忽略 SA JSON 作為認證方式，仍可借用 JSON 內的 project_id
        # 來定位 Secret Manager（不涉及使用 SA 做 API auth）。
        project_id = _extract_project_id_from_sa_json(cfg.google_application_credentials)
    if project_id:
        try:
            from google.cloud import secretmanager

            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{project_id}/secrets/GOOGLE_DRIVE_ACCESS_TOKEN/versions/latest"
            response = client.access_secret_version(request={"name": name})
            sm_token = response.payload.data.decode("utf-8").strip()
            if sm_token:
                logger.info("Drive 認證：已從 Secret Manager 取得最新 Access Token（不記錄 token）")
                return sm_token
            logger.warning(
                "Secret Manager 的 GOOGLE_DRIVE_ACCESS_TOKEN 為空，fallback 至環境變數。"
                " 請確認 secret 已有可用版本。"
            )
        except Exception as exc:
            logger.warning(
                "Secret Manager 讀取 GOOGLE_DRIVE_ACCESS_TOKEN 失敗（%s），fallback 至環境變數。"
                " 若為權限不足（403），請確認執行服務的 Service Account"
                " 已綁定 roles/secretmanager.secretAccessor。",
                type(exc).__name__,
            )

    # 路徑 3：環境變數 token（本機 / 雲端 fallback）
    if cfg.google_drive_access_token:
        return cfg.google_drive_access_token

    raise RuntimeError("缺少 Google Drive 認證方式 (需提供 SA JSON 或 Access Token)。")


def ensure_gdrive_folder(
    token: str, folder_name: str, parent_id: str | None = None, timeout: int = 60
) -> str:
    """在 Google Drive 確保資料夾存在，回傳其 ID。"""
    # 處理資料夾名稱中的單引號 (Drive API query 語法需跳脫)
    safe_name = folder_name.replace("'", "\\'")
    query = (
        f"name='{safe_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    if parent_id:
        query += f" and '{parent_id}' in parents"

    # Shared Drive 注意事項：
    # - 目標 parent_id 若在 Shared Drive，未帶 supportsAllDrives/includeItemsFromAllDrives
    #   可能會拿到 404 (File not found) 即使權限實際存在。
    url = (
        "https://www.googleapis.com/drive/v3/files"
        f"?q={requests.utils.quote(query)}"
        "&fields=files(id,name,createdTime)"
        "&supportsAllDrives=true"
        "&includeItemsFromAllDrives=true"
        "&corpora=allDrives"
        "&orderBy=createdTime"
    )
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(url, headers=headers, timeout=timeout)
    if resp.status_code == 200:
        files = resp.json().get("files", [])
        if files:
            if len(files) > 1:
                logger.warning(
                    "偵測到重複的 Drive 資料夾（name=%s, parent_id=%s）：%s 個，將使用最早建立者。",
                    folder_name,
                    parent_id,
                    len(files),
                )
            return files[0]["id"]

    # 不存在則建立
    print(f"📁 雲端資料夾 '{folder_name}' 不存在，正在建立...")
    create_url = "https://www.googleapis.com/drive/v3/files?supportsAllDrives=true"
    metadata = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        metadata["parents"] = [parent_id]

    resp = requests.post(create_url, headers=headers, json=metadata, timeout=timeout)
    if resp.status_code == 200:
        return resp.json()["id"]

    raise RuntimeError(f"無法建立雲端資料夾 '{folder_name}'：{resp.text}")


def get_target_folder_id_by_type(token: str, root_id: str, file_path: Path) -> str:
    """根據檔案類型決定目標子資料夾 ID。"""
    ext = file_path.suffix.lower()

    if ext in (".json", ".csv", ".xlsx"):
        return ensure_gdrive_folder(token, "reports", parent_id=root_id)

    if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        assets_id = ensure_gdrive_folder(token, "assets", parent_id=root_id)
        return ensure_gdrive_folder(token, "images", parent_id=assets_id)

    if ext in (".mp4", ".mov", ".avi"):
        assets_id = ensure_gdrive_folder(token, "assets", parent_id=root_id)
        return ensure_gdrive_folder(token, "videos", parent_id=assets_id)

    return root_id


def _drive_upload_file(
    *,
    token: str,
    target_folder_id: str | None,
    file_path: Path,
    upload_name: str,
    timeout: int = 120,
) -> dict[str, Any]:
    """執行檔案上傳至 Google Drive。"""
    metadata: dict[str, Any] = {"name": upload_name}
    if target_folder_id:
        metadata["parents"] = [target_folder_id]

    url = (
        "https://www.googleapis.com/upload/drive/v3/files"
        "?uploadType=multipart"
        "&supportsAllDrives=true"
        "&fields=id,name,webViewLink,webContentLink"
    )

    headers = {"Authorization": f"Bearer {token}"}

    with file_path.open("rb") as f:
        files = {
            "metadata": (
                "metadata",
                json.dumps(metadata, ensure_ascii=False),
                "application/json; charset=utf-8",
            ),
            "file": (upload_name, f, "application/octet-stream"),
        }
        resp = requests.post(url, headers=headers, files=files, timeout=timeout)

    if resp.status_code >= 400:
        raise RuntimeError(f"Google Drive 上傳失敗（{resp.status_code}）：{resp.text}")

    return resp.json()


def upload_media_assets(
    *,
    media_dir: Path | None = None,
    max_files: int | None = None,
    dry_run: bool = False,
    provider: str | None = None,
) -> dict[str, Any]:
    """主程序：掃描素材並上傳至雲端。"""
    media_dir = media_dir or MEDIA_ASSETS_DIR
    cfg = load_cloud_config()
    chosen_provider = (provider or cfg.provider or "none").strip().lower()

    scan = scan_media_assets(media_dir=media_dir, recursive=True)
    all_files: list[Path] = []
    all_files.extend(scan.images)
    all_files.extend(scan.videos)

    if max_files is not None:
        all_files = all_files[: max(0, int(max_files))]

    results: list[UploadResult] = []
    token = None

    if not dry_run and chosen_provider == "gdrive":
        token = get_gdrive_access_token(cfg)

    for p in all_files:
        try:
            size = p.stat().st_size
            sha8 = compute_sha256_8_from_file(p)
            material_type = infer_material_type(p)
            naming = build_media_filename(
                original_name=p.name,
                material_type=material_type,
                sha256_8=sha8,
                suffix=p.suffix,
            )
            upload_name = naming.filename

            if dry_run or chosen_provider == "none":
                results.append(
                    UploadResult(
                        local_path=str(p),
                        upload_name=upload_name,
                        provider=chosen_provider,
                        status="dry_run" if dry_run else "skipped",
                        sha256_8=sha8,
                        size=size,
                    )
                )
                continue

            if chosen_provider == "gdrive" and token:
                # 自動判斷子資料夾
                root_id = cfg.google_drive_folder_id
                target_id = get_target_folder_id_by_type(token, root_id, p) if root_id else None

                data = _drive_upload_file(
                    token=token,
                    target_folder_id=target_id,
                    file_path=p,
                    upload_name=upload_name,
                    timeout=cfg.http_timeout_s,
                )
                results.append(
                    UploadResult(
                        local_path=str(p),
                        upload_name=upload_name,
                        provider=chosen_provider,
                        status="uploaded",
                        sha256_8=sha8,
                        size=size,
                        remote_id=data.get("id"),
                        remote_url=data.get("webViewLink") or data.get("webContentLink"),
                    )
                )
                continue

            raise RuntimeError(f"不支援的雲端提供者：{chosen_provider}")

        except Exception as e:
            results.append(
                UploadResult(
                    local_path=str(p),
                    upload_name=p.name,
                    provider=chosen_provider,
                    status="error",
                    error=str(e),
                )
            )

    # 寫入 manifest
    write_upload_manifest(results, media_dir=media_dir)

    return {
        "media_uploader_version": "media_uploader.stage3.v1",
        "provider": chosen_provider,
        "media_dir": str(media_dir),
        "total_files": len(all_files),
        "dry_run": dry_run,
        "manifest_path": str(UPLOAD_MANIFEST_PATH),
        "results": [asdict(r) for r in results],
    }


def write_upload_manifest(
    results: list[UploadResult],
    *,
    media_dir: Path | None = None,
    manifest_path: Path | None = None,
) -> None:
    """將結果追加至 upload_manifest.json。"""
    manifest_path = manifest_path or UPLOAD_MANIFEST_PATH

    existing: list[dict[str, Any]] = []
    if manifest_path.exists():
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    existing = data
        except (OSError, json.JSONDecodeError):
            pass

    timestamp = datetime.now().isoformat(timespec="seconds")
    for r in results:
        existing.append(
            {
                "timestamp": timestamp,
                "local_path": r.local_path,
                "upload_name": r.upload_name,
                "sha256_8": r.sha256_8,
                "remote_id": r.remote_id,
                "remote_url": r.remote_url,
                "status": r.status,
                "error": r.error if r.error else None,
            }
        )

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def main() -> None:
    """CLI 入口。"""
    import argparse

    parser = argparse.ArgumentParser(description="媒體素材上傳器 (Stage 3)")
    parser.add_argument("--upload", action="store_true", help="執行實際上傳")
    parser.add_argument("--provider", default=None, help="覆寫雲端供提供者")
    parser.add_argument("--max-files", type=int, default=None, help="最多處理檔案數")
    args = parser.parse_args()

    out = upload_media_assets(
        dry_run=not args.upload,
        provider=args.provider,
        max_files=args.max_files,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
