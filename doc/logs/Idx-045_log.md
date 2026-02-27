# Log: Idx-045

**Index**: Idx-045
**Date**: 2026-02-27

## Summary
Step F 觸發 Google Drive 週備份時，在 **GCP 雲端環境**每次取得 access token 的來源改為「即時讀取 Secret Manager latest」，避免依賴服務重啟/環境變數更新；同時在 folder id 缺失時，雲端會嘗試從 Secret Manager 取得 `GOOGLE_DRIVE_FOLDER_ID` 後再決定是否略過備份。

## Changes
- scripts/media_uploader.py
  - `get_gdrive_access_token()`：
    - SA JSON（`GOOGLE_APPLICATION_CREDENTIALS`）維持最高優先序。
    - 雲端（存在 `GOOGLE_CLOUD_PROJECT`）且未用 SA JSON 時：每次優先從 Secret Manager 讀取 `GOOGLE_DRIVE_ACCESS_TOKEN`（latest）。
    - Secret Manager 讀取失敗/空值：warning（不含敏感資訊）並 fallback 回環境變數 token。
- ui/steps.py
  - `_trigger_gdrive_backup()`：
    - 若 `GOOGLE_DRIVE_FOLDER_ID` 缺失且在雲端：嘗試從 Secret Manager 讀取 `GOOGLE_DRIVE_FOLDER_ID`（latest），成功則寫入 env 並 reload config 後繼續。
    - 讀取失敗/空值：warning（不含敏感資訊）並略過備份（不阻斷主流程）。
- doc/Implementation_Plan_index.md
  - 新增 Idx-045 任務列。

## Verification
- Lint（阻擋型）：`ruff check . --select=E9,F63,F7,F82 --target-version=py311` ✅
- Tests：`pytest tests/ -q` ✅（1 skipped：golden files 尚未建立）

## Notes / Risks
- IAM 權限：雲端執行服務的 Service Account 需具備 `roles/secretmanager.secretAccessor` 才能讀取：
  - `GOOGLE_DRIVE_ACCESS_TOKEN`
  - `GOOGLE_DRIVE_FOLDER_ID`
  若權限不足（常見 403），本次改動會走 fallback（token）或略過備份（folder id）。
- 資安：log 僅記錄行為/錯誤類型，不輸出 token 值或任何 secret 內容。

## Rollback
- 立即停用備份：設定 `ENABLE_GDRIVE_WEEKLY_BACKUP!=1`（例如 `0`）。
- 程式回退：以 `git revert` 回退本任務相關變更。
