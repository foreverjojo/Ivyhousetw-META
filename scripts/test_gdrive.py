"""
檔案用途：測試 Google Drive Service Account 連線
職責：
  - 驗證 secrets/ 下的 JSON 金鑰是否有效
  - 測試能否列出 Google Drive 檔案
"""

import os
import json
from pathlib import Path
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import requests

def test_gdrive_connection(json_path: str):
    print(f"🔍 正在測試金鑰：{json_path}")

    if not os.path.exists(json_path):
        print(f"❌ 找不到金鑰檔案：{json_path}")
        return

    # 1. 載入認證
    scopes = ['https://www.googleapis.com/auth/drive.readonly']
    creds = service_account.Credentials.from_service_account_file(json_path, scopes=scopes)

    # 2. 取得 Access Token
    print("🔑 正在取得 Access Token...")
    creds.refresh(Request())
    token = creds.token
    print("✅ 取得 Token 成功")

    # 3. 測試 API 呼叫 (List Files)
    print("📡 正在呼叫 Google Drive API (files.list)...")
    url = "https://www.googleapis.com/drive/v3/files?pageSize=5&fields=files(id,name)"
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(url, headers=headers)

    if resp.status_code == 200:
        data = resp.json()
        print("🟢 連線成功！以下是最近的 5 個檔案：")
        for f in data.get('files', []):
            print(f" - {f['name']} ({f['id']})")
        if not data.get('files'):
            print(" (資料夾為空，但連線正常)")
    else:
        print(f"🔴 API 呼叫失敗 ({resp.status_code})：{resp.text}")

if __name__ == "__main__":
    # 使用使用者提供的路徑
    KEY_PATH = "secrets/ivyhouse-ad-analyzer-e3a920e555a7.json"
    test_gdrive_connection(KEY_PATH)
