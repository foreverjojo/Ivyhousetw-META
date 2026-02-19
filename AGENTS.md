# AGENTS.md

本檔案是給「在此 repo 工作的 coding agents」的快速上手指南。

硬性規則：與 agent 的對話請使用「繁體中文」回覆；若需要產出給終端使用的指令/片段，指令本身維持原樣。

專案概況：Python 3.11 專案，使用 Ruff + Pytest。CI 會執行 lint/format/tests 與 repo 內的驗證腳本。

---

## 🚀 Dev-Team Workflow 入口

當需要啟動開發團隊工作流程時：
- 使用 `/dev` 或 `/dev-team` 指令
- 詳細流程請參閱：`.agent/workflows/dev-team.md`

> 📌 **注意**：如果你有個人的 Copilot prompt file 使用 `/dev`，建議改用其他名稱（如 `/devchat`）以避免與 repo workflow 衝突。

---
## Repo Layout（high signal）

- `core/`: 核心業務邏輯（建議 <= 400 行/檔；硬上限 500）
- `utils/`: 輔助工具（建議 <= 300 行/檔；硬上限 400）
- `scripts/`: 一次性腳本、驗證工具（建議 <= 400 行/檔；硬上限 500）
- `tests/`: pytest 測試 + 內建驗證腳本
- `.agent/`: dev-team 工作流與 skills 工具（Ruff 排除）
- `doc/`: plans/logs/adr/runbooks 與流程文件


## 開發環境 Setup

- Python：3.11+
- 安裝依賴：
  - `pip install -r requirements.txt -r requirements-dev.txt`

注意：
- 禁止提交任何 secret（API Key / Token / 密碼）。請使用 `.env`。


## 常用指令（與 CI 對齊）

### Lint（Ruff）

CI 分兩段：

- 阻擋型（語法/未定義名稱，CI 會 fail）：
  - `ruff check . --select=E9,F63,F7,F82 --target-version=py311`
- 風格型（CI 目前告警但不阻擋，請本地修）：
  - `ruff check core utils scripts tests main.py --target-version=py311`

### Format（Ruff formatter）

- 檢查格式：
  - `ruff format --check core utils scripts tests main.py`
- 自動格式化：
  - `ruff format core utils scripts tests main.py`

格式預設（參考 `.ruff.toml`）：
- 行長：100
- 引號：double quotes

### Tests（Pytest）

- 跑全部測試：
  - `pytest tests/ -v --cov=. --cov-report=term-missing`

- 跑單一檔案：
  - `pytest -q tests/test_kpi_golden.py`

- 跑單一測試：
  - `pytest -q tests/test_kpi_golden.py::test_kpi_golden`

- 用關鍵字挑測試：
  - `pytest -q -k trace_id`

### Repo-specific verifiers（CI 會跑）

- Schema 驗證：
  - `python tests/verify_skill_schemas.py`

- Runtime 驗證：
  - `python tests/verify_skills_runtime.py`


## 程式碼風格與工程規範

### Imports

- 優先使用 repo root 的絕對匯入，避免相對匯入。
- import 分三段（段與段間空一行）：
  1) 標準庫
  2) 第三方
  3) 專案內模組
- 禁止 wildcard imports（`from x import *`）。

### 命名

- 模組/函式/變數：`snake_case`
- 類別：`PascalCase`
- 常數：`UPPER_SNAKE_CASE`

### 型別（Types）

- public function 與非 trivial helper 請加 type hints。
- 對外/核心接口建議寫明確 return type。
- 型別過複雜時，優先引入小型 dataclass / TypedDict。

### 錯誤處理（Error Handling）

- 禁止 bare `except:`；請捕捉明確例外類型。
- raise 的錯誤訊息要可行動（能協助定位/修復）。
- 不要悄悄吞掉錯誤；若必須吞，需有 logging 並說明原因。

### Logging

- 優先使用 repo 既有的 structured logging（若該模組已有工具）。
- log 中禁止洩漏敏感資訊（token、raw auth header 等）。

### 檔案長度限制（來自 `ivy_house_rules.md`）

- 主程式（`app.py`/`main.py`）：建議 <= 600 行；硬上限 800
- UI 模組（`ui/*.py`）：建議 <= 500 行；硬上限 600
- 業務邏輯（`core/*.py`、`scripts/*.py`）：建議 <= 400 行；硬上限 500
- 工具模組（`utils/*.py`）：建議 <= 300 行；硬上限 400
- 測試檔（`tests/*.py`）：建議 <= 500 行；硬上限 1000

超過建議值請拆檔/抽模組，避免單檔過胖。


## Git / Process 規範（高影響）

- Commit message 遵循 Conventional Commits。
- Repo 有 State Gate（commit-msg hook）：`scripts/validate_state_gate.py`
  - 若使用 `feat(Idx-NNN): ...` 風格，請確認 `Idx-NNN` 已存在於 `doc/Implementation_Plan_index.md`。


## Pre-commit

repo 有 `.pre-commit-config.yaml`：

- 安裝：
  - `pip install pre-commit`
  - `pre-commit install`
  - `pre-commit install --hook-type commit-msg`

- 手動執行：
  - `pre-commit run --all-files`


## Cursor / Copilot 規則

- 目前 repo 中未發現 `.cursor/rules/**`、`.cursorrules`、`.github/copilot-instructions.md`。


## Dev-Team Agent Workflow（最重要）

此 repo 的 `/dev`（相容 `/dev-team`）工作流定義在：
- `.agent/workflows/dev-team.md`

入口規範在（開始前必讀）：
- `.agent/workflows/AGENT_ENTRY.md`

另外所有角色都必須遵守：
- `ivy_house_rules.md`

### 角色與責任範圍

- Coordinator：固定由 GitHub Copilot Chat 擔任，只負責統籌/問 Gate/更新 Plan/Log，不做實作與 QA
  - `.agent/roles/coordinator.md`
- Planner：產出 Spec/Plan（只寫計畫，不選工具、不回填 executor_tool/qa_tool）
  - `.agent/roles/planner.md`
- Meta Expert：僅在涉及指標計算（ROAS/CPC/CTR/CPM）或 Meta API 時觸發
  - `.agent/roles/meta_expert.md`
- Engineer：依 Plan 實作程式碼
  - `.agent/roles/engineer.md`
- QA：依 Plan 做審查，包含資安與 Cross-QA 規則
  - `.agent/roles/qa.md`

### 高層流程（不要跳步）

1) Coordinator 釐清目標與驗收 → 交給 Planner
2) Planner 產出 `doc/plans/Idx-XXX_plan.md`
3) User Approve Gate（用戶核准 Plan）
4) （條件式）Meta Expert Review
5) Tool Selection Gate（用戶選 Engineer Tool / QA Tool）
6) Engineer 執行（Codex CLI 或 OpenCode CLI）→ 需輸出 `[ENGINEER_DONE]`
7) QA 執行（需與 last_change_tool 不同）→ 需輸出 `[QA_DONE]`
8) 若 FAIL：進入修正迴圈 → 修正完成需輸出 `[FIX_DONE]`，再做 Cross-QA
9) PASS/PASS_WITH_RISK：Coordinator 產出 `doc/logs/Idx-XXX_log.md`，是否 commit 由用戶決定

### Completion markers（硬性要求）

- `[ENGINEER_DONE]`：工程實作完成
- `[QA_DONE]`：QA 審查完成
- `[FIX_DONE]`：修正完成（通常出現在 FAIL loop）

未輸出 marker 視為該階段未完成。

### 終端使用規則（VS Code Native）

- 固定終端角色：
  - `Codex CLI`：跑 codex
  - `OpenCode CLI`：跑 opencode
  - `Project`：跑 git / diff / pytest / ruff 等

硬性禁止：
- 禁止用 `terminal.sendText` 對 Codex/OpenCode 終端注入 git 指令（例如 `git diff`, `git checkout`, `git stash`）。
- git 操作只能在 `Project` terminal 或 VS Code SCM 執行。

### Scope Gate（防止 scope creep）

- 只允許變更 Plan 檔案白名單（Plan 的「檔案變更表」）內的路徑。
- 若發現額外檔案被修改/新增：必須停下來詢問用戶是否接受擴 scope、回滾，或拆成新 Plan。

### Cross-QA 規則（硬性）

- `qa_tool != last_change_tool`
- 若因例外情況必須同工具，必須：
  - 用戶明確同意
  - 在 Plan 的 `qa_compliance` 記錄原因（例如小修正、緊急 P0、純文件變更等）

### Skills（內建工具）

以下工具位於 `.agent/skills/`，常見用法如下：

- Plan 驗證：
  - `python .agent/skills/plan_validator.py <plan_file_path>`
- 代碼審查（含 API Key/檔案長度/規範檢查）：
  - `python .agent/skills/code_reviewer.py <file_path>`
- 測試執行：
  - `python .agent/skills/test_runner.py [test_path]`
- Log 統計/稽核（skills execution 成功率）：
  - `python .agent/skills/skills_evaluator.py <log_file_path>`
- Git diff 統計（給 Gate 判斷是否觸發 UI/UX 或 Maintainability）：
  - `python .agent/skills/git_stats_reporter.py /tmp/diff_stats.txt`
- 外部技能搜尋（GitHub Explorer）：
  - `python .agent/skills/github_explorer.py search <keyword>`
  - `python .agent/skills/github_explorer.py preview <repo>`
- 文件生成：
  - `python .agent/skills/doc_generator.py <file_path>`

### Plan / Log 模板（參考來源）

- Plan 模板：`doc/plans/Idx-000_plan.template.md`
- Dev-team 工作流：`.agent/workflows/dev-team.md`
- 入口約束：`.agent/workflows/AGENT_ENTRY.md`


## 備註

- 此 AGENTS.md 旨在描述「此 repo 的工作方式與規則」。
- 若與實際 CI 或 `.agent` 規範不一致，以 `.github/workflows/ci.yml` 與 `.agent/workflows/dev-team.md` 為準。
