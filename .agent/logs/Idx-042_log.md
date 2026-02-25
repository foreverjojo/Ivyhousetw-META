# Idx-042 QA Log（docs/governance）

- QA User: vscode
- QA Window (UTC): 2026-02-25T16:12:00Z ~ 2026-02-25T16:33:17Z
- last_change_tool: copilot-chat
- qa_tool (declared in plan): codex-cli
- QA Result: PASS_WITH_RISK

## Summary
- 將 Coordinator「必做 preflight」清單化，並在 workflow/docs 中固定引用 Injector + Monitor 的 command IDs。
- 明確標示 Orchestrator（`ivyhouseTerminalOrchestrator.*`）為 deprecated/legacy，避免新流程誤用。
- `git diff --check` 已為乾淨（無 whitespace errors）。

## QA Evidence

### 1) Plan validator
- Command: `python .agent/skills/plan_validator.py .agent/plans/Idx-042_plan.md`
- Result: PASS

### 2) Code reviewer（敏感資訊/檔案長度檢查）
- Command: `python .agent/skills/code_reviewer.py .agent/roles/coordinator.md`
- Result: WARNING
- Note: `.agent/roles/coordinator.md` 行數 837（超過 500 建議上限）；本次未拆檔，僅做規範一致化。

- Command: `python .agent/skills/code_reviewer.py .agent/workflows/dev-team.md`
- Result: PASS

- Command: `python .agent/skills/code_reviewer.py .agent/workflows/AGENT_ENTRY.md`
- Result: PASS

- Command: `python .agent/skills/code_reviewer.py .agent/Workflow_Plan_index.md`
- Result: PASS

- Command: `python .agent/skills/code_reviewer.py doc/DEV_TEAM_WORKFLOW_SUMMARY.md`
- Result: PASS

- Command: `python .agent/skills/code_reviewer.py doc/TOOL_USAGE.md`
- Result: PASS

### 3) Whitespace check
- Command: `git diff --check`
- Result: PASS

## State Gate Notes
- 因本次同時修改 `.agent/**` 與 `doc/**`，State Gate 會將其視為不同領域 Index。
- 依建議採兩個 commit：
  - commit A：僅 `.agent/**` 使用 `feat(Idx-042): ...`
  - commit B：僅 `doc/**` 使用 `docs: ...`

## Marker Evidence
```
[QA_DONE]
TIMESTAMP=2026-02-25T16:33:17Z
TASK_ID=Idx-042
QA_RESULT=PASS_WITH_RISK
```
