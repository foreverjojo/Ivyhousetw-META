# Log: Idx-018 Dev-Team Workflow Artifact Segregation (Dual Index)

- 日期：2026-01-19
- 狀態：ENGINEER_DONE（待 QA）

## 目標
- 建立雙 Index：`doc/Implementation_Plan_index.md`（project）與 `.agent/Workflow_Plan_index.md`（workflow）。
- workflow artifacts 收斂到 `.agent/**`（plans/logs/scripts）。

## 變更摘要
- 新增 `.agent/Workflow_Plan_index.md`
- 搬移 workflow logs：`doc/logs/Idx-009~017_*` → `.agent/logs/`
- 搬移 workflow plans：`doc/plans/Idx-010~015_*` → `.agent/plans/`
- 搬移 workflow scripts：`scripts/dev_team.py`、`scripts/crew_agents.py` → `.agent/scripts/`
- 新增 `.agent/scripts/validate_state_gate.py`（routing）
- 保留 `scripts/validate_state_gate.py` shim（預計 2026-02-09 移除）
- 新增 `doc/FILE_OWNERSHIP.md`

## 驗證
- State Gate shim 轉發可用
- routing：staged 含 `.agent/**` → workflow index

## 後續
- 建議補上 `doc/Implementation_Plan_index.md` 的最小更新：移除/不再引用已搬移的 workflow 條目（避免 broken link）。
