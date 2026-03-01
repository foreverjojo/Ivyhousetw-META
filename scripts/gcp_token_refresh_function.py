"""
Google Cloud Function: 自動刷新 Google Drive OAuth Access Token

觸發方式：Cloud Scheduler（每 7 天執行一次）
功能：使用 refresh_token 交換新的 access_token，並更新 Secret Manager

部署命令：
  gcloud functions deploy refresh-oauth-token \
    --runtime python311 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point refresh_token \
    --region asia-east1 \
    --set-env-vars PROJECT_ID=ivyhouse-ad-analyzer
"""

import json
import logging
import os
from datetime import datetime, timedelta

import functions_framework
import requests
from google.cloud import secretmanager

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_secret(secret_name: str, project_id: str) -> str:
    """從 Google Cloud Secret Manager 讀取 secret"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": secret_path})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"❌ 讀取 secret '{secret_name}' 失敗：{str(e)}")
        raise


def update_secret(secret_name: str, secret_value: str, project_id: str) -> bool:
    """更新 Google Cloud Secret Manager 中的 secret"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        secret_path = f"projects/{project_id}/secrets/{secret_name}"

        client.add_secret_version(
            request={"parent": secret_path, "payload": {"data": secret_value.encode("UTF-8")}}
        )

        logger.info(f"✅ 已更新 secret：{secret_name}")
        return True
    except Exception as e:
        logger.error(f"❌ 更新 secret '{secret_name}' 失敗：{str(e)}")
        raise


@functions_framework.http
def refresh_token(request):
    """Cloud Function 入口點"""

    project_id = os.environ.get("PROJECT_ID")
    if not project_id:
        return {"status": "error", "message": "PROJECT_ID 環境變數未設定"}, 500

    logger.info("=" * 80)
    logger.info("🔄 開始刷新 Google Drive OAuth Token")
    logger.info("=" * 80)

    try:
        # 1. 讀取必要的 secrets
        logger.info("📋 讀取 secrets...")

        client_id = get_secret("GOOGLE_DRIVE_CLIENT_ID", project_id)
        client_secret = get_secret("GOOGLE_DRIVE_CLIENT_SECRET", project_id)
        refresh_token = get_secret("GOOGLE_DRIVE_REFRESH_TOKEN", project_id)
        get_secret("GOOGLE_DRIVE_ACCESS_TOKEN", project_id)

        logger.info("✅ 成功讀取 secrets")

        # 檢查 refresh_token 是否是佔位符
        if "PLACEHOLDER" in refresh_token:
            return {
                "status": "error",
                "message": "Refresh Token 尚未設定。請執行初始授權流程。",
                "action": "需要在 Google Cloud Console 中手動更新 GOOGLE_DRIVE_REFRESH_TOKEN secret",
            }, 400

        # 2. 交換新的 access_token
        logger.info("🔄 向 Google OAuth API 請求新 token...")

        token_endpoint = "https://oauth2.googleapis.com/token"

        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        response = requests.post(token_endpoint, data=payload, timeout=10)

        if response.status_code != 200:
            logger.error(f"❌ Token 交換失敗：{response.status_code}")
            logger.error(f"   響應：{response.text}")

            return {
                "status": "error",
                "message": f"Token 交換失敗：{response.text}",
                "status_code": response.status_code,
            }, response.status_code

        token_response = response.json()
        new_access_token = token_response.get("access_token")
        expires_in = token_response.get("expires_in", 3600)

        if not new_access_token:
            return {
                "status": "error",
                "message": "回應中缺少 access_token",
                "response": token_response,
            }, 400

        logger.info(f"✅ 成功取得新 access_token（有效期：{expires_in} 秒）")

        # 3. 更新 Secret Manager
        logger.info("📤 更新 Secret Manager...")

        update_secret("GOOGLE_DRIVE_ACCESS_TOKEN", new_access_token, project_id)

        # 如果回應中有新的 refresh_token，也更新它
        if "refresh_token" in token_response:
            new_refresh_token = token_response["refresh_token"]
            update_secret("GOOGLE_DRIVE_REFRESH_TOKEN", new_refresh_token, project_id)
            logger.info("🔄 refresh_token 也已更新")

        # 4. 回傳成功響應
        expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)

        result = {
            "status": "success",
            "message": "OAuth Token 已成功刷新",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "access_token_refreshed": True,
            "expires_in": expires_in,
            "expiry_time": expiry_time.isoformat() + "Z",
            "next_refresh": (datetime.utcnow() + timedelta(days=6)).isoformat() + "Z",
        }

        logger.info("=" * 80)
        logger.info("✅ Token 刷新成功！")
        logger.info(f"   新 token 有效期至：{expiry_time.isoformat()}")
        logger.info(f"   建議下次刷新時間：{result['next_refresh']}")
        logger.info("=" * 80)

        return result, 200

    except Exception as e:
        logger.error(f"❌ 未預期的錯誤：{str(e)}")
        import traceback

        logger.error(traceback.format_exc())

        return {"status": "error", "message": f"未預期的錯誤：{str(e)}"}, 500


if __name__ == "__main__":
    # 本地測試
    import sys

    # 設定環境變數
    os.environ["PROJECT_ID"] = "ivyhouse-ad-analyzer"

    # 模擬 HTTP request
    class MockRequest:
        pass

    try:
        result, status_code = refresh_token(MockRequest())
        print(json.dumps(result, indent=2))
        sys.exit(0 if status_code == 200 else 1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)
