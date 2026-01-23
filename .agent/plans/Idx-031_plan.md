# Plan: Idx-031

**Index**: Idx-031
**Created**: 2026-01-23
**Planner**: GitHub Copilot

---

## 🎯 目標

收斂並完成「治理可稽核閉環」與「本機/跨平台可用性」：

1) P0：把目前工作樹所有未 commit 變更完成 commit 並 push，讓 Idx-030 的 log/plan 能填入可稽核的 `commit_hash`。
2) P1：針對 Workflow index 中標記「log 缺失」的歷史任務（Idx-021/023/025/027/028）補齊占位 log，並明確標註「不再追溯」，避免稽核斷鏈。
3) P1：修正 VS Code task 的 Windows-only 路徑，使其跨平台（Windows/macOS/Linux）可用。
4) P2：secret scan 強化（gitleaks/detect-secrets）本次不處理（明確排除）。

---

## 📋 SPEC

### Goal
- 讓 Idx-030 的 `commit_hash` 不再是 `pending`，且整個治理鏈條（plan/index/log）可追溯。

### Non-goals
- ❌ 不導入 gitleaks/detect-secrets（本次先不處理）
- ❌ 不重跑/重做歷史任務（僅補占位 log，並標註不再追溯）
- ❌ 不改動 CI 流程或 repo 其他功能

### Acceptance Criteria
1. ✅ `git status --porcelain` 於最後為空（沒有未提交變更）。
2. ✅ `Idx-030` 的 `.agent/plans/Idx-030_plan.md` 與 `.agent/logs/Idx-030_log.md` 中 `commit_hash` 已回填為實際 commit hash（不再是 pending）。
3. ✅ `Idx-021/023/025/027/028` 均新增 `.agent/logs/Idx-0XX_log.md` 占位檔，且文件內明確標註「不再追溯」。
4. ✅ `.agent/Workflow_Plan_index.md` 的 Idx-021/023/025/027/028 之 Log 欄位更新為新占位 log 檔路徑，備註中也標註「不再追溯」。
5. ✅ `.vscode/tasks.json` 的「Run Python (Active File) via .venv」在 Linux 與 Windows 都有正確的 interpreter path（OS-specific 設定）。
6. ✅ 變更完成後已 push 到 GitHub：`origin/feature/idx-024-clear-on-pass`。

### Edge cases
- GitHub 認證尚未設定 → push 會失敗：需由使用者在此環境完成 `git credential` 或 SSH key 設定後再重試。
- `.venv` 不存在 → task 仍會失敗：屬於環境未初始化，需依 repo 文件建立 venv（本次不改動 env 建立流程）。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- Repo 內規範：`.agent/workflows/AGENT_ENTRY.md`、`.agent/workflows/dev-team.md`、`ivy_house_rules.md`
- 任務索引：`.agent/Workflow_Plan_index.md`

### Assumptions
- ✅ VERIFIED：目前工作樹存在未提交變更（已由 `git status --porcelain` 確認）。
- ⚠️ RISK: unverified：此環境是否已配置 GitHub push 憑證（若未配置，需要使用者介入）。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `.agent/plans/Idx-031_plan.md` - 新增：本計畫
- `.agent/logs/Idx-031_log.md` - 新增：本任務執行記錄
- `.agent/Workflow_Plan_index.md` - 修改：登記 Idx-031、並更新缺失 logs 的指向/備註
- `.agent/logs/Idx-021_log.md` - 新增：占位 log（不再追溯）
- `.agent/logs/Idx-023_log.md` - 新增：占位 log（不再追溯）
- `.agent/logs/Idx-025_log.md` - 新增：占位 log（不再追溯）
- `.agent/logs/Idx-027_log.md` - 新增：占位 log（不再追溯）
- `.agent/logs/Idx-028_log.md` - 新增：占位 log（不再追溯）
- `.vscode/tasks.json` - 修改：跨平台（Windows/Linux/macOS）可用
- `.agent/plans/Idx-030_plan.md` - 修改：回填 commit_hash
- `.agent/logs/Idx-030_log.md` - 修改：回填 commit_hash（或同等可稽核欄位）

（以下為目前工作樹已存在的未提交變更檔案；本計畫允許一併 commit）：
- `tools/vscode_terminal_orchestrator/extension.js`
- `tools/vscode_terminal_orchestrator/README.md`
- `.agent/roles/engineer.md`
- `.agent/roles/qa.md`
- `.agent/workflows/dev-team.md`

### Done 定義
1. ✅ Idx-031 已在 `.agent/Workflow_Plan_index.md` 註冊。
2. ✅ 缺失 logs 已補占位且標註不再追溯。
3. ✅ tasks.json 已改為跨平台 OS-specific 命令。
4. ✅ 完成 commit（可能為 2 commits：先提交變更、再回填 commit_hash）並 push。
5. ✅ `.agent/logs/Idx-031_log.md` 已補齊（含 commit hash 與變更摘要）。

### Rollback 策略
- **Level**: L2
- **前置條件**: 若尚未 push，可直接回滾 worktree。
- **回滾動作**:
  - 還原 tracked 變更：`git restore --worktree --staged -- .`
  - 刪除新增的占位 log/plan：`git clean -fd -- .agent/plans/Idx-031_plan.md .agent/logs/Idx-031_log.md .agent/logs/Idx-021_log.md .agent/logs/Idx-023_log.md .agent/logs/Idx-025_log.md .agent/logs/Idx-027_log.md .agent/logs/Idx-028_log.md`

### Max rounds
- **估計**: 1
- **超過處理**: 若 push 因憑證問題失敗，先停下回報，請使用者完成 GitHub 認證後再續。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| .agent/plans/Idx-031_plan.md | 新增 | 本計畫 |
| .agent/logs/Idx-031_log.md | 新增 | 本任務執行 log（含 commit hash） |
| .agent/Workflow_Plan_index.md | 修改 | 新增 Idx-031 列；更新缺失 log 指向與備註「不再追溯」 |
| .agent/logs/Idx-021_log.md | 新增 | 占位 log（不再追溯） |
| .agent/logs/Idx-023_log.md | 新增 | 占位 log（不再追溯） |
| .agent/logs/Idx-025_log.md | 新增 | 占位 log（不再追溯） |
| .agent/logs/Idx-027_log.md | 新增 | 占位 log（不再追溯） |
| .agent/logs/Idx-028_log.md | 新增 | 占位 log（不再追溯） |
| .vscode/tasks.json | 修改 | 將 Windows-only python 路徑改為 OS-specific（跨平台） |
| .agent/plans/Idx-030_plan.md | 修改 | 回填 commit_hash（由 commit 產出後回填） |
| .agent/logs/Idx-030_log.md | 修改 | 回填 commit_hash（由 commit 產出後回填） |

---

## 📝 邏輯細節

### 1) 缺失 logs 占位（不再追溯）
- 新增 5 份 `.agent/logs/Idx-0XX_log.md`，固定包含：
  - `Status: 不再追溯`
  - 缺失原因（repo 未保留原始 log/證據）
  - 本次補齊範圍（僅占位，不回填歷史證據）

### 2) `.vscode/tasks.json` 跨平台調整
- 使用 VS Code tasks 的 OS-specific 覆寫（`windows` / `linux` / `osx`）指定 `.venv` interpreter：
  - Windows：`${workspaceFolder}\\.venv\\Scripts\\python.exe`
  - Linux/macOS：`${workspaceFolder}/.venv/bin/python`

### 3) Commit 與 log binding
- 建議 commit 策略（為了能回填 commit_hash）：
  1. Commit A：先把所有變更（含 Idx-030 現有變更 + Idx-031 占位 logs + tasks 修正 + index/plan/log）提交。
  2. 取得 Commit A 的 hash 後，回填 `.agent/plans/Idx-030_plan.md` 與 `.agent/logs/Idx-030_log.md`（必要時也回填 Idx-031 log）。
  3. Commit B：只提交「回填 commit_hash」的文件變更。
- 兩次 commit 皆需 push。

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-01-23 05:40:00+00:00
plan_approved: 2026-01-23 05:40:00+00:00
scope_policy: strict
expert_required: false
expert_conclusion: N/A
scope_exceptions: ["Coordinator 直接以 VS Code 工具修改檔案並執行 git（屬治理/收斂任務）"]

# Engineer 執行
executor_tool: manual
executor_tool_version: N/A
executor_user: GitHub Copilot (VS Code)
executor_start: 2026-01-23 05:40:00+00:00
executor_end: [TBD]
session_id: N/A
last_change_tool: manual

# QA 執行
qa_tool: manual
qa_tool_version: N/A
qa_user: GitHub Copilot (VS Code)
qa_start: [TBD]
qa_end: [TBD]
qa_result: [TBD]
qa_compliance: ⚠️ 例外：本次為治理/文件/設定收斂，未走 codex/opencode 交叉終端 QA

# 收尾
log_file_path: .agent/logs/Idx-031_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

---

## ✅ 用戶確認

- [x] Spec 已確認（使用者輸入：approve）
- [ ] 允許我在此環境執行 `git commit` 與 `git push`（若需登入/憑證，會請你介入）
