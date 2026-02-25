# Idx-042 — Coordinator Preflight 清單化 + Command IDs 規範化（只認 Injector+Monitor；Orchestrator deprecated）

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-02-25 14:30:00+00:00
plan_approved: 2026-02-25 16:10:30+00:00
scope_policy: strict
expert_required: false
expert_conclusion: N/A
execution_backend_policy: extension-sendtext-required
scope_exceptions: []

# Engineer 執行
executor_tool: copilot-chat
executor_backend: copilot-chat
monitor_backend: manual_confirmation
executor_tool_version: gpt-5.2
executor_user: vscode
executor_start: 2026-02-25T16:11:00Z
executor_end: 2026-02-25T16:33:17Z
session_id: N/A
last_change_tool: copilot-chat

# Copilot Chat 小修正政策（僅當 executor_tool=copilot-chat 才允許填；其餘 executor 保持 placeholder）
copilot_chat_small_fix_allowed: true
copilot_chat_small_fix_reason: docs-only（workflow 規範一致化 + command IDs 固化）
copilot_chat_max_changed_lines: 3500
copilot_chat_allowed_path_globs: ["doc/**", "README.md", "CHANGELOG.md", "CHECKLIST.md", "*.md", ".agent/**"]

# QA 執行
qa_tool: codex-cli
qa_tool_version: N/A
qa_user: vscode
qa_start: 2026-02-25T16:12:00Z
qa_end: 2026-02-25T16:33:17Z
qa_result: PASS_WITH_RISK
qa_compliance: ⚠️ 例外：本任務為文件一致化，QA 以一致性檢核（grep/存在性）替代終端注入 cross-QA

# 收尾
log_file_path: .agent/logs/Idx-042_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

---

## 📋 SPEC

### Goal
把「Coordinator 注入/監控的必做命令」變成**固定、可複製、可稽核**的 preflight 清單，並在 workflow 文件中**統一只引用 Injector+Monitor 的 command IDs**，降低發生「需要你一再提醒才調用 extension」的機率。

### Non-goals
- ❌ 不修改 `tools/vscode_terminal_injector/**` 與 `tools/vscode_terminal_monitor/**` 的程式碼或命令。
- ❌ 不新增第三套 injection/capture 機制（例如新 HTTP bridge）。
- ❌ 不改動 workflow loop 狀態機與 marker 判定規則（沿用既有規範）。

### Acceptance Criteria
1. ✅ `.agent/roles/coordinator.md` 新增「固定 preflight（必做）」段落，內容至少包含：
   - 在 Project terminal 執行 `python scripts/vscode/workflow_preflight_check.py --json`，並以 `checks.proposed_api_true.ok == true` 作為注入前必要條件。
   - 注入/啟動固定使用 Injector 的 command IDs（不再只寫 Command Palette 標題）。
   - 監測/自檢固定使用 Monitor 的 command IDs（包含 `/status` 自動驗證）。
2. ✅ `.agent/workflows/dev-team.md` 與 `.agent/workflows/AGENT_ENTRY.md`：
   - 明確寫出「只認 Injector + Monitor；Orchestrator 是 deprecated，不應再用於新流程」。
   - 在 Role Selection / Preflight Gate 段落統一列出 command IDs（single source of truth）。
3. ✅ `doc/TOOL_USAGE.md` 與 `doc/DEV_TEAM_WORKFLOW_SUMMARY.md` 內關於注入/監控的描述，與上述規範一致（避免同 repo 內出現互相矛盾的說法）。
4. ✅ 文件中引用的 command IDs 必須存在於 extension 實作：
   - Injector: `ivyhouseTerminalInjector.startAll`, `ivyhouseTerminalInjector.sendLiteralToCodex`, `ivyhouseTerminalInjector.sendLiteralToOpenCode`, `ivyhouseTerminalInjector.resetSessionState`
   - Monitor: `ivyhouseTerminalMonitor.ping`, `ivyhouseTerminalMonitor.autoCaptureCodexStatus`, `ivyhouseTerminalMonitor.verifyCodexStatusInjection`, `ivyhouseTerminalMonitor.openLastCodexCapture`, `ivyhouseTerminalMonitor.clearCodexCapture`
5. ✅ Orchestrator 命令（`ivyhouseTerminalOrchestrator.*`）在文件中只以「deprecated / legacy」方式出現，且不再被寫為必做或預設流程。

### Preflight（規範草案，將寫入 Coordinator）
- 1) Project terminal：`python scripts/vscode/workflow_preflight_check.py --json`
- 2) VS Code command：`ivyhouseTerminalInjector.startAll`
- 3) VS Code command：`ivyhouseTerminalMonitor.verifyCodexStatusInjection`
- 4) 若驗證失敗：`ivyhouseTerminalMonitor.openLastCodexCapture`（供診斷），並停止注入（先修復環境）

---

## 🔍 RESEARCH & ASSUMPTIONS
research_required: false

### Sources
- Injector README / package / code：`tools/vscode_terminal_injector/README.md`, `tools/vscode_terminal_injector/package.json`, `tools/vscode_terminal_injector/extension.js`
- Monitor README / package / code：`tools/vscode_terminal_monitor/README.md`, `tools/vscode_terminal_monitor/package.json`, `tools/vscode_terminal_monitor/extension.js`
- Preflight script：`scripts/vscode/workflow_preflight_check.py`
- Workflow 規範：`.agent/roles/coordinator.md`, `.agent/workflows/dev-team.md`, `.agent/workflows/AGENT_ENTRY.md`

### Assumptions
- ✅ VERIFIED：Monitor 會寫入 `.service/terminal_capture/monitor_debug.jsonl` 供 preflight 判定 Proposed API 狀態。
- ✅ VERIFIED：Injector/Monitor 的 command IDs 均由 `registerCommand(...)` 註冊，適合作為文件中唯一的機械化引用。

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `.agent/roles/coordinator.md`
- `.agent/workflows/dev-team.md`
- `.agent/workflows/AGENT_ENTRY.md`
- `doc/TOOL_USAGE.md`
- `doc/DEV_TEAM_WORKFLOW_SUMMARY.md`
- `.agent/Workflow_Plan_index.md`
- `.agent/plans/Idx-042_plan.md`
- `.agent/logs/Idx-042_log.md`（執行完成後新增）

### Done 定義
- 滿足所有 Acceptance Criteria，且文件間不再出現互相矛盾的「注入/監控」描述。

### Rollback 策略
- **Level**: L1（文件/流程規範）
- 回滾動作：`git restore --worktree --staged -- .agent/roles/coordinator.md .agent/workflows/dev-team.md .agent/workflows/AGENT_ENTRY.md doc/TOOL_USAGE.md doc/DEV_TEAM_WORKFLOW_SUMMARY.md .agent/Workflow_Plan_index.md`

### Max rounds
- 2 rounds（文件修訂 1 + QA/一致性修正 1）

---

## 📁 檔案變更表

| 檔案 | 動作 | 說明 |
|------|------|------|
| .agent/roles/coordinator.md | 修改 | 加入固定 preflight 清單 + 固定 command IDs 引用 + 明確 deprecated Orchestrator |
| .agent/workflows/dev-team.md | 修改 | Role Selection / Preflight Gate 統一寫 command IDs；只認 Injector+Monitor |
| .agent/workflows/AGENT_ENTRY.md | 修改 | 與 dev-team.md 一致化（避免規範分歧） |
| doc/TOOL_USAGE.md | 修改 | 把「注入/監控」描述改成 extension command IDs（避免誤導回到內建 sendText） |
| doc/DEV_TEAM_WORKFLOW_SUMMARY.md | 修改 | 與上述一致化 |
| .agent/Workflow_Plan_index.md | 修改 | 登記 Idx-042 |
| .agent/plans/Idx-042_plan.md | 新增 | 本 Plan |
| .agent/logs/Idx-042_log.md | 新增 | 完成後產出 log（含 QA 結果與一致性檢核） |
