---
index: Idx-018
title: Dev-Team Workflow Artifact Segregation (Dual Index)
workflow: dev-team
owner: "@foreverjojo"
status: in_progress
priority: P0
created: 2026-01-19
planner: "@GitHubCopilot"
---

# Plan: Idx-018 Dev-Team Workflow Artifact Segregation (Dual Index)

## 🎯 目標

解決 dev-team workflow artifacts 與專案交付檔案混雜的問題，採用「雙 Index + 目錄完全分離」：

- Workflow/治理：集中在 `.agent/**`（plans/logs/scripts/index）
- 專案/產品：維持在 `doc/**`（plans/logs/index）

並讓 State Gate 依 staged 變更路徑自動路由到正確的 Index。

---

## 📋 SPEC

### Goal
- 建立 `.agent/Workflow_Plan_index.md` 作為 workflow/治理 domain 的 source-of-truth。
- 將 workflow plans/logs 由 `doc/plans/`、`doc/logs/` 搬移至 `.agent/plans/`、`.agent/logs/`。
- 將 workflow scripts 搬移至 `.agent/scripts/`，並保留 `scripts/validate_state_gate.py` shim（相容 3 週）。
- State Gate 依 staged 變更路徑 routing：
  - staged 內含 `.agent/**` → 驗 `.agent/Workflow_Plan_index.md`
  - 否則 → 驗 `doc/Implementation_Plan_index.md`

### Non-goals
- 不改動產品功能邏輯（僅做資訊架構/治理工具鏈調整）。

### Acceptance Criteria
1. ✅ `.agent/Workflow_Plan_index.md` 存在，且包含 Idx-009~018（或至少覆蓋本次搬移範圍）。
2. ✅ workflow plans/logs/scripts 以 `git mv` 方式搬移，沒有留下「全文重複檔」在舊路徑。
3. ✅ `scripts/validate_state_gate.py` 仍可使用（shim），並清楚提示遷移與移除日期。
4. ✅ State Gate routing 實測可用（workflow 變更→workflow index；project 變更→project index）。
5. ✅ `doc/FILE_OWNERSHIP.md` 文件化領域邊界與 routing 規則。

### Edge cases
- 若同一個變更同時包含 `.agent/**` 與非 `.agent/**`：routing 優先 workflow index（避免誤把 workflow 變更當作 project）。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: true

### Sources
- `.agent/workflows/dev-team.md`
- `.agent/skills/plan_validator.py`
- GitHub Docs: default community health file (`.github`) 的集中治理做法
  - https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file
- Kubernetes: `hack/` 目錄集中開發/驗證腳本
  - https://raw.githubusercontent.com/kubernetes/kubernetes/master/hack/README.md

### Assumptions
- repo 內 workflow/治理 tasks 允許與產品 tasks 拆成不同 Index，以降低混雜與誤觸。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist (允許變更)
- `.agent/Workflow_Plan_index.md`
- `.agent/plans/**`
- `.agent/logs/**`
- `.agent/scripts/**`
- `.agent/workflows/**`
- `doc/FILE_OWNERSHIP.md`
- `doc/Implementation_Plan_index.md`
- `scripts/validate_state_gate.py`（shim）

### Done 定義
- workflow artifacts 已完成搬移與索引更新，且 State Gate routing 可用。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `.agent/Workflow_Plan_index.md` | 新增 | workflow/治理 Index |
| `.agent/scripts/validate_state_gate.py` | 新增 | routing + State Gate 主實作 |
| `scripts/validate_state_gate.py` | 修改 | shim 轉發（3 週後移除） |
| `doc/FILE_OWNERSHIP.md` | 新增 | ownership + routing 規則 |
| `doc/Implementation_Plan_index.md` | 修改 | 移除 workflow 類項目或改指向 workflow index |

---

## 執行資訊

<!-- EXECUTION_BLOCK_START -->
plan_created: 2026-01-19 11:00:00
plan_approved: [待確認]
scope_policy: strict
expert_required: false
expert_conclusion: N/A
scope_exceptions: []

# Engineer 執行
executor_tool: opencode
executor_tool_version: [待填寫]
executor_user: [待填寫]
executor_start: [待填寫]
executor_end: [待填寫]
session_id: [待填寫]
last_change_tool: opencode

# QA 執行
qa_tool: codex-cli
qa_tool_version: [待填寫]
qa_user: [待填寫]
qa_start: [待填寫]
qa_end: [待填寫]
qa_result: [PASS|PASS_WITH_RISK|FAIL]
qa_compliance: [待填寫]

# 收尾
log_file_path: .agent/logs/Idx-018_log.md
commit_hash: [pending]
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->
