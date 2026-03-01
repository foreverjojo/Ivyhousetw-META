# Plan: Idx-049

**Index**: Idx-049
**Created**: 2026-03-01
**Planner**: GitHub Copilot

---

## 🎯 目標

修正「一鍵最終」Step F 週備份：已可在 Google Drive 建立 `weekly_backups/<week>/<fp>/` 資料夾，但檔案實際上傳全部失敗（manifest 顯示 403：`Service Accounts do not have storage quota`）。

---

## 📋 SPEC

### Goal
在不改變現有備份資料夾結構的前提下，讓週備份在遇到 Service Account 配額限制時，能自動改用 OAuth Access Token 上傳並成功落盤 manifest。

### Non-goals
- ❌ 不重做 Idx-043 的備份路徑/保留策略（仍維持 `weekly_backups/<week>/<fp>/`）。
- ❌ 不新增 UI 頁面/額外流程。
- ❌ 不在程式碼內硬編碼任何 token/金鑰。
- ❌ 不在本次任務中重新實作 OAuth refresh（Idx-044 已有 token 自動化）。

### Acceptance Criteria
1. ✅ 針對本次失敗案例（manifest 顯示 403 quota），重新跑 Step F 後，Drive 目標資料夾內可看到備份檔案（至少 `meeting.md`、`workflow_state.json`）。
2. ✅ `backup_manifest.gdrive.json` 顯示 `uploaded > 0`，且每個成功檔案帶有 `remote_url`。
3. ✅ 若 OAuth token 不可用，manifest 的 `error` 必須包含可行動提示（例如：需改用 OAuth 或改放 Shared Drive），且不包含 token 值。
4. ✅ 不影響既有「Shared Drive + Service Account 可上傳」的路徑：只有在偵測到特定 403 quota 錯誤時才切換。

### Edge cases
- 若第一個檔案就觸發 403 quota：應切換到 OAuth 並重試該檔案一次，後續檔案沿用 OAuth。
- 若 OAuth token 也失敗（401/403）：仍需把每個檔案的錯誤寫入 manifest 以利追查。
- 若目標本來就在 Shared Drive 且 SA 正常：不應改用 OAuth（避免不必要的依賴）。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- history/2025-W49/meta/versions/fp-45a2ae50/backup_manifest.gdrive.json（顯示每個檔案 `Drive 上傳失敗（403）` 且訊息含 `Service Accounts do not have storage quota`）
- scripts/gdrive_weekly_backup.py（週備份實作）
- scripts/media_uploader.py::get_gdrive_access_token（Drive token 取得邏輯：SA 優先）
- core/cloud_config.py（雲端設定載入）

### Assumptions
- ✅ VERIFIED - 目前週備份待上傳檔案清單非空（manifest total_files=10）。
- ✅ VERIFIED - 失敗主因為「使用 SA token 上傳檔案」被 Drive quota 規則擋下（403）。
- ⚠️ RISK: unverified - 執行環境能取得有效的 OAuth access token（可能來自 env 或 Secret Manager 最新版本）。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- scripts/media_uploader.py - 擴充 token 取得 API（允許在 SA 存在時改取 OAuth token）。
- scripts/gdrive_weekly_backup.py - 偵測 403 quota 後切換 OAuth token 並重試上傳。
- doc/Implementation_Plan_index.md - 新增 Idx-049 任務列（避免 State Gate/稽核斷鏈）。
- doc/logs/Idx-049_log.md - 任務收尾稽核 Log（workflow 必要產物）。

### Done 定義
1. ✅ 在本機實測 Step F（或 CLI）可成功上傳檔案到 Drive。
2. ✅ 失敗時 manifest 的錯誤訊息可行動、無敏感資訊。

### Rollback 策略
- **Level**: L2
- **前置條件**: worktree 可回復（`git status --porcelain` 可清空）
- **回滾動作**: `git restore --worktree --staged -- scripts/media_uploader.py scripts/gdrive_weekly_backup.py doc/Implementation_Plan_index.md`

### Max rounds
- **估計**: 2 回合（一次修正 + 一次 QA/再修正）
- **超過處理**: 若仍無法上傳，停下改以「明確要求 Shared Drive」或「要求提供 OAuth token 來源」兩選一，避免盲試。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| scripts/media_uploader.py | 修改 | 讓呼叫端可指定「強制 OAuth」取得 token（即使 SA JSON 存在）。 |
| scripts/gdrive_weekly_backup.py | 修改 | 遇到 403 quota 時，自動切換 OAuth token，重試一次並繼續上傳。 |
| doc/Implementation_Plan_index.md | 修改 | 新增 Idx-049 任務列與狀態欄位。 |
| doc/logs/Idx-049_log.md | 新增 | 任務執行/QA 稽核紀錄（完成後補齊）。 |

---

## 📝 邏輯細節

### 1. scripts/media_uploader.py
- 調整 `get_gdrive_access_token(cfg)`：新增參數或新增同等功能的 helper（不破壞既有呼叫點），支援：
  - `mode="auto"`（預設）：維持現況（SA JSON 優先）。
  - `mode="oauth"`：忽略 SA JSON，改走「雲端 Secret Manager 最新 token → env token」流程。
- 資安：不得 log token 值；若讀取 Secret Manager 失敗只記錄 error type。

### 2. scripts/gdrive_weekly_backup.py
- 在逐檔上傳時，若捕捉到 `RuntimeError` 且內容符合：
  - HTTP 403
  - 且訊息包含 `Service Accounts do not have storage quota`
  則觸發一次性切換：
  1) 以 `mode="oauth"` 取得 token（若無 token → 在 manifest 以可行動提示標記 error）
  2) 用 OAuth token 重新確保備份路徑（沿用同一 root/week/fp）
  3) 立刻重試「當前失敗檔案」一次
  4) 後續檔案沿用 OAuth token
- manifest：每個檔案仍保留既有 entry schema；錯誤訊息需包含「應改用 OAuth 或改放 Shared Drive」的提示，但不可包含 token。

### 3. doc/Implementation_Plan_index.md
- 新增一列：Idx-049（本任務），狀態先設為 ⏳ 待處理，Executor/QA TBD。

---

## ⚠️ 注意事項

- **風險提示**：OAuth token 若過期會 401；此情境需引導使用者確認 Idx-044 的 token 刷新是否生效。
- **資安考量**：任何 log/manifest 都不能輸出 access token 內容。
- **相依性**：此修正不應影響素材上傳（Stage 3）；僅在週備份遇到特定 403 quota 才切換。

---

## 🔗 相關資源

- doc/Implementation_Plan_index.md（Index 追蹤）
- doc/plans/Idx-043_plan.md（既有週備份設計參考）
- doc/logs/Idx-044_log.md（OAuth token 自動化）

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-03-01 03:00:00
plan_approved: 2026-03-01 03:00:50
scope_policy: strict
expert_required: false
expert_conclusion: N/A
execution_backend_policy: extension-sendtext-required
scope_exceptions: []

# Engineer 執行
executor_tool: opencode
executor_backend: ivyhouse_sendtext_extension
monitor_backend: proposed_api_monitor
executor_tool_version: 1.2.15
executor_user: [github-account or email]
executor_start: 2026-03-01 03:00:50
executor_end: 2026-03-01 03:09:27
session_id: [terminal session ID if available]
last_change_tool: opencode

# QA 執行
qa_tool: codex-cli
qa_tool_version: 0.106.0
qa_user: [github-account or email]
qa_start: 2026-03-01 03:06:00
qa_end: 2026-03-01 03:09:27
qa_result: PASS
qa_compliance: ✅ 符合

# 收尾
log_file_path: doc/logs/Idx-049_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

---

## ✅ 用戶確認

- [ ] Spec 已確認，可進入 Step 2（此任務不需 Meta Expert，可略過）
- [ ] Engineer Tool 已選擇：`[codex-cli|opencode]`
- [ ] QA Tool 已選擇：`[codex-cli|opencode]`（必須 ≠ last_change_tool）
- [ ] Execution Backend Policy 已確認：`extension-sendtext-required`
- [ ] Monitor Backend Policy 已確認：`proposed-primary-with-extension-fallback`
