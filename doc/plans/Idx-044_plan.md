# Idx-044：Google Cloud OAuth Token 自動化部署

**計畫日期**：2026-02-26
**優先級**：P0
**Executor**：待選擇（建議 Codex 或 OpenCode）
**QA Tool**：待選擇（需異於 Executor）

---

## 📋 SPEC

### 目標

完成 Google Cloud 自動化基礎設施部署，實現 Google Drive OAuth token 的週期性自動刷新機制，確保備份服務不會因 token 過期中斷。

**預期成果**：
- ✅ 5 個 secrets 已上傳至 GCP Secret Manager（**已完成**）
- ✅ Cloud Function `refresh-oauth-token` 已部署
- ✅ Cloud Scheduler Job 已配置（每週日 00:00 UTC+8）
- ✅ 自動化 token 刷新流程已驗證

### 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `scripts/setup_gcp_secrets.sh` | 修改 | 修正 bash glob 檢查邏輯（已完成） |
| `doc/plans/Idx-044_plan.md` | 新增 | 本計畫檔 |
| `doc/logs/Idx-044_log.md` | 新增 | 執行日誌（待填） |

## 📁 檔案變更

此部分與上表相同，維持一致性

### 邏輯細節

#### Step 3：部署 Cloud Function

**命令**：
```bash
bash scripts/deploy_token_refresh_function.sh ivyhouse-ad-analyzer
```

**預期流程**：
1. 啟用 APIs：`secretmanager.googleapis.com`, `cloudfunctions.googleapis.com`, `cloudscheduler.googleapis.com`, `cloudlogging.googleapis.com`, `appengine.googleapis.com`
2. 部署 gen2 Cloud Function：
   - 名稱：`refresh-oauth-token`
   - Runtime：`python3.11`
   - 區域：`asia-east1`
   - 記憶體：256MB
   - Timeout：60s
   - Entry point：`refresh_token`
   - 依賴：`gcp_requirements.txt`
3. 輸出 Function trigger URL

**預期輸出示例**：
```
✓ Cloud Functions API 已啟用
✓ Function deployed successfully
📌 Trigger URL：https://asia-east1-ivyhouse-ad-analyzer.cloudfunctions.net/refresh-oauth-token
```

#### Step 4：配置 Cloud Scheduler

**命令**：
```bash
FUNC_URL=$(gcloud functions describe refresh-oauth-token \
  --gen2 --region=asia-east1 --project=ivyhouse-ad-analyzer \
  --format='value(serviceConfig.uri)')

bash scripts/setup_cloud_scheduler.sh ivyhouse-ad-analyzer "$FUNC_URL"
```

**預期流程**：
1. 取得 Function trigger URL
2. 建立 Scheduler Job：
   - 名稱：`refresh-gdrive-token`
   - 排程：`0 0 * * 0`（每週日午夜 UTC+8）
   - HTTP 方法：GET
   - 時區：Asia/Taipei
3. 連接到 Function trigger URL

#### Step 5A-C：驗證和測試

**命令序列**：
```bash
# A. 手動觸發
gcloud scheduler jobs run refresh-gdrive-token \
  --location=asia-east1 --project=ivyhouse-ad-analyzer

# B. 查看日誌（等待 3-5 秒）
sleep 5
gcloud functions logs read refresh-oauth-token \
  --limit 10 --region=asia-east1 --project=ivyhouse-ad-analyzer

# C. 驗證 Secret 更新
gcloud secrets versions list GOOGLE_DRIVE_ACCESS_TOKEN \
  --project=ivyhouse-ad-analyzer
```

**預期結果**：
- A：Job 執行成功（status: SUCCESS）
- B：日誌包含「OAuth Token 已成功刷新」或類似訊息
- C：Secret Manager 中有新版本（時間戳最新）

---

## 🔍 RESEARCH & ASSUMPTIONS

**research_required: false**

此計畫不涉及新的外部調查需求。所有 OAuth credentials、GCP 服務設定、腳本邏輯已在前期驗證完成。

### 假設

1. ✅ **OAuth credentials 已取得**
   - Client ID、Client Secret 已存儲在 `secrets/client_secret_*.json`
   - Access Token、Refresh Token、Folder ID 已在 `ifp.env`
   - 所有 secrets 已上傳到 GCP Secret Manager（Step 2 已完成）

2. ✅ **gcloud 認證已就位**
   - 使用者已登入 gcloud（驗證）
   - Project ID：`ivyhouse-ad-analyzer` 已設定

3. ✅ **部署腳本已驗證**
   - `scripts/setup_gcp_secrets.sh` 的 glob 檢查已修正
   - `scripts/deploy_token_refresh_function.sh` 可正常啟用 APIs
   - `scripts/setup_cloud_scheduler.sh` 可建立排程任務

4. **部署不會影響現有備份功能**
   - 改動僅涉及 GCP 基礎設施，不修改備份邏輯
   - 備份腳本可無縫讀取更新後的 tokens

---

## 🔒 SCOPE & CONSTRAINTS

### 受保護的檔案清單（不可修改）

- `app.py`, `main.py`
- `core/`, `utils/`, `ui/` 目錄
- `tests/`, `.github/`, `.agent/` 目錄
- `.gitignore`, `pyproject.toml`, `requirements*.txt`

### 允許變更的檔案

- ✅ 新增：`doc/plans/Idx-044_plan.md`, `doc/logs/Idx-044_log.md`
- ✅ 修改：`scripts/setup_gcp_secrets.sh`（已完成）

### Done 定義

**各 Step 成功標準**：

| Step | 完成標準 |
|------|---------|
| 3 | Cloud Function 部署成功，HTTP GET 請求返回 200 OK + JSON 響應 |
| 4 | Scheduler Job 已建立，狀態為 ENABLED |
| 5A | Scheduler Job 可手動執行，exit code 0，status: SUCCESS |
| 5B | 函數日誌包含成功訊息（如「刷新成功」、「expires_in」） |
| 5C | Secret Manager 中 GOOGLE_DRIVE_ACCESS_TOKEN 有新版本 |

### 風險與回滾

| 風險 | 嚴重性 | 回滾方案 |
|------|--------|---------|
| Cloud Function 部署失敗 | M | 檢查 Python 語法、requirements.txt，或 gcloud API 配額 |
| Scheduler URL 錯誤 | M | 手動刪除 job：`gcloud scheduler jobs delete refresh-gdrive-token` |
| Token 刷新失敗（API 調用失敗） | M | 檢查 Secret Manager 中的 credentials；重新驗證 refresh_token 有效性 |
| 無備份影響 | L | 備份腳本改從環境變數讀取（若 Secret Manager 失敗） |

### 最大重試次數

- **Engineer 修正迴圈**：最多 2 輪（失敗 2 次後必須停下）
- **QA 驗收迴圈**：最多 1 輪（FAIL 後回 Engineer 修正）

---

## 🎬 EXECUTION_BLOCK

<!-- EXECUTION_BLOCK_START -->
```
executor_tool: opencode
executor_backend: extension-sendtext-required
qa_tool: codex
monitor_backend: proposed-primary-with-extension-fallback
last_change_tool: opencode
approval_timestamp: 2026-02-26T18:40:00Z
```
<!-- EXECUTION_BLOCK_END -->

---

## ✅ 檢查清單

### Pre-Execution Checklist

- [x] Plan 已產出並清晰
- [x] Step 2（Secret Manager）已完成
- [ ] User 確認 Plan（Approve Gate）
- [ ] User 選擇 Executor 和 QA Tool
- [ ] Plan 驗證通過：`python .agent/skills/plan_validator.py doc/plans/Idx-044_plan.md`
- [ ] Preflight 檢查通過：`python scripts/vscode/workflow_preflight_check.py --json`

### Execution Checklist

- [ ] Step 3 完成：Cloud Function 部署成功
- [ ] Step 4 完成：Cloud Scheduler Job 已建立
- [ ] Step 5A 完成：Scheduler 可手動執行
- [ ] Step 5B 完成：函數日誌驗證
- [ ] Step 5C 完成：Secret 版本更新驗證
- [ ] Engineer 輸出：`[ENGINEER_DONE]`

### QA Checklist

- [ ] 驗證 5 個 GCP 部署步驟均完成
- [ ] 確認系統端到端可運作（含自動化排程）
- [ ] QA 輸出：`[QA_DONE]` 或 `[QA_FAIL]`

---

## 📝 Notes

- **時間估計**：每步 3-5 分鐘，總計 20-30 分鐘
- **依賴順序**：Step 3 → Step 4 → Step 5（不可並行，且 Step 4 依賴 Step 3 的 URL 輸出）
- **監控頻率**：部署完成後，建議每月檢查一次 Scheduler 執行狀態

---

**計畫版本**：v1.0 (2026-02-26 18:35 UTC+8)
