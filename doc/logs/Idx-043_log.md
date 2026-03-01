# Task Execution Log: Idx-043

**Index**: Idx-043
**Plan Version**: 2026-02-25-v1
**Task Description**: Google Drive 每週備份 + Drive 端 12 週保留（只移到 Trash）

---

## 說明（補登記）

此 log 為補齊專案治理軌跡：Index 內 Idx-043 狀態為已完成，但 `Log 檔` 欄位長期為 pending 且缺檔。
本次補登記僅基於「repo 內實作與單元測試/自檢結果」提供可稽核證據；**未進行任何需要外部 Drive 憑證的端到端上傳/刪除驗收**。

---

## Evidence（Repo 內實作）

- 週備份主程式：`scripts/gdrive_weekly_backup.py`
  - Drive 路徑根：`weekly_backups/<week_id>/<fp>/`
  - 會寫入本機 manifest：`backup_manifest.gdrive.json`
- Retention（只移到 Trash）：`scripts/gdrive_retention.py`
  - 預設 dry-run，需 `--apply --confirm TRASH_OLDER_THAN_12_WEEKS` 才會執行
- UI 掛載點：`ui/steps.py`
  - Step B：落盤 raw inputs 快照到 `inputs/raw/`
  - Step F：條件式觸發 Drive 備份（失敗不阻斷 meeting 交付）
- 單元測試（純本地，不打外網）：`tests/test_gdrive_retention.py`

---

## QA Commands（本次補登記實際執行）

- `python scripts/portable/self_check.py --strict` ✅ PASS
- `pytest -q tests/test_gdrive_retention.py` ✅ PASS

---

## QA Result

- **Status**: ⚠️ PASS WITH RISK
- **Risk Notes**:
  - 未以真實 Drive 憑證做端到端上傳/Trash 驗收（避免在無憑證環境誤操作）。
  - 已有本地單元測試與 strict self-check 作為最低限度的可稽核證據。

---

## 最小 E2E 驗收清單（使用者可在安全環境執行）

> ⚠️ **資安提醒**：執行前確認不會在終端輸出任何 token/憑證值；Drive 操作建議先在 sandbox 資料夾測試，避免誤操作正式資料。

### Step 1：Cloud Run 最小存活檢查

**指令**（以實際 Service URL 替換 `$SERVICE_URL`）：

```bash
curl -I $SERVICE_URL/
```

**驗收點**：
- HTTP 200 或 302，且回應包含 HTML 內容（Streamlit 頁面）

### Step 2：Drive 週備份（兩階段）

**Dry-run 先跑**（以實際週次替換 `<YYYY-Www>`，例如 `2026-W09`）：

```bash
./.venv/bin/python -m scripts.gdrive_weekly_backup --week <YYYY-Www> --dry-run
```

**實際上傳**（確認 OAuth/SA 憑證與 Drive 目標資料夾正確後執行）：

```bash
./.venv/bin/python -m scripts.gdrive_weekly_backup --week <YYYY-Www>
```

**驗收點**：
- 版本資料夾內生成 `backup_manifest.gdrive.json`
- dry-run 時：`dry_run=true` 且 `skipped_dry_run == total_files`
- 實際上傳時：`uploaded > 0` 且 `errors == 0`

### Step 3：Retention（預設 dry-run；apply 可選）

**Dry-run**：

```bash
./.venv/bin/python -m scripts.gdrive_retention
```

**Apply（可選，僅 sandbox 環境；將符合條件的資料夾移至 Trash）**：

```bash
./.venv/bin/python -m scripts.gdrive_retention --apply --confirm TRASH_OLDER_THAN_12_WEEKS
```

**驗收點**：
- dry-run：`to_trash` 清單符合預期（僅列出，不執行）
- apply 後：`executed=true` 且 `trashed_error==0`

---

## Marker Evidence

```
[QA_DONE]
TIMESTAMP=2026-03-01T00:00:00Z
TASK_ID=Idx-043
QA_RESULT=PASS_WITH_RISK
NOTE=補登記；僅含 repo 內證據與本機測試
```

---

**Log Created**: 2026-03-01
**Last Updated**: 2026-03-01
