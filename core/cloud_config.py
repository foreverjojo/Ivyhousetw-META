"""
檔案用途：雲端整合設定（Stage 1 + Stage 2 同步更新）
職責：
  - 從環境變數載入雲端上傳所需設定
  - 支援 GOOGLE_APPLICATION_CREDENTIALS (SA JSON) 與 Access Token 兩種認證
  - 不在程式碼內硬編碼任何金鑰/Token（全部走環境變數或外部注入）
  - 提供「可擴充」的 provider 介面，方便後續改成 MCP / Google Drive / GCS
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class CloudConfig:
    """雲端設定（以「媒體素材上傳」為主要情境）。"""

    provider: str

    # Google Drive 設定
    google_drive_folder_id: Optional[str]
    google_drive_access_token: Optional[str]
    google_application_credentials: Optional[str]  # SA JSON 路徑

    # HTTP 參數
    http_timeout_s: int = 120


def load_cloud_config(environ: Optional[dict[str, str]] = None) -> CloudConfig:
    """
    從環境變數載入設定。

    支援的環境變數：
    - CLOUD_MEDIA_PROVIDER：none / gdrive（預設 none）
    - GOOGLE_DRIVE_FOLDER_ID：上傳目的資料夾（可留空，則上傳到根目錄/預設位置）
    - GOOGLE_APPLICATION_CREDENTIALS：SA JSON 檔案路徑（推薦）
    - GOOGLE_DRIVE_ACCESS_TOKEN：OAuth Access Token（短效）
      - 相容別名：GOOGLE_OAUTH_ACCESS_TOKEN

    認證優先順序：
    1. 若 GOOGLE_APPLICATION_CREDENTIALS 存在且檔案有效，使用 SA 認證
    2. 否則使用 GOOGLE_DRIVE_ACCESS_TOKEN
    """
    environ = environ or os.environ

    provider = (environ.get("CLOUD_MEDIA_PROVIDER") or "none").strip().lower()

    drive_folder_id = (environ.get("GOOGLE_DRIVE_FOLDER_ID") or "").strip() or None

    # SA JSON 路徑
    sa_creds_path = (environ.get("GOOGLE_APPLICATION_CREDENTIALS") or "").strip() or None
    if sa_creds_path and not Path(sa_creds_path).is_file():
        sa_creds_path = None  # 路徑無效則忽略

    # Access Token (fallback)
    drive_token = (
        (environ.get("GOOGLE_DRIVE_ACCESS_TOKEN") or "").strip()
        or (environ.get("GOOGLE_OAUTH_ACCESS_TOKEN") or "").strip()
        or None
    )

    timeout_s_raw = (environ.get("CLOUD_HTTP_TIMEOUT_S") or "").strip()
    try:
        timeout_s = int(timeout_s_raw) if timeout_s_raw else 120
    except Exception:
        timeout_s = 120

    return CloudConfig(
        provider=provider,
        google_drive_folder_id=drive_folder_id,
        google_drive_access_token=drive_token,
        google_application_credentials=sa_creds_path,
        http_timeout_s=timeout_s,
    )
