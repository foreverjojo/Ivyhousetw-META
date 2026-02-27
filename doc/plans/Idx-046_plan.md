# Plan: Idx-046

**Index**: Idx-046
**Created**: 2026-02-27
**Planner**: GitHub Copilot（Coordinator）

---

## 🎯 目標

清理目前剩餘的兩個 git stash（`stash@{0}`、`stash@{1}`），以「各自建立 recovery 分支 → 套用 stash → commit + push」的方式保存變更，同時確保 `main` 分支不被污染、工作目錄最後回到乾淨狀態。

---

## 📋 SPEC

### Goal
把兩個 stash 都轉成可追溯的遠端分支（含 commit），並將 stash 清空。

### Non-goals
- ❌ 不將 stash 內容直接 merge/cherry-pick 回 `main`（僅保存到 recovery branches）。
- ❌ 不重構/整理 stash 內的程式碼品質（只做必要的敏感資訊檢查與基本驗證）。
- ❌ 不修改 stash 內文件/程式內容（除非遇到明確的敏感資訊或無法 commit 的阻擋問題）。

### Acceptance Criteria
1. ✅ GitHub 上存在兩個 recovery 分支，各自包含對應 stash 的 commit。
2. ✅ `git stash list` 為空（或至少不再包含這兩筆）。
3. ✅ `main` 回到乾淨狀態（`git status --porcelain` 無輸出）。
4. ✅ 產出對應 log，記錄分支名稱、commit hash、驗證結果與風險。

### Edge cases
- stash 內含「當時的 untracked 檔」→ 使用 `git stash branch` 以避免在 `main` 直接 apply 造成衝突。
- recovery 分支建立後，內容可能與目前 `main` 差距很大 → 僅做保存，不強行對齊。
- 若掃描到疑似 secret/token 片段 → 必須先停下，改用 placeholder 或移除敏感片段後才允許 push。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- 本次現場盤點（Coordinator 以 `git stash show --include-untracked` 取得檔案清單與統計）

### Assumptions
- ✅ VERIFIED - 使用 `git stash branch <branch> <stash>` 可在 stash 原始基底 commit 上建立分支並套用變更，降低與目前 `main` 的衝突風險。
- ✅ VERIFIED - 依 repo 規範，git 操作需在 Project terminal/SCM 執行（不注入到 Codex/OpenCode 終端）。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist（針對 `main`）
- `doc/plans/Idx-046_plan.md` - 本計畫文件
- `doc/logs/Idx-046_log.md` - 執行紀錄（將在完成後新增）
- `doc/Implementation_Plan_index.md` - 新增 Idx-046 任務列（保存/清理 stash）

> 注意：stash 內容會被保存到「recovery 分支」並 push；不會直接改動 `main`。

### Branch scopes（將被保存到 recovery branches 的檔案）
- `stash@{0}: wip: out-of-scope pre Idx-038`
  - `.agent/Workflow_Plan_index.md`
  - `.agent/roles/coordinator.md`
  - `pages/02_report_generation.py`
  - `scripts/sendtext_bridge_client.py`
  - `tools/vscode_terminal_orchestrator/extension.js`
  - `tools/vscode_terminal_orchestrator/package.json`
  - （另含當時的 untracked 版本：`.agent/plans/Idx-041_plan.md`、`.agent/logs/Idx-041_log.md`）

- `stash@{1}: wip: park non-Idx-037 changes`
  - `core/__init__.py`
  - `core/validation.py`
  - `doc/Implementation_Plan_index.md`
  - `schemas/consultant_notes.v1.json`
  - `schemas/report_insights.v1.json`
  - `schemas/workflow_state.v1.json`
  - `scripts/consultants.py`
  - `scripts/json_to_readable.py`
  - `scripts/self_test.py`
  - `ui/steps.py`

### Done 定義
1. ✅ 兩個 stash 都完成「建立 recovery 分支 → commit → push」
2. ✅ stash 清空 + `main` 乾淨
3. ✅ log/index 更新完成

### Rollback 策略
- **Level**: L2
- **前置條件**: `main` 分支乾淨可切換
- **回滾動作**:
  - 若 recovery 分支 push 後發現不應存在：刪除遠端分支（需你確認）
  - 本地恢復到 `main`：`git checkout main` + `git status --porcelain` 確認乾淨

### Max rounds
- **估計**: 2
- **超過處理**: 若任一 stash 因衝突/敏感資訊無法安全 push，停止並回報，請你決定：改成 drop、或改為另開新 Idx 計畫整理後再提交。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `doc/plans/Idx-046_plan.md` | 新增 | 本計畫文件 |
| `doc/logs/Idx-046_log.md` | 新增 | 執行紀錄（分支/commit/驗證/風險） |
| `doc/Implementation_Plan_index.md` | 修改 | 新增 Idx-046 列，記錄 stash recovery |

---

## 📝 邏輯細節

### 1) 建立 recovery 分支並保存 stash
- 為避免直接在 `main` apply 造成衝突，對每個 stash 使用：
  - `git stash branch recovery/stash0-20260227 stash@{0}`
  - `git stash branch recovery/stash1-20260227 stash@{1}`
- 每個分支上：
  - `git status --porcelain` 確認變更
  - 進行敏感資訊掃描（關鍵字：`BEGIN PRIVATE KEY` / `client_secret` / `refresh_token` / `access_token` / `Bearer ` / `AIza` / `ya29.` 等）
  - 視變更範圍執行基本品質檢查：
    - Python 變更：`ruff check`（阻擋型）+ `pytest`（若可行）
    - schema 變更：跑 repo 內 verifier（若該分支變更範圍涵蓋）

### 2) Commit + Push
- 以 Conventional Commits 建立 commit：
  - stash0：`chore(recovery): preserve stash0 changes (pre Idx-038)`
  - stash1：`chore(recovery): preserve stash1 changes (non-Idx-037 park)`
- Push 到 origin（同名分支）。

### 3) 回到 main + 補齊稽核文件
- 切回 `main`，確認 working tree 乾淨。
- 新增 `doc/logs/Idx-046_log.md` 記錄：
  - recovery 分支名稱
  - commit hash
  - 驗證指令與結果
  - 風險/後續（是否要把分支內容 merge 回 main，需另開新 plan）
- 更新 `doc/Implementation_Plan_index.md` 新增 Idx-046 列。

---

## ⚠️ 注意事項

- **資安考量**：任何疑似 token/secret 的字串都不可被推上 GitHub；必要時以 placeholder 取代。
- **治理約束**：不把不同任務混進 `main`；本輪只做「保存 stash → 清空 stash」。
- **後續整併**：若要把 recovery 分支內容正式合併回 `main`，必須另開新 Idx 計畫並走完整 QA。

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-02-27 10:00:00 UTC
plan_approved: 2026-02-27 17:54:26 UTC
scope_policy: strict
expert_required: false
expert_conclusion: N/A
execution_backend_policy: extension-sendtext-required
scope_exceptions: []

# Engineer 執行
executor_tool: opencode
executor_backend: ivyhouse_sendtext_extension
monitor_backend: manual_confirmation
executor_tool_version: pending
executor_user: pending
executor_start: pending
executor_end: pending
session_id: pending
last_change_tool: opencode

# QA 執行
qa_tool: codex-cli
qa_tool_version: pending
qa_user: pending
qa_start: pending
qa_end: pending
qa_result: pending
qa_compliance: pending

# 收尾
log_file_path: doc/logs/Idx-046_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->
