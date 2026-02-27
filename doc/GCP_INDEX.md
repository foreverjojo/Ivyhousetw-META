# 📑 Google Cloud OAuth Token 自動化 - 文件索引

> **最後更新**：2026-02-26
> **階段**：核心部署腳本和文件完成
> **預期完成時間**：使用者執行 20-30 分鐘

---

## 🗂️ 文件結構

```
ivyhousetw-META/
├── doc/
│   ├── GCP_TOKEN_AUTOMATION.md          ← 📘 完整部署指南（詳盡版）
│   ├── GCP_QUICK_REFERENCE.md           ← ⚡ 速查表（命令參考）
│   ├── GCP_TROUBLESHOOTING.md           ← 🔧 故障排查
│   ├── GCP_DEPLOYMENT_CHECKLIST.md      ← ✅ 部署清單
│   └── GCP_INDEX.md                     ← 📑 本文件（導覽）
│
├── scripts/
│   ├── setup_gcp_secrets.sh             ← 🔑 Step 1：Secret Manager 初始化
│   ├── gcp_token_refresh_function.py    ← 🔄 Step 2：Token 刷新邏輯（內部使用）
│   ├── deploy_token_refresh_function.sh ← 🚀 Step 3：Function 部署
│   ├── setup_cloud_scheduler.sh         ← ⏰ Step 4：Scheduler 配置
│   ├── verify_gcp_setup.sh              ← 🧪 工具：環境驗證
│   ├── gcp_secret_manager.py            ← 🛠️  工具：Python 應用端使用
│   └── gcp_requirements.txt             ← 📦 Cloud Function 依賴
│
└── [其他現有結構...]
```

---

## 📖 文件詳細說明

### 1. **GCP_TOKEN_AUTOMATION.md** （推薦閱讀）

**適用者**：需要完整理解的開發者
**包含內容**：
- ✅ 部署流程 (5 大步驟)
- 🔑 Secret Manager 管理命令
- ☁️ Cloud Function 操作
- ⏰ Cloud Scheduler 配置
- 📊 監控和日志
- 🔐 安全最佳實踐
- 🔄 Token 刷新流程圖
- 📞 支援和更新指南

**閱讀時間**：15-20 分鐘

**何時使用**：首次部署、需要完整背景知識

---

### 2. **GCP_QUICK_REFERENCE.md** （常用速查）

**適用者**：已部署過，需要快速查命令的開發者
**包含內容**：
- ⚡ 常用命令表
- 🆔 環境設定指令
- 🔑 Secret Manager 速查表
- ☁️ Cloud Function 操作列表
- ⏰ Cloud Scheduler 命令表
- 🧪 測試和驗證命令
- ⚠️ 常見錯誤和解決
- 🎯 30秒快速部署流程

**閱讀時間**：5-10 分鐘

**何時使用**：想快速查找命令、切勿翻閱長文件時

---

### 3. **GCP_TROUBLESHOOTING.md** （遇到問題時）

**適用者**：遇到部署或運行錯誤的開發者
**包含內容**：
- 🔍 快速診斷指南
- 1️⃣-6️⃣ 按問題類別排查：
  - 認證和 gcloud 問題
  - Secret Manager 問題
  - Cloud Function 部署問題
  - Cloud Scheduler 問題
  - Token 和認證問題
  - 備份和整合問題
- 🧪 完整驗證流程
- 📞 獲取更多幫助

**閱讀時間**：20-30 分鐘（依具體問題）

**何時使用**：部署/運行出現錯誤時，按錯誤訊息查找對應問題

---

### 4. **GCP_DEPLOYMENT_CHECKLIST.md** （部署時跟蹤）

**適用者**：正在部署的開發者
**包含內容**：
- ✅ 5 大步驟清單
- 📋 Step 1-5 的詳細檢查點
- 🎉 完成驗收清單
- ⚠️ 常見檢查點
- 🔄 後續維護指南

**閱讀時間**：5 分鐘（部署前）+ 30 分鐘（部署期間）

**何時使用**：部署時，跟蹤進度

---

### 5. **GCP_INDEX.md** （本文件）

**用途**：文件導覽和快速查詢
**應該保持簡短，方便快速定位**

---

## 🔧 腳本詳細說明

### **setup_gcp_secrets.sh** （Step 1）
```bash
bash scripts/setup_gcp_secrets.sh ivyhouse-ad-analyzer
```
- **目的**：初始化 Google Cloud Secret Manager
- **執行時間**：3-5 分鐘
- **必需資訊**：PROJECT_ID、ifp.env、client_secret.json、refresh_token
- **輸出**：5 個 GCP secrets 已建立
- **文件位置**：`scripts/setup_gcp_secrets.sh`

---

### **gcp_token_refresh_function.py** （Step 2 - 內部使用）
```python
# 不直接執行，由 Cloud Function 自動使用
# 邏輯：讀 secrets → 刷新 token → 更新 secrets
```
- **目的**：Cloud Function 的核心邏輯
- **Entry Point**：`refresh_token(request)`
- **Returns**：JSON with status, message, expires_in, etc.
- **文件位置**：`scripts/gcp_token_refresh_function.py`

---

### **deploy_token_refresh_function.sh** （Step 3）
```bash
bash scripts/deploy_token_refresh_function.sh ivyhouse-ad-analyzer
```
- **目的**：部署 Cloud Function 到 Google Cloud
- **執行時間**：5-10 分鐘
- **輸出**：Function trigger URL（複製備用）
- **文件位置**：`scripts/deploy_token_refresh_function.sh`

---

### **setup_cloud_scheduler.sh** （Step 4）
```bash
bash scripts/setup_cloud_scheduler.sh ivyhouse-ad-analyzer <FUNCTION_URL>
```
- **目的**：配置每週自動執行任務
- **執行時間**：3-5 分鐘
- **排程**：0 0 * * 0（每週日午夜 UTC+8）
- **文件位置**：`scripts/setup_cloud_scheduler.sh`

---

### **verify_gcp_setup.sh** （驗證工具）
```bash
bash scripts/verify_gcp_setup.sh ivyhouse-ad-analyzer
```
- **目的**：驗證本機和 GCP 環境是否正確設置
- **執行時間**：2-3 分鐘
- **輸出**：彩色進度報告、完成度百分比
- **通過標準**：>= 80% 通過
- **文件位置**：`scripts/verify_gcp_setup.sh`

---

### **gcp_secret_manager.py** （應用程式工具）
```python
from scripts.gcp_secret_manager import get_oauth_credentials

creds = get_oauth_credentials()  # 自動檢測環境
access_token = creds['access_token']
```
- **目的**：Python 應用程式讀取 secrets 的工具模組
- **優先級**：Secret Manager → 環境變數 → ifp.env
- **自動環境檢測**：Cloud Run vs 本機
- **文件位置**：`scripts/gcp_secret_manager.py`

---

### **gcp_requirements.txt**
- **google-cloud-secret-manager==2.16.0**
- **requests==2.31.0**
- **functions-framework==3.5.0**
- **用途**：Cloud Function 部署時的 Python 依賴

---

## 🎯 快速決策樹

```
你現在想做什麼？
│
├─ 🚀 首次部署
│  └─ 讀 → GCP_DEPLOYMENT_CHECKLIST.md (步驟清單)
│     參考 → GCP_TOKEN_AUTOMATION.md (詳盡指南)
│
├─ ⚡ 快速查命令
│  └─ 參考 → GCP_QUICK_REFERENCE.md
│
├─ 🔧 遇到錯誤
│  └─ 查詢 → GCP_TROUBLESHOOTING.md (按錯誤類別)
│
├─ 🧪 驗證環境
│  └─ 執行 → bash scripts/verify_gcp_setup.sh
│
├─ 🔄 整合應用程式
│  └─ 使用 → scripts/gcp_secret_manager.py
│
└─ 📚 深度學習
   └─ 閱讀 → GCP_TOKEN_AUTOMATION.md (完整版)
```

---

## 📋 文件使用時間表

| 時間點 | 應做什麼 | 參考文件 |
|-------|------|--------|
| **決定部署前** | 理解整體架構 | GCP_TOKEN_AUTOMATION.md |
| **部署前準備** | 驗證環境 | GCP_DEPLOYMENT_CHECKLIST.md |
| **開始部署** | 執行 Step 1-5 | GCP_DEPLOYMENT_CHECKLIST.md |
| **卡住了** | 查找錯誤 | GCP_TROUBLESHOOTING.md |
| **部署完成後** | 驗證成功 | GCP_DEPLOYMENT_CHECKLIST.md |
| **日常維護** | 快速查命令 | GCP_QUICK_REFERENCE.md |
| **應用程式整合** | 讀取 tokens | scripts/gcp_secret_manager.py |

---

## 🔑 關鍵環境變數和 Secrets

| 名稱 | 來源 | 用途 | 儲存位置 |
|------|------|------|---------|
| `GOOGLE_DRIVE_CLIENT_ID` | OAuth 2.0 設定 | API 認證 | Secret Manager |
| `GOOGLE_DRIVE_CLIENT_SECRET` | OAuth 2.0 設定 | API 認證 | Secret Manager |
| `GOOGLE_DRIVE_ACCESS_TOKEN` | Token 交換後 | Drive API 授權 | Secret Manager + ifp.env |
| `GOOGLE_DRIVE_REFRESH_TOKEN` | 初次授權時 | 更新 access token | Secret Manager |
| `GOOGLE_DRIVE_FOLDER_ID` | Google Drive | 上傳位置 | Secret Manager + ifp.env |

---

## 📁 實際部署檔案位置

```
/workspaces/ivyhousetw ad analyzer/Ivyhousetw-META/
│
├─ doc/
│  ├─ GCP_TOKEN_AUTOMATION.md         ← 詳細指南
│  ├─ GCP_QUICK_REFERENCE.md          ← 速查表
│  ├─ GCP_TROUBLESHOOTING.md          ← 故障排查
│  ├─ GCP_DEPLOYMENT_CHECKLIST.md     ← 檢查清單
│  └─ GCP_INDEX.md                    ← 本文件
│
└─ scripts/
   ├─ setup_gcp_secrets.sh             ← 執行 Step 1
   ├─ gcp_token_refresh_function.py    ← Cloud Function 邏輯
   ├─ deploy_token_refresh_function.sh ← 執行 Step 3
   ├─ setup_cloud_scheduler.sh         ← 執行 Step 4
   ├─ verify_gcp_setup.sh              ← 驗證工具
   ├─ gcp_secret_manager.py            ← 應用端工具
   └─ gcp_requirements.txt             ← 依賴清單
```

---

## ✨ 部署完成後的樣子

部署完成後，你將擁有：

1. ✅ **Google Cloud Secret Manager** - 存放所有敏感信息
2. ✅ **Cloud Function** (refresh-oauth-token) - 自動刷新邏輯
3. ✅ **Cloud Scheduler** (refresh-gdrive-token) - 每週日自動執行
4. ✅ **完全自動化的 token 生命週期管理** - 無需手動干預

系統會自動：
- 每週日午夜刷新 access token
- 將新 token 保存到 Secret Manager
- 應用程式自動讀取最新 token
- Google Drive 備份不會因 token 過期中斷

---

## 🚀 立即開始

### 新手推薦流程：

```bash
# 1️⃣  驗證環境
bash scripts/verify_gcp_setup.sh ivyhouse-ad-analyzer

# 2️⃣  如果通過 >= 80%，開始部署
# 參考：GCP_DEPLOYMENT_CHECKLIST.md

# 3️⃣  遇到問題？
# 查詢：GCP_TROUBLESHOOTING.md
```

### 有經驗的開發者：

```bash
# 快速參考
cat doc/GCP_QUICK_REFERENCE.md

# 30 秒快速部署（參考該文件最後部分）
```

---

## 📞 索引速查

需要什麼？點擊或參考對應章節：

- **如何部署？** → `GCP_DEPLOYMENT_CHECKLIST.md`
- **命令怎麼用？** → `GCP_QUICK_REFERENCE.md`
- **出錯了怎麼辦？** → `GCP_TROUBLESHOOTING.md`
- **細節怎麼理解？** → `GCP_TOKEN_AUTOMATION.md`
- **環境對不對？** → `bash scripts/verify_gcp_setup.sh`
- **應用程式如何讀 token？** → `scripts/gcp_secret_manager.py`

---

## 📝 部署紀錄

```
部署開始時間：_______________
部署完成時間：_______________
負責人：_______________
驗證完成：□ 是  □ 否
```

---

## 🎓 學習路徑

### 新手（30 分鐘）
1. 讀 GCP_DEPLOYMENT_CHECKLIST.md → 了解整體步驟
2. 執行 Step 1-5
3. 完成驗收

### 進階（1.5 小時）
1. 讀 GCP_TOKEN_AUTOMATION.md → 深度理解架構
2. 部署並測試所有功能
3. 集成到應用程式（使用 gcp_secret_manager.py）
4. 設置 Cloud Logging 監控

### 專家（2+ 小時）
1. 熟讀所有文件和腳本源碼
2. 定制 Cloud Function 邏輯（例如添加重試機制）
3. 添加高級監控和告警
4. 集成 CI/CD 管道

---

## 💡 提示和最佳實踐

1. **按步驟走** - 不要跳步，每步驗證成功再進行下一步
2. **保存所有輸出** - Function URL 等重要訊息要複製備用
3. **觀察日志** - 一旦出問題，首先查看 Cloud Function 日志
4. **定期檢查** - 每月驗證一次 token 刷新是否正常
5. **文件備份** - 重要的 secrets 存一份本地備份（加密）

---

## 📞 更新和支援

- **文件最後更新**：2026-02-26
- **腳本版本**：1.0
- **相容 Python**：3.11+
- **相容 gcloud CLI**：所有最新版本

如發現任何問題或有改進建議，請參考相關文件中的「獲取更多幫助」部分。

---

**祝部署順利！🚀**
