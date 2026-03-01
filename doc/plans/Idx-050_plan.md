# Plan: Idx-050

**Index**: Idx-050
**Created**: 2026-03-01
**規劃者**: GitHub Copilot Chat（Coordinator；依 /dev 流程代行 Planner 產出 Plan）

---

## 🎯 目標

提供一份「最小 E2E 驗收清單（Drive / LLM / Cloud Run）」的可執行指令與驗收點，並將清單回填到既有治理檔案：`doc/logs/Idx-038_log.md` 與 `doc/logs/Idx-043_log.md`，讓兩項任務能在具備真實憑證/外網的環境下被安全地端到端驗收、降低 `PASS WITH RISK` 的不確定性。

---

## 📋 SPEC

### 目標
- 產出「最小、可重跑、低風險」的 E2E 驗收步驟（包含指令 + 期望輸出/判定點），並寫入兩份 log，供使用者在安全環境自行執行。

### 非目標
- ❌ 不在此任務中實際執行任何會觸發外部系統的操作（Drive 上傳/Trash、OpenRouter 呼叫、Cloud Run 部署）。
- ❌ 不新增任何新功能、不修改任何業務邏輯程式碼。
- ❌ 不重寫既有部署文件（例如 DEPLOY.md 的歷史描述）；本任務只回填「可驗收步驟」到指定 log。

### 驗收標準
1. ✅ `doc/Implementation_Plan_index.md` 新增 Idx-050 任務列（狀態可先標示為 ⏳ 待處理，待執行/QA 完成再更新）。
2. ✅ `doc/logs/Idx-038_log.md` 新增「最小 E2E 驗收清單」：聚焦 LLM（Step C/E/E2）與 E2 schema 驗證，並提供可直接執行的指令與驗收點。
3. ✅ `doc/logs/Idx-043_log.md` 新增「最小 E2E 驗收清單」：聚焦 Drive 週備份（dry-run → 實際上傳）與 retention（dry-run → 可選 apply），並包含 Cloud Run 最小存活檢查驗收點。
4. ✅ 兩份 log 的指令與驗收點「不包含任何 secret」：不得出現 API key/token 值、不得要求貼出敏感輸出；若需檢查僅能用「存在性/長度/遮罩」原則。

### 邊界情況
- 沒有 gcloud / docker：提供「本機（headless）」驗收路徑仍可跑（`scripts/debug_pipeline.py` / `python -m scripts.*`）。
- Drive 在 Shared Drive / SA quota 403：驗收步驟要明確要求先用 `--dry-run`，再確認 OAuth/SA 方式與目標資料夾權限。
- 擔心誤刪：Retention 預設 dry-run，apply 必須明確包含 `--confirm TRASH_OLDER_THAN_12_WEEKS`，並建議在 sandbox folder 測試。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### 來源
（僅使用 repo 內文件/程式碼）
- `scripts/debug_pipeline.py`：headless E2E（B→C→E→F）
- `scripts/consultants.py`：E2 交叉審核 `generate_consultant_cross_reviews(...)`
- `core/validation.py`：E2 單筆 schema 驗證 `validate_consultant_cross_review(...)`
- `scripts/gdrive_weekly_backup.py`：Drive 週備份 CLI（支援 `--dry-run`）
- `scripts/gdrive_retention.py`：Retention CLI（預設 dry-run；apply 需 confirm 字串）
- `CHECKLIST.md`：Cloud Run 驗證段落（`curl $SERVICE_URL/`）
- `CLOUD_RUN_SUMMARY.md`：健康檢查建議以 `/` 作為最小存活檢查

### 假設
- ✅ VERIFIED - LLM 金鑰環境變數鍵為 `OPENAI_API_KEY` 或 `OPENROUTER_API_KEY`（見 `scripts/consultants.py` / `scripts/llm_insights.py`）。
- ⚠️ RISK: unverified - 使用者擁有一個「可安全驗收」的 GCP 專案/Drive folder（建議使用 sandbox，避免誤操作正式資料）。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `doc/Implementation_Plan_index.md` - 新增 Idx-050 任務列（治理登記）。
- `doc/logs/Idx-038_log.md` - 回填「最小 E2E 驗收清單（LLM/E2）」。
- `doc/logs/Idx-043_log.md` - 回填「最小 E2E 驗收清單（Drive/Cloud Run）」。
- `doc/plans/Idx-050_plan.md` - 本 plan 檔。

### Done 定義
1. ✅ 兩份 log 都包含：指令（可 copy/paste）、驗收點（明確 PASS/FAIL 判斷）、以及「避免洩漏 secrets」注意事項。
2. ✅ Index 已登記 Idx-050，且 `Log 檔` 欄位指向本任務的 log（待 Engineer/QA 完成後補上）。

### Rollback 策略
- **Level**: L2
- **前置條件**: worktree 可回復（`git status` 可確認）
- **回滾動作**: 只要是文件變更，使用 `git restore --worktree --staged -- <files...>` 回復。

### Max rounds
- **估計**: 1 round（純文件修改）
- **超過處理**: 若需要新增/修改非白名單檔案 → 立即停下回報 `SCOPE BREAK`。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `doc/Implementation_Plan_index.md` | 修改 | 新增 Idx-050 任務列（治理登記） |
| `doc/logs/Idx-038_log.md` | 修改 | 新增「最小 E2E 驗收清單（LLM/E2）」 |
| `doc/logs/Idx-043_log.md` | 修改 | 新增「最小 E2E 驗收清單（Drive/Cloud Run）」 |
| `doc/logs/Idx-050_log.md` | 新增 | 本任務執行/QA 結果紀錄（由 Engineer/QA 完成後產出） |

---

## 📝 邏輯細節

### 1) `doc/logs/Idx-038_log.md` 要新增的內容（LLM / E2）

新增章節：`## 最小 E2E 驗收清單（使用者可在安全環境執行）`

包含：
- 前置條件（不貼 secret）：
  - `OPENAI_API_KEY` 或 `OPENROUTER_API_KEY` 已設定（只檢查存在性，不輸出值）
  - 有可用的 input 資料（可用 `examples/meta/`）
- Step C/E（headless）：
  - 指令（建議用專案 venv；需要已設定 `OPENAI_API_KEY` 或 `OPENROUTER_API_KEY`）：
    - `./.venv/bin/python scripts/debug_pipeline.py --input-dir examples/meta`
  - 驗收點：
    - 終端會列出 `Artifacts:` 清單，確認有產生：`report_insights.json`、`consultant_notes.json`、`workflow_state.json`、`meeting.md`
    - `report_insights.json` 與 `consultant_notes.json` 內不應包含 `error` 欄位（或 error 需為空）
- Step E2（交叉審核）：
  - 指令：提供一段可 copy/paste 的 python snippet：
    - 以 debug_pipeline 輸出的 vdir 為輸入
    - 讀取 `report_summary.json`、`report_insights.json`、`consultant_notes.json`
    - 呼叫 `scripts.consultants.generate_consultant_cross_reviews(...)`
    - 將結果寫入 `consultant_cross_reviews.json`
    - 逐一用 `core.validation.validate_consultant_cross_review(...)` 驗證 `reviews.reviewer_A/B/C` 的輸出
  - 驗收點：
    - `error_count == 0`
    - schema validator 全數通過

  （供 log 直接貼上的 snippet 內容建議如下；vdir 請替換成 debug_pipeline 輸出顯示的路徑）

  ```bash
  ./.venv/bin/python - <<'PY'
  import json
  from pathlib import Path

  from core import SCHEMAS_DIR
  from core.validation import validate_consultant_cross_review
  from scripts.consultants import generate_consultant_cross_reviews

  vdir = Path("<PASTE_VDIR_PATH_HERE>")

  def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

  rs = load(vdir / "report_summary.json")
  ri = load(vdir / "report_insights.json")
  cn = load(vdir / "consultant_notes.json")

  cr = generate_consultant_cross_reviews(rs, ri, cn, version_fp=vdir.name)
  (vdir / "consultant_cross_reviews.json").write_text(
    json.dumps(cr, ensure_ascii=False, indent=2),
    encoding="utf-8",
  )

  reviews = (cr.get("reviews") or {})
  for reviewer_key, review in reviews.items():
    validate_consultant_cross_review(review, SCHEMAS_DIR)

  print("E2 schema OK")
  print("success_count=", cr.get("success_count"), "error_count=", cr.get("error_count"))
  PY
  ```

### 2) `doc/logs/Idx-043_log.md` 要新增的內容（Drive / Cloud Run）

新增章節：`## 最小 E2E 驗收清單（使用者可在安全環境執行）`

包含：
- Cloud Run 最小存活檢查（不要求 /health）：
  - 指令：`gcloud run deploy ...`（或引用既有 service）→ `curl -I $SERVICE_URL/`
  - 驗收點：HTTP 200/302 + 回應內容為 HTML（Streamlit）
- Drive 週備份（兩階段）：
  - Dry-run：`python -m scripts.gdrive_weekly_backup --week <YYYY-Www> --dry-run`
  - 實際上傳：移除 `--dry-run`
  - 驗收點：
    - 版本資料夾內生成 `backup_manifest.gdrive.json`
    - dry-run 時 `dry_run=true` 且 `skipped_dry_run == total_files`
    - 實際上傳時 `uploaded > 0` 且 `errors == 0`
- Retention（預設 dry-run；apply 可選）：
  - Dry-run：`python -m scripts.gdrive_retention`
  - Apply（可選，僅 sandbox）：`python -m scripts.gdrive_retention --apply --confirm TRASH_OLDER_THAN_12_WEEKS`
  - 驗收點：dry-run 的 `to_trash` 清單符合預期；apply 後 `executed=true` 且 `trashed_error==0`

---

## ⚠️ 注意事項

- **資安**：log 內不得要求貼出 token 值；若需要檢查，只能寫「存在性檢查」與「遮罩輸出」。
- **破壞性操作**：Retention apply 會把資料夾移到 Trash；預設只允許 dry-run，apply 必須在 sandbox 且使用者明確確認。
- **可重跑性**：指令應以「可重跑」為優先（dry-run / headless pipeline / schema validate）。

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-03-01 05:55:00
plan_approved: 2026-03-01 06:02:00
scope_policy: strict
expert_required: false
expert_conclusion: N/A
execution_backend_policy: extension-sendtext-required
scope_exceptions: []

# Engineer 執行
executor_tool: opencode
executor_backend: ivyhouse_sendtext_extension
monitor_backend: proposed-primary-with-extension-fallback
executor_tool_version: [TBD]
executor_user: [TBD]
executor_start: [TBD]
executor_end: [TBD]
session_id: [TBD]
last_change_tool: opencode

# QA 執行
qa_tool: codex-cli
qa_tool_version: [TBD]
qa_user: [TBD]
qa_start: [TBD]
qa_end: [TBD]
qa_result: [TBD]
qa_compliance: ✅ 豁免（文件修正）- 檔案：doc/Implementation_Plan_index.md, doc/logs/Idx-038_log.md, doc/logs/Idx-043_log.md

# 收尾
log_file_path: doc/logs/Idx-050_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->
