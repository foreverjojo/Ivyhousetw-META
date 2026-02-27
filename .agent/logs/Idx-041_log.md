# Log: Idx-041

**Index**: Idx-041
**Date**: 2026-02-22
**Goal**: Workflow Loop：將「QA FAIL 且 round >= maxRounds」的決策互動，從 VS Code QuickPick 改為 pendingDecision + `POST /workflow/decision` 回寫（Coordinator 以 Chat Ask Questions 收集答案）。

---

## ✅ 結果摘要

- 決策點不再呼叫 `vscode.window.showQuickPick`（僅針對 `checkFailAndAskUser()` 決策）。
- `/workflow/status` 回傳 `pendingDecision`；只要 pending 存在就強制 `state=needs_user_input`。
- 新增 `POST /workflow/decision`（protected endpoint）提交 `{decisionId, decision, freeText, phase}`。
- 行為符合 Idx-041：
  - `CONTINUE`：同一 workflow loop 原地續跑下一輪（不需重啟）。
  - `MORE_INFO`：先記錄自由輸入並輸出診斷，之後回到 final 決策。
  - 自由輸入（FREEFORM）：記錄 note 後要求明確決策。
  - Timeout：安全停止並持久化 `needs_user_input`。
- QA 結論：**PASS WITH RISK**（原因：既有檔案過長警示；本次未拆檔）。

---

## 🧭 Plan / Gate

- Plan：`.agent/plans/Idx-041_plan.md`
- Scope policy：strict（本次為完成閉環新增 log，視為 user request scope exception）

---

## 🔒 Scope Gate（strict scope + exception）

### Plan whitelist（依 Idx-041）
- `tools/vscode_terminal_orchestrator/extension.js`
- `tools/vscode_terminal_orchestrator/package.json`
- `scripts/sendtext_bridge_client.py`
- `.agent/roles/coordinator.md`
- `.agent/Workflow_Plan_index.md`

### Scope exception（用戶要求閉環）
- `.agent/logs/Idx-041_log.md`（本檔）

---

## 🔧 變更摘要（高層）

- Extension：導入 `pendingDecision` + wait/timeout 機制，並新增 `/workflow/decision` handler。
- Bridge status：`/workflow/status` 增加 `pendingDecision` payload；pending 時 state 以 `needs_user_input` 呈現。
- Python client：新增 `workflow-decision` 子命令，協助 Coordinator 回寫 decision。
- Coordinator SOP：更新 T8，改為 status 取 `decisionId` → workflow-decision 回寫。

---

## 🧪 QA 證據（skills + 測試）

### Plan Validator
- Command: `python .agent/skills/plan_validator.py .agent/plans/Idx-041_plan.md`
- Result: `pass`

### Code Reviewer
- `tools/vscode_terminal_orchestrator/extension.js`：warning（file_too_long，約 4953 行；屬既有檔案結構限制）
- `scripts/sendtext_bridge_client.py`：pass
- `.agent/roles/coordinator.md`：warning（file_too_long，約 1173 行；屬既有檔案結構限制）

### Syntax / Tests
- `node --check tools/vscode_terminal_orchestrator/extension.js`：OK
- `python -m py_compile scripts/sendtext_bridge_client.py`：OK
- `pytest -q`：PASS（1 個既有 SKIP：golden files 尚未建立）

---

## ⚠️ 風險與限制

- **file_too_long 警示**：`tools/vscode_terminal_orchestrator/extension.js` 與 `.agent/roles/coordinator.md` 皆遠超建議行數；本次為最小變更任務未拆檔，故 QA 定為 PASS WITH RISK。
- **E2E 互動需人工驗證**：本次以 unit/smoke/skills 為主；若需完整互動演練，建議實際觸發 maxRounds → 以 `workflow-status` 取得 `pendingDecision.decisionId` → `workflow-decision` 回寫並觀察 loop 行為。

---

## 📌 收尾狀態

- Log：已產出（本檔）。
- Commit：pending user decision（此 repo 規範下是否 commit 由使用者決定）。
