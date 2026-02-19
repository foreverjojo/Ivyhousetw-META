# Evidence: Idx-010 - Agent Architecture Enhancement

**Plan**: [doc/plans/Idx-010_agent_architecture_enhancement.md](../plans/Idx-010_agent_architecture_enhancement.md)
**Log**: [doc/logs/Idx-010_log.md](Idx-010_log.md)
**Created**: 2026-01-17 14:30:00

---

## 變更摘要

**總變更行數**: 2477（新增 357 + 刪除 2120）

### 核心變更（Idx-010 相關）
- `doc/plans/Idx-000_plan.template.md`: +102/-16（新增 SPEC/RESEARCH/SCOPE 段落）
- `.agent/roles/coordinator.md`: 新增檔案（707 lines，包含三個 Gate 規則）
- `.agent/workflows/dev-team.md`: +92/-73（整合三個 Gate 流程說明）
- `doc/logs/Idx-010_log_template_example.md`: 新增檔案（117 lines）

### 連帶變更（清理 terminal bridge）
- 刪除 4 個 terminal bridge 相關檔案（-1,829 lines）
- 更新多個文檔以反映新工作流

---

## 完整變更清單

```bash
git status --porcelain
 M .agent/AGENT_WORKFLOW_TEMPLATE_PREP.md
 M .agent/PORTABLE_WORKFLOW.md
 D .agent/docs/HANDOFF_TERMINAL_BRIDGE.md          # -510 lines
 D .agent/docs/SESSION_SUMMARY.md                  # -229 lines
 D .agent/docs/TERMINAL_BRIDGE_SERVER.md           # -443 lines
 M .agent/roles/engineer.md
 M .agent/roles/meta_expert.md
 M .agent/roles/planner.md
 M .agent/roles/qa.md
 M .agent/scripts/setup_workflow.sh
 D .agent/scripts/start_terminal_bridge.sh         # -74 lines
 D .agent/scripts/stop_terminal_bridge.sh          # -42 lines
 D .agent/scripts/terminal_bridge_server.py        # -411 lines
 D .agent/scripts/test_terminal_bridge.sh          # -120 lines
 M .agent/skills/explore_cli_tool.md
 M .agent/workflows/AGENT_ENTRY.md
 M .agent/workflows/dev-team.md                    # +92/-73
 M app.py
 M doc/1_pending.md
 M doc/DEV_TEAM_WORKFLOW_SUMMARY.md
 M doc/Implementation_Plan_index.md
 M doc/SKILL_SECURITY_POLICY.md
 M doc/TOOL_USAGE.md
 M doc/adr/0003-multi-agent-workflow.md
 M doc/next_steps_checklist.md
 M doc/plans/Idx-000_plan.template.md              # +102/-16
 M doc/tech_debt.md
 M doc/workflow_completion_summary.md
 M doc/workflow_implementation_report.md
 M doc/workflow_quick_reference.md
 M ivy_house_rules.md
 M scripts/check_verification_due.py
 M scripts/task_branch.py
 M scripts/validate_state_gate.py
?? .agent/roles/coordinator.md                     # NEW: 707 lines
?? doc/plans/Idx-010_agent_architecture_enhancement.md  # NEW: 642 lines
?? doc/logs/Idx-010_log_template_example.md        # NEW: 117 lines
```

---

## 變更行數統計（git diff --numstat）

```
4       21      .agent/AGENT_WORKFLOW_TEMPLATE_PREP.md
4       4       .agent/PORTABLE_WORKFLOW.md
0       510     .agent/docs/HANDOFF_TERMINAL_BRIDGE.md
0       229     .agent/docs/SESSION_SUMMARY.md
0       443     .agent/docs/TERMINAL_BRIDGE_SERVER.md
4       3       .agent/roles/engineer.md
1       1       .agent/roles/meta_expert.md
9       36      .agent/roles/planner.md
50      32      .agent/roles/qa.md
11      19      .agent/scripts/setup_workflow.sh
0       74      .agent/scripts/start_terminal_bridge.sh
0       42      .agent/scripts/stop_terminal_bridge.sh
0       411     .agent/scripts/terminal_bridge_server.py
0       120     .agent/scripts/test_terminal_bridge.sh
1       1       .agent/skills/explore_cli_tool.md
8       6       .agent/workflows/AGENT_ENTRY.md
92      73      .agent/workflows/dev-team.md
1       1       doc/1_pending.md
13      11      doc/DEV_TEAM_WORKFLOW_SUMMARY.md
2       2       doc/Implementation_Plan_index.md
3       3       doc/SKILL_SECURITY_POLICY.md
21      33      doc/TOOL_USAGE.md
1       1       doc/adr/0003-multi-agent-workflow.md
2       2       doc/next_steps_checklist.md
102     16      doc/plans/Idx-000_plan.template.md
1       1       doc/tech_debt.md
1       1       doc/workflow_completion_summary.md
5       5       doc/workflow_implementation_report.md
3       3       doc/workflow_quick_reference.md
```

**Total: 357 additions, 2120 deletions**

---

## 關鍵變更節錄

### 1. Plan 模板新增 SPEC 段落

**檔案**: `doc/plans/Idx-000_plan.template.md`

新增內容（L15-32）：
```markdown
## 📋 SPEC

### Goal
[任務的主要目標，一句話總結]

### Non-goals
[明確排除的範圍，避免 scope 漂移]
- ❌ 不做：[具體排除項目]

### Acceptance Criteria
[可驗收的條件清單]
1. ✅ [驗收條件 1]
2. ✅ [驗收條件 2]

### Edge cases
[需要處理的邊界情況]
- [邊界情況 1] → [處理方式]
```

### 2. Coordinator 新增三個 Gate 規則

**檔案**: `.agent/roles/coordinator.md`（新增檔案）

關鍵段落（L82-102）：
```markdown
**Research Gate**
- 觸發：Plan 內 `research_required: true`，或依賴檔案變更
- 規則：Link-required
- 未完成：退回 SPEC_MODE / Planner 補齊

**Maintainability Gate**
- 觸發：存在程式碼變更 且（總行數 > 50 或命中核心路徑）
- 輸出：Log 補 `MAINTAINABILITY REVIEW` 段落
- 硬規則：Reviewer 永不改 code

**UI/UX Gate**
- 觸發：變更檔案命中 UI 路徑模式
- 輸出：SCOPE GATE 固定記錄 + UI/UX CHECK 段落
- 硬規則：是 QA 報告段落，非獨立工具

**Evidence Gate（可選）**
- 允許新增條件：變更行數 > 200 或引用行數 > 80
- 未命中：不得新增 Evidence
```

### 3. dev-team 整合 Gate 流程

**檔案**: `.agent/workflows/dev-team.md`

新增內容（L93-96, L217-220）：
```markdown
**Research Gate（條件式，必先完成）**：
- 若 Plan 的 `research_required: true` 或依賴檔案變更
  - 必須先補齊 Plan 的 `RESEARCH & ASSUMPTIONS`
  - 未完成不得進入 Engineer 執行

...（Step 4 QA 階段）

   - **UI/UX Gate**：若 Scope Gate 判定 `UI/UX triggered: YES`
     → QA 報告後必須補 `## UI/UX CHECK`
   - **Maintainability Gate**：若存在程式碼變更 且（行數 > 50 或核心路徑）
     → QA 報告後必須補 `## MAINTAINABILITY REVIEW`
```

---

## 刪除檔案清單（terminal bridge 清理）

以下檔案已刪除（總計 1,829 lines）：

1. `.agent/docs/HANDOFF_TERMINAL_BRIDGE.md` (510 lines)
2. `.agent/docs/SESSION_SUMMARY.md` (229 lines)
3. `.agent/docs/TERMINAL_BRIDGE_SERVER.md` (443 lines)
4. `.agent/scripts/start_terminal_bridge.sh` (74 lines)
5. `.agent/scripts/stop_terminal_bridge.sh` (42 lines)
6. `.agent/scripts/terminal_bridge_server.py` (411 lines)
7. `.agent/scripts/test_terminal_bridge.sh` (120 lines)

**刪除原因**: 改用 VS Code Proposed API（terminalDataWriteEvent）直接監控終端，不再需要 bridge/server 架構。

---

**Evidence Version**: 1.0.0
**Last Updated**: 2026-01-17 14:30:00
