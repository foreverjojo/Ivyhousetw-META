"""
檔案用途：Google Secret Manager 存取封裝層
職責：
  - 從 GCP Secret Manager 讀取敏感資料（如 API Key）
  - 提供備援機制：若 Secret Manager 不可用，則從環境變數讀取
  - 支援本機開發與雲端部署兩種模式
"""

import logging
import os

# 嘗試使用專案的 logger，若不存在則使用標準 logger
try:
    from core.logging_config import get_logger

    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


# 快取已讀取的 secrets，避免重複呼叫 API
_secret_cache: dict = {}
# 快取失敗的 secret_id，避免重複嘗試（熔斷機制）
_failed_secrets: set = set()


def _get_secret_from_gcp(project_id: str, secret_id: str, version: str = "latest") -> str | None:
    """
    從 GCP Secret Manager 讀取 secret

    需要：
    1. google-cloud-secret-manager 套件
    2. GCP 認證（Service Account 或 ADC）
    """
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"

        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")

        logger.debug("✅ 從 Secret Manager 讀取成功")
        return secret_value

    except ImportError:
        logger.warning("⚠️ google-cloud-secret-manager 套件未安裝，無法使用 Secret Manager")
        return None
    except Exception as e:
        logger.warning(f"⚠️ Secret Manager 讀取失敗: {e}")
        return None


def get_secret(secret_id: str, env_var_name: str | None = None) -> str | None:
    """
    取得 secret 值（優先順序：快取 → Secret Manager → 環境變數）

    參數：
        secret_id: GCP Secret Manager 中的 secret ID
        env_var_name: 對應的環境變數名稱（備援用），若為 None 則使用 secret_id

    回傳：
        secret 值，若都找不到則回傳 None
    """
    env_var = env_var_name or secret_id

    # 1. 檢查快取
    if secret_id in _secret_cache:
        return _secret_cache[secret_id]

    # 2. 檢查是否曾經失敗（熔斷機制）
    if secret_id in _failed_secrets:
        # 直接使用環境變數備援
        return os.getenv(env_var)

    # 3. 檢查是否啟用 Secret Manager
    secret_manager_enabled = os.getenv("SECRET_MANAGER_ENABLED", "false").lower() == "true"
    project_id = os.getenv("GCP_PROJECT_ID", "")

    secret_value = None

    if secret_manager_enabled and project_id:
        # 4. 嘗試從 Secret Manager 讀取
        secret_value = _get_secret_from_gcp(project_id, secret_id)

        # 若失敗，加入熔斷名單
        if secret_value is None:
            _failed_secrets.add(secret_id)

    if not secret_value:
        # 5. 備援：從環境變數讀取
        secret_value = os.getenv(env_var)
        if secret_value:
            logger.debug("📋 從環境變數讀取")

    # 6. 快取結果
    if secret_value:
        _secret_cache[secret_id] = secret_value

    return secret_value


def get_openrouter_api_key() -> str | None:
    """
    取得 OpenRouter API Key
    優先順序：Secret Manager → OPENROUTER_API_KEY → OPENAI_API_KEY
    """
    # 嘗試從 Secret Manager 或環境變數讀取
    key = get_secret("openrouter-api-key", "OPENROUTER_API_KEY")

    if not key:
        # 備援到 OPENAI_API_KEY
        key = os.getenv("OPENAI_API_KEY")
        if key:
            logger.debug("📋 使用 OPENAI_API_KEY 作為備援")

    return key


def load_secrets_to_env() -> None:
    """
    將所有需要的 secrets 載入到環境變數中
    應該在 app 啟動時呼叫一次
    """
    secret_manager_enabled = os.getenv("SECRET_MANAGER_ENABLED", "false").lower() == "true"

    if not secret_manager_enabled:
        logger.info("🔒 Secret Manager 未啟用，使用環境變數")
        return

    logger.info("🔐 正在從 Secret Manager 載入 secrets...")

    # 定義需要載入的 secrets 映射：(secret_id, env_var_name)
    secrets_to_load = [
        ("openrouter-api-key", "OPENROUTER_API_KEY"),
        # 未來可以新增更多 secrets
    ]

    loaded_count = 0
    for secret_id, env_var in secrets_to_load:
        value = get_secret(secret_id, env_var)
        if value and not os.getenv(env_var):
            os.environ[env_var] = value
            loaded_count += 1
            logger.debug("  ✅ 已載入一個 secret")

    logger.info(f"🔐 Secret Manager 載入完成：{loaded_count} 個 secrets")
