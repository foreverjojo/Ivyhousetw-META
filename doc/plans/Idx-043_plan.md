# Plan: Idx-043

**Index**: Idx-043
**Created**: 2026-02-25
**Planner**: GitHub Copilot（Coordinator 兼任 Planner）

---

## 🎯 目標

讓三顧問專案在每次成功產出 `meeting.md` 後，能把「本週分析所需的關鍵產物（含上傳報表/媒體的快照）」備份到 Google Drive，並提供一個安全的 Retention 機制：**只刪除 Google Drive 上的舊備份（移到 Trash，可回復），本機檔案不做任何刪除**，預設只保留最近 **12 週**。

---

## 📋 SPEC

### Goal
- 建立「每週備份到 Google Drive」能力：包含報表（原始上傳檔）、meeting summary、history 中的關鍵 JSON/Markdown 產物。
- 建立「Drive 端 12 週保留」能力：只針對本任務建立的備份資料夾樹做 Retention；預設 **dry-run**，且需要 **二次確認** 才能實際移到 Trash。

### Non-goals
- ❌ 不刪除本機任何檔案（你會自行處理本機備份/清理）。
- ❌ 不做永久刪除（不做 Drive `delete`，僅 `trashed=true`）。
- ❌ 不新增 UI 頁面/按鈕/流程步驟（避免 UX 擴張）；僅做「流程內部落盤」與提供 CLI 腳本。
- ❌ 不把任何 `.env`、token、Service Account JSON 檔上傳到 Drive 或寫進 log。

### Acceptance Criteria
1. ✅ Step B 能把「使用者上傳的原始報表檔」以 bytes 快照方式落盤到版本資料夾（`history/<week_id>/meta/versions/<fp>/inputs/raw/`），至少包含：
   - Meta：adset CSV、ads CSV、web Excel
   - Shopee/Momo：raw CSV/XLSX
2. ✅ Step F（成功寫出 `meeting.md`）後，若啟用備份開關，會上傳該版本資料夾的「白名單產物」到 Drive 專用資料夾樹：
   - Drive 路徑（概念）：`<GOOGLE_DRIVE_FOLDER_ID>/weekly_backups/<week_id>/<fp>/...`
   - 上傳失敗不得阻斷主流程（必須 graceful degradation：只警告/記錄，meeting 仍正常生成）。
3. ✅ Retention CLI 腳本只針對 `weekly_backups/` 之下的週資料夾執行，且：
   - 預設 `--dry-run` 僅列出將被移到 Trash 的清單
   - 必須提供 `--apply` 且 `--confirm <固定字串>` 才會真正執行（移到 Trash）
4. ✅ 任何 manifest/log 不得出現敏感資訊：
   - 不輸出 Access Token
   - 不輸出 SA JSON 檔內容
   - 不把 SA JSON 檔本身上傳
5. ✅ 具備可驗收的「操作指令」與失敗排查路徑（例如缺少 env、權限不足、folderId 無效）。

### Edge cases
- `CLOUD_MEDIA_PROVIDER != gdrive` 或未設定 `GOOGLE_DRIVE_FOLDER_ID`：
  - 備份功能應直接跳過（或只做 dry-run 記錄），不得報錯中止主流程。
- 週資料夾命名不符合 `YYYY-Www`（例如 `Shopee_YYYY-MM-DD`）：
  - Retention 以「可解析」為前提；無法解析者預設不刪。
- 使用者重跑同一週、同一 fp：
  - 允許覆寫/重上傳同名檔，但 manifest 需可追溯（至少記錄 timestamp + local_path + remote_id）。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources（repo 內）
- `core/cloud_config.py`：雲端 provider 與 Google Drive 認證來源
- `scripts/media_uploader.py`：Google Drive REST v3 multipart upload、子資料夾建立
- `ui/steps.py`：Step B/F 產物落盤位置與流程掛載點
- `scripts/moderator_meeting.py`：`write_artifacts()` 寫入 `meeting.md`/`workflow_state.json`

### Assumptions
- ✅ VERIFIED（以 repo 現況）：Drive 上傳可用 `requests + access token` 直連 REST v3。
- ⚠️ RISK: unverified - 將資料夾設為 `trashed=true` 是否足以達成「整週資料夾在 Drive UI 中消失且不再造成干擾」。
  - 風險緩解：Retention 預設 dry-run + 二次確認 + 使用 Trash（可回復），且僅作用於 `weekly_backups/` 之下的資料夾。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `ui/steps.py` - 在 Step B 落盤原始上傳檔快照；在 Step F 成功後（條件式）觸發備份
- `scripts/gdrive_weekly_backup.py` - 新增：負責上傳指定版本資料夾白名單產物至 Drive + 寫入備份 manifest
- `scripts/gdrive_retention.py` - 新增：Drive 端 Retention（只對 `weekly_backups/`），支援 dry-run 與二次確認
- `tests/test_gdrive_retention.py` - 新增（如專案既有測試模式允許）：測試週字串解析/排序/保留計算（不打外網）

### Done 定義
1. ✅ 版本資料夾能包含 inputs/raw 快照（可人工檢查檔案存在）
2. ✅ `scripts/gdrive_weekly_backup.py` 能在 dry-run 與 upload 模式運作（upload 模式需真實 Drive 憑證）
3. ✅ `scripts/gdrive_retention.py` 能在 dry-run 列出將被 Trash 的週資料夾，且 apply 需要 confirm

### Rollback 策略
- **Level**: L2
- **前置條件**: 任何自動備份/Retention 都必須可透過 env 關閉
- **回滾動作**:
  - 關閉備份：移除/關閉環境變數開關（見「注意事項」）
  - 程式回滾：`git revert` 相關 commit
  - Drive 回復：從 Trash 還原被移除的週資料夾（不做永久刪除）

### Max rounds
- **估計**: 2
- **超過處理**: 停下來調整 scope（例如只先做「備份」不做「Retention」）

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `ui/steps.py` | 修改 | Step B 落盤 raw inputs；Step F 條件式呼叫 Drive 備份（失敗不阻斷） |
| `scripts/gdrive_weekly_backup.py` | 新增 | 版本資料夾白名單上傳至 Drive，建立 `weekly_backups/<week>/<fp>` 結構，寫 manifest（無敏感資訊） |
| `scripts/gdrive_retention.py` | 新增 | Drive 端 12 週保留（只移到 Trash），dry-run + `--apply --confirm` |
| `tests/test_gdrive_retention.py` | 新增（可選） | 純本地測試：週解析/排序/保留計算 |

---

## 📝 邏輯細節

### 1) `ui/steps.py`
- Step B：在建立 `vdir` 後，把本次上傳檔案 bytes 快照寫到：
  - `vdir/inputs/raw/`
  - 命名採固定名（例如 `meta_adset.csv`、`meta_ads.csv`、`web.xlsx`、`shopee_raw.csv`、`momo_raw.xlsx`），避免把使用者原始檔名（可能含個資）直接寫入公開位置。
- Step F：`write_artifacts()` 成功後，若環境變數啟用（例如 `ENABLE_GDRIVE_WEEKLY_BACKUP=1`）且 provider 為 gdrive，則：
  - 呼叫 `scripts/gdrive_weekly_backup.py` 的 Python 函式（避免 shell 注入）
  - 失敗只記錄 warning，不 raise（確保 meeting 交付不受影響）

### 2) `scripts/gdrive_weekly_backup.py`
- 輸入：`week_id`、`vdir`（或 `--latest` 自動找 latest 版本）
- 行為：
  - 取得 token（沿用 `core.cloud_config.load_cloud_config()` + `scripts.media_uploader.get_gdrive_access_token()` 或等價函式）
  - 在 `GOOGLE_DRIVE_FOLDER_ID` 下確保存在 `weekly_backups/<week_id>/<fp>/`
  - 僅上傳白名單檔案：
    - `meeting.md`, `workflow_state.json`, `report_summary.json`, `report_insights.json`, `consultant_notes.json`, `pipeline_state.json`, `inputs.json`
    - `inputs/raw/**`（原始上傳檔快照）
  - 寫入本機 manifest：`vdir/backup_manifest.gdrive.json`
    - 只包含：timestamp、local_rel_path、sha256_8、size、remote_id、remote_url
    - 絕不包含：token、SA JSON 路徑、任何環境變數內容

### 3) `scripts/gdrive_retention.py`
- 只針對 `weekly_backups/` 之下的「週資料夾」做保留：
  - 保留最近 `KEEP_WEEKS=12`
  - 預設 dry-run：列出將被 Trash 的週資料夾（id/name）
  - 需要 `--apply` 並且 `--confirm TRASH_OLDER_THAN_12_WEEKS`（固定字串）才執行
  - 執行方式：以 Drive API 將 folder 設為 `trashed=true`（可回復）

---

## ⚠️ 注意事項

- **誤刪防護（你已指定為重要項）**：Retention 預設不執行、只 dry-run，且只能移到 Trash；不做永久刪除。
- **敏感資訊防護（你已指定為重要項）**：備份來源限定在 `history/<week>/.../versions/<fp>/` 並採白名單挑檔；log/manifest 做 redaction，不記 token/憑證。

---

## 🔗 相關資源

- `doc/CLOUD_INTEGRATION.md`（若需要補充 env 參數，後續再更新）

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-02-25 17:40:00
plan_approved: 2026-02-25 17:45:37 UTC
scope_policy: strict
expert_required: false
expert_conclusion: N/A
execution_backend_policy: extension-sendtext-required
scope_exceptions: ["bridge-injection-approved"]

# Engineer 執行
executor_tool: opencode
executor_backend: sendtext_bridge_client
monitor_backend: proposed_api_monitor
executor_tool_version: unknown
executor_user: vscode
executor_start: unknown
executor_end: unknown
session_id: N/A
last_change_tool: opencode

# QA 執行
qa_tool: codex-cli
qa_tool_version: unknown
qa_user: vscode
qa_start: unknown
qa_end: 2026-02-25T18:21:09Z
qa_result: PASS
qa_compliance: ✅ 符合（qa_tool=codex-cli != last_change_tool=opencode）

# 收尾
log_file_path: doc/logs/Idx-043_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->
