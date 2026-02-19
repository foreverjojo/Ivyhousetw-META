# Template Repo 回推建議（不含 portable）

本文件目的：把本 repo（Ivyhousetw-META）已落地且穩定的 dev-team workflow / skills 強化，整理成可回推到 template repo（`foreverwow001/agent-workflow-template`）的「最小可行同步包」。

> ✅ 依使用者要求：**一鍵復原/自檢模組（portable）不回推**。

---

## 1) 建議回推的內容（高優先）

### A. Skills 系統強化（建議整包同步）
目標：讓 template repo 在「Plan 驗證、變更統計 Gate、skills manifest、skills 執行統計」上具備機械化能力。

建議同步：
- `.agent/skills/plan_validator.py`：Plan Gate（必跑）
- `.agent/skills/git_stats_reporter.py`：Maintainability/UI-UX Gate 判定依據
- `.agent/skills/manifest_updater.py` + `.agent/skills/skill_manifest.json`：skills 清單同步（builtin/external/legacy）
- `.agent/skills/skills_evaluator.py`：從 Log 產生 skills 成功率/失敗統計
- `.agent/skills/github_explorer.py` + `.agent/skills/skill_converter.py`：安全的外部技能搜尋/預覽/下載流程
- `.agent/skills/schemas/**`：skills JSON output schema（graceful degradation）
- `.agent/skills/SKILL.md`：技能索引文件（讓使用者可複製指令）

### B. Workflow 合約文件（建議同步）
目標：template repo 的「Gate/證據鏈/Role Selection/Cross-QA」可直接沿用。

建議同步：
- `.agent/workflows/AGENT_ENTRY.md`：唯一入口與 READ_BACK_REPORT Gate
- `.agent/workflows/dev-team.md`：Plan → Approve → Role Selection → Execute → QA → Log → Close 的主流程
- `.agent/roles/*.md`：planner/engineer/qa/coordinator（以及 domain/meta expert 視 template 需求保留）

### C. VS Code 系統檔（建議同步）
目標：把「終端注入/監控」與 deterministic gates 的規範落地。

建議同步：
- `.agent/VScode_system/**`

### D. Template 初始化腳本（視 template 現況擇一同步）
目標：讓 template repo 的一鍵初始化能建立完整 `.agent/` 結構與必備檔案。

建議同步：
- `.agent/scripts/setup_workflow.sh`
- `.agent/scripts/run_codex_template.sh`

### E. VS Code 周邊（A+B：終端管理/編排 + sendText/監測）（建議同步）
目標：讓新專案從 template 開箱就具備「終端注入（sendText）+ 監測（capture）」能力。

建議同步：
- `tools/vscode_terminal_injector/**`：local VS Code extension（只負責 sendText 注入）
- `tools/vscode_terminal_monitor/**`：local VS Code extension（Proposed API 監測 + fallback capture）
- `tools/vscode_terminal_orchestrator/**`：legacy 相容（workflow loop / bridge 場景）
- 兩個套件的 VSIX 安裝命令（`code-insiders --install-extension ...`）
- `.vscode/**`：workspace settings / tasks / extension recommendations（包含 Copilot terminal command debug 開關）

---

## 2) 不回推的內容（本次明確排除）

- `scripts/portable/**`：一鍵復原/自檢模組（依使用者指示不做）
- `.agent/logs/**`、`.agent/plans/**`：稽核/任務紀錄屬於 repo 私有，避免污染 template
- `.agent/active_sessions.json`、`.agent/execution_log.jsonl`：runtime 狀態檔

---

## 3) 一鍵同步腳本（在本 repo 執行）

本 repo 已提供同步腳本（預設 dry-run）：

```bash
python scripts/template/sync_agent_workflow_to_template.py --template-root /path/to/agent-workflow-template
```

要實際套用覆寫/寫入（仍不會 commit）：

```bash
python scripts/template/sync_agent_workflow_to_template.py --template-root /path/to/agent-workflow-template --apply
```

（選用）也同步 VS Code 周邊（A+B）：

```bash
python scripts/template/sync_agent_workflow_to_template.py --template-root /path/to/agent-workflow-template --include-peripherals
python scripts/template/sync_agent_workflow_to_template.py --template-root /path/to/agent-workflow-template --include-peripherals --apply
```

建議操作流程：
1. 在本機 clone `foreverwow001/agent-workflow-template` 到某個資料夾
2. 先跑 dry-run 看要覆寫哪些檔案
3. 確認無誤後再加 `--apply`
4. 到 template repo 內跑 lint/tests（若有）並開 PR

---

## 4) 驗收清單（template repo）

- ✅ `AGENT_ENTRY.md` 的 READ_BACK_REPORT Gate 可正常要求「必讀檔案逐檔閱讀」
- ✅ `dev-team.md` 內的 Role Selection / Cross-QA / Skills Execution Gate 說明完整
- ✅ `plan_validator.py` 能對 template 的 plan 檔案通過/失敗給出明確 JSON
- ✅ `manifest_updater.py --check` 在 template repo 可正常運作
