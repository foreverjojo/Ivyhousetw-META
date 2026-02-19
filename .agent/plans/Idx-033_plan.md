# Plan: Idx-033

**Index**: Idx-033
**Created**: 2026-01-23
**Planner**: GitHub Copilot（Coordinator）

---

## 🎯 目標

1) 在主 README 與環境復原指南各加一個「一鍵自檢入口指令」，並提供可直接執行的自檢腳本。
2) 針對 `foreverwow001/agent-workflow-template` 與本 repo 的 dev workflow / roles / skills 差異，產出「可回推」的更新包與同步工具（**不包含一鍵復原/自檢模組**）。

---

## 📋 SPEC

### Goal
- 讓新加入/剛復原環境的人可以用「一行指令」完成：restore readiness 檢查 + ruff + pytest。
- 讓 template repo 可以快速同步本 repo 已落地的 workflow/skills 強化（不碰 portable restore）。

### Non-goals
- ❌ 不把 `scripts/portable/**`（一鍵復原/自檢模組）回推到 template repo。
- ❌ 不在此任務中處理與自檢無關的功能開發或大規模重構。

### Acceptance Criteria
1. ✅ `python scripts/portable/self_check.py --strict` 可在本 repo 內正常執行並回傳 0（通過）
2. ✅ 主 README 與 `doc/ENVIRONMENT_RECOVERY.md` 都有「一鍵自檢入口指令」且指向同一個入口
3. ✅ 產出 template 回推清單（檔案對應表 + 理由 + 操作步驟），並提供可重跑的同步腳本（sync `.agent/**` 相關子集）
4. ✅ 同步腳本不會觸碰 portable restore 相關路徑

### Edge cases
- 在未安裝 dev dependencies（ruff/pytest）時，自檢要回報「缺少套件」並給出可行動的安裝提示。
- 在沒有測試或 pytest 收到 no tests 時，自檢應回報合理狀態（不應當作 crash）。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- 本 repo 現有腳本：`scripts/portable/verify_restore_state.py`
- 本 repo 現有文件：`readme.md`、`doc/ENVIRONMENT_RECOVERY.md`
- 本 repo skills/workflow：`.agent/workflows/*`、`.agent/skills/*`

### Assumptions
- ✅ VERIFIED - 本 repo 目前使用 Python 3.11，並有 `requirements-dev.txt` / `pyproject.toml` 的 dev extra。
- ⚠️ RISK: unverified - 使用者具備推送 template repo 的權限（本任務只產出可套用內容/工具）。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `scripts/portable/self_check.py` - 新增：一鍵自檢入口腳本（restore readiness + ruff + pytest）
- `readme.md` - 修改：加入一鍵自檢入口指令
- `doc/ENVIRONMENT_RECOVERY.md` - 修改：加入一鍵自檢入口指令
- `scripts/template/sync_agent_workflow_to_template.py` - 新增：把本 repo 的 `.agent/` 子集同步到 template repo（排除 portable）
- `doc/AGENT_WORKFLOW_TEMPLATE_UPSTREAM.md` - 新增：回推清單（檔案對應 + 操作步驟）
- `.agent/Workflow_Plan_index.md` - 修改：登記 Idx-033
- `.agent/logs/Idx-033_log.md` - 新增：收尾 log（由 Coordinator 產出）

### Done 定義
1. ✅ 自檢腳本具備 `--strict` 與清楚的 exit code（pass=0，fail>0）
2. ✅ 文件入口一致、可複製貼上就能跑
3. ✅ template 回推內容可操作（有命令/步驟），且不包含 portable restore

### Rollback 策略
- **Level**: L2
- **前置條件**: 乾淨 worktree 才建議使用硬回滾
- **回滾動作**: `git restore --worktree --staged -- .`（tracked）+ 手動刪除新增檔案

### Max rounds
- **估計**: 2 rounds（實作→自檢→修正）
- **超過處理**: 停下來回報 blocker 並請用戶決策（縮 scope 或拆任務）

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| scripts/portable/self_check.py | 新增 | 一鍵自檢入口（verify_restore_state + ruff + pytest） |
| readme.md | 修改 | 加入「一鍵自檢入口指令」 |
| doc/ENVIRONMENT_RECOVERY.md | 修改 | 加入「一鍵自檢入口指令」 |
| scripts/template/sync_agent_workflow_to_template.py | 新增 | 同步 `.agent` 子集到 template repo（排除 portable） |
| doc/AGENT_WORKFLOW_TEMPLATE_UPSTREAM.md | 新增 | Template 回推清單（不含 portable） |
| .agent/Workflow_Plan_index.md | 修改 | 登記 Idx-033 |
| .agent/logs/Idx-033_log.md | 新增 | 完成後的 Log |

---

## 📝 邏輯細節

### 1) `scripts/portable/self_check.py`
- 預設流程（建議順序）：
  1. `python scripts/portable/verify_restore_state.py --strict`
  2. `python -m ruff check ...`（依 repo 建議路徑）
  3. `python -m ruff format --check ...`
  4. `python -m pytest tests/ -q`
- CLI flags：
  - `--strict`：失敗即 fail（非 strict 可允許部分 warning）
  - `--json`（可選）：輸出 machine-readable 結果（若時間足夠）
  - `--skip-tests`（可選）：只跑 lint/restore
- Exit codes：0 pass；1 fail；2 error（例如 command not found）

### 2) 文件更新（`readme.md` / `doc/ENVIRONMENT_RECOVERY.md`）
- 新增一段「一鍵自檢」區塊：
  - 一行指令：`python scripts/portable/self_check.py --strict`
  - 補充：如果沒裝 dev deps，提示用 `pip install -r requirements.txt -r requirements-dev.txt` 或 `uv sync --extra dev`

### 3) Template 回推（不含 portable）
- 新增同步腳本 `scripts/template/sync_agent_workflow_to_template.py`：
  - 目標：把本 repo 的 `.agent/workflows`、`.agent/skills`、`.agent/roles`、`.agent/VScode_system`、以及必要的 `.agent/scripts/{setup_workflow.sh,run_codex_template.sh}` 同步到 template repo 路徑
  - 必須支援 `--dry-run`，並在實際寫入前列出將覆蓋的檔案
  - 必須有 `--apply` 才會真的寫入
- 新增文件 `doc/AGENT_WORKFLOW_TEMPLATE_UPSTREAM.md`：
  - 檔案對應表（本 repo → template repo）
  - 為什麼要回推（改善點）
  - 最小套用步驟（含 dry-run）

---

## ⚠️ 注意事項

- **資安**：不得新增任何 token/API key；同步腳本需避免複製 `.agent/logs`、`.agent/plans`、`.agent/active_sessions.json` 等可能含環境資訊的檔案。
- **Scope**：除 whitelist 外不改動其他檔案。

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-01-23 07:05:00
plan_approved: 2026-01-23 07:13:17+00:00
scope_policy: strict
expert_required: false
expert_conclusion: N/A
scope_exceptions: []

# Engineer 執行
executor_tool: opencode
executor_tool_version: N/A
executor_user: copilot
executor_start: 2026-01-23 07:13:17+00:00
executor_end: 2026-01-23 07:26:49+00:00
session_id: N/A
last_change_tool: opencode

# QA 執行
qa_tool: codex-cli
qa_tool_version: N/A
qa_user: copilot
qa_start: 2026-01-23 07:20:00+00:00
qa_end: 2026-01-23 07:26:49+00:00
qa_result: PASS_WITH_RISK
qa_compliance: ✅ 符合（依用戶指示自動選擇預設工具組合）

# 收尾
log_file_path: .agent/logs/Idx-033_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

---

## ✅ 用戶確認

- [ ] Spec 已確認，可進入 Engineer
- [ ] Engineer Tool 已選擇：`codex-cli` 或 `opencode`
- [ ] QA Tool 已選擇：`codex-cli` 或 `opencode`（必須 ≠ last_change_tool）
