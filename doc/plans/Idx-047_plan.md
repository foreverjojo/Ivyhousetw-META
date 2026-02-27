# Plan: Idx-047

**Index**: Idx-047
**Created**: 2026-02-27
**Planner**: GitHub Copilot（Coordinator）

---

## 🎯 目標

將 `recovery/stash1-20260227` 保存的變更（preserve commit：`61b86cc`）整理成「可安全合回 `main`」的最小變更集：逐檔 review、排除不該回填的文件（特別是 Index 類文件）、補齊必要驗證與 QA，最後以乾淨的 integration branch/PR 合併回 `main`。

---

## 📋 SPEC

### Goal
把 `61b86cc` 內的核心程式碼與 schema 變更，乾淨地帶回 `main`，並確保 repo 既有驗證腳本、Ruff 與 Pytest 維持通過。

### Non-goals
- ❌ 不直接 merge `recovery/stash1-20260227` 分支（避免把「基底較舊造成的整體差異」誤合回 `main`）。
- ❌ 不回填/覆寫 `61b86cc` 內的 `doc/Implementation_Plan_index.md` 變更（Index 只保留本次新增的 Idx-047 任務列）。
- ❌ 不趁機重構未涉及的模組、UI 或測試（僅處理這次 commit 帶回來的檔案）。

### Acceptance Criteria
1. ✅ 以 `main` 為基底建立 integration branch，並以 cherry-pick 方式引入 `61b86cc` 的「目標檔案變更」。
2. ✅ `doc/Implementation_Plan_index.md` 不會被 `61b86cc` 覆寫（僅保留本次登記 Idx-047 的新增列）。
3. ✅ `ruff check core utils scripts tests main.py --target-version=py311` 通過。
4. ✅ `ruff format --check core utils scripts tests main.py` 通過。
5. ✅ `pytest tests/ -q` 通過（允許既有 skip，但不得新增非必要 xfail/skip）。
6. ✅ Repo verifiers 通過：
   - `python tests/verify_skill_schemas.py`
   - `python tests/verify_skills_runtime.py`
7. ✅ 敏感資訊檢查：不得提交 token / key / private key 片段（含 `ya29.`、`AIza`、`BEGIN PRIVATE KEY`、`Bearer ` 等）。

### Edge cases
- `ui/steps.py` 可能與 `main` 有衝突 → 以「保留 `main` 行為」為優先，逐段對照後再帶入 stash1 的必要差異。
- `schemas/*.json` 變更可能影響 runtime 驗證 → 以 verifier 作為最終裁決。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- preserve commit：`61b86cc`（來源分支：`recovery/stash1-20260227`）
- 受影響檔案（來自 `git show --name-status 61b86cc`）：
  - `core/__init__.py`
  - `core/validation.py`
  - `schemas/consultant_notes.v1.json`
  - `schemas/report_insights.v1.json`
  - `schemas/workflow_state.v1.json`
  - `scripts/consultants.py`
  - `scripts/json_to_readable.py`
  - `scripts/self_test.py`
  - `ui/steps.py`

### Assumptions
- ✅ VERIFIED - `recovery/stash1-20260227` 相對 `main` 的巨大 diff 主要來自「分支基底較舊」，因此只應 cherry-pick preserve commit，而非 merge 分支。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `doc/plans/Idx-047_plan.md` - 本計畫文件
- `doc/logs/Idx-047_log.md` - 執行完成後新增
- `doc/Implementation_Plan_index.md` - 已新增 Idx-047 任務列（本任務僅允許維持/微調該列，不回填舊變更）

- `core/__init__.py` - cherry-pick + review
- `core/validation.py` - cherry-pick + review
- `schemas/consultant_notes.v1.json` - cherry-pick + review
- `schemas/report_insights.v1.json` - cherry-pick + review
- `schemas/workflow_state.v1.json` - cherry-pick + review
- `scripts/consultants.py` - cherry-pick + review
- `scripts/json_to_readable.py` - cherry-pick + review
- `scripts/self_test.py` - cherry-pick + review
- `ui/steps.py` - cherry-pick + review

### Done 定義
1. ✅ Idx-047 integration branch 可乾淨合併回 `main`（不包含不相關刪檔/回退）。
2. ✅ 驗證（Ruff/Format/Pytest/Verifier/敏感掃描）全部通過。
3. ✅ 產出 Idx-047 log 並回填 commit hash。

### Rollback 策略
- **Level**: L2
- **前置條件**: 保持 worktree 乾淨（`git status --porcelain` 無輸出）
- **回滾動作**:
  - 若 cherry-pick 尚未 commit：`git restore --worktree --staged -- .`
  - 若已 commit：優先 `git revert <commit>` 保留審計軌跡

### Max rounds
- **估計**: 3（cherry-pick/衝突 → 修正 → QA）
- **超過處理**: 若 `ui/steps.py` 或 schema 牽涉面擴大，停止並請你決定是否拆成更小 Idx。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `doc/plans/Idx-047_plan.md` | 新增 | 本計畫文件 |
| `doc/logs/Idx-047_log.md` | 新增 | 執行與 QA 紀錄 |
| `doc/Implementation_Plan_index.md` | 修改 | 已登記 Idx-047 任務列 |
| `core/__init__.py` | 修改 | 來自 `61b86cc`，需 review |
| `core/validation.py` | 修改 | 來自 `61b86cc`，需 review |
| `schemas/consultant_notes.v1.json` | 修改 | 來自 `61b86cc`，需 review |
| `schemas/report_insights.v1.json` | 修改 | 來自 `61b86cc`，需 review |
| `schemas/workflow_state.v1.json` | 修改 | 來自 `61b86cc`，需 review |
| `scripts/consultants.py` | 修改 | 來自 `61b86cc`，需 review |
| `scripts/json_to_readable.py` | 修改 | 來自 `61b86cc`，需 review |
| `scripts/self_test.py` | 修改 | 來自 `61b86cc`，需 review |
| `ui/steps.py` | 修改 | 來自 `61b86cc`，需 review |

---

## 📝 邏輯細節

### 1) 建立 integration branch（以 main 為基底）
- 從 `main` 建立：`idx-047-integrate-stash1`

### 2) 以 preserve commit cherry-pick（禁止 merge 分支）
- 使用 `git cherry-pick --no-commit 61b86cc` 取得變更，但先不 commit。
- 立即排除 Index 回填：
  - `git restore --staged --worktree doc/Implementation_Plan_index.md`

### 3) 逐檔 review（最小化帶回）
- `core/__init__.py`：確認 export/初始化行為不破壞既有 import。
- `core/validation.py`：確認 schema 驗證錯誤訊息可行動、無 bare except、型別註記合理。
- `schemas/*.json`：確認版本欄位/required/enum 變更與 pipeline 期待一致。
- `scripts/*.py`：確認 CLI 介面與輸出格式不破壞既有使用方式。
- `ui/steps.py`：確認 Step flow 不變更既有 UX（除非是修 bug），並避免引入新頁面/新流程。

### 4) Commit（Conventional Commits + State Gate）
- 建議訊息：`feat(Idx-047): integrate stash1 changes for schemas/scripts/ui`

---

## ⚠️ 注意事項

- **最大風險**：誤把 recovery 分支「整體落後 main」的差異當成要合併 → 本任務必須以 cherry-pick preserve commit 為唯一入口。
- **Index 風險**：`doc/Implementation_Plan_index.md` 曾有 CRLF/LF 混用歷史；本次只在 table 區域做最小變更，且 cherry-pick 時要排除該檔。
- **資安**：不得在 scripts/UI 中硬編碼任何 token/key。

---

## 🔧 執行資訊

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
executor_tool: [待用戶確認: codex-cli|opencode]
executor_backend: ivyhouse_sendtext_extension
monitor_backend: proposed-primary-with-extension-fallback
executor_tool_version: [pending]
executor_user: [pending]
executor_start: [pending]
executor_end: [pending]
session_id: [pending]
last_change_tool: [codex-cli|opencode]

# QA 執行
qa_tool: [待用戶確認: codex-cli|opencode]
qa_tool_version: [pending]
qa_user: [pending]
qa_start: [pending]
qa_end: [pending]
qa_result: [PASS|PASS_WITH_RISK|FAIL]
qa_compliance: [✅ 符合|⚠️ 例外：原因]

# 收尾
log_file_path: doc/logs/Idx-047_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->
