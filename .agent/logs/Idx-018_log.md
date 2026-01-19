# Log: Idx-018 Dev-Team Workflow Artifact Segregation (Dual Index)

- 日期：2026-01-19
- 狀態：QA_DONE（已完成）
- commit：de0d3cd

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
- Plan Validator：PASS（Idx-018 plan）
- State Gate：PASS（shim 轉發可用；routing：變更含 `.agent/**` → workflow index）
- Ruff：PASS（lint + format check）
- Pytest：PASS（1 skipped：golden files 尚未建立）
- Pre-commit：PASS（trailing whitespace / EOF fixer 自動修正後通過）

## 交付內容
- 已完成雙 Index 分離：
	- Project index：`doc/Implementation_Plan_index.md`
	- Workflow index：`.agent/Workflow_Plan_index.md`
- workflow artifacts 已集中到 `.agent/**`：`plans/`、`logs/`、`scripts/`、`workflows/`
- `scripts/validate_state_gate.py` 保留 shim（預計 2026-02-09 移除）

## 風險與備註
- 本次 commit 依用戶要求「一併納入昨日尚未 commit 的變更」，因此同一個 commit 也包含 core/scripts/tests/utils 等修改。
- 若後續需要更嚴格的治理，建議將「repo 治理/結構調整」與「功能/品質改動」拆成不同 Idx 與獨立 commit。

## 後續
- 建議補上 `doc/Implementation_Plan_index.md` 的最小更新：移除/不再引用已搬移的 workflow 條目（避免 broken link）。
