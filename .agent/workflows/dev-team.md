---
description: 艾薇虛擬開發團隊工作流程 - 自動化 Plan → Consult → Implement → Review
---
# 🤖 艾薇虛擬開發團隊工作流程

當使用者輸入 `/dev-team` 或請求「啟動開發團隊」時，請依照以下步驟執行。

---

## 📋 前置準備

1. **確認需求**：先請使用者說明他們的開發需求是什麼。
2. **閱讀規則**：在開始任何工作前，先閱讀 `ivy_house_rules.md` 確認核心規範。

---

## 🔄 工作流程（依序執行）

### Step 1️⃣ 艾薇規劃師 (Planner)
**角色定義**：參考 `.agent/roles/planner.md`

**任務**：
1. 掃描專案目錄結構，理解現有檔案。
2. 閱讀相關程式碼（如 `app.py`, `scripts/`）。
3. 產出一份 Markdown 格式的 **開發規格書 (Spec)**，包含：
   - 目標描述
   - 需要修改/新增的檔案清單
   - 每個檔案的邏輯細節
   - 注意事項與風險提示
4. **保存 Spec 為獨立文件**：`doc/plans/Idx-NNN_plan.md`

**產出格式**：參考模板 `doc/plans/Idx-000_plan.template.md`

```markdown
## 📄 開發規格書

### 目標
[描述]

### 檔案變更
| 檔案 | 動作 | 說明 |
|------|------|------|
| xxx.py | 修改 | ... |

### 邏輯細節
...

### 注意事項
...
```

> 🛑 **必要停頓點**：Spec 產出後，必須等待用戶確認才能進入 Step 2。

---

### Step 2️⃣ Meta廣告數據專家 (Meta Expert)
**角色定義**：參考 `.agent/roles/meta_expert.md`

**任務**：
1. 檢視 Planner 的 Spec。
2. 如果涉及 **數據計算** (如 ROAS, CPC, CTR) 或 **Meta API 串接**，提供專業建議。
3. 確認計算邏輯是否正確（例如：ROAS = Revenue / Spend）。
4. 如果這次任務與數據無關，可以簡短回覆「此任務不涉及數據分析，跳過專家審核」。

**產出格式**：
```markdown
## 📊 數據專家審核

### 涉及的計算邏輯
- [列出相關公式]

### 建議
- [任何改進或注意事項]

### 結論
✅ 通過 / ⚠️ 需要修正
```

---

### Step 2.5️⃣ 執行工具選擇 (Role Selection Gate) 🚦

**執行者**: Planner（暫時）或 Workflow Coordinator（未來）

**觸發條件**: Plan 通過 User Approval Gate 且 Meta Expert Review 完成

**任務**: 選擇適當的執行工具並更新 Plan

**選項**:
1. **GitHub Copilot**: 互動式開發，需要即時反饋，小規模修改
2. **Codex CLI**: 批次執行，明確的檔案操作，大規模變更

**決策因素**:
- **任務複雜度**: 簡單修改 → Copilot；複雜多檔案 → Codex CLI
- **即時反饋需求**: 需要互動 → Copilot；可批次處理 → Codex CLI
- **檔案數量**: 1-3 個檔案 → Copilot；4+ 個檔案 → Codex CLI
- **操作類型**: 邏輯重構 → Copilot；模板化新增 → Codex CLI

**輸出**: 在 `plan.md` 中填入以下欄位

```markdown
## 🔧 執行資訊

**execution**: [copilot|codex-cli]
**terminal**: [使用現有 Terminal | 需要新 Terminal（請說明原因）]
```

**Terminal 規則**:
- ✅ Codex CLI 執行時，所有命令必須發送到同一個 Terminal（由 Terminal Manager 自動管理）
- ✅ 除非 Plan 明確要求（例如：同時運行 server 和 client），否則不得創建新 Terminal
- ✅ 使用 `.agent/scripts/terminal_manager.py` 管理 Terminal 會話
- ❌ 禁止為每個 Plan 創建新 Terminal
- ❌ 禁止手動指定 Terminal ID（應使用 Terminal Manager）

**參考文檔**: `.agent/TERMINAL_MANAGEMENT.md`

---

### Step 3️⃣ 全端工程師 (Engineer)
**角色定義**：參考 `.agent/roles/engineer.md`

**任務**：根據 Planner 的 Spec、Meta Expert 的建議與 Plan 中的 `execution` 欄位，落實程式碼。

**執行模式**（由 Step 2.5 決定）：

#### 模式 A: GitHub Copilot 執行
- **適用於**: 小規模修改（1-3 個檔案）、關鍵邏輯重構、需要即時反饋
- **執行方式**: 由 GitHub Copilot 直接在 IDE 中實作
- **產出格式**:
  ```markdown
  ## 🔧 實作報告 (GitHub Copilot)

  ### 已修改/新增的檔案
  - `path/to/file.py`: [變更說明]

  ### 主要變更
  [列出關鍵修改]
  ```

#### 模式 B: Codex CLI 執行
- **適用於**: 大規模檔案新增（4+ 個檔案）、模板化重複性工作、批次處理
- **執行方式**: 使用 `.agent/scripts/run_codex_template.sh` 包裝腳本
- **執行命令**:
  ```bash
  .agent/scripts/run_codex_template.sh doc/plans/Idx-XXX_plan.md
  ```
- **Terminal 管理**:
  - ✅ 腳本會自動調用 Terminal Manager
  - ✅ 所有命令發送到同一個 Terminal
  - ✅ 執行失敗時自動觸發 L2 Rollback
- **產出格式**:
  ```markdown
  ## 🔧 實作報告 (Codex CLI)

  ### Terminal 資訊
  - Terminal ID: codex-session
  - Execution Start: YYYY-MM-DD HH:MM
  - Execution End: YYYY-MM-DD HH:MM

  ### 已修改/新增的檔案
  [由 Codex 輸出]
  ```

**通用規範**（兩種模式都必須遵守）：
- 每個檔案開頭有中文用途註釋
- 單檔不超過 500 行
- 無 Hard-code API Key
- 遵循 `ivy_house_rules.md` 核心守則

**產出格式** (若為模式 A)：
```markdown
## 🔧 實作報告 (Antigravity Direct)

### 已修改/新增的檔案
...完整程式碼...
```

---

### Step 4️⃣ 艾薇品管員 (QA)
**角色定義**：參考 `.agent/roles/qa.md`

**任務**：
1. 審查工程師的程式碼。
2. **確認 Cross-QA 規則**：QA 工具必須與 Executor 不同
   - Executor: Copilot → QA: Codex CLI
   - Executor: Codex CLI → QA: Copilot
3. 執行 Checklist：
   - [ ] 無 Hard-code API Key？
   - [ ] 有中文檔案註釋？
   - [ ] 符合 `ivy_house_rules.md`？
   - [ ] 邏輯正確？
   - [ ] **Cross-QA 規則已遵守？**
   - [ ] **若使用新的 CLI 工具，是否已遵循探索流程？**
4. 產出審查報告。

> 💡 **工具探索流程**：首次使用新工具時，必須執行 `<tool> --help` 確認參數，禁止憑經驗臆測。詳見 [`.agent/skills/explore_cli_tool.md`](file:///.agent/skills/explore_cli_tool.md)

> ⚠️ **Cross-QA 違規處理**：如果 Executor 與 QA Tool 相同，必須在 Log 中標記 `QA Compliance: ⚠️ 違規` 並說明原因。

**產出格式**：
```markdown
## ✅ 品管審查報告

### Cross-QA 檢核
- Executor: [GitHub Copilot | Codex CLI]
- QA Tool: [Codex CLI | GitHub Copilot]
- Compliance: [✅ 符合 | ⚠️ 違規：原因]

### Checklist
- [x] 無 Hard-code API Key
- [x] 有中文檔案註釋
- [x] Cross-QA 規則已遵守
- [ ] 符合 ivy_house_rules.md（問題：...）

### 發現的問題
| 檔案 | 行號 | 問題描述 | 建議修正 |
|------|------|----------|----------|
| ... | ... | ... | ... |

### 結論
🟢 通過 / 🟡 通過但有風險 / 🔴 需要修正
```

---

## 🏁 完成

當 QA 審查通過後，整個流程結束。
如果 QA 發現問題，請回到 **Step 3 (Engineer)** 修正後再次審查。

---

## ⚠️ 必須遵守的規則
在整個流程中，所有角色都必須嚴格遵守：
- 📜 `ivy_house_rules.md` - 艾薇手工坊系統開發核心守則
