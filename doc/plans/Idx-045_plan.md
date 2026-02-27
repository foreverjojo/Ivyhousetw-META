# Plan: Idx-045

**Index**: Idx-045
**Created**: 2026-02-27
**Planner**: GitHub Copilot（Coordinator 兼任 Planner）

---

## 🎯 目標

讓三顧問專案在執行 Step F 觸發 Google Drive 週備份時，於 **Google Cloud 執行環境**每次都能「即時讀取 Secret Manager 的最新 `GOOGLE_DRIVE_ACCESS_TOKEN`」來進行上傳（不依賴 Streamlit/服務重啟來更新環境變數），以銜接 Idx-044 的 Scheduler 刷新 token。

---

## 📋 SPEC

### Goal
在 Step F 的 Drive 週備份流程中，當使用 Access Token（非 SA JSON）作為認證時：
- **每次備份都優先從 GCP Secret Manager 取最新 token**，確保 token 已由 Scheduler 刷新也能立即被使用。

### Non-goals
- ❌ 不新增 UI 頁面/按鈕/新的流程步驟（僅調整既有備份行為）。
- ❌ 不改動 Idx-044 的雲端部署（Cloud Function / Scheduler / Secrets 內容）
- ❌ 不把任何 token、SA JSON 內容、secret 值寫入 log/manifest。
- ❌ 不改變既有「備份失敗不阻斷主流程」的行為。

### Acceptance Criteria
1. ✅ 在 Google Cloud 執行環境（存在 `GOOGLE_CLOUD_PROJECT`）下觸發 Step F Drive 備份時，即使環境變數中的 `GOOGLE_DRIVE_ACCESS_TOKEN` 為舊值/空值，仍能成功改用 Secret Manager 的最新版本完成上傳（或在權限不足時給出可行動的 warning 並 fallback/略過）。
2. ✅ 本機環境行為不變：仍可沿用 `ifp.env` / `.env` 或既有 env var 提供 token 進行備份（不強制要求 Secret Manager）。
3. ✅ 不新增任何敏感資訊輸出：logger/manifest 不得包含 access token、client_secret、refresh_token、SA JSON 檔內容。
4. ✅ CI 基本品質門檻：`ruff check ...` 與 `pytest`（若此任務新增測試）通過。

### Edge cases
- 雲端環境但 Secret Manager 權限不足（403）→ 不得噴出 token，需 warning（含「請賦予哪個 SA 哪個角色」的可行動訊息），並 fallback 到 env token（若仍不可用則維持既有錯誤行為）。
- 使用 `GOOGLE_APPLICATION_CREDENTIALS`（SA JSON）→ 維持既有優先序（SA JSON 仍優先於 Access Token），不必讀 Secret Manager token。
- `GOOGLE_DRIVE_FOLDER_ID` 未設在環境變數但存在於 Secret Manager → 允許在雲端嘗試讀取後繼續備份（避免不必要 skip）。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources（repo 內）
- `ui/steps.py`：Step F 備份觸發點 `_trigger_gdrive_backup()`
- `scripts/gdrive_weekly_backup.py`：備份上傳流程（呼叫 `get_gdrive_access_token()`）
- `scripts/media_uploader.py`：`get_gdrive_access_token()` 現況只從 SA JSON / env token 取值
- `scripts/gcp_secret_manager.py`：已存在從 GCP Secret Manager 讀取 Drive secrets 的工具（包含 `GOOGLE_DRIVE_ACCESS_TOKEN` 與 `GOOGLE_DRIVE_FOLDER_ID`）
- `requirements.txt`：已包含 `google-cloud-secret-manager>=2.16.0`（不需新增依賴）

### Assumptions
- ✅ VERIFIED：Idx-044 已驗證 Scheduler 會刷新並更新 Secret Manager 的 `GOOGLE_DRIVE_ACCESS_TOKEN` 版本。
- ⚠️ RISK: unverified - Streamlit/執行服務使用的 Service Account 是否已具備讀取上述 secrets 的權限（需 `roles/secretmanager.secretAccessor`）。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `doc/Implementation_Plan_index.md` - 新增 Idx-045 任務列（登記任務，滿足 Index gate）
- `ui/steps.py` - （最小改動）當 `GOOGLE_DRIVE_FOLDER_ID` 缺失時，僅在雲端嘗試從 Secret Manager 取得後再決定是否 skip
- `scripts/media_uploader.py` - （核心改動）在雲端且未使用 SA JSON 時，優先從 Secret Manager 取得最新 Access Token
- `doc/plans/Idx-045_plan.md` - 本計畫檔（本次已新增）
- `doc/logs/Idx-045_log.md` - 執行日誌（由流程產出）

### Done 定義
1. ✅ Step F 週備份在雲端可「每次」讀到 Secret Manager 的最新 access token（不依賴重啟）。
2. ✅ 本機行為不被破壞；且敏感資訊不會出現在 log/manifest。

### Rollback 策略
- **Level**: L2
- **前置條件**: 可用環境變數 `ENABLE_GDRIVE_WEEKLY_BACKUP=0` 立即停用備份（避免上傳異常影響流程）。
- **回滾動作**:
  - 以 `git revert` 回退本任務 commit
  - 若需緊急停用：將 `ENABLE_GDRIVE_WEEKLY_BACKUP` 設為非 `1`

### Max rounds
- **估計**: 2
- **超過處理**: 先停下，改以最小修正（只做 token 來源，不做 folder id fallback）或拆成新 Idx。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `doc/Implementation_Plan_index.md` | 修改 | 登記 NEW TASK：Idx-045（避免 Index gate 阻擋） |
| `scripts/media_uploader.py` | 修改 | `get_gdrive_access_token()`：雲端且未用 SA 時，優先讀 Secret Manager 的 `GOOGLE_DRIVE_ACCESS_TOKEN` |
| `ui/steps.py` | 修改 | `_trigger_gdrive_backup()`：雲端且缺 `GOOGLE_DRIVE_FOLDER_ID` 時，嘗試讀 Secret Manager 後再決定 skip |
| `doc/logs/Idx-045_log.md` | 新增 | 執行/驗收紀錄 |

---

## 📝 邏輯細節

### 1) `scripts/media_uploader.py`
- 調整 `get_gdrive_access_token(cfg)`：
  - 若 `cfg.google_application_credentials` 存在：維持原本 SA JSON 流程（最穩定，不需 token）。
  - 否則：
    - 若偵測到雲端環境（`GOOGLE_CLOUD_PROJECT` 存在）→ 嘗試呼叫 `scripts.gcp_secret_manager.get_oauth_credentials()`，取回 `access_token` 並回傳。
    - 若 Secret Manager 讀取失敗（包含權限不足）→ 記錄「不含敏感資訊」的 warning，並 fallback 回 `cfg.google_drive_access_token`。
  - 安全要求：任何 log 不得輸出 token 值；僅可輸出錯誤類型/簡短訊息（截斷至固定長度）。

### 2) `ui/steps.py`
- 在 `_trigger_gdrive_backup()` 的 `GOOGLE_DRIVE_FOLDER_ID` 檢查前，加入最小 fallback：
  - 若 `cfg.google_drive_folder_id` 為空且在雲端 → 嘗試從 Secret Manager 取回 `folder_id`，成功則寫入 `os.environ["GOOGLE_DRIVE_FOLDER_ID"]` 後 reload config；失敗則維持既有 skip 行為。
- 保持「備份失敗不阻斷主流程」不變。

### 3) `doc/Implementation_Plan_index.md`
- 新增一列 Idx-045：標題可用「Step F Drive 備份：每次讀取 Secret Manager 最新 Access Token」；狀態先設 ⏳ 待處理（或依你偏好）。

---

## ⚠️ 注意事項

- **資安**：不得把任何 secret 值輸出到 log / manifest；任何錯誤訊息需截斷，避免意外包含敏感資訊。
- **權限**：若雲端 SA 無 `roles/secretmanager.secretAccessor`，本改動會讓備份回到 fallback（env token）或失敗；需在 QA/Log 明確列出該 SA 與建議的 IAM 綁定。
- **穩定性**：Secret Manager 讀取會增加一次 API 呼叫；需確保 timeout/例外處理不影響主流程。

---

## 🔗 相關資源

- `doc/plans/Idx-043_plan.md`（Drive 週備份原始設計）
- `doc/plans/Idx-044_plan.md`、`doc/logs/Idx-044_log.md`（token 自動刷新已完成）

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-02-27 01:41:33 UTC
plan_approved: 2026-02-27 02:47:04 UTC
scope_policy: strict
expert_required: false
expert_conclusion: N/A
execution_backend_policy: extension-sendtext-required
scope_exceptions: []

# Engineer 執行
executor_tool: opencode
executor_backend: ivyhouse_sendtext_extension
monitor_backend: proposed_api_monitor
executor_tool_version: [version number]
executor_user: [github-account or email]
executor_start: [執行開始時間]
executor_end: [執行結束時間]
session_id: [terminal session ID if available]
last_change_tool: opencode

# QA 執行
qa_tool: codex-cli
qa_tool_version: [version number]
qa_user: [github-account or email]
qa_start: [QA 開始時間]
qa_end: [QA 結束時間]
qa_result: [PASS|PASS_WITH_RISK|FAIL]
qa_compliance: [✅ 符合|⚠️ 例外：原因]

# 收尾
log_file_path: doc/logs/Idx-045_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

---

## ✅ 用戶確認

> 🛑 **必要停頓點**：請先確認下列「需求複述」是否正確；你 Approve 後我才會進入 Engineer/QA Gate。

### 需求複述（請你確認）
- 你希望：三顧問一鍵最終 Step F 觸發 Google Drive 週備份時，在雲端每次都能直接從 Secret Manager 取得最新 `GOOGLE_DRIVE_ACCESS_TOKEN`（而不是依賴重啟/環境變數更新），以確保 Idx-044 刷新後的 token 立即生效。
- 我將採取最小改動：主要改 `scripts/media_uploader.get_gdrive_access_token()` 增加「雲端優先讀 Secret Manager」；必要時在 `ui/steps.py` 對 `GOOGLE_DRIVE_FOLDER_ID` 做同樣的雲端 fallback，避免誤判 skip。

- [ ] 我已確認需求複述正確，允許進入下一步（User Approval Gate：Approve/Reject/Revise）
