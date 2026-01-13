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

**決策選項**:
1. **GitHub Copilot**: 互動式開發，需要即時反饋
2. **Codex CLI**: 批次執行，明確的檔案操作

**決策因素**:
- 任務複雜度
- 是否需要即時反饋
- 檔案數量與操作類型

**輸出格式**（寫入 Plan 檔）：

```markdown
<!-- EXECUTION_BLOCK_START -->
execution: [copilot|codex-cli]
<!-- EXECUTION_BLOCK_END -->
```

**VS Code 原生模式**:
- Codex CLI 執行時，使用 VS Code 原生終端（會話自然延續，無需 tmux）
- 若需要「對話框 → 終端」注入互動指令（例如 `/status`、分段 Enter），使用 SendText Bridge 透過 `terminal.sendText` 注入到固定 terminal（`Codex CLI`）
- 建議用腳本：`.agent/scripts/sendtext.sh`（`text` / `enter`）
- 失敗時自動觸發 L2 Rollback（乾淨 worktree 前提；審計檔保留於 `.agent/`）

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
- **執行方式**:
  - **批次模式**: 使用 `.agent/scripts/run_codex_template.sh`（`codex exec` + exit code + JSONL 審計）
  - **自動化模式**: 使用 `.agent/scripts/auto_execute_plan.sh`（發送 Plan → 自動監測完成 → 提示執行 QA）

**執行命令**:

  ```bash
  # 方式 1: 批次執行（同步，立即回傳結果）
  .agent/scripts/run_codex_template.sh doc/plans/Idx-XXX_plan.md

  # 方式 2: 自動化執行（發送 → 監測 → QA 提示）
  .agent/scripts/auto_execute_plan.sh doc/plans/Idx-XXX_plan.md
  ```

**自動化模式工作流程**:
  1. 📤 **發送 Plan** 到 Codex CLI terminal
  2. ⏳ **自動監測** Codex CLI 執行狀態（透過 `/wait` 端點輪詢 `git status`）
  3. ✅ **偵測完成** 後自動提示執行 QA（Cross-QA: Copilot）

**技術實作**:
  - 使用 SendText Bridge 的 `/wait` 端點
  - 每 2 秒檢查一次 `git status --porcelain`
  - 最多等待 5 分鐘（可調整）
  - 有變更即表示 Codex CLI 完成

- **執行記錄**:
  - ✅ 每次執行追加到 `.agent/execution_log.jsonl`
  - ✅ 失敗時自動觸發 L2 Rollback（僅限乾淨 worktree）
- **產出格式**:
  ```markdown
  ## 🔧 實作報告 (Codex CLI)

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

**觸發時機**:
- **模式 A (Copilot)**: 實作完成後立即執行
- **模式 B (Codex CLI 自動化)**: 由 `auto_execute_plan.sh` 偵測完成後自動提示
- **模式 B (Codex CLI 批次)**: 手動確認完成後執行

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

當 QA 審查通過後：
1. **建立執行記錄**: 將 `doc/plans/Idx-XXX_plan.md` 轉為 `doc/logs/Idx-XXX_log.md`
2. **刪除 Plan 檔案**: 刪除 `doc/plans/Idx-XXX_plan.md`
3. **提交變更**: `git commit` 所有變更

如果 QA 發現問題，請回到 **Step 3 (Engineer)** 修正後再次審查。

---

## 📊 執行模式比較

| 模式 | 適用情境 | 啟動方式 | 監測 | QA 觸發 |
|------|---------|---------|------|---------|
| Copilot 直接執行 | 小規模修改（1-3 檔） | IDE 內實作 | 手動 | 立即 |
| Codex CLI 批次 | 大規模批次處理 | `run_codex_template.sh` | 手動 | 手動確認後 |
| Codex CLI 自動化 | 大規模 + 需自動監測 | `auto_execute_plan.sh` | **自動** | **自動提示** |

---

## ⚠️ 必須遵守的規則
在整個流程中，所有角色都必須嚴格遵守：
- 📜 `ivy_house_rules.md` - 艾薇手工坊系統開發核心守則
