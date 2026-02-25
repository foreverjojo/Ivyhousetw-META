# Idx-041 — Role Selection Gate：納入 Copilot Chat（小修正）+ 強制工具一致性（防止選 A 卻用 B）

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-02-25 03:48:00+00:00
plan_approved: 2026-02-25 03:48:00+00:00
scope_policy: strict
expert_required: false
expert_conclusion: N/A
execution_backend_policy: extension-sendtext-required
scope_exceptions: []

# Engineer 執行
executor_tool: opencode
executor_backend: ivyhouse_sendtext_extension
monitor_backend: proposed_api_monitor
executor_tool_version: opencode-latest
executor_user: opencode-agent
executor_start: 2026-02-25T03:48:00+00:00
executor_end: 2026-02-25T05:00:00+00:00
session_id: idx-041-opencode-session
last_change_tool: opencode

# Copilot Chat 小修正政策（僅當 executor_tool=copilot-chat 才允許填）
# - 目的：讓「點單小修正」可由 Copilot Chat 直接做，但必須可機械化驗證，且不影響你選定 opencode/codex 的任務。
copilot_chat_small_fix_allowed: [true|false]
copilot_chat_small_fix_reason: [TBD]
copilot_chat_max_changed_lines: 20
copilot_chat_allowed_path_globs: ["doc/**", "README.md", "CHANGELOG.md", "CHECKLIST.md", "*.md"]

# QA 執行
qa_tool: codex-cli
qa_tool_version: codex-cli 0.104.0
qa_user: vscode
qa_start: 2026-02-25T04:19:04Z
qa_end: 2026-02-25T04:19:58Z
qa_result: PASS_WITH_RISK
qa_compliance: ✅ 符合（qa_tool=codex-cli != last_change_tool=opencode）

# 收尾
log_file_path: .agent/logs/Idx-041_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

---

## 📋 SPEC

### Goal
1. **把 `copilot-chat` 納入 Role Selection Gate**：允許「點單小修正」在你明確選擇 `copilot-chat` 作為 Executor 時，由 Copilot Chat 直接在 workspace 內修改檔案。
2. **強制工具一致性（可機械化阻擋）**：當你在 Plan 中選擇 `opencode` 或 `codex-cli` 作為 Executor 時：
   - Copilot Chat 必須回到「Coordinator no-write」模式（只做 Gate/注入/監控/回填），
   - 並且在 **commit-msg State Gate** 直接阻擋「工具不一致／證據不足」的提交，避免再發生「你選 opencode/codex，但實際是 Copilot Chat 直接改」的情況。

### Non-goals
- ❌ 不追求「不可偽造」等級的密碼學保證（例如無法證明檔案每一行都只能由某個終端產生）。
- ❌ 不改動既有的 Injector/Monitor 基礎架構與既有 workflow loop 狀態機（本任務聚焦在 Role Gate + State Gate 硬擋）。
- ❌ 不更動既有 exempt commit types（`docs:`/`chore:` 等）行為（避免對日常提交造成破壞性變更）。

### Acceptance Criteria
1. ✅ `.agent/workflows/dev-team.md` 的 Role Selection Gate 正式新增 `copilot-chat` 選項，並定義「小修正」政策欄位（上面 EXECUTION_BLOCK 的 `copilot_chat_*`）。
2. ✅ `.agent/roles/coordinator.md` 調整為「預設 no-write」，但當 `executor_tool=copilot-chat` 且 `copilot_chat_small_fix_allowed=true` 時，允許 Copilot Chat 執行小修正（其餘情況仍禁止）。
3. ✅ `.agent/scripts/validate_state_gate.py` 新增硬性檢查（只對含 `Idx-NNN` 的非豁免提交生效）：
   - 會定位對應 Plan 檔（從 `.agent/Workflow_Plan_index.md` 或 `doc/Implementation_Plan_index.md` 解析 `Plan：...` 路徑）。
   - 會解析 Plan 的 `EXECUTION_BLOCK`，並檢查必填欄位是否已填（不可留 `[TBD]` 或 placeholder）。
4. ✅ 若 Plan 指定 `executor_tool=opencode|codex-cli`：
   - `last_change_tool` 必須等於該 executor（不可為 `copilot-chat`）。
   - `qa_tool` 必須存在且 `qa_tool != last_change_tool`（Cross-QA）。
   - `qa_result` 必須是 `PASS` 或 `PASS_WITH_RISK`，否則 State Gate 阻擋 commit。
5. ✅ 若 Plan 指定 `executor_tool=copilot-chat`：
   - `copilot_chat_small_fix_allowed=true` 必須明確填寫。
   - staged 變更檔案必須全部符合 `copilot_chat_allowed_path_globs`。
   - staged 變更總行數（add+del）不得超過 `copilot_chat_max_changed_lines`。
   - `qa_result` 仍需 `PASS|PASS_WITH_RISK`（避免小修正完全無驗證）。
6. ✅ 新增/更新測試覆蓋 State Gate 新規則（放在 `tests/test_validate_state_gate.py`），至少包含：
   - `executor_tool=copilot-chat` 且超出行數/路徑 → FAIL。
   - `executor_tool=opencode` 但 `last_change_tool=copilot-chat` → FAIL。

### Edge cases
- Plan/Index 找不到對應 Plan 路徑 → State Gate 顯示可行動錯誤訊息並 FAIL。
- Plan `EXECUTION_BLOCK` 欄位缺漏或還是 placeholder → FAIL（提示需要回填）。
- staged 只有豁免提交（`docs:`/`chore:` 等）→ 維持既有行為（不強制 Idx/Plan/證據）。

---

## 🔍 RESEARCH & ASSUMPTIONS
research_required: false

### Sources
- Repo 內規範：`.agent/workflows/dev-team.md`、`.agent/roles/coordinator.md`、`.agent/scripts/validate_state_gate.py`。

### Assumptions
- ✅ VERIFIED：State Gate 目前已能偵測 staged 變更路徑並選擇對應 Index。
- ⚠️ RISK: unverified：Index 表格中的 `Plan：...` 欄位格式是否所有任務都一致（實作時需兼容數種常見格式）。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `.agent/workflows/dev-team.md` - 在 Role Selection Gate 新增 `copilot-chat` + 小修正政策欄位。
- `.agent/roles/coordinator.md` - 明確化「預設 no-write；僅在 Plan 明確允許時可小修正」。
- `.agent/scripts/validate_state_gate.py` - 加入 Plan/證據/工具一致性檢查（commit-msg blocking）。
- `tests/test_validate_state_gate.py` - 新增測試覆蓋上述規則。
- `.agent/Workflow_Plan_index.md` - 新增 Idx-041 追蹤列。
- `.agent/plans/Idx-041_plan.md` - 本計畫文件。

### Done 定義
- 上述 AC#1~6 全部滿足，且 `ruff check core utils scripts tests main.py --target-version=py311` 與 `pytest tests/ -q` 通過。

### Rollback 策略
- **Level**: L2
- **回滾動作**：`git restore --worktree --staged -- .agent/workflows/dev-team.md .agent/roles/coordinator.md .agent/scripts/validate_state_gate.py tests/test_validate_state_gate.py .agent/Workflow_Plan_index.md`

### Max rounds
- 估計 2 rounds（實作 1 + 修正 1）；超過則縮 scope，只先落地最小「State Gate 阻擋工具不一致」規則。

---

## 📁 檔案變更表

| 檔案 | 動作 | 說明 |
|------|------|------|
| .agent/workflows/dev-team.md | 修改 | Role Selection Gate 納入 `copilot-chat` + 小修正政策欄位與規則 |
| .agent/roles/coordinator.md | 修改 | Coordinator 規範新增「小修正例外」但預設 no-write |
| .agent/scripts/validate_state_gate.py | 修改 | commit-msg 時解析 Plan 並硬性阻擋工具不一致/證據不足 |
| tests/test_validate_state_gate.py | 修改 | 新增覆蓋測試 |
| .agent/Workflow_Plan_index.md | 修改 | 登記 Idx-041 |
| .agent/plans/Idx-041_plan.md | 新增 | 本 Plan |
