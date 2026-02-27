# 🚀 Google Cloud OAuth Token 自動化管理指南

## 概述

本文件說明如何在 Google Cloud 上設定自動化的 Google Drive OAuth Token 刷新，確保備份服務不因 token 過期而中斷。

---

## 📋 必要條件

### 1. 本機準備

```bash
# 登入 gcloud
gcloud auth login

# 設定預設 project
gcloud config set project ivyhouse-ad-analyzer
```

### 2. 必要的 API

以下 APIs 需要被啟用：
- ✅ Google Drive API
- ✅ Cloud Functions API
- ✅ Cloud Scheduler API
- ✅ Cloud Logging API
- ✅ Secret Manager API

---

## 🔧 部署步驟

### **Step 1️⃣ ：初始化 Secret Manager**

#### 1. 準備本機環境

確保你有：
- ✅ `secrets/client_secret_*.json`（OAuth credentials）
- ✅ `ifp.env`（包含 `GOOGLE_DRIVE_ACCESS_TOKEN` 和 `GOOGLE_DRIVE_FOLDER_ID`）

#### 2. 執行初始化腳本

```bash
# 將本地 secrets 上傳到 Google Cloud Secret Manager
bash scripts/setup_gcp_secrets.sh ivyhouse-ad-analyzer

# 該腳本會提示輸入 refresh_token
# 如果沒有，可以稍後手動更新
```

#### 3. 驗證 Secrets

```bash
# 列出所有 secrets
gcloud secrets list --project=ivyhouse-ad-analyzer

# 查看特定 secret（不含值）
gcloud secrets describe GOOGLE_DRIVE_ACCESS_TOKEN --project=ivyhouse-ad-analyzer
```

---

### **Step 2️⃣ ：部署 Cloud Function**

#### 1. 執行部署腳本

```bash
bash scripts/deploy_token_refresh_function.sh ivyhouse-ad-analyzer
```

輸出示例：
```
✅ Cloud Function 已部署
📌 Trigger URL：
   https://asia-east1-ivyhouse-ad-analyzer.cloudfunctions.net/refresh-oauth-token
```

#### 2. 驗證部署

```bash
# 查看 Function 詳情
gcloud functions describe refresh-oauth-token \
  --gen2 \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer

# 查看最近的日志（應該看到初始運行）
gcloud functions logs read refresh-oauth-token \
  --limit 50 \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer
```

#### 3. 測試 Function（可選）

```bash
# 手動觸發 Function（立即測試刷新邏輯）
curl "https://asia-east1-ivyhouse-ad-analyzer.cloudfunctions.net/refresh-oauth-token"

# 或使用 gcloud
gcloud functions call refresh-oauth-token \
  --gen2 \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer
```

預期響應：
```json
{
  "status": "success",
  "message": "OAuth Token 已成功刷新",
  "expires_in": 3599,
  "expiry_time": "2026-02-27T18:00:00Z",
  "next_refresh": "2026-03-05T18:00:00Z"
}
```

---

### **Step 3️⃣ ：設定 Cloud Scheduler**

#### 1. 獲取 Function URL

```bash
FUNCTION_URL=$(gcloud functions describe refresh-oauth-token \
  --gen2 \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer \
  --format='value(serviceConfig.uri)')

echo "Function URL: $FUNCTION_URL"
```

#### 2. 設定定期執行

```bash
bash scripts/setup_cloud_scheduler.sh ivyhouse-ad-analyzer "$FUNCTION_URL"
```

#### 3. 驗證 Scheduler

```bash
# 查看 Job 詳情
gcloud scheduler jobs describe refresh-gdrive-token \
  --location=asia-east1 \
  --project=ivyhouse-ad-analyzer

# 查看 Job 運行狀態
gcloud scheduler jobs list \
  --location=asia-east1 \
  --project=ivyhouse-ad-analyzer
```

#### 4. 手動測試 Scheduler（可選）

```bash
# 立即執行 Job（用於測試）
gcloud scheduler jobs run refresh-gdrive-token \
  --location=asia-east1 \
  --project=ivyhouse-ad-analyzer

# 等待 5 秒後查看日志
sleep 5
gcloud functions logs read refresh-oauth-token \
  --limit 20 \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer
```

---

## 🔑 Secret Manager 管理

### 查看所有 Secrets

```bash
gcloud secrets list --project=ivyhouse-ad-analyzer --format=table
```

### 手動更新 Secret

```bash
# 如果獲得了新的 refresh_token，手動更新
echo "1//0eEc2IUWr2r00..." | gcloud secrets versions add \
  GOOGLE_DRIVE_REFRESH_TOKEN \
  --data-file=- \
  --project=ivyhouse-ad-analyzer
```

### 刪除 Secret

```bash
# ⚠️  謹慎操作，刪除後無法復原
gcloud secrets delete GOOGLE_DRIVE_ACCESS_TOKEN \
  --project=ivyhouse-ad-analyzer
```

---

## 📊 監控和日志

### 查看 Cloud Function 日志

```bash
# 最近 100 行日志
gcloud functions logs read refresh-oauth-token \
  --limit 100 \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer

# 即時跟蹤日志
gcloud functions logs read refresh-oauth-token \
  --limit 50 \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer \
  --follow
```

### 查看 Scheduler 執行歷史

```bash
# 查看最近的 Scheduler 執行日志
gcloud scheduler jobs describe refresh-gdrive-token \
  --location=asia-east1 \
  --project=ivyhouse-ad-analyzer \
  --format='value(lastAttemptTime, status)'
```

### Cloud Logging 控制台

在 Google Cloud Console 查看：
1. 進入 Logging → Logs Explorer
2. 篩選資源：`Cloud Functions` - `refresh-oauth-token`
3. 或搜尋：`resource.type="cloud_function" resource.labels.function_name="refresh-oauth-token"`

---

## 🔐 安全最佳實踐

### 1. Secret Manager 權限控制

```bash
# 给特定 Service Account 授予 secret 存取權限
gcloud secrets add-iam-policy-binding GOOGLE_DRIVE_ACCESS_TOKEN \
  --member=serviceAccount:YOUR_SERVICE_ACCOUNT@appspot.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor \
  --project=ivyhouse-ad-analyzer

# 查看現有權限
gcloud secrets get-iam-policy GOOGLE_DRIVE_ACCESS_TOKEN \
  --project=ivyhouse-ad-analyzer
```

### 2. 定期輪換 Refresh Token

**為什麼？** Refresh token 的有效期是 7 天。如果 7 天內沒有使用，會自動失效。

**執行週期：** 建議每 7 天執行一次刷新（已通過 Cloud Scheduler 自動完成）

**手動輪換（如果需要）：**

```bash
# 1. 重新執行授權流程取得新的 refresh_token
#   (在本機執行之前提供的授權腳本)

# 2. 更新 Secret Manager
echo "新的_REFRESH_TOKEN_值" | gcloud secrets versions add \
  GOOGLE_DRIVE_REFRESH_TOKEN \
  --data-file=- \
  --project=ivyhouse-ad-analyzer
```

### 3. 監控 API 配額

在 Google Cloud Console：
1. 進入 APIs & Services → Quotas
2. 搜尋 `Google Drive API`
3. 查看 `Queries per day` 和 `Queries per 100 seconds`

---

## 🔄 Token 刷新流程圖

```
┌─────────────────────────────────────────────────────────────┐
│ Cloud Scheduler (每週日 00:00 執行)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
    ┌──────────────────────────────────────┐
    │ Cloud Function (refresh-oauth-token) │
    └──────────────────┬───────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
    ┌────────┐  ┌───────────┐  ┌────────────┐
    │ 讀取    │  │ Google    │  │ 讀取現有   │
    │ Secrets│  │ OAuth API │  │ Refresh   │
    │Manager │  │ (交換)    │  │ Token     │
    └────┬───┘  └─────┬─────┘  └────┬──────┘
         │             │             │
         └─────────────┼─────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ 更新 Secret Manager          │
        │ (新 Access Token)            │
        └──────────────┬───────────────┘
                       │
                       ▼
          ┌────────────────────────┐
          │ Cloud Run / 本機應用   │
          │ 讀取新 Token 使用      │
          │ (next refresh cycle)   │
          └────────────────────────┘
```

---

## 🐛 故障排排查

### 常見問題

#### 1. Function 報錯：`Refresh Token 尚未設定`

**原因：** Secret Manager 中的 `GOOGLE_DRIVE_REFRESH_TOKEN` 未正確設定

**解決：**
```bash
# 檢查 secret 值
gcloud secrets versions access latest --secret=GOOGLE_DRIVE_REFRESH_TOKEN --project=ivyhouse-ad-analyzer

# 如果是佔位符，重新執行授權流程並更新
```

#### 2. Function 報錯：`Request had invalid authentication credentials`

**原因：** Access token 已過期且無法用 refresh_token 更新

**解決：** 重新執行完整授權流程：
```bash
# 回到本機，執行授權腳本...
# 然後更新 Secret Manager
```

#### 3. Cloud Scheduler Job 顯示失敗

**檢查：**
```bash
# 查看 Function 日志
gcloud functions logs read refresh-oauth-token \
  --limit 50 \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer

# 檢查 Cloud Run 日志（gen2 functions 在 Cloud Run 中執行）
gcloud run services describe refresh-oauth-token \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer
```

---

## 📝 在應用程式中使用 Token

### 在 Cloud Run 中

```python
from scripts.gcp_secret_manager import get_oauth_credentials

# 自動從 Secret Manager 或環境變數讀取
creds = get_oauth_credentials()

access_token = creds['access_token']
folder_id = creds['folder_id']

# 使用 token 訪問 Google Drive API
```

### 在本機開發中

```python
import os

# 自動從環境變數或 ifp.env 讀取
from scripts.gcp_secret_manager import get_oauth_credentials

creds = get_oauth_credentials()
# 或手動讀取
access_token = os.environ.get('GOOGLE_DRIVE_ACCESS_TOKEN')
```

---

## 📞 支援和更新

- **文件位置：** `doc/GCP_TOKEN_AUTOMATION.md`
- **腳本位置：** `scripts/setup_gcp_secrets.sh`, `scripts/deploy_token_refresh_function.sh` 等
- **日志位置：** Google Cloud Console → Cloud Functions / Cloud Logging

---

## ✅ 檢查清單

部署完成後，確認以下項目：

- [ ] `.gitignore` 包含 `secrets/`、`.env`、`ifp.env`
- [ ] Google Cloud Secret Manager 已初始化（包含所有必要 secrets）
- [ ] Cloud Function `refresh-oauth-token` 已部署
- [ ] Cloud Scheduler Job `refresh-gdrive-token` 已設定
- [ ] 手動測試 Function（curl 或 gcloud）成功
- [ ] 日志中看到「Token 刷新成功」訊息
- [ ] Cloud Scheduler 排程設定正確（每週日午夜）
- [ ] 備份腳本可以從 Secret Manager 讀取 token

---

**最後更新：** 2026-02-26
