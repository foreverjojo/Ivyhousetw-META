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

### Step 3️⃣ 全端工程師 (Engineer)
**角色定義**：參考 `.agent/roles/engineer.md`

**任務**：根據 Planner 的 Spec 與 Meta Expert 的建議，落實程式碼。

**總司令指令 (Commander Options)**：
> 此步驟需請詢問使用者選擇執行模式：

- **模式 A (直接實作)**：由 Antigravity (IDE Agent) 直接改寫檔案。
  - 適用於：小規模修改、關鍵邏輯重構。
- **模式 B (Codex 代理)**：由 Antigravity 產出 `codex edit` 指令。
  - 適用於：大規模檔案新增、模板化重複性工作。
  - **關鍵規範**：總司令生成的指令**必須**明確指出 Codex 此刻扮演的角色 (參考 `.agent/roles/`)，並指示其呼叫相關技能腳本 (參考 `.agent/skills/`)。
  - **產出格式**：可在對話框點擊運行的終端機複合指令。

**通用規範**：
- 每個檔案開頭有中文用途註釋
- 單檔不超過 500 行
- 無 Hard-code API Key

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
2. 執行 Checklist：
   - [ ] 無 Hard-code API Key？
   - [ ] 有中文檔案註釋？
   - [ ] 符合 `ivy_house_rules.md`？
   - [ ] 邏輯正確？
   - [ ] **若使用新的 CLI 工具，是否已遵循探索流程？**
3. 產出審查報告。

> 💡 **工具探索流程**：首次使用新工具時，必須執行 `<tool> --help` 確認參數，禁止憑經驗臆測。詳見 [`.agent/skills/explore_cli_tool.md`](file:///.agent/skills/explore_cli_tool.md)


**產出格式**：
```markdown
## ✅ 品管審查報告

### Checklist
- [x] 無 Hard-code API Key
- [x] 有中文檔案註釋
- [ ] 符合 ivy_house_rules.md（問題：...）

### 發現的問題
| 檔案 | 行號 | 問題描述 | 建議修正 |
|------|------|----------|----------|
| ... | ... | ... | ... |

### 結論
🟢 通過 / 🔴 需要修正
```

---

## 🏁 完成

當 QA 審查通過後，整個流程結束。
如果 QA 發現問題，請回到 **Step 3 (Engineer)** 修正後再次審查。

---

## ⚠️ 必須遵守的規則
在整個流程中，所有角色都必須嚴格遵守：
- 📜 `ivy_house_rules.md` - 艾薇手工坊系統開發核心守則
