# Firebase Studio (IDX) 使用說明

## 🎯 重要概念

此專案支援兩種運行模式：

### 1. **開發模式**（Firebase Studio / 本地開發）
- 直接運行 Streamlit：`streamlit run app.py`
- 不需要 Flask 包裝器
- 適合開發和測試

### 2. **生產模式**（Google Cloud Run）
- 使用 Flask 包裝 Streamlit：`python main.py`
- 監聽 `PORT` 環境變數
- 包含健康檢查端點

---

## 🚀 Firebase Studio 快速開始

### 自動預覽（推薦）

1. 開啟專案後，環境會自動建置
2. 點擊 **"Preview"** 按鈕
3. Firebase Studio 會自動：
   - 安裝 Python 依賴（`pip install -r requirements.txt`）
   - 啟動 Streamlit（`streamlit run app.py`）
   - 開啟預覽視窗

### 手動運行

如果自動預覽有問題，可以在終端機執行：

```bash
# 1. 安裝依賴（首次或更新依賴時）
pip install -r requirements.txt

# 2. 運行 Streamlit
streamlit run app.py
```

---

## 🔧 常見問題

### Q: 為什麼 Firebase Studio 不用 `main.py`？

**A:** `main.py` 是 Flask 包裝器，專門為 Cloud Run 設計：
- **Cloud Run 需要**：監聽 `PORT` 環境變數、提供健康檢查
- **開發環境不需要**：Streamlit 本身就很好用

### Q: Preview 失敗顯示 "No module named 'flask'"？

**A:** 這是正常的！最新版的 `.idx/dev.nix` 已經改為直接運行 Streamlit，不再需要 Flask：
1. 點擊 **"Rebuild environment"** 按鈕
2. 或手動在終端執行：`streamlit run app.py`

### Q: 依賴安裝失敗？

**A:** 在終端手動安裝：
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Q: 如何測試 Cloud Run 部署模式？

**A:** 在 Firebase Studio 終端執行：
```bash
# 安裝 Flask
pip install flask

# 運行 main.py
python main.py
```

---

## 📋 環境變數設定

### CrewAI API 金鑰

CrewAI 需要 OpenAI API 金鑰。在 Firebase Studio 中設定：

#### 方法 1: 使用 .env 檔案（開發用）

1. 建立 `.env` 檔案：
   ```bash
   echo "OPENAI_API_KEY=sk-your-api-key-here" > .env
   ```

2. 在程式中載入（如果需要）：
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

#### 方法 2: 直接設定環境變數

在終端執行：
```bash
export OPENAI_API_KEY="sk-your-api-key-here"
streamlit run app.py
```

---

## 🎨 開發工作流程

### 典型的開發流程

1. **在 Firebase Studio 中修改程式碼**
   - 編輯 `app.py`、`scripts/` 等檔案
   - Streamlit 會自動偵測變更

2. **預覽變更**
   - Streamlit 會提示 "Source file changed"
   - 點擊 "Always rerun" 或 "Rerun"

3. **測試功能**
   - 上傳測試檔案
   - 驗證各步驟輸出

4. **提交變更**
   ```bash
   git add .
   git commit -m "描述你的變更"
   git push
   ```

---

## 🚢 部署到 Cloud Run

當開發完成，準備部署時：

### 方法 1: 使用部署腳本（Windows）

```powershell
.\deploy.ps1 -ProjectId "your-project-id"
```

### 方法 2: 直接使用 gcloud

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

### 方法 3: 從 Firebase Studio 部署

1. 在終端執行：
   ```bash
   # 登入 Google Cloud
   gcloud auth login

   # 設定專案
   gcloud config set project YOUR_PROJECT_ID

   # 部署
   gcloud run deploy ivyhouse-meta-analyzer --source .
   ```

---

## 📁 專案結構說明

```
Ivyhousetw-META/
├── app.py              # 主要 Streamlit 應用（開發時運行這個）
├── main.py             # Flask 包裝器（僅 Cloud Run 部署時使用）
├── requirements.txt    # Python 依賴
├── .idx/
│   └── dev.nix        # Firebase Studio 配置
├── scripts/           # CrewAI 業務邏輯
│   ├── kpi_calc.py
│   ├── llm_insights.py
│   ├── consultants.py
│   └── moderator.py
├── schemas/           # JSON Schema 驗證
└── history/           # 歷史資料（會在容器中重建）
```

---

## 🔍 除錯技巧

### 查看詳細錯誤

Streamlit 的錯誤訊息通常很詳細，直接顯示在網頁上。

### 使用 Python 除錯器

在程式碼中加入：
```python
import pdb; pdb.set_trace()
```

### 查看日誌

Firebase Studio 的終端會顯示所有輸出。

---

## 💡 最佳實踐

1. **經常提交變更**：使用 Git 版本控制
2. **使用 .env 檔案**：不要將 API 金鑰硬編碼
3. **本地測試後再部署**：確保功能正常
4. **查看部署日誌**：部署後檢查 Cloud Run 日誌

---

## 🆘 需要幫助？

- 📖 查看 [DEPLOY.md](./DEPLOY.md) - 完整部署指南
- 📋 查看 [CHECKLIST.md](./CHECKLIST.md) - 部署檢查清單
- 📝 查看 [CLOUD_RUN_SUMMARY.md](./CLOUD_RUN_SUMMARY.md) - 改造總結

---

**🎉 享受在 Firebase Studio 中開發的樂趣！**
