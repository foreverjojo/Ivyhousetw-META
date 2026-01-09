"""
檔案用途：環境變數載入
職責：
  - 載入 .env 或 ifp.env 檔案
  - 優先讀取 ifp.env
  - 強制覆蓋已存在的環境變數
  - 整合 Secret Manager 載入敏感資料
"""

import os
from pathlib import Path
from dotenv import load_dotenv


def load_environment_variables() -> None:
    """
    載入環境變數（優先讀取 ifp.env，強制覆蓋已存在的環境變數）
    並從 Secret Manager 載入敏感資料（若啟用）
    """
    # 取得專案根目錄（相對於此檔案的父目錄）
    project_root = Path(__file__).parent.parent

    # 1. 載入 .env 檔案
    ifp_env_path = project_root / "ifp.env"
    default_env_path = project_root / ".env"

    if ifp_env_path.exists():
        load_dotenv(ifp_env_path, override=True)
        print(f"✅ 已載入環境變數：{ifp_env_path}")
    elif default_env_path.exists():
        load_dotenv(default_env_path, override=True)
        print(f"✅ 已載入環境變數：{default_env_path}")
    else:
        print("⚠️ 未找到 ifp.env 或 .env 檔案")

    # 2. 從 Secret Manager 載入敏感資料（若啟用）
    try:
        from core.secret_manager import load_secrets_to_env
        load_secrets_to_env()
    except ImportError:
        # 如果 secret_manager 模組不存在，忽略
        pass
    except Exception as e:
        print(f"⚠️ Secret Manager 載入失敗：{e}")
