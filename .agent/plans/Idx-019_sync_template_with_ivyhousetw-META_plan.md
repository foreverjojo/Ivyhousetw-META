---
index: Idx-019
title: "Sync Template: Align agent-workflow-template with Ivyhousetw-META dev-team workflow"
workflow: dev-team
owner: foreverjojo
status: approved
priority: P1
created: 2026-01-19
planner: GitHub Copilot
---

## 📋 SPEC

### 目標

將 GitHub 上的 template repository `foreverwow001/agent-workflow-template` 的 Dev-Team workflow 文件與相關腳本**同步更新為本專案（Ivyhousetw-META）當前的 dev-team workflow**（完全一致）。

**重點**：
- **刪除 SendText Bridge（`tools/sendtext-bridge/`）相關檔案與自動化腳本**（確定不再使用、已被評估為 legacy）。
- **同步 Template 中的工作流程文件與入口檔**（`.agent/workflows/dev-team.md`、`.agent/workflows/AGENT_ENTRY.md`、`.agent/PORTABLE_WORKFLOW.md` 等）為本 repo 的內容（包含以 `terminal.sendText` + VS Code Proposed API 為主要執行/監控方式的說明）。
- 更新 `README.md`、`CHANGELOG_v1.1.0.md`、`setup_workflow.sh` 等文件，記錄移除理由、回滾指引與備註（保留歷史 tag/branch）。

> **Note**：本 Plan 為 Idx-019 re-scoped 版本（參考先前 commit `5373f03` 為 doc-only /dev clarification），此次變更屬高影響（跨 repo），已將 `research_required: true`。

### 主要變更檔案清單（Template repo 中）

| 檔案 (template) | 動作 | 說明 |
|---|---:|---|
| `tools/sendtext-bridge/` | **刪除** | 移除 SendText Bridge 程式碼、extension、vsix 與相關檔案 |
| `.agent/scripts/sendtext.sh` | **刪除** | CLI wrapper（依賴 SendText Bridge） |
| `.agent/scripts/auto_execute_plan.sh` | **刪除** | 自動化執行腳本（依賴 SendText Bridge） |
| `.agent/workflows/dev-team.md` | **替換/更新** | 將文件內容同步為 Ivyhousetw-META 的 `dev-team.md`（移除 sendtext references，強調 `terminal.sendText` + Proposed API） |
| `.agent/workflows/AGENT_ENTRY.md` | **更新** | 與本 repo 的 AGENT_ENTRY 保持一致（必讀檔 / READ_BACK_REPORT 等） |
| `.agent/PORTABLE_WORKFLOW.md` | **更新** | 移除與 SendText Bridge 相關章節，說明目前推薦做法為 `terminal.sendText` + Proposed API |
| `.agent/CHANGELOG_v1.1.0.md` | **更新** | 註明已移除 SendText Bridge、提供移除理由與回滾步驟 |
| `README.md` | **更新** | 移除或標註 SendText Bridge 為已刪除 / 不建議安裝（並指向 v1.1.0 以前的 tag 作為參考） |
| `.agent/scripts/setup_workflow.sh` | **更新** | 移除複製 SendText Bridge 的步驟（或註記為 optional / legacy） |
| `.agent/VScode_system/**` | **新增/同步** | 將本 repo 的 `.agent/VScode_system/` 可攜設定檔（4 個）同步至 template（不含 token） |
| 其他 `.agent/*` docs referencing SendText | **更新** | 統一說明，不留矛盾資訊 |

---

## 🔍 RESEARCH & ASSUMPTIONS

- research_required: true
- 我已檢視 `foreverwow001/agent-workflow-template` 的 `.agent/CHANGELOG_v1.1.0.md`（含 SendText Bridge）、`.agent/workflows/dev-team.md`（含 auto_exec 節點）與相關 scripts/roles/skills 檔案，並比對我們 repo 的對應檔案。
- 假設我們可在 template repo 建 branch 與 PR（若無權限，將 fork 並發 PR），並於 PR 說明中列出移除/替換的詳細理由與回滾步驟。
- 假設移除 SendText Bridge 對多數使用者為無痛升級（仍會在 README/CHANGELOG 明確註明與提供回滾指引）。

## 🔒 SCOPE & CONSTRAINTS

- **Scope（包含）**：上述列出的 files/sections（主要在 `.agent/`、`tools/`、`README.md`、`CHANGELOG_v1.1.0.md`、`setup_workflow.sh`）。
- **Scope（不包含）**：Template 的技能程式（`code_reviewer.py`, `test_runner.py` 等）除非與 SendText Bridge 有直接相依關係，否則不更動。
- 決策：**完全移除** SendText Bridge（不是保留為 optional）；並在 README/CHANGELOG 註明移除理由與回滾步驟。

### Whitelists
- **Ivyhousetw-META whitelist (本 repo)**:
  - `.agent/plans/`
  - `.agent/Workflow_Plan_index.md`
  - `.agent/logs/`
  - `.agent/VScode_system/**`
- **Template repo whitelist (要刪除/更新的檔案清單)**:
  - `tools/sendtext-bridge/**` (刪除)
  - `.agent/scripts/sendtext.sh` (刪除)
  - `.agent/scripts/auto_execute_plan.sh` (刪除)
  - `.agent/workflows/dev-team.md` (替換)
  - `.agent/workflows/AGENT_ENTRY.md` (更新)
  - `.agent/PORTABLE_WORKFLOW.md` (更新)
  - `.agent/CHANGELOG_v1.1.0.md` (更新)
  - `README.md` (更新)
  - `.agent/VScode_system/**` (新增/同步)

## 🔁 執行步驟（概述）
1. Clone template repo (`git clone https://github.com/foreverwow001/agent-workflow-template.git`)
2. 建立 branch: `chore/sync-dev-team-Idx-019`
3. 建立備份 tag/branch（保留舊的 `v1.1.0` sendtext 資源）
4. 刪除 `tools/sendtext-bridge/` 與依賴腳本（`sendtext.sh`, `auto_execute_plan.sh`）
5. 將本 repo 的 `.agent/workflows/dev-team.md` / `.agent/workflows/AGENT_ENTRY.md` / `.agent/PORTABLE_WORKFLOW.md` 等內容覆寫到 template（確保與本 repo 相同）
6. 將 `.agent/VScode_system/**` 4 個檔案同步到 template（檢查無 token / 機器特定路徑）
7. 更新 `README.md`, `.agent/CHANGELOG_v1.1.0.md`, `.agent/scripts/setup_workflow.sh`（移除 sendtext 相關步驟 / 標註 legacy / 提供回滾指引）
8. 執行 linter / plan validator / code reviewer 對變更檔案做檢查
9. Commit + Push 到 branch → 開 PR（標題：`chore(Idx-019): sync dev-team workflow w/ Ivyhousetw-META`）
10. 等待 Cross-QA（codex-cli / opencode）完成審查，修正後合併


## 📁 檔案變更（本次會在 template 上進行）
- 刪除： `tools/sendtext-bridge/`
- 刪除： `.agent/scripts/sendtext.sh`
- 刪除： `.agent/scripts/auto_execute_plan.sh`
- 更新： `.agent/workflows/dev-team.md`（同步內容）
- 更新： `.agent/workflows/AGENT_ENTRY.md`（同步內容）
- 更新： `.agent/PORTABLE_WORKFLOW.md`（移除 sendtext references）
- 更新： `README.md`（移除 / 標註）
- 更新： `.agent/CHANGELOG_v1.1.0.md`（記錄移除）
- 更新： `.agent/scripts/setup_workflow.sh`（移除 sendtext copy 步驟 / 註記 legacy）
- 新增： `.agent/VScode_system/*`（4 個檔案）

## ✅ Done Definition (Reiteration)
- Template repo 的上述檔案已被移除 / 更新，PR 已建立並通過 QA，且 Log 中包含 PR 連結與 commit hash。

<!-- EXECUTION_BLOCK_START -->
plan_created: 2026-01-19T23:48:12+00:00
plan_approved: 2026-01-19T23:48:12+00:00
scope_policy: strict
expert_required: true
expert_conclusion: pending
scope_exceptions: []

# Engineer 執行
executor_tool: codex-cli
executor_tool_version: TBD
executor_user: TBD
executor_start: TBD
executor_end: TBD
session_id: TBD
last_change_tool: codex-cli

# QA 執行
qa_tool: opencode
qa_tool_version: TBD
qa_user: TBD
qa_start: TBD
qa_end: TBD
qa_result: pending
qa_compliance: pending

# 收尾
log_file_path: .agent/logs/Idx-019_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->
