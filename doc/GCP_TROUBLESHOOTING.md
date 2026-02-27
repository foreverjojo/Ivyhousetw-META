# 🔧 Google Cloud OAuth Token 自動化 - 故障排排查指南

## 快速診斷

在開始排查之前，請先執行環境驗證腳本：

```bash
bash scripts/verify_gcp_setup.sh ivyhouse-ad-analyzer
```

該腳本會告訴你當前環境的完整狀態。

---

## 📋 常見問題分類

### 1️⃣ **認證和 gcloud 問題**

#### 問題：`gcloud: command not found`

**原因：** Google Cloud SDK 未安裝

**解決方案：**
```bash
# 安裝 Google Cloud SDK（macOS）
brew install google-cloud-sdk

# 安裝（Linux）
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

---

#### 問題：`ERROR: (gcloud.config.set) The caller does not have permission`

**原因：** gcloud 使用了非授權帳號

**解決方案：**
```bash
# 檢查當前登入帳號
gcloud auth list

# 切換帳號
gcloud config set account YOUR_EMAIL@gmail.com

# 或重新登入
gcloud auth login
```

---

#### 問題：`ERROR: User [xyz@gmail.com] does not have permission to access project`

**原因：** 該帳號沒有訪問此 GCP project 的權限

**解決方案：**

1. 確保你是 GCP project owner 或有正確的 IAM 角色
2. 在 [Google Cloud Console](https://console.cloud.google.com) 添加該帳號為 project 成員：
   - 進入 IAM & Admin → Service Accounts
   - 點擊 "Grant Access"
   - 授予 `Editor` 或 `Owner` 角色

或者檢查 project ID 是否正確：
```bash
gcloud config set project ivyhouse-ad-analyzer
gcloud config get-value project
```

---

### 2️⃣ **Secret Manager 問題**

#### 問題：`ERROR: (gcloud.secrets.create) Secret [XXX] already exists`

**原因：** Secret 已存在，嘗試重複建立

**解決方案：**
```bash
# 刪除舊 secret（謹慎操作）
gcloud secrets delete GOOGLE_DRIVE_ACCESS_TOKEN --project=ivyhouse-ad-analyzer

# 或更新 secret 值
echo "NEW_TOKEN_VALUE" | gcloud secrets versions add \
  GOOGLE_DRIVE_ACCESS_TOKEN \
  --data-file=- \
  --project=ivyhouse-ad-analyzer
```

---

#### 問題：`ERROR: Failed to retrieve secret: (gcloud.secrets.versions.access) The caller does not have permission`

**原因：** 使用的帳號沒有 Secret Manager 讀取權限

**解決方案：**
```bash
# 檢查當前帳號
gcloud config get-value account

# 添加權限（假設你是 project owner）
gcloud secrets add-iam-policy-binding GOOGLE_DRIVE_ACCESS_TOKEN \
  --member=user:YOUR_EMAIL@gmail.com \
  --role=roles/secretmanager.secretAccessor \
  --project=ivyhouse-ad-analyzer
```

---

#### 問題：`ERROR: Failed to read secret value: Secret not found`

**原因：** Secret 在 Secret Manager 中不存在

**解決方案：**
```bash
# 列出所有 secrets
gcloud secrets list --project=ivyhouse-ad-analyzer

# 檢查該 secret 是否真的存在
gcloud secrets describe GOOGLE_DRIVE_ACCESS_TOKEN --project=ivyhouse-ad-analyzer

# 如果不存在，重新執行初始化腳本
bash scripts/setup_gcp_secrets.sh ivyhouse-ad-analyzer
```

---

### 3️⃣ **Cloud Function 部署問題**

#### 問題：`ERROR: (gcloud.functions.deploy) INVALID_ARGUMENT: Cloud Functions API has not been used in project`

**原因：** Cloud Functions API 未啟用

**解決方案：**
```bash
# 啟用 API
gcloud services enable cloudfunctions.googleapis.com --project=ivyhouse-ad-analyzer

# 如果其他 API 也缺失，一次啟用所有
gcloud services enable \
  cloudfunctions.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  cloudlogging.googleapis.com \
  appengine.googleapis.com \
  --project=ivyhouse-ad-analyzer
```

---

#### 問題：`ERROR: (gcloud.functions.deploy) Invalid runtime specified: python3.11`

**原因：** Python 3.11 不是有效的 Cloud Functions runtime（檢查版本支援）

**解決方案：**
```bash
# 檢查支援的 runtime
gcloud functions runtimes list

# 修改 deploy 腳本使用受支援的版本（例如 python3.10、python3.9）
# 編輯 scripts/deploy_token_refresh_function.sh
# 將 --runtime=python3.11 改為 --runtime=python3.10
```

---

#### 問題：`ERROR: (gcloud.functions.deploy) The user-provided function did not set the required "FUNCTION_TARGET" environment variable`

**原因：** 腳本中 entry point 設定錯誤

**解決方案：**
```bash
# 確認 gcp_token_refresh_function.py 有正確的入口函數
grep "def refresh_token" scripts/gcp_token_refresh_function.py

# 確認 deploy 腳本中的 entry point 正確
grep "entry-point" scripts/deploy_token_refresh_function.sh
# 應該是 --entry-point=refresh_token
```

---

#### 問題：Cloud Function 部署成功，但無法調用（HTTP 500 錯誤）

**原因：** Function 程式碼有錯誤

**解決方案：**
```bash
# 查看 Function 日志
gcloud functions logs read refresh-oauth-token \
  --limit 50 \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer

# 查看詳細的運行日志（Cloud Logging）
gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=refresh-oauth-token" \
  --limit 20 \
  --project=ivyhouse-ad-analyzer \
  --format=json | jq '.[] | {time:.timestamp, message:.textPayload, severity:.severity}'
```

常見的運行時錯誤：
- `ModuleNotFoundError`：缺失依賴（檢查 requirements.txt）
- `KeyError`：缺失環境變數或 secret
- `requests.Timeout`：連線超時（增加超時時間）

---

### 4️⃣ **Cloud Scheduler 問題**

#### 問題：`ERROR: (gcloud.scheduler.jobs.create) The caller does not have permission`

**原因：** 帳號缺少 Scheduler 操作權限

**解決方案：**
```bash
# 添加 Scheduler 管理員角色
gcloud projects add-iam-policy-binding ivyhouse-ad-analyzer \
  --member=user:YOUR_EMAIL@gmail.com \
  --role=roles/cloudscheduler.admin
```

---

#### 問題：`ERROR: (gcloud.scheduler.jobs.create) Cloud Scheduler API has not been used in project`

**原因：** Cloud Scheduler API 未啟用

**解決方案：**
```bash
gcloud services enable cloudscheduler.googleapis.com --project=ivyhouse-ad-analyzer
```

---

#### 問題：Scheduler Job 建立成功，但出現 `FAILED` 狀態

**檢查步驟：**

```bash
# 1. 查看 job 詳情
gcloud scheduler jobs describe refresh-gdrive-token \
  --location=asia-east1 \
  --project=ivyhouse-ad-analyzer \
  --format=json | jq '.lastAttemptTime, .httpTarget'

# 2. 查看最近的執行日志
gcloud scheduler jobs executions list refresh-gdrive-token \
  --location=asia-east1 \
  --project=ivyhouse-ad-analyzer \
  --limit=5

# 3. 查看 Cloud Function 日志
gcloud functions logs read refresh-oauth-token \
  --limit 20 \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer
```

常見原因：
- **Function URL 錯誤**：檢查 httpTarget.uri 是否與實際 Function URL 一致
- **Function 無法調用**：可能 Function 已刪除或區域不同
- **認證失敗**：OIDC token 已過期或權限不足

---

#### 問題：`Job runs successfully but no "access_token" is updated in Secret Manager`

**原因：** Scheduler 呼叫了 Function，但 Function 未能更新 secret

**解決方案：**

1. 檢查 Function 的實際執行日志：
   ```bash
   gcloud functions logs read refresh-oauth-token \
     --limit 20 \
     --region=asia-east1 \
     --project=ivyhouse-ad-analyzer
   ```

2. 查詢 Function 執行結果（檢查返回值）：
   ```bash
   curl "https://asia-east1-ivyhouse-ad-analyzer.cloudfunctions.net/refresh-oauth-token" | jq
   ```

3. 驗證 secret 是否真的未更新：
   ```bash
   # 查看 secret 版本歷史
   gcloud secrets versions list GOOGLE_DRIVE_ACCESS_TOKEN \
     --project=ivyhouse-ad-analyzer
   ```

---

### 5️⃣ **Token 和認證問題**

#### 問題：`ERROR: Refresh Token 尚未設定`

**原因：** Secret Manager 中的 GOOGLE_DRIVE_REFRESH_TOKEN 未設定或仍是佔位符

**解決方案：**

```bash
# 1. 檢查當前值
gcloud secrets describe GOOGLE_DRIVE_REFRESH_TOKEN --project=ivyhouse-ad-analyzer

# 2. 更新為有效的 refresh_token
# 需要從本機的 ifp.env 或之前的授權取得
echo "YOUR_ACTUAL_REFRESH_TOKEN" | gcloud secrets versions add \
  GOOGLE_DRIVE_REFRESH_TOKEN \
  --data-file=- \
  --project=ivyhouse-ad-analyzer
```

---

#### 問題：`ERROR: (Google API Error) 401: invalid_grant - Token has been revoked`

**原因：** Refresh token 已過期（超過 7 天未使用）或被使用者手動撤銷

**解決方案：**

重新執行完整的授權流程以取得新的 refresh_token：

```bash
# 1. 在本機執行授權腳本（假設有建立）
# 根據此前提供的 OAuth 授權步驟...

# 2. 取得新的 refresh_token 後，更新 Secret Manager
echo "NEW_REFRESH_TOKEN" | gcloud secrets versions add \
  GOOGLE_DRIVE_REFRESH_TOKEN \
  --data-file=- \
  --project=ivyhouse-ad-analyzer

# 3. 驗證
gcloud scheduler jobs run refresh-gdrive-token \
  --location=asia-east1 \
  --project=ivyhouse-ad-analyzer
```

---

#### 問題：`HTTP 403: googleapis.com Error 403: Insufficient Permission`

**原因：** Access token 權限不足（例如缺少 `drive.file` scope）

**解決方案：**

1. 重新授權確保包含完整的 Drive API 權限
2. 檢查 OAuth 客戶端的 scope 設定是否包含 `https://www.googleapis.com/auth/drive.file`

---

### 6️⃣ **備份和整合問題**

#### 問題：備份腳本報錯：`401 invalid_grant - Malformed auth header`

**原因：** 使用的 access_token 無效或已過期

**解決方案：**

```bash
# 1. 檢查備份腳本是否正確讀取 token
# 編輯 scripts/gdrive_weekly_backup.py 或相關備份腳本
# 確保它從 Secret Manager 或環境變數讀取最新 token

# 2. 驗證 token 有效性（在本機測試）
curl -H "Authorization: Bearer $GOOGLE_DRIVE_ACCESS_TOKEN" \
  "https://www.googleapis.com/drive/v3/files" | head -50

# 3. 如果 token 無效，手動觸發 Scheduler 以刷新
gcloud scheduler jobs run refresh-gdrive-token \
  --location=asia-east1 \
  --project=ivyhouse-ad-analyzer

# 4. 等待 5 秒後重試備份
sleep 5
python -m scripts.gdrive_weekly_backup --week 2025-W49 --fp 45a2ae50
```

---

#### 問題：Cloud Run 上的應用無法訪問 Secret Manager 中的 secrets

**原因：** Cloud Run Service Account 缺少權限

**解決方案：**

```bash
# 1. 獲取 Cloud Run Service Account
gcloud run services describe YOUR_SERVICE_NAME \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer \
  --format='value(spec.template.spec.serviceAccountName)'

# 2. 授予該 Service Account Secret Manager 存取權限
gcloud secrets add-iam-policy-binding GOOGLE_DRIVE_ACCESS_TOKEN \
  --member=serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor \
  --project=ivyhouse-ad-analyzer

# 3. 應用程式側面使用：
from google.cloud import secretmanager

def access_secret_version(secret_id, version_id="latest"):
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")
```

---

## 🧪 完整驗證流程

如果遇到多個問題，請按以下順序逐步驗證：

### 步驟 1：環境驗證

```bash
bash scripts/verify_gcp_setup.sh ivyhouse-ad-analyzer
```

### 步驟 2：手動測試 Secret 讀取

```bash
# 讀取 Secret
gcloud secrets versions access latest --secret=GOOGLE_DRIVE_REFRESH_TOKEN \
  --project=ivyhouse-ad-analyzer

# 如果成功，應該看到 token 值（不含佔位符）
```

### 步驟 3：手動測試 Function 調用

```bash
# 取得 Function URL
FUNC_URL=$(gcloud functions describe refresh-oauth-token \
  --gen2 --region=asia-east1 --project=ivyhouse-ad-analyzer \
  --format='value(serviceConfig.uri)')

# 調用
curl "$FUNC_URL" | jq

# 應該返回成功的 JSON：
# {
#   "status": "success",
#   "message": "OAuth Token 已成功刷新",
#   ...
# }
```

### 步驟 4：檢查 Secret Manager 更新

```bash
# 查看版本歷史
gcloud secrets versions list GOOGLE_DRIVE_ACCESS_TOKEN \
  --project=ivyhouse-ad-analyzer

# 應該看到最近的版本有新的時間戳
```

### 步驟 5：測試 Scheduler

```bash
# 立即執行
gcloud scheduler jobs run refresh-gdrive-token \
  --location=asia-east1 \
  --project=ivyhouse-ad-analyzer

# 等待
sleep 5

# 查看日志
gcloud functions logs read refresh-oauth-token \
  --limit 10 \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer
```

---

## 📞 獲取更多幫助

### 查看詳細日志

```bash
# Cloud Function 詳細日志
gcloud logging read "resource.type=cloud_function" \
  --limit 50 \
  --project=ivyhouse-ad-analyzer \
  --format=json

# Scheduler 詳細日志
gcloud logging read "resource.type=cloud_scheduler_job" \
  --limit 50 \
  --project=ivyhouse-ad-analyzer \
  --format=json
```

### 相關文件

- [GCP_TOKEN_AUTOMATION.md](GCP_TOKEN_AUTOMATION.md) - 完整部署指南
- [GCP_QUICK_REFERENCE.md](GCP_QUICK_REFERENCE.md) - 命令快速參考
- [Google Cloud 官方文檔](https://cloud.google.com/docs)
- [Cloud Functions 故障排查](https://cloud.google.com/functions/docs/troubleshooting)
- [Cloud Scheduler 故障排查](https://cloud.google.com/scheduler/docs/troubleshooting)

---

**最後更新：** 2026-02-26
