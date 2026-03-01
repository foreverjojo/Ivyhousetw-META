"""
Google Cloud Secret Manager 工具模組
用於在 Cloud Run、Cloud Functions 或本機環境中讀取 Google Drive 認證信息

使用方式：
  from scripts.gcp_secret_manager import get_oauth_credentials

  creds = get_oauth_credentials()
  access_token = creds['access_token']
  folder_id = creds['folder_id']
"""

import logging
import os

from google.cloud import secretmanager

logger = logging.getLogger(__name__)


class SecretManagerClient:
    """Google Cloud Secret Manager 客戶端"""

    def __init__(self, project_id: str | None = None):
        """初始化客戶端

        Args:
            project_id: Google Cloud 專案 ID
                       如果未指定，將從環境變數或 gcloud 配置中自動偵測
        """
        if not project_id:
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
            if not project_id:
                # 嘗試從 gcloud 配置中獲取
                try:
                    import subprocess

                    result = subprocess.run(
                        ["gcloud", "config", "get-value", "project"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    project_id = result.stdout.strip()
                except Exception:
                    pass

        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()

    def get_secret(self, secret_name: str) -> str:
        """從 Secret Manager 讀取 secret

        Args:
            secret_name: secret 的名稱（例如：GOOGLE_DRIVE_ACCESS_TOKEN）

        Returns:
            secret 的值

        Raises:
            Exception: 如果無法讀取 secret
        """
        try:
            secret_path = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
            response = self.client.access_secret_version(request={"name": secret_path})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"❌ 讀取 secret '{secret_name}' 失敗：{str(e)}")
            raise

    def get_multiple_secrets(self, secret_names: list[str]) -> dict[str, str | None]:
        """批量讀取多個 secrets

        Args:
            secret_names: secret 名稱列表

        Returns:
            {secret_name: secret_value} 字典
        """
        result: dict[str, str | None] = {}
        for name in secret_names:
            try:
                result[name] = self.get_secret(name)
            except Exception as e:
                logger.warning(f"⚠️  無法讀取 '{name}'：{str(e)}")
                result[name] = None

        return result


def get_oauth_credentials(project_id: str | None = None) -> dict[str, str | None]:
    """獲取 Google Drive OAuth 認證信息

    優先級：
    1. Google Cloud Secret Manager（如果在 Cloud Run/Functions 中）
    2. 環境變數（如果已設定）
    3. ifp.env 檔案（本機開發）

    Returns:
        {
            'access_token': '<ACCESS_TOKEN>',
            'client_id': '<CLIENT_ID>',
            'client_secret': '<CLIENT_SECRET>',
            'folder_id': '<FOLDER_ID>',
            'refresh_token': '<REFRESH_TOKEN>'  # 可選
        }
    """

    # 檢查是否在 Google Cloud 環境中
    in_cloud = bool(os.environ.get("GOOGLE_CLOUD_PROJECT"))

    if in_cloud:
        logger.info("📍 在 Google Cloud 環境中運行，從 Secret Manager 讀取認證")
        return _get_from_secret_manager(project_id)
    else:
        logger.info("📍 在本機環境運行，嘗試從環境變數或 ifp.env 讀取認證")
        return _get_from_env_or_file()


def _get_from_secret_manager(project_id: str | None) -> dict[str, str | None]:
    """從 Google Cloud Secret Manager 讀取認證

    所需 secrets：
    - GOOGLE_DRIVE_ACCESS_TOKEN
    - GOOGLE_DRIVE_CLIENT_ID
    - GOOGLE_DRIVE_CLIENT_SECRET
    - GOOGLE_DRIVE_FOLDER_ID
    """
    try:
        client = SecretManagerClient(project_id)

        secret_names = [
            "GOOGLE_DRIVE_ACCESS_TOKEN",
            "GOOGLE_DRIVE_CLIENT_ID",
            "GOOGLE_DRIVE_CLIENT_SECRET",
            "GOOGLE_DRIVE_FOLDER_ID",
            "GOOGLE_DRIVE_REFRESH_TOKEN",  # 可選
        ]

        secrets = client.get_multiple_secrets(secret_names)

        result: dict[str, str | None] = {
            "access_token": secrets.get("GOOGLE_DRIVE_ACCESS_TOKEN"),
            "client_id": secrets.get("GOOGLE_DRIVE_CLIENT_ID"),
            "client_secret": secrets.get("GOOGLE_DRIVE_CLIENT_SECRET"),
            "folder_id": secrets.get("GOOGLE_DRIVE_FOLDER_ID"),
        }

        # 如果有 refresh_token，也加入
        if secrets.get("GOOGLE_DRIVE_REFRESH_TOKEN"):
            result["refresh_token"] = secrets["GOOGLE_DRIVE_REFRESH_TOKEN"]

        logger.info("✅ 成功從 Secret Manager 讀取認證")
        return result

    except Exception as e:
        logger.error(f"❌ 無法從 Secret Manager 讀取認證：{str(e)}")
        raise


def _get_from_env_or_file() -> dict[str, str | None]:
    """從環境變數或 ifp.env 檔案讀取認證"""

    result = {}

    # 先嘗試環境變數
    env_keys = {
        "access_token": "GOOGLE_DRIVE_ACCESS_TOKEN",
        "client_id": "GOOGLE_DRIVE_CLIENT_ID",
        "client_secret": "GOOGLE_DRIVE_CLIENT_SECRET",
        "folder_id": "GOOGLE_DRIVE_FOLDER_ID",
        "refresh_token": "GOOGLE_DRIVE_REFRESH_TOKEN",
    }

    for key, env_var in env_keys.items():
        result[key] = os.environ.get(env_var)

    # 如果環境變數不足，嘗試讀取 ifp.env
    if not all([result["access_token"], result["folder_id"]]):
        logger.info("📁 從 ifp.env 檔案讀取認證...")

        ifp_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ifp.env")

        if os.path.exists(ifp_env_path):
            try:
                with open(ifp_env_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue

                        if "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()

                            if key == "GOOGLE_DRIVE_ACCESS_TOKEN" and not result["access_token"]:
                                result["access_token"] = value
                            elif key == "GOOGLE_DRIVE_CLIENT_ID" and not result["client_id"]:
                                result["client_id"] = value
                            elif (
                                key == "GOOGLE_DRIVE_CLIENT_SECRET" and not result["client_secret"]
                            ):
                                result["client_secret"] = value
                            elif key == "GOOGLE_DRIVE_FOLDER_ID" and not result["folder_id"]:
                                result["folder_id"] = value
                            elif (
                                key == "GOOGLE_DRIVE_REFRESH_TOKEN" and not result["refresh_token"]
                            ):
                                result["refresh_token"] = value

                logger.info("✅ 成功從 ifp.env 讀取認證")

            except Exception as e:
                logger.warning(f"⚠️  讀取 ifp.env 失敗：{str(e)}")

    # 驗證必要的字段
    required_fields = ["access_token", "folder_id"]
    missing = [f for f in required_fields if not result.get(f)]

    if missing:
        raise ValueError(
            f"❌ 缺少必要的認證信息：{', '.join(missing)}\n請檢查環境變數或 ifp.env 檔案"
        )

    return result


def test_secret_manager(project_id: str | None = None) -> bool:
    """測試 Secret Manager 連線

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("🧪 測試 Secret Manager 連線...")

        client = SecretManagerClient(project_id)

        # 嘗試讀取一個 secret（access_token 是必須的）
        token = client.get_secret("GOOGLE_DRIVE_ACCESS_TOKEN")

        if token and len(token) > 10:
            logger.info("✅ Secret Manager 連線成功")
            return True
        else:
            logger.error("❌ Secret Manager 回傳的 secret 無效")
            return False

    except Exception as e:
        logger.error(f"❌ Secret Manager 連線失敗：{str(e)}")
        return False


if __name__ == "__main__":
    # 本機測試
    logging.basicConfig(level=logging.INFO)

    try:
        creds = get_oauth_credentials()

        print("=" * 80)
        print("✅ 成功讀取 OAuth 認證")
        print("=" * 80)
        print()
        # 資安：避免在本機測試輸出任何 secret 值（包含 token/secret/ID）
        print(f"📌 Access Token：{'✓' if creds.get('access_token') else '✗'}")
        print(f"📌 Folder ID：{'✓' if creds.get('folder_id') else '✗'}")
        print(f"📌 Client ID：{'✓' if creds.get('client_id') else '✗'}")
        print(f"📌 Client Secret：{'✓' if creds.get('client_secret') else '✗'}")
        print(f"📌 Refresh Token：{'✓' if creds.get('refresh_token') else '✗'}")
        print()

    except Exception as e:
        print(f"❌ 錯誤：{str(e)}")
