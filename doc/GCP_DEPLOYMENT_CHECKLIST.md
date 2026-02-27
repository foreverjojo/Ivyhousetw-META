# ✅ Google Cloud OAuth Token 自動化 - 部署清單

## 🎯 快速檢查清單

在開始部署前，請確保以下條件已滿足：

### 本機環境檢查

- [ ] 已安裝 `gcloud` CLI（`gcloud --version`）
- [ ] 已安裝 `curl`（`curl --version`）
- [ ] 已安裝 Python 3.11+（`python3 --version`）
- [ ] 已登入 GCP（`gcloud auth login`）
- [ ] GCP Project 已設定（`gcloud config set project ivyhouse-ad-analyzer`）
- [ ] `ifp.env` 檔案存在且包含有效的 OAuth tokens
- [ ] `secrets/client_secret_*.json` 檔案存在
- [ ] `.gitignore` 包含 `secrets/`、`ifp.env`、`.env`

### 自動驗證

```bash
bash scripts/verify_gcp_setup.sh ivyhouse-ad-analyzer
```

完成度需達 **80% 以上**才能繼續部署。

---

## 🚀 部署步驟清單

### **Step 1️⃣ ：環境檢查**（5 分鐘）

```bash
# 執行驗證
bash scripts/verify_gcp_setup.sh ivyhouse-ad-analyzer

# 預期結果：✓ 通過檢查 >= 80%
```

- [ ] 通過驗證
- [ ] 所有本機檔案都已準備好

---

### **Step 2️⃣ ：初始化 Secret Manager**（3-5 分鐘）

```bash
bash scripts/setup_gcp_secrets.sh ivyhouse-ad-analyzer
```

指令將提示：
1. 自動檢測 `ifp.env` 中的 `GOOGLE_DRIVE_ACCESS_TOKEN` 和 `GOOGLE_DRIVE_FOLDER_ID`
2. 要求輸入 `GOOGLE_DRIVE_REFRESH_TOKEN`（從 `ifp.env` 複製）

預期輸出：
```
✓ Secret [GOOGLE_DRIVE_CLIENT_ID] 已建立
✓ Secret [GOOGLE_DRIVE_CLIENT_SECRET] 已建立
✓ Secret [GOOGLE_DRIVE_ACCESS_TOKEN] 已建立
✓ Secret [GOOGLE_DRIVE_FOLDER_ID] 已建立
✓ Secret [GOOGLE_DRIVE_REFRESH_TOKEN] 已建立
```

- [ ] 所有 5 個 secrets 已建立
- [ ] 沒有出現 permission 錯誤

驗證：
```bash
gcloud secrets list --project=ivyhouse-ad-analyzer | grep GOOGLE_DRIVE
```

---

### **Step 3️⃣ ：部署 Cloud Function**（5-10 分鐘）

```bash
bash scripts/deploy_token_refresh_function.sh ivyhouse-ad-analyzer
```

指令將：
1. 啟用必要的 APIs（secretmanager, cloudfunctions, cloudscheduler 等）
2. 部署 `refresh-oauth-token` Function
3. 輸出 Function trigger URL

預期輸出：
```
✓ Cloud Functions API 已啟用
✓ Cloud Scheduler API 已啟用
✓ Secret Manager API 已啟用
...
✓ Function deployed successfully
📌 Trigger URL：
   https://asia-east1-ivyhouse-ad-analyzer.cloudfunctions.net/refresh-oauth-token
```

**重要：複製 Trigger URL，Step 4 將使用到！**

- [ ] 所有 APIs 已啟用
- [ ] Function 部署成功
- [ ] Trigger URL 已複製

驗證：
```bash
curl "https://asia-east1-ivyhouse-ad-analyzer.cloudfunctions.net/refresh-oauth-token"

# 預期返回：JSON with "status": "success"
```

---

### **Step 4️⃣ ：配置 Cloud Scheduler**（3-5 分鐘）

```bash
# 使用 Step 3 中複製的 Trigger URL
bash scripts/setup_cloud_scheduler.sh ivyhouse-ad-analyzer \
  "https://asia-east1-ivyhouse-ad-analyzer.cloudfunctions.net/refresh-oauth-token"
```

指令將：
1. 建立 Scheduler Job：`refresh-gdrive-token`
2. 設定排程：每週日 00:00 (UTC+8)
3. 連接到 Function trigger URL

預期輸出：
```
✓ Cloud Scheduler Job 已建立
📌 Job 名稱：refresh-gdrive-token
📌 排程：0 0 * * 0 (Asia/Taipei)
📌 HTTP 目標：https://asia-east1-ivyhouse-ad-analyzer.cloudfunctions.net/refresh-oauth-token
```

- [ ] Job 已建立
- [ ] 排程設定正確（0 0 * * 0）
- [ ] 沒有出現錯誤

驗證：
```bash
gcloud scheduler jobs describe refresh-gdrive-token \
  --location=asia-east1 \
  --project=ivyhouse-ad-analyzer
```

---

### **Step 5️⃣ ：驗證和測試**（2-3 分鐘）

#### A. 手動觸發 Scheduler Job

```bash
gcloud scheduler jobs run refresh-gdrive-token \
  --location=asia-east1 \
  --project=ivyhouse-ad-analyzer

# 應該顯示：
# id: xxx
# status: SUCCESS
```

- [ ] Job 執行成功（STATUS = SUCCESS）

#### B. 檢查 Function 日志

```bash
# 等待 3-5 秒後查看日志
sleep 5

gcloud functions logs read refresh-oauth-token \
  --limit 10 \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer
```

預期日志包含：
```
OAuth Token 已成功刷新
expires_in: 3599
```

- [ ] 日志中顯示「刷新成功」訊息

#### C. 驗證 Secret Manager 更新

```bash
gcloud secrets versions list GOOGLE_DRIVE_ACCESS_TOKEN \
  --project=ivyhouse-ad-analyzer
```

應該看到新的版本（時間戳最新）

- [ ] 有新的 secret 版本

---

## 🎉 完成驗收

所有以下條件都滿足了嗎？

### ✓ 部署完成清單

- [ ] Step 1：環境驗證通過（>= 80%）
- [ ] Step 2：5 個 secrets 已建立到 Secret Manager
- [ ] Step 3：Cloud Function 已部署並可調用
- [ ] Step 4：Cloud Scheduler Job 已建立
- [ ] Step 5A：Scheduler Job 可手動執行且成功
- [ ] Step 5B：Function 日志顯示刷新成功
- [ ] Step 5C：Secret Manager 中有新的 secret 版本

### ✓ 系統運作驗收

- [ ] 自動刷新機制已啟動（Scheduler 每週日 00:00 執行）
- [ ] Function 可成功讀取和更新 tokens
- [ ] 備份腳本可從 Secret Manager 讀取最新的 token（可選）
- [ ] 沒有 permission 或 configuration 錯誤

---

## 📚 相關文件

| 文件 | 用途 |
|------|------|
| `doc/GCP_TOKEN_AUTOMATION.md` | 完整部署指南（詳盡版） |
| `doc/GCP_QUICK_REFERENCE.md` | 常用命令快速參考 |
| `doc/GCP_TROUBLESHOOTING.md` | 故障排查和常見問題 |
| `scripts/verify_gcp_setup.sh` | 環境驗證工具 |

---

## ⚠️ 常見檢查點

### 如果 Step 2 失敗：

```bash
# 檢查 GCP 認證
gcloud auth list

# 如果帳號有誤，重新登入
gcloud auth login

# 確認 project
gcloud config set project ivyhouse-ad-analyzer
```

### 如果 Step 3 失敗：

```bash
# 檢查 API 啟用狀態
gcloud services list --enabled --project=ivyhouse-ad-analyzer | grep cloudfunctions

# 手動啟用（如未啟用）
gcloud services enable cloudfunctions.googleapis.com --project=ivyhouse-ad-analyzer
```

### 如果 Step 4 失敗：

```bash
# 檢查 Function URL 是否正確
gcloud functions describe refresh-oauth-token \
  --gen2 \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer \
  --format='value(serviceConfig.uri)'

# 使用輸出的 URL（不要手動複製）
FUNC_URL=$(gcloud functions describe refresh-oauth-token \
  --gen2 --region=asia-east1 --project=ivyhouse-ad-analyzer \
  --format='value(serviceConfig.uri)')

bash scripts/setup_cloud_scheduler.sh ivyhouse-ad-analyzer "$FUNC_URL"
```

### 如果 Step 5 失敗：

參考 `doc/GCP_TROUBLESHOOTING.md`

---

## 🔄 後續維護

### 日常監控

```bash
# 查看最後一次 Scheduler 執行
gcloud scheduler jobs describe refresh-gdrive-token \
  --location=asia-east1 \
  --project=ivyhouse-ad-analyzer \
  --format='value(lastAttemptTime)'

# 查看最近的 Function 日志
gcloud functions logs read refresh-oauth-token \
  --limit 20 \
  --region=asia-east1 \
  --project=ivyhouse-ad-analyzer \
  --format=table
```

### 定期檢查（每月一次）

1. 確認 Scheduler Job 仍在執行
2. 檢查 Secret Manager 中的 token 已定期更新
3. 驗證備份流程仍然正常

### 如果 Refresh Token 過期

```bash
# 重新執行 OAuth 授權流程（參考早期步驟）
# 然後更新 Secret Manager
echo "NEW_REFRESH_TOKEN" | gcloud secrets versions add \
  GOOGLE_DRIVE_REFRESH_TOKEN \
  --data-file=- \
  --project=ivyhouse-ad-analyzer
```

---

## 🎓 深度理解

想要了解背後的原理？

- **Token 流程**：`doc/GCP_TOKEN_AUTOMATION.md` → 「Token 刷新流程圖」部分
- **Cloud Function 細節**：`scripts/gcp_token_refresh_function.py`
- **Secret Manager 整合**：`scripts/gcp_secret_manager.py`

---

## 📞 需要幫助？

1. **快速查詢命令**：`doc/GCP_QUICK_REFERENCE.md`
2. **遇到錯誤**：`doc/GCP_TROUBLESHOOTING.md`
3. **完整細節**：`doc/GCP_TOKEN_AUTOMATION.md`
4. **環境檢查**：`bash scripts/verify_gcp_setup.sh ivyhouse-ad-analyzer`

---

## 📝 部署紀錄

部署日期：________________
完成人員：________________
預期運行開始：周日 00:00 (Asia/Taipei)

---

**預期完成時間：20-30 分鐘**

祝部署順利！ 🚀
