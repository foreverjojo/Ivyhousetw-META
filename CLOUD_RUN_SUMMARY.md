# 🚀 Cloud Run 部署完成總結

## ✅ 已完成的改造

您的 Python 專案已成功改造為適合 Google Cloud Run 部署的格式！

### 1. **main.py** - Streamlit 啟動器（Cloud Run）
- ✅ 監聽 `PORT` 環境變數（Cloud Run 必需）
- ✅ 啟動 Streamlit 並在收到 SIGTERM/SIGINT 時優雅關機
- ✅ 健康檢查建議以 `/` 作為最小存活檢查（由 Streamlit 回應）

### 2. **Dockerfile** - 容器配置
- ✅ 基於 `python:3.11-slim`
- ✅ 使用 `uv` 加速依賴安裝
- ✅ 多階段優化（系統依賴 + Python 依賴）
- ✅ 健康檢查配置
- ✅ 正確的環境變數設定

### 3. **.idx/dev.nix** - Firebase Studio 配置
- ✅ Python 3.11 環境
- ✅ 自動依賴安裝
- ✅ Web 預覽配置
- ✅ VS Code Python 擴展

### 4. **額外優化檔案**
- ✅ `requirements.txt` - 簡化依賴管理
- ✅ `.dockerignore` - 優化 Docker 建置
- ✅ `.gcloudignore` - 優化 Cloud Build
- ✅ `deploy.ps1` - 一鍵部署腳本
- ✅ `DEPLOY.md` - 完整部署指南
- ✅ 更新 `pyproject.toml` - 加入 Flask 和 jsonschema

## 📋 專案結構

```
Ivyhousetw-META/
├── main.py              # ⭐ Flask 入口點（Cloud Run）
├── app.py               # Streamlit 應用
├── Dockerfile           # ⭐ 容器配置
├── requirements.txt     # Python 依賴
├── pyproject.toml       # 專案元資料
├── .idx/
│   └── dev.nix         # ⭐ Firebase Studio 配置
├── .dockerignore        # Docker 忽略檔案
├── .gcloudignore        # gcloud 忽略檔案
├── deploy.ps1           # 部署腳本
├── DEPLOY.md            # 部署指南
├── scripts/             # CrewAI 腳本
│   ├── consultants.py
│   ├── kpi_calc.py
│   ├── llm_insights.py
│   ├── moderator.py
│   └── ...
└── schemas/             # JSON Schema 驗證
    └── *.json
```

## 🎯 快速開始

### 方法 1: 使用部署腳本（最簡單）

```powershell
.\deploy.ps1 -ProjectId "your-project-id" -ServiceName "ivyhouse-meta"
```

### 方法 2: 手動部署

```bash
# 1. 設定專案
gcloud config set project YOUR_PROJECT_ID

# 2. 部署
gcloud run deploy ivyhouse-meta-analyzer \
  --source . \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600
```

### 方法 3: 使用 Firebase Studio

1. 前往 https://idx.google.com/
2. 匯入此專案
3. `.idx/dev.nix` 會自動配置環境
4. 點擊 "Run" 按鈕

## 🧪 本地測試

### 使用 Docker

```bash
# 建置
docker build -t ivyhouse-meta .

# 運行
docker run -p 8080:8080 -e PORT=8080 ivyhouse-meta

# 開啟瀏覽器
# http://localhost:8080
```

### 直接使用 Python

```bash
# 安裝依賴
pip install -r requirements.txt

# 運行
python main.py
```

## 🔧 配置選項

### 環境變數
- `PORT` - 服務監聽埠（Cloud Run 自動設定）
- `OPENAI_API_KEY` - OpenAI API 金鑰（CrewAI 需要）
- 其他自訂環境變數...

### 資源配置
根據使用量調整：
- **小型**: 1Gi 記憶體, 1 CPU
- **中型**: 2Gi 記憶體, 2 CPU（預設）
- **大型**: 4Gi 記憶體, 4 CPU

## 📊 架構說明

```
使用者請求
    ↓
Cloud Run (main.py)
    ↓
Flask (健康檢查 + 路由)
    ↓
Streamlit (app.py)
    ↓
CrewAI (scripts/)
    ↓
├── KPI 計算 (kpi_calc.py)
├── LLM 洞察 (llm_insights.py)
├── 顧問系統 (consultants.py)
└── 會議主持 (moderator.py)
```

## 🔐 安全性建議

1. **生產環境移除 `--allow-unauthenticated`**
   ```bash
   gcloud run deploy --no-allow-unauthenticated
   ```

2. **使用 Secret Manager 管理 API 金鑰**
   ```bash
   gcloud secrets create openai-api-key --data-file=-
   gcloud run services update --set-secrets="OPENAI_API_KEY=openai-api-key:latest"
   ```

3. **啟用 Cloud Armor** 防護 DDoS

## 💰 成本估算

- **免費額度**: 每月 200 萬次請求
- **運算時間**: 視使用量計費
- **儲存**: Container Registry 費用

詳見: https://cloud.google.com/run/pricing

## 📚 參考文件

- [DEPLOY.md](./DEPLOY.md) - 完整部署指南
- [readme.md](./readme.md) - 專案說明
- [Google Cloud Run 文件](https://cloud.google.com/run/docs)

## 🆘 常見問題

### Q: 部署失敗怎麼辦？
A: 檢查 `DEPLOY.md` 的常見問題章節，或執行：
```bash
gcloud run services logs read SERVICE_NAME --region asia-east1 --limit 50
```

### Q: 如何更新已部署的服務？
A: 重新執行部署命令即可，Cloud Run 會自動處理滾動更新。

### Q: 可以使用其他區域嗎？
A: 可以！修改 `--region` 參數，例如：
- `us-central1` (美國)
- `europe-west1` (歐洲)
- `asia-northeast1` (日本)

### Q: CrewAI 需要哪些環境變數？
A: 主要需要 `OPENAI_API_KEY`，請使用 Secret Manager 安全管理。

## ✨ 下一步

1. ✅ 本地測試：`python main.py`
2. ✅ Docker 測試：`docker build -t test . && docker run -p 8080:8080 test`
3. ✅ 部署到 Cloud Run：`.\deploy.ps1 -ProjectId "your-id"`
4. ✅ 設定環境變數和 Secrets
5. ✅ 配置自訂網域（可選）
6. ✅ 啟用監控和告警

---

**🎉 恭喜！您的專案已準備好部署到 Google Cloud Run！**

有任何問題請參考 [DEPLOY.md](./DEPLOY.md) 或 Google Cloud 文件。
