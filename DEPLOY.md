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

## 目前已驗證的私有入口方案（Idx-051）

### 現況摘要

- 目前正式驗證可行的入口不是 direct IAP on Cloud Run，而是 `Global External HTTPS Load Balancer + Serverless NEG + IAP`。
- direct IAP on Cloud Run 已確認不適用於本專案，原因是此 project 不屬於任何 organization。
- Cloud Run 服務 `ivyhouse-meta-analyzer` 已維持 private，且 ingress 已收斂為 `internal-and-cloud-load-balancing`。
- 初期驗證曾使用 self-signed certificate 與 static IP `34.95.93.163`；目前正式入口已切到 `https://adanalyzer.shincold.com/`，並使用 Google-managed certificate。
- 2026-03-07 已改用 Google Auth Platform 建立 customer-owned Web OAuth client，IAP backend 也已重新綁定；真人瀏覽器驗收現已可成功完成 Google 帳戶選擇、OAuth 同意與首頁載入。
- 目前 OAuth consent screen 為 `External / 測試` 狀態；若之後要擴大給更多外部使用者，仍需處理正式發布、驗證與公開條款頁面。

### 已建立的驗證資源

- Cloud Run service: `ivyhouse-meta-analyzer`
- Global static IP: `ivyhouse-meta-iap-ip` → `34.95.93.163`
- SSL certificate: `ivyhouse-meta-iap-cert`（self-managed / self-signed）
- Serverless NEG: `ivyhouse-meta-iap-neg`
- Backend service: `ivyhouse-meta-iap-backend`
- URL map: `ivyhouse-meta-iap-map`
- Target HTTPS proxy: `ivyhouse-meta-iap-proxy`
- Forwarding rule: `ivyhouse-meta-iap-fr`

### 最小設定步驟

1. 在 Google Auth Platform 建立 customer-owned Web OAuth client。
2. 把 OAuth client 的 redirect URI 設為 IAP 實際使用的 `https://iap.googleapis.com/v1/oauth/clientIds/<CLIENT_ID>:handleRedirect`。
3. 建立 global external HTTPS Load Balancer，後端以 serverless NEG 指向 `ivyhouse-meta-analyzer`。
4. 授予 `service-971489052398@gcp-sa-iap.iam.gserviceaccount.com` `roles/run.invoker`。
5. 在 backend service 啟用 IAP，並帶入 OAuth client id / secret。
6. 在 IAP backend service 資源層級授予需要登入的 principal `roles/iap.httpsResourceAccessor`。
7. 將 Cloud Run ingress 收斂為 `internal-and-cloud-load-balancing`。

### 驗收方式

```bash
# 未登入：應回 302 到 Google OAuth
curl -k -I https://34.95.93.163/

# 已授權 service account：應回 200
CLIENT_ID="<iap-oauth-client-id>"
TOKEN=$(gcloud auth print-identity-token \
  --impersonate-service-account="971489052398-compute@developer.gserviceaccount.com" \
  --audiences="$CLIENT_ID" \
  --include-email | tail -n 1)

curl -k -H "Authorization: Bearer $TOKEN" https://34.95.93.163/

# 直接外部打 run.app：在 ingress 收斂後不應再作為對外入口
curl -I https://ivyhouse-meta-analyzer-dlnp2adjbq-de.a.run.app/
```

### 2026-03-07 修復結果

- live IAP backend 已改綁 customer-owned OAuth client：`971489052398-untjbrcfdlqc5bg61hbce6aigeia033e.apps.googleusercontent.com`。
- live 入口 `https://adanalyzer.shincold.com/` 現在會回 302 到新的 Google OAuth authorize URL，不再使用先前的 generic client。
- 真人瀏覽器驗收已通過：Google 帳戶選擇頁 → OAuth 同意頁 → `首頁 | Ivy House Meta`。
- 舊 generic client `a5889775f-e34f-481b-b30f-9ab52de675bc` 僅保留為歷史探查結果，不再作為正式 browser login client。

### 正式化建議

- 正式環境請改用自訂網域 + Google-managed certificate。
- 完成 DNS 後，可把使用者導向正式網域，而不是 self-signed IP。
- 若要更完整封死旁路，可再評估是否停用 Cloud Run 預設 `run.app` URL。

### 可重跑腳本

目前 repo 已提供可重跑腳本：`scripts/setup_cloud_run_iap_entry.sh`

> [!CAUTION]
> - 不要把 `IAP_OAUTH_CLIENT_SECRET` 直接寫死在 shell 指令、腳本檔或 repo。
> - 若 secret 曾出現在 shell history、終端截圖或共享文件，應立即輪替該 OAuth client credential。

```bash
export IAP_OAUTH_CLIENT_ID="<iap-client-id>"
export IAP_OAUTH_CLIENT_SECRET_NAME="iap-oauth-client-secret"
export IAP_OAUTH_CLIENT_SECRET_VERSION="latest"
export IAP_USER_MEMBER="user:foreverwow001@gmail.com"
export IAP_SERVICE_ACCOUNT_MEMBER="serviceAccount:971489052398-compute@developer.gserviceaccount.com"
# 若要做完整 allowlist 收斂，可改用：
# export IAP_ACCESS_MEMBERS="user:foreverwow001@gmail.com,serviceAccount:971489052398-compute@developer.gserviceaccount.com"

bash scripts/setup_cloud_run_iap_entry.sh \
  ivyhouse-ad-analyzer \
  asia-east1 \
  ivyhouse-meta-analyzer \
  adanalyzer.shincold.com
```

建議先把 client secret 放入 Secret Manager：

```bash
printf '%s' '<iap-client-secret>' | gcloud secrets create iap-oauth-client-secret \
  --data-file=- \
  --replication-policy=automatic \
  --project=ivyhouse-ad-analyzer

# 若 secret 已存在，改新增版本：
printf '%s' '<iap-client-secret>' | gcloud secrets versions add iap-oauth-client-secret \
  --data-file=- \
  --project=ivyhouse-ad-analyzer
```

腳本現在支援優先從 `IAP_OAUTH_CLIENT_SECRET_NAME` / `IAP_OAUTH_CLIENT_SECRET_VERSION` / `IAP_OAUTH_CLIENT_SECRET_PROJECT` 讀取 secret；若未提供，再回退到直接讀 `IAP_OAUTH_CLIENT_SECRET`。
執行腳本的操作者需具備對該 secret 的讀取權限，例如 `roles/secretmanager.secretAccessor`。
若只設定 `IAP_USER_MEMBER` / `IAP_SERVICE_ACCOUNT_MEMBER`，腳本會補齊指定成員但保留其他既有 accessor；若要讓 allowlist 完整收斂，請明確提供 `IAP_ACCESS_MEMBERS`。
此腳本負責收斂 LB / NEG / IAP / ingress 與 accessor 狀態，但不會替你建立 Google OAuth consent screen；若提供的 client 不是 browser-capable customer-owned Web OAuth client，真人登入仍可能失敗。

### 公開 Privacy / Terms 頁面

OAuth consent screen 若要進一步正式發布，homepage、privacy policy、terms of service 都必須是公開可見網址。

本 repo 已新增 GitHub Pages 版公開頁面來源：`public_site/`，預設部署後網址為：

- Home: `https://foreverjojo.github.io/Ivyhousetw-META/`
- Privacy: `https://foreverjojo.github.io/Ivyhousetw-META/privacy/`
- Terms: `https://foreverjojo.github.io/Ivyhousetw-META/terms/`

部署 workflow：`.github/workflows/public-legal-pages.yml`

若後續要送 Google brand verification，建議再把這組公開頁切到可由你驗證所有權的正式網域，例如 `legal.shincold.com`，並依 `doc/OAUTH_CONSENT_PUBLICATION.md` 完成 Search Console 驗證與 Branding 更新。

此腳本會可重跑地處理：
- global static IP
- Google-managed certificate
- serverless NEG
- backend service
- URL map / HTTPS proxy / forwarding rule
- IAP 啟用
- Cloud Run Invoker 綁定
- IAP backend service 級別的 `roles/iap.httpsResourceAccessor` 綁定
- Cloud Run ingress 收斂

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
