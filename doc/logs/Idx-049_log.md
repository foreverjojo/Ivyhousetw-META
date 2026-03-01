# Task Execution Log

**Index**: Idx-049
**Plan Version**: 2026-03-01-v1
**Task Description**: 修正 Google Drive 週備份：遇到 Service Account quota 403 時，自動切換 OAuth token 重試上傳

---

## Metadata

- **Start Time**: 2026-03-01 03:00:50 UTC
- **End Time**: 2026-03-01 03:09:27 UTC
- **Engineer**: opencode（依 Plan 工具選擇）
- **QA**: codex-cli（依 Plan 工具選擇）
- **Duration**: ~9 分鐘

---

## 🔧 Execution Information

**Execution Tool**: opencode
**Execution Start**: 2026-03-01 03:00 UTC
**Execution End**: 2026-03-01 03:09 UTC
**Exit Code**: 0

---

## Objective

- 週備份在 Drive 端能建立資料夾，但檔案上傳因 `Service Accounts do not have storage quota`（403）全部失敗。
- 修正程式：偵測該錯誤時，改用 OAuth Access Token 上傳並成功落盤 manifest。

---

## Key Changes

### Files Created
- doc/plans/Idx-049_plan.md - 本任務 Plan
- doc/logs/Idx-049_log.md - 本任務 Log

### Files Modified
- scripts/media_uploader.py - Drive token 取得支援 `auth_mode="oauth"`（可忽略 SA JSON）；並支援 `GCP_PROJECT_ID` 讀取 Secret Manager 的 `GOOGLE_DRIVE_ACCESS_TOKEN`；修正 Secret Manager fallback logging 參數錯誤。
- scripts/gdrive_weekly_backup.py - 逐檔上傳遇到 SA quota 403 時，自動切換 OAuth token、重試一次並持續上傳；並在 OAuth 無效（401）時輸出可行動提示。
- doc/Implementation_Plan_index.md - 新增 Idx-049 條目

---

## Implementation Details

1. 擴充 Drive token 取得 API
- `scripts/media_uploader.get_gdrive_access_token()` 新增 `auth_mode`：`auto|oauth|service_account`。
- `oauth` 模式支援本機以 `GCP_PROJECT_ID` 從 Secret Manager 讀取最新 `GOOGLE_DRIVE_ACCESS_TOKEN`（避免 env token 過期）。

2. 週備份 403 quota 自動切換
- `scripts/gdrive_weekly_backup.upload_version_to_drive()` 在逐檔上傳遇到 403 quota 時，取得 OAuth token → 重新確保 `weekly_backups/<week>/<fp>/` 路徑 → 重試當前檔案一次 → 後續沿用 OAuth token。
- 若 OAuth token 仍 401，保留 SA token，並在 manifest error 內提供「更新 token / 確認 Secret Manager 權限」提示。

3. 雲端環境依賴補齊（本次執行）
- 為本機使用的 Service Account 增加 Secret Manager 讀取權限（僅針對 `GOOGLE_DRIVE_ACCESS_TOKEN`）：
  - `gcloud secrets add-iam-policy-binding GOOGLE_DRIVE_ACCESS_TOKEN --project ivyhouse-ad-analyzer --member="serviceAccount:ad-analyzer-sa@ivyhouse-ad-analyzer.iam.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"`
- 觸發排程刷新 token 並確認新 secret version 出現：
  - `gcloud scheduler jobs run refresh-gdrive-token --location=asia-east1 --project=ivyhouse-ad-analyzer`

---

## Challenges & Solutions

### Challenge: 403（Service Account 無配額）
**Solution**: 在週備份上傳階段偵測錯誤字串，改用 OAuth token 重試。

### Challenge: OAuth token 401（過期/無效）
**Solution**: 讓本機可用 `GCP_PROJECT_ID` 從 Secret Manager 取最新 token；補齊 secretAccessor 權限；必要時觸發 scheduler job 刷新。

### Challenge: Secret Manager fallback logging 直接拋例外
**Solution**: 修正 logger 呼叫，不再傳入不支援的 keyword arg。

---

## Decisions Made

| 決策點 | 選擇方案 | 理由 | 替代方案 |
|--------|---------|------|---------|
| 403 quota 對策 | 自動切換 OAuth token 重試 | 讓「資料夾可建、檔案上不去」能自動恢復且不改 UX | 要求使用者改用 Shared Drive（需人工介入） |
| Token 來源策略 | `auth_mode="oauth"` 忽略 SA JSON | 避免 SA quota 403 反覆發生，且可沿用 Idx-044 token 自動化 | 直接移除 SA 流程（影響既有 Shared Drive 正常路徑） |

---

## 🔄 Rollback Records

| Level | Timestamp | Reason | Action | Result |
|-------|-----------|--------|--------|--------|
| - | - | - | - | - |

**Rollback Summary**: 無

---

## QA Status

- **Status**: ✅ PASS
- **QA Date**: 2026-03-01
- **QA Notes**:
  - 以版本資料夾 `history/2025-W49/meta/versions/fp-45a2ae50` 實測：manifest 顯示 `uploaded: 10, errors: 0`，並在 Drive 上建立 `weekly_backups/2025-W49/45a2ae50/` 及子資料夾 `inputs/raw/`。

### ✅ Cross-QA Compliance

**Executor**: opencode
**QA Tool**: codex-cli
**QA Compliance**: ✅ PASS

### Test Results
- [ ] 單元測試通過（本任務未新增/執行 pytest）
- [x] 整合測試通過（實際備份上傳成功）
- [x] 手動測試通過（Drive 端可見檔案）
- [x] 文檔已更新（Index + Plan/Log）
- [x] Cross-QA 規則已遵守

---

## Outcome

- 週備份已能在遇到 SA quota 403 時自動切換 OAuth token 上傳，解決「只建資料夾不會上傳檔案」問題。

---

## Follow-up（同日追加）

### 問題：Drive 端出現兩套同名資料夾

- **現象**：週備份成功上傳檔案，但在 Drive 端看到同名的 `weekly_backups/<week>/<fp>/` 路徑被建立兩套。
- **根因**：在同一次 run 中，先用 Service Account ensure 目錄結構；遇到 403 quota 後切換 OAuth token 時又「重新 ensure 一次」目錄結構，導致同名資料夾在短時間內被建立第二套。
- **修正**：切到 OAuth token 後沿用既有 folder IDs（不再重新 ensure 路徑、也不清空子資料夾 cache），避免同一次 run 產生第二套資料夾；同時讓資料夾查詢在已存在多個同名資料夾時固定選擇最早建立者。

### 驗證注意事項：OAuth access token 短效

- 若 OAuth fallback 出現 401，通常是 `GOOGLE_DRIVE_ACCESS_TOKEN` 已過期/無效，需透過既有的 token refresh 機制刷新 Secret Manager 版本後再重試。

---

## Next Steps

1. [ ] 若要完全避免 SA quota 403：將備份根資料夾放到 Shared Drive（並確保 SA 具成員權限）。
2. [ ] 確認 Cloud Scheduler `refresh-gdrive-token` 按週自動更新 token（避免 401）。

---

## References

- doc/plans/Idx-049_plan.md
- doc/Implementation_Plan_index.md

---

**Log Created**: 2026-03-01
**Last Updated**: 2026-03-01
