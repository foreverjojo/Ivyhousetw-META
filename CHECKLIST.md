# ✅ Cloud Run 部署檢查清單

## 📋 部署前檢查

### 1. 環境準備
- [ ] 已安裝 Google Cloud CLI
  ```bash
  gcloud version
  ```
- [ ] 已登入 Google Cloud
  ```bash
  gcloud auth login
  ```
- [ ] 已建立或選擇 GCP 專案
  ```bash
  gcloud projects list
  ```
- [ ] 已啟用計費（Cloud Run 需要）
  - 前往：https://console.cloud.google.com/billing

### 2. 專案文件檢查
- [x] `main.py` 存在且正確
- [x] `app.py` 存在（原 Streamlit 應用）
- [x] `Dockerfile` 存在且正確
- [x] `requirements.txt` 或 `pyproject.toml` 存在
- [x] `.idx/dev.nix` 存在（Firebase Studio 用）
- [x] `schemas/` 資料夾存在
- [x] `scripts/` 資料夾存在

### 3. API 金鑰準備
- [ ] OpenAI API 金鑰（CrewAI 需要）
  - 取得：https://platform.openai.com/api-keys
  - 不要硬編碼在程式碼中！
- [ ] 其他必要的 API 金鑰或憑證

---

## 🚀 部署步驟

### 方法 A: 使用自動化腳本（推薦）

```powershell
# 1. 設定專案 ID（替換成你的）
$PROJECT_ID = "your-project-id"

# 2. 執行部署腳本
.\deploy.ps1 -ProjectId $PROJECT_ID

# 3. 等待部署完成（約 3-5 分鐘）
# 腳本會自動：
#   - 啟用必要的 API
#   - 建置 Docker 映像
#   - 部署到 Cloud Run
#   - 顯示服務 URL
```

**部署進度檢查：**
- [ ] API 啟用成功
- [ ] Docker 建置成功
- [ ] Cloud Build 上傳成功
- [ ] Cloud Run 部署成功
- [ ] 收到服務 URL

---

### 方法 B: 手動部署

#### Step 1: 設定 GCP 專案
```bash
# 設定專案
gcloud config set project YOUR_PROJECT_ID

# 確認當前專案
gcloud config get-value project
```
- [ ] 專案設定完成

#### Step 2: 啟用必要的 API
```bash
# 啟用 Cloud Run
gcloud services enable run.googleapis.com

# 啟用 Cloud Build
gcloud services enable cloudbuild.googleapis.com
```
- [ ] Cloud Run API 已啟用
- [ ] Cloud Build API 已啟用

#### Step 3: 部署到 Cloud Run
```bash
gcloud run deploy ivyhouse-meta-analyzer \
  --source . \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600
```
- [ ] 部署命令執行成功
- [ ] 收到服務 URL

---

## 🔧 部署後設定

### 1. 設定環境變數
```bash
# 方法 1: 直接設定（開發測試用）
gcloud run services update ivyhouse-meta-analyzer \
  --set-env-vars "OPENAI_API_KEY=sk-your-key" \
  --region asia-east1
```
- [ ] 環境變數設定完成

```bash
# 方法 2: 使用 Secret Manager（生產環境推薦）
# 建立 secret
echo -n "sk-your-api-key" | gcloud secrets create openai-api-key --data-file=-

# 授權 Cloud Run 存取 secret
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 綁定到服務
gcloud run services update ivyhouse-meta-analyzer \
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest" \
  --region asia-east1
```
- [ ] Secret Manager 設定完成

### 2. 安全性設定（生產環境）
```bash
# 移除公開訪問（需要驗證）
gcloud run services update ivyhouse-meta-analyzer \
  --no-allow-unauthenticated \
  --region asia-east1

# 設定 IAM 權限
gcloud run services add-iam-policy-binding ivyhouse-meta-analyzer \
  --member="user:your-email@example.com" \
  --role="roles/run.invoker" \
  --region asia-east1
```
- [ ] 存取控制設定完成
- [ ] IAM 權限設定完成

### 3. 自訂網域（可選）
```bash
# 映射自訂網域
gcloud run domain-mappings create \
  --service ivyhouse-meta-analyzer \
  --domain your-domain.com \
  --region asia-east1
```
- [ ] 自訂網域設定完成
- [ ] DNS 記錄更新完成

---

## ✅ 驗證測試

### 1. 基本功能測試
```bash
# 取得服務 URL
SERVICE_URL=$(gcloud run services describe ivyhouse-meta-analyzer \
  --region asia-east1 \
  --format="value(status.url)")

# 測試健康檢查
curl $SERVICE_URL/

# 預期輸出：{"status":"healthy"}
```
- [ ] 健康檢查通過
- [ ] 可以訪問服務 URL（瀏覽器開啟）

### 2. Streamlit 應用測試
- [ ] 首頁載入正常
- [ ] 可以上傳檔案
- [ ] Step A 預覽功能正常
- [ ] Step B/C/D 流程正常（需要 API 金鑰）

### 3. 效能測試
```bash
# 檢視日誌
gcloud run services logs read ivyhouse-meta-analyzer \
  --region asia-east1 \
  --limit 50

# 檢視指標
gcloud run services describe ivyhouse-meta-analyzer \
  --region asia-east1
```
- [ ] 啟動時間 < 30 秒
- [ ] 記憶體使用正常
- [ ] 無錯誤日誌

---

## 📊 監控設定

### 1. Cloud Monitoring
- [ ] 前往 Cloud Console > Monitoring
- [ ] 設定告警政策
  - CPU 使用率 > 80%
  - 記憶體使用率 > 90%
  - 錯誤率 > 5%
- [ ] 設定通知管道（Email/Slack）

### 2. Cloud Logging
- [ ] 設定日誌篩選器
- [ ] 匯出重要日誌到 BigQuery（可選）
- [ ] 設定日誌保留政策

---

## 🔄 更新部署

### 當程式碼有變更時
```bash
# 重新部署（自動建置新映像）
.\deploy.ps1 -ProjectId YOUR_PROJECT_ID

# 或手動
gcloud run deploy ivyhouse-meta-analyzer --source .
```
- [ ] 新版本部署成功
- [ ] 舊版本自動淘汰
- [ ] 零停機時間

---

## 🆘 問題排查

### 常見問題 Checklist

#### 問題 1: 部署失敗
- [ ] 檢查 Dockerfile 語法
- [ ] 檢查 requirements.txt 依賴
- [ ] 查看 Cloud Build 日誌
  ```bash
  gcloud builds list --limit 5
  gcloud builds log BUILD_ID
  ```

#### 問題 2: 服務無法啟動
- [ ] 檢查 main.py 是否正確
- [ ] 檢查環境變數設定
- [ ] 查看 Cloud Run 日誌
  ```bash
  gcloud run services logs read --limit 100
  ```

#### 問題 3: 記憶體不足
- [ ] 增加記憶體配置
  ```bash
  gcloud run services update --memory 4Gi
  ```

#### 問題 4: 請求超時
- [ ] 增加超時時間
  ```bash
  gcloud run services update --timeout 3600
  ```

#### 問題 5: API 金鑰錯誤
- [ ] 確認 Secret Manager 設定正確
- [ ] 確認服務帳號有存取權限
- [ ] 檢查環境變數名稱

---

## 📞 支援資源

- 📖 [專案文件](./readme.md)
- 🚀 [部署指南](./DEPLOY.md)
- 📝 [部署總結](./CLOUD_RUN_SUMMARY.md)
- 🌐 [Google Cloud Run 官方文件](https://cloud.google.com/run/docs)
- 💬 [Stack Overflow - google-cloud-run](https://stackoverflow.com/questions/tagged/google-cloud-run)

---

## ✨ 完成確認

### 最終檢查清單
- [ ] 服務已部署並運行
- [ ] 環境變數已設定
- [ ] 安全性設定完成
- [ ] 功能測試通過
- [ ] 監控告警已設定
- [ ] 團隊成員已授權存取
- [ ] 文件已更新
- [ ] 備份計劃已建立

**🎉 恭喜！您的應用已成功部署到 Google Cloud Run！**

---

_最後更新: 2026-01-02_
