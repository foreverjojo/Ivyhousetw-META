# ADR-0003: 採用多代理工作流程治理

## 狀態

✅ 已接受

## 背景

專案開發過程中面臨以下挑戰：
- AI 助手可能產生不一致或錯誤的輸出
- 缺乏明確的任務追蹤和責任歸屬
- 代碼變更難以追溯決策原因
- 多個 AI 工具之間切換時上下文遺失

需要一套治理框架來確保開發品質和可追溯性。

## 決策

採用 **VS Code 多代理工作流程**，包含：
1. **五條鐵律**：State Gate、Execution Mode Recording、QA Grading、Parallel Isolation、Log Binding
2. **角色分工**：Planner → Engineer → QA
3. **工件為真值**：Index / Plan / Log / Commit
4. **自動化驗證**：Pre-commit hooks + CI

## 理由

1. **可追溯性**：每個決策都有文件記錄
2. **品質保證**：強制 QA 審查和分級
3. **防止錯誤**：State Gate 阻止跳躍式開發
4. **工具無關**：可在不同 AI 工具間切換
5. **適合單人/小團隊**：不過度工程化

## 後果

### 優點

- 開發過程有完整記錄
- 減少 AI 自我欺騙的風險
- 回滾時有明確的決策點
- 新人（或未來的自己）能理解歷史決策

### 缺點

- 增加文件維護成本
- 小修改也需要走流程（已有 ≤20 行豁免）
- 需要學習和適應新流程

## 替代方案

### 方案 A: 無治理框架

**描述**：直接使用 AI 工具開發，不做額外治理

**未採用原因**：
- 難以追溯為什麼做了某個決策
- AI 錯誤無法被系統性地發現
- 技術債務快速累積

### 方案 B: 傳統 Scrum/Kanban

**描述**：使用 JIRA/Trello 等工具管理

**未採用原因**：
- 過於重量級（單人團隊）
- 與 AI 工具整合不便
- 無法處理 AI 特有的問題（如 context loss）

### 方案 C: Git-based workflow only

**描述**：只依賴 Git commit 和 PR 進行治理

**未採用原因**：
- 缺少「執行前規劃」的強制步驟
- 無法追蹤「為什麼選擇這個方案」
- AI 可能產生大量 commit，難以審查

## 相關資訊

- **決策者**：Jonas + AI Assistants
- **決策日期**：2026-01-09
- **相關檔案**：
  - `doc/workflow_process_analysis.md`
  - `doc/Implementation_Plan_index.md`
  - `.agent/roles/`
  - `scripts/validate_state_gate.py`
  - `scripts/check_active_task.py`

---

**最後更新**：2026-01-10
