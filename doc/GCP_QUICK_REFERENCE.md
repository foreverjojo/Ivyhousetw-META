# 🚀 Google Cloud OAuth Token 自動化 - 快速參考表

## 📌 核心命令速查

### **環境設定**

```bash
# 登入 GCP
gcloud auth login
gcloud config set project ivyhouse-ad-analyzer

# 確認 project 設定
gcloud config get-value project
```

---

## 🔧 部署命令

| 步驟 | 命令 | 說明 |
|-----|------|------|
| **1** | `bash scripts/setup_gcp_secrets.sh ivyhouse-ad-analyzer` | 初始化 Secret Manager |
| **2** | `bash scripts/deploy_token_refresh_function.sh ivyhouse-ad-analyzer` | 部署 Cloud Function |
| **3** | 取得 Function URL（見下表） | 準備 Scheduler 配置 |
| **4** | `bash scripts/setup_cloud_scheduler.sh ivyhouse-ad-analyzer <FUNCTION_URL>` | 設定自動執行排程 |

---

## 🔑 Secret Manager 操作

| 操作 | 命令 |
|-----|------|
| **列出所有 Secrets** | `gcloud secrets list --project=ivyhouse-ad-analyzer` |
| **查看特定 Secret 詳情** | `gcloud secrets describe GOOGLE_DRIVE_ACCESS_TOKEN --project=ivyhouse-ad-analyzer` |
| **更新 Secret 值** | `echo "新值" \| gcloud secrets versions add SECRET_NAME --data-file=- --project=ivyhouse-ad-analyzer` |
| **刪除 Secret** | `gcloud secrets delete SECRET_NAME --project=ivyhouse-ad-analyzer` |

---

## ☁️ Cloud Function 操作

| 操作 | 命令 |
|-----|------|
| **查看 Function 詳情** | `gcloud functions describe refresh-oauth-token --gen2 --region=asia-east1 --project=ivyhouse-ad-analyzer` |
| **取得 Function URL** | `gcloud functions describe refresh-oauth-token --gen2 --region=asia-east1 --project=ivyhouse-ad-analyzer --format='value(serviceConfig.uri)'` |
| **查看 Function 日志** | `gcloud functions logs read refresh-oauth-token --limit 50 --region=asia-east1 --project=ivyhouse-ad-analyzer` |
| **即時跟蹤日志** | `gcloud functions logs read refresh-oauth-token --limit 50 --region=asia-east1 --project=ivyhouse-ad-analyzer --follow` |
| **手動觸發 Function** | `gcloud functions call refresh-oauth-token --gen2 --region=asia-east1 --project=ivyhouse-ad-analyzer` |
| **刪除 Function** | `gcloud functions delete refresh-oauth-token --gen2 --region=asia-east1 --project=ivyhouse-ad-analyzer` |

---

## ⏰ Cloud Scheduler 操作

| 操作 | 命令 |
|-----|------|
| **列出所有 Jobs** | `gcloud scheduler jobs list --location=asia-east1 --project=ivyhouse-ad-analyzer` |
| **查看 Job 詳情** | `gcloud scheduler jobs describe refresh-gdrive-token --location=asia-east1 --project=ivyhouse-ad-analyzer` |
| **立即執行 Job** | `gcloud scheduler jobs run refresh-gdrive-token --location=asia-east1 --project=ivyhouse-ad-analyzer` |
| **修改 Job 排程** | `gcloud scheduler jobs update app-engine refresh-gdrive-token --location=asia-east1 --schedule="0 12 * * 0" --project=ivyhouse-ad-analyzer` |
| **查看 Job 執行歷史** | `gcloud scheduler jobs executions list refresh-gdrive-token --location=asia-east1 --project=ivyhouse-ad-analyzer` |
| **暫停 Job** | `gcloud scheduler jobs pause refresh-gdrive-token --location=asia-east1 --project=ivyhouse-ad-analyzer` |
| **恢復 Job** | `gcloud scheduler jobs resume refresh-gdrive-token --location=asia-east1 --project=ivyhouse-ad-analyzer` |
| **刪除 Job** | `gcloud scheduler jobs delete refresh-gdrive-token --location=asia-east1 --project=ivyhouse-ad-analyzer` |

---

## 🔍 診斷和監控

| 任務 | 命令 |
|-----|------|
| **驗證 Secret Manager 中所有密鑰都已設定** | `gcloud secrets list --project=ivyhouse-ad-analyzer \| grep GOOGLE_DRIVE` |
| **檢查 API 啟用狀態** | `gcloud services list --enabled --project=ivyhouse-ad-analyzer \| grep -E "secretmanager\|cloudfunctions\|cloudscheduler"` |
| **查看 Cloud Function 的 Cloudtrail 記錄** | `gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=refresh-oauth-token" --limit 50 --project=ivyhouse-ad-analyzer --format=json` |
| **檢查 API 配額使用情況** | 進入 Google Cloud Console → APIs & Services → Quotas |

---

## 🧪 測試和驗證

### **測試 Function 是否正常運作**

```bash
curl "https://asia-east1-ivyhouse-ad-analyzer.cloudfunctions.net/refresh-oauth-token"
```

預期返回：
```json
{
  "status": "success",
  "message": "OAuth Token 已成功刷新",
  "expires_in": 3599,
  "expiry_time": "2026-02-27T18:00:00Z",
  "next_refresh": "2026-03-05T18:00:00Z"
}
```

### **即時測試 Scheduler（立即執行而不是等待排程時間）**

```bash
# 1. 運行 Job
gcloud scheduler jobs run refresh-gdrive-token --location=asia-east1 --project=ivyhouse-ad-analyzer

# 2. 等待 3-5 秒
sleep 5

# 3. 查看日志確認執行成功
gcloud functions logs read refresh-oauth-token --limit 10 --region=asia-east1 --project=ivyhouse-ad-analyzer
```

---

## 🛠️ 對應的腳本檔案

| 檔案 | 目的 | 需要執行 |
|-----|------|---------|
| `scripts/setup_gcp_secrets.sh` | 初始化 Secret Manager | ✅ 是 |
| `scripts/gcp_token_refresh_function.py` | Cloud Function 程式碼 | ❌ 內部使用 |
| `scripts/deploy_token_refresh_function.sh` | Part 部署 Function | ✅ 是 |
| `scripts/setup_cloud_scheduler.sh` | 配置排程任務 | ✅ 是 |
| `scripts/gcp_requirements.txt` | Function 依賴清單 | ❌ 自動使用 |
| `scripts/gcp_secret_manager.py` | Python Secret Manager 工具 | ❌ 應用程式使用 |

---

## ⚠️ 常見錯誤和解決方案

### **錯誤：`The caller does not have permission`**

**解決：** 確保 gcloud 使用了正確的 GCP 帳號

```bash
gcloud auth list
gcloud config set account YOUR_EMAIL@gmail.com
```

### **錯誤：`Function not found`**

**解決：** 確認 Function 已正確部署

```bash
gcloud functions list --gen2 --project=ivyhouse-ad-analyzer
```

### **錯誤：`Refresh Token 尚未設定`**

**解決：** 初始化時沒有正確設定 refresh_token，手動更新

```bash
echo "YOUR_REFRESH_TOKEN" | gcloud secrets versions add \
  GOOGLE_DRIVE_REFRESH_TOKEN \
  --data-file=- \
  --project=ivyhouse-ad-analyzer
```

### **Job 顯示「No recent executions」**

**解決：** 確認排程時間設定正確，和/或手動執行一次

```bash
gcloud scheduler jobs run refresh-gdrive-token --location=asia-east1 --project=ivyhouse-ad-analyzer
```

---

## 📊 常見查詢

### **查看當前環境變數和配置**

```bash
# 列出所有輸出環境變數
env | grep -i google

# 查看本機 .env 檔案
cat ifp.env | head -20
```

### **驗證 Google Drive Folder ID 是否有效**

```bash
# 在 Google Drive 中打開資料夾
# URL 格式：https://drive.google.com/drive/folders/FOLDER_ID
# 例如：https://drive.google.com/drive/folders/1IAyVw4PQo0E2UFiSF1ymtxySiP0QjA56
```

### **檢查備份檔案是否已上傳到 Google Drive**

```bash
# 查看最新的備份 manifest
cat backup_manifest.gdrive.json | jq '.entries' | head -10
```

---

## 🎯 30秒快速部署

如果你急著部署，按照以下順序：

```bash
# 1️⃣  設定預設 project
gcloud config set project ivyhouse-ad-analyzer

# 2️⃣  初始化 Secrets（會提示輸入 refresh_token）
bash scripts/setup_gcp_secrets.sh ivyhouse-ad-analyzer

# 3️⃣  部署 Function
bash scripts/deploy_token_refresh_function.sh ivyhouse-ad-analyzer

# 4️⃣  取得 Function URL（複製輸出中的 URI）
FUNC_URL=$(gcloud functions describe refresh-oauth-token \
  --gen2 --region=asia-east1 --project=ivyhouse-ad-analyzer \
  --format='value(serviceConfig.uri)')

# 5️⃣  設定 Scheduler
bash scripts/setup_cloud_scheduler.sh ivyhouse-ad-analyzer "$FUNC_URL"

# 6️⃣  驗證
gcloud scheduler jobs run refresh-gdrive-token --location=asia-east1 --project=ivyhouse-ad-analyzer
sleep 3
gcloud functions logs read refresh-oauth-token --limit 5 --region=asia-east1 --project=ivyhouse-ad-analyzer
```

完成！ ✅

---

**最後更新：** 2026-02-26
**相關文件：** [完整指南](GCP_TOKEN_AUTOMATION.md)
