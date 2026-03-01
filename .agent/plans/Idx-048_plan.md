# Idx-048 — 整併 recovery/stash0-20260227（commit 00d4b23）：整理後可合回 main

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-02-27T18:26:49+00:00
plan_approved: 2026-02-27T18:44:54+00:00
scope_policy: strict
expert_required: false
expert_conclusion: N/A
execution_backend_policy: extension-sendtext-required
scope_exceptions: []

# Engineer 執行
executor_tool: opencode
executor_backend: ivyhouse_sendtext_extension
monitor_backend: proposed-primary-with-extension-fallback
executor_tool_version: N/A
executor_user: vscode
executor_start: 2026-02-27T18:52:03+00:00
executor_end: 2026-02-27T18:52:03+00:00
session_id: N/A
last_change_tool: opencode

# QA 執行
qa_tool: codex-cli
qa_tool_version: N/A
qa_user: vscode
qa_start: 2026-02-27T18:52:03+00:00
qa_end: 2026-02-27T18:52:03+00:00
qa_result: PASS_WITH_RISK
qa_compliance: ✅ 符合

# 收尾
log_file_path: .agent/logs/Idx-048_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

---

## 📋 SPEC

### Goal
將 `recovery/stash0-20260227` 保存的變更（preserve commit：`00d4b23`）整理成「可安全合回 `main`」的最小變更集：逐檔 review、排除不該回填的審計文件（既有 `.agent/plans/**`、`.agent/logs/**`）、補齊必要驗證與 QA，最後以乾淨的 integration branch/PR 合併回 `main`。

### Non-goals
- ❌ 不直接 merge `recovery/stash0-20260227` 分支（避免把「基底較舊造成的整體差異」誤合回 `main`）。
- ❌ 不覆寫既有的審計/治理文件（尤其是已存在於 `main` 的 `.agent/plans/Idx-041_plan.md`、`.agent/logs/Idx-041_log.md`）。
- ❌ 不把 Orchestrator（legacy）重新拉回「預設注入/監控路徑」：本 Idx 僅整併程式碼變更，不改寫新流程的預設規範。

### Acceptance Criteria
1. ✅ 以 `main` 為基底建立 integration branch，並以 cherry-pick 方式引入 `00d4b23` 的「目標檔案變更」。
2. ✅ 不會因 cherry-pick 覆寫/回填既有審計文件（`.agent/plans/**` / `.agent/logs/**`）。
3. ✅ Python 變更檔可編譯，且 Ruff 阻擋型檢查通過：`ruff check . --select=E9,F63,F7,F82 --target-version=py311`。
4. ✅ 基本測試通過：`pytest -q`（允許既有 skip，但不得新增非必要 xfail/skip）。
5. ✅ Extension 檔案維持語法與 JSON 正確（至少能被讀取/解析）。
6. ✅ 敏感資訊檢查：不得提交 token / key / private key 片段。

### Edge cases
- `.agent/roles/coordinator.md` 內容若與現行「Injector+Monitor only」規範衝突 → 以 `main` 現行規範為準，必要時在本 Idx 內做最小修正或直接排除該段變更。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- preserve commit：`00d4b23`（來源分支：`recovery/stash0-20260227`）
- 受影響檔案（來自 `git show --name-status 00d4b23`）：
  - `.agent/Workflow_Plan_index.md`（本 Idx 會避免被覆寫；以本次登記 Idx-048 列為準）
  - `.agent/logs/Idx-041_log.md`（`main` 已存在 → 預期排除）
  - `.agent/plans/Idx-041_plan.md`（`main` 已存在 → 預期排除）
  - `.agent/roles/coordinator.md`
  - `pages/02_report_generation.py`
  - `scripts/sendtext_bridge_client.py`
  - `tools/vscode_terminal_orchestrator/extension.js`
  - `tools/vscode_terminal_orchestrator/package.json`

### Assumptions
- ✅ VERIFIED - `recovery/stash0-20260227` 相對 `main` 的巨大 diff 主要來自「分支基底較舊」，因此只應 cherry-pick preserve commit，而非 merge 分支。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `.agent/plans/Idx-048_plan.md` - 本計畫文件
- `.agent/logs/Idx-048_log.md` - 執行完成後新增
- `.agent/Workflow_Plan_index.md` - 已新增 Idx-048 任務列（本任務僅允許維持/微調該列，不回填舊變更）

- `.agent/roles/coordinator.md` - cherry-pick + review
- `pages/02_report_generation.py` - cherry-pick + review
- `scripts/sendtext_bridge_client.py` - cherry-pick + review
- `tools/vscode_terminal_orchestrator/extension.js` - cherry-pick + review
- `tools/vscode_terminal_orchestrator/package.json` - cherry-pick + review

### 明確排除（cherry-pick 後必須移除）
- `.agent/plans/Idx-041_plan.md`
- `.agent/logs/Idx-041_log.md`

### Done 定義
1. ✅ Idx-048 integration branch 可乾淨合併回 `main`（不包含不相關刪檔/回退）。
2. ✅ 驗證（Ruff/pytest/py_compile/敏感掃描）通過。
3. ✅ 產出 Idx-048 log 並回填 commit hash。

### Rollback 策略
- **Level**: L2
- **前置條件**: 保持 worktree 乾淨（`git status --porcelain` 無輸出）
- **回滾動作**:
  - 若 cherry-pick 尚未 commit：`git restore --worktree --staged -- .`
  - 若已 commit：優先 `git revert <commit>` 保留審計軌跡

### Max rounds
- 3 rounds（cherry-pick/衝突 → 修正 → QA）

---

## 📁 檔案變更表

| 檔案 | 動作 | 說明 |
|------|------|------|
| `.agent/plans/Idx-048_plan.md` | 新增 | 本計畫文件 |
| `.agent/logs/Idx-048_log.md` | 新增 | 執行與 QA 紀錄 |
| `.agent/Workflow_Plan_index.md` | 修改 | 已登記 Idx-048 任務列 |
| `.agent/roles/coordinator.md` | 修改 | 來自 `00d4b23`，需 review |
| `pages/02_report_generation.py` | 修改 | 來自 `00d4b23`，需 review |
| `scripts/sendtext_bridge_client.py` | 修改 | 來自 `00d4b23`，需 review |
| `tools/vscode_terminal_orchestrator/extension.js` | 修改 | 來自 `00d4b23`，需 review |
| `tools/vscode_terminal_orchestrator/package.json` | 修改 | 來自 `00d4b23`，需 review |

---

## 📝 執行步驟（給 Engineer）

### 1) 建立 integration branch（以 main 為基底）
- 從 `main` 建立：`idx-048-integrate-stash0`

### 2) 以 preserve commit cherry-pick（禁止 merge 分支）
- 使用 `git cherry-pick --no-commit 00d4b23` 取得變更，但先不 commit。

### 3) 立即排除不允許回填的檔案
- 排除既有審計文件：
  - `git restore --staged --worktree .agent/plans/Idx-041_plan.md .agent/logs/Idx-041_log.md`
- 避免覆寫 workflow Index（本 Idx 只維持已新增的 Idx-048 列）：
  - `git restore --staged --worktree .agent/Workflow_Plan_index.md`（如有被 cherry-pick 變更）

### 4) 逐檔 review（重點）
- `.agent/roles/coordinator.md`：
  - 確認不會把 Orchestrator/bridge 寫回「預設流程」；若有衝突，優先維持 `main` 的 Injector+Monitor only。
- `scripts/sendtext_bridge_client.py`：
  - 確認不含敏感資料，且不會被 workflow 文件當作預設機制。
- `tools/vscode_terminal_orchestrator/*`：
  - 確認仍為 legacy 相容用途（文件不得依賴它作為預設）。
- `pages/02_report_generation.py`：
  - 確認不更動 UX 範圍（不新增頁面/流程），僅修 bug 或維持現有行為。

### 5) Commit（Conventional Commits + State Gate）
- 建議訊息：`chore(Idx-048): integrate stash0 legacy tooling changes`

---

## 🧪 QA 檢核（給 QA）

- `ruff check . --select=E9,F63,F7,F82 --target-version=py311`
- `python -m py_compile pages/02_report_generation.py scripts/sendtext_bridge_client.py`
- `pytest -q`
- 敏感掃描（grep）：`BEGIN PRIVATE KEY|ya29\.|AIza|Bearer `

---

## ✅ 用戶確認（Gate）

- [ ] Spec 已確認，可進入執行
- [ ] 已選 Engineer Tool（codex-cli / opencode）
- [ ] 已選 QA Tool（需 ≠ last_change_tool）
