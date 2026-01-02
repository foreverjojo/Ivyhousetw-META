# Google Cloud Run 部署指南

## 概述
本專案已配置為可在 Google Cloud Run 上運行：
- ✅ `main.py` - Flask 包裝的 Streamlit 應用，監聽 PORT 環境變數
- ✅ `Dockerfile` - 使用 python:3.11-slim 基礎映像
- ✅ `.idx/dev.nix` - Firebase Studio 配置檔

## 前置需求

1. **安裝 Google Cloud CLI**
   ```bash
   # Windows (使用 PowerShell)
   (New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")
   & $env:Temp\GoogleCloudSDKInstaller.exe
   ```

2. **登入並設定專案**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

## 部署步驟

### 方法 1: 使用 Cloud Build（推薦）

```bash
# 1. 設定專案 ID 和服務名稱
$PROJECT_ID = "your-project-id"
$SERVICE_NAME = "ivyhouse-meta-analyzer"
$REGION = "asia-east1"  # 台灣

# 2. 啟用必要的 API
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# 3. 建置並部署到 Cloud Run
gcloud run deploy $SERVICE_NAME `
  --source . `
  --platform managed `
  --region $REGION `
  --allow-unauthenticated `
  --memory 2Gi `
  --cpu 2 `
  --timeout 3600 `
  --project $PROJECT_ID
```

### 方法 2: 手動建置 Docker 映像

```bash
# 1. 建置 Docker 映像
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME .

# 2. 推送到 Google Container Registry
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME

# 3. 部署到 Cloud Run
gcloud run deploy $SERVICE_NAME `
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME `
  --platform managed `
  --region $REGION `
  --allow-unauthenticated `
  --memory 2Gi `
  --cpu 2 `
  --timeout 3600
```

## 環境變數設定

如需設定環境變數（例如 API 金鑰）：

```bash
gcloud run services update $SERVICE_NAME `
  --set-env-vars "OPENAI_API_KEY=your-api-key" `
  --region $REGION
```

或使用 Secret Manager（更安全）：

```bash
# 建立 secret
echo -n "your-api-key" | gcloud secrets create openai-api-key --data-file=-

# 將 secret 綁定到服務
gcloud run services update $SERVICE_NAME `
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest" `
  --region $REGION
```

## Firebase Studio（IDX）使用

1. 前往 [Firebase Studio](https://idx.google.com/)
2. 點擊 "Import from GitHub" 或 "Open existing project"
3. 選擇此專案資料夾
4. `.idx/dev.nix` 會自動配置開發環境
5. 點擊 "Run" 按鈕啟動應用

## 本地測試

### 使用 Docker 本地測試

```bash
# 建置映像
docker build -t ivyhouse-meta-analyzer .

# 運行容器
docker run -p 8080:8080 -e PORT=8080 ivyhouse-meta-analyzer

# 瀏覽器開啟
# http://localhost:8080
```

### 使用 Python 本地測試

```bash
# 安裝依賴
pip install -r requirements.txt

# 設定環境變數並運行
$env:PORT="8080"
python main.py
```

## 容量配置建議

根據使用量調整：

```bash
# 小型使用（<100 用戶/天）
gcloud run services update $SERVICE_NAME --memory 1Gi --cpu 1

# 中型使用（100-1000 用戶/天）
gcloud run services update $SERVICE_NAME --memory 2Gi --cpu 2

# 大型使用（>1000 用戶/天）
gcloud run services update $SERVICE_NAME --memory 4Gi --cpu 4
```

## 監控與日誌

```bash
# 查看日誌
gcloud run services logs read $SERVICE_NAME --region $REGION --limit 50

# 查看服務狀態
gcloud run services describe $SERVICE_NAME --region $REGION
```

## 常見問題

### 1. 部署失敗：記憶體不足
增加記憶體配置：
```bash
gcloud run services update $SERVICE_NAME --memory 4Gi
```

### 2. 請求超時
增加超時時間：
```bash
gcloud run services update $SERVICE_NAME --timeout 3600
```

### 3. CrewAI 相關錯誤
確保環境變數正確設定：
```bash
gcloud run services update $SERVICE_NAME --set-env-vars "OPENAI_API_KEY=sk-..."
```

## 成本估算

Cloud Run 採用用量計費：
- **免費額度**：每月 200 萬次請求
- **運算時間**：依 CPU 和記憶體計費
- **儲存**：Container Registry 儲存費用

詳見：https://cloud.google.com/run/pricing

## 安全性建議

1. **啟用驗證**：生產環境移除 `--allow-unauthenticated`
2. **使用 Secret Manager**：不要在程式碼中硬編碼金鑰
3. **設定 VPC**：限制網路訪問
4. **啟用 Cloud Armor**：防禦 DDoS 攻擊

## 支援

遇到問題？
- 查看 [Cloud Run 文件](https://cloud.google.com/run/docs)
- 查看專案 `readme.md`
- 檢查 `history/` 資料夾的 `pipeline_state.json` 日誌
