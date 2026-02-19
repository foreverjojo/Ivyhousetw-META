# Log: Idx-033

**Index**: Idx-033
**Date**: 2026-01-23

## ✅ 結果摘要

- 已在主 README 與環境復原指南新增「一鍵自檢入口指令」。
- 已新增一鍵自檢腳本 `scripts/portable/self_check.py`（restore readiness + ruff + pytest）。
- 已新增 template 回推文件與同步腳本（僅同步 `.agent/**` 相關子集；明確排除 portable）。

## 📁 變更檔案

- 新增：`scripts/portable/self_check.py`
- 新增：`scripts/template/sync_agent_workflow_to_template.py`
- 新增：`doc/AGENT_WORKFLOW_TEMPLATE_UPSTREAM.md`
- 修改：`readme.md`
- 修改：`doc/ENVIRONMENT_RECOVERY.md`
- 修改：`.agent/Workflow_Plan_index.md`（登記 Idx-033）
- 新增：`.agent/plans/Idx-033_plan.md`

## 🧪 驗證與證據

### 1) 一鍵自檢（strict）
- 指令：`python scripts/portable/self_check.py --strict`
- 結果：PASS

### 2) Skills Execution Gate

- `code_reviewer.py scripts/portable/self_check.py`：pass
- `code_reviewer.py scripts/template/sync_agent_workflow_to_template.py`：pass
- `test_runner.py tests/`：exit_code=0（有 skip；status 顯示為 no_tests）

## 📦 Template 回推（不含 portable）

- 回推清單：`doc/AGENT_WORKFLOW_TEMPLATE_UPSTREAM.md`
- 同步腳本：`scripts/template/sync_agent_workflow_to_template.py`
  - 預設 dry-run；需加 `--apply` 才會寫入。
  - allowlist：`.agent/workflows` / `.agent/roles` / `.agent/skills` / `.agent/VScode_system` / `.agent/templates` + 兩個必要腳本。
  - 明確不會同步：`scripts/portable/**`、`.agent/logs/**`、`.agent/plans/**`、runtime 狀態檔。

## ⚠️ 風險與備註

- 本次同步工具僅在本 repo 產出；實際回推到 template repo 仍需在 template repo 另行檢查與建立 PR。
