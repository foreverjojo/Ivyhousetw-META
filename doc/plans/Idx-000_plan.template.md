# Plan: Idx-NNN

**Index**: Idx-NNN
**Created**: YYYY-MM-DD
**Planner**: @AgentName

---

## 🎯 目標

[任務目標描述]

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| path/to/file.py | 新增/修改/刪除 | 變更說明 |

---

## 📝 邏輯細節

### 1. [檔案名稱]
[具體修改說明，給 Engineer 足夠的實作指引]

### 2. [檔案名稱]
[具體修改說明]

---

## ⚠️ 注意事項

- **風險提示**：[可能會弄壞的地方]
- **資安考量**：[API Key、敏感資料處理]
- **相依性**：[與其他檔案或功能的關聯]

---

## 🔗 相關資源

- [相關文檔或 Issue]
- [參考資料]

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
executor_tool: [待用戶確認: copilot|codex-cli|opencode]
executor_tool_version: [version number]
executor_user: [github-account or email]
executor_start: [執行開始時間]
executor_end: [執行結束時間]
session_id: [terminal session ID if available]
qa_tool: [待用戶確認: copilot|codex-cli|opencode]
qa_tool_version: [version number]
qa_user: [github-account or email]
qa_start: [QA 開始時間]
qa_result: [PASS|PASS_WITH_RISK|FAIL]
<!-- EXECUTION_BLOCK_END -->

### 執行模式建議

| 工具 | 適用場景 | 優勢 | 限制 | 需要監控 |
|------|---------|------|------|----------|
| **Copilot** | 互動式開發、複雜邏輯重構、需即時反饋 | 內建監控、即時回應、上下文理解強 | 執行速度較慢 | ❌ 否 |
| **Codex CLI** | 批次檔案操作、模板化工作、大規模重構 | 執行速度快、支援批次操作 | 需要外部監控、無即時反饋 | ✅ 是 |
| **OpenCode** | 需要 captured output、複雜指令執行 | 強大的 terminal 整合、output 監控 | 需要學習曲線、設定較複雜 | ✅ 是 |

### QA 模式建議

| Executor Tool | 建議 QA Tool | 理由 |
|---------------|--------------|------|
| Copilot | Codex CLI / OpenCode | 自動化 QA 可驗證 Copilot 產出的語法正確性 |
| Codex CLI | Copilot / OpenCode | Copilot 可提供語意檢查，OpenCode 可驗證執行結果 |
| OpenCode | Copilot / Codex CLI | Copilot 可提供程式碼審查，Codex CLI 可批次驗證 |

**Cross-QA 例外情況**：

| 例外類型 | 條件 | 審批流程 | 記錄格式 |
|---------|------|---------|----------|
| **小修正** | ≤20 行程式碼變更 | 1. Copilot 詢問用戶確認<br/>2. 用戶明確回覆「允許」<br/>3. 記錄變更行數 | `QA Compliance: ⚠️ 例外（小修正）- 變更：[X 行] - 用戶：已確認` |
| **緊急修復** | P0 級別 bug<br/>影響生產環境 | 1. 確認優先級為 P0<br/>2. 用戶說明緊急原因<br/>3. 記錄 issue/ticket 編號 | `QA Compliance: ⚠️ 例外（緊急修復）- Issue: [#NNN] - 理由：[說明]` |
| **文件修正** | 無程式碼變更<br/>僅修改 .md/.txt | 自動豁免<br/>無需用戶確認 | `QA Compliance: ✅ 豁免（文件修正）- 檔案：[列表]` |

**違規處理流程**：
1. QA 工具檢測到 `executor_tool == qa_tool`
2. 檢查是否符合例外條件（小修正/緊急修復/文件修正）
3. 若不符合例外，**拒絕執行** QA 並要求用戶重新選擇工具
4. 若符合例外，詢問用戶確認並記錄到 plan 的 EXECUTION_BLOCK
5. 所有例外情況必須在最終 Log 檔中說明

---

## 🔄 Rollback 策略

**L1 (自我修正)**: Engineer 發現錯誤，立即修正

**L2 (腳本回滾)**: 執行失敗時自動觸發（僅限 `execution: codex-cli`）
  - 前置條件：乾淨 worktree（`git status --porcelain` 為空）
  - 回滾動作：
    - 還原 tracked 變更：`git restore --worktree --staged -- .`
    - 刪除新增的 untracked 檔案（不含 `.agent/`）
    - 若 HEAD 改變，執行 `git reset --hard <PRE_HEAD>`
  - 保留審計證據：`.agent/` 目錄始終保留

**L3 (Copilot 建議)**: QA 不通過時，Copilot 分析 git log 並提供回滾建議
  - `git revert <commit>`（推薦，保留歷史）
  - 或 `git reset --soft HEAD~N`（保留變更於 staging）

**L4 (任務中止)**: User 確認後執行
  - `git reset --soft HEAD~N`（保留變更）
  - 或 `git reset --hard`（完全捨棄，需明確確認）

**預期 Rollback Level**: [L1|L2|L3|L4]

---

## ✅ 用戶確認

> 🛑 **必要停頓點**：Planner 產出 Spec 後，必須等待用戶確認才能進入 Step 2。

- [ ] Spec 已確認，可進入 Step 2 (Meta Expert)
- [ ] 執行工具已選擇：`[copilot|codex-cli]`
- [ ] Terminal 管理策略已確認

---

**Template Version**: 2.1.0
**Last Updated**: 2026-01-13
