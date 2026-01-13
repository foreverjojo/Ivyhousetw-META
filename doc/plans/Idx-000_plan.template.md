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
execution: [copilot|codex-cli]
<!-- EXECUTION_BLOCK_END -->

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
