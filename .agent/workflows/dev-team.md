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
5. **Plan 固定段落（必須存在）**：
   - `## 📋 SPEC`
   - `## 🔍 RESEARCH & ASSUMPTIONS`（至少包含 `research_required: true/false`）
   - `## 🔒 SCOPE & CONSTRAINTS`（含 File whitelist / Done 定義 / Rollback / Max rounds）

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

**執行者**: GitHub Copilot Chat（固定作為 Coordinator）

**觸發條件**: Plan 通過 User Approval Gate 且 Meta Expert Review 完成

**任務**: 由用戶選擇 Engineer/QA 要使用的終端工具，Coordinator 更新 Plan 的 `EXECUTION_BLOCK`

**Research Gate（條件式，必先完成）**：
- 若 Plan 的 `research_required: true` 或依賴檔案變更（`requirements.txt`、`pyproject.toml`、`*requirements*.txt`）
  - 必須先補齊 Plan 的 `RESEARCH & ASSUMPTIONS`（Link-required；無來源則標 `RISK: unverified`）
  - 未完成不得進入 Engineer 執行

**決策選項**:
1. **Codex CLI（VS Code Terminal）**: 執行 / QA
2. **OpenCode CLI（VS Code Terminal）**: 執行 / QA

**決策因素**:
- 工具可用性（目前哪個 terminal 可用、是否已啟動）
- 任務型態（批次修改 / 需要實際跑指令 / 需要互動式調整）
- Cross-QA（QA 工具必須 ≠ 最後修改程式碼的工具）

**輸出格式**（寫入 Plan 檔；新 Plan 一律使用 `EXECUTION_BLOCK`）：

```markdown
<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: [YYYY-MM-DD HH:mm:ss]
plan_approved: [YYYY-MM-DD HH:mm:ss]
scope_policy: [strict|flexible]
expert_required: [true|false]
expert_conclusion: [N/A|結論摘要]
scope_exceptions: []

# Engineer 執行
executor_tool: [codex-cli|opencode]
executor_tool_version: [version]
executor_user: [github-account or email]
executor_start: [YYYY-MM-DD HH:mm:ss]
executor_end: [YYYY-MM-DD HH:mm:ss]
session_id: [terminal session ID if available]
last_change_tool: [codex-cli|opencode]

# QA 執行
qa_tool: [codex-cli|opencode]
qa_tool_version: [version]
qa_user: [github-account or email]
qa_start: [YYYY-MM-DD HH:mm:ss]
qa_end: [YYYY-MM-DD HH:mm:ss]
qa_result: [PASS|PASS_WITH_RISK|FAIL]
qa_compliance: [✅ 符合|⚠️ 例外：原因]

# 收尾
log_file_path: [doc/logs/Idx-XXX_log.md]
commit_hash: [pending|hash]
rollback_at: [N/A|YYYY-MM-DD HH:mm:ss]
rollback_reason: [N/A|原因]
rollback_files: [N/A|檔案清單]
<!-- EXECUTION_BLOCK_END -->
```

> ⚠️ **注意**：`last_change_tool` 只允許 `codex-cli` 或 `opencode`，不含 `copilot`（Copilot 固定為 Coordinator，不做實作）。

**VS Code 原生模式**:
- Codex/OpenCode 一律在 VS Code 原生終端中執行（會話自然延續）
- **指令注入**：由 Coordinator 使用 VS Code 內建 `terminal.sendText` 對指定終端送出指令/文字
- **禁止**：用 bash 腳本「代送」指令到 Codex/OpenCode（可能導致程序/TUI 退出或狀態被重置）
- **即時監控**：由 Coordinator 使用 VS Code Proposed API 監測終端輸出（例如 `terminalDataWriteEvent`）

---

### Step 3️⃣ 全端工程師 (Engineer)
**角色定義**：參考 `.agent/roles/engineer.md`

**任務**：根據 Planner 的 Spec、Meta Expert 的建議與 Plan 的 `EXECUTION_BLOCK.executor_tool`，由選定的終端工具完成實作。

**執行方式**（由 Step 2.5 決定）：

#### 共同規則（Coordinator 必須落地）
- **Plan 注入方式**：僅使用 VS Code 內建 `terminal.sendText` 對「已啟動的 Codex/OpenCode 終端」送出指令/Plan 文字
- **完成條件**：Engineer 結束時在終端輸出 completion marker（例如：`[ENGINEER_DONE]`）
- **即時監控**：Coordinator 以 Proposed API 監測終端輸出，直到偵測 completion marker 或 timeout
- **Scope Gate**：偵測到變更後，Coordinator 必須先確認變更檔案未超出 Plan 的檔案清單（超出則停下來請用戶決策）

- **執行記錄**:
  - ✅ 每次執行追加到 `.agent/execution_log.jsonl`
  - ✅ 失敗/超範圍時，先由 Coordinator 詢問用戶是否回滾/拆分（禁止自動執行破壞性操作）
- **產出格式**:
  ```markdown
  ## 🔧 實作報告 (Executor Tool)

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
- Engineer completion marker 被偵測後立即執行

**Cross-QA 工具檢測（在審查前執行）**：
1. 讀取 Plan 的 `EXECUTION_BLOCK.last_change_tool`
2. 用戶選擇 `qa_tool`（`codex-cli|opencode`）
3. 若 `qa_tool == last_change_tool` → **拒絕執行 QA**，要求改選另一個工具（除非符合例外並記錄）

**記錄格式**:
- 違規: `qa_compliance: ⚠️ 違規（同工具）- 理由：[用戶說明]`
- 例外: `qa_compliance: ⚠️ 例外（小修正）- 變更：[X 行]`
- 豁免: `qa_compliance: ✅ 豁免（文件修正）- 檔案：[列表]`
**任務**：
1. 審查工程師的程式碼。
2. **確認 Cross-QA 規則**：QA 工具必須與 `last_change_tool` 不同
   - last_change_tool: codex-cli → QA: opencode
   - last_change_tool: opencode → QA: codex-cli
3. **條件式 Gate（輸出到 Log）**：
   - **UI/UX Gate**：若 Scope Gate 判定 `UI/UX triggered: YES`（基於變更檔案清單）
     - QA 報告後必須補 `## UI/UX CHECK`（code review 為主；不跑獨立工具）
   - **Maintainability Gate**：若存在程式碼變更（例如 `.py`）且（變更行數 > 50 或命中核心路徑 `core/**`/`utils/**`/`config.py`）
     - QA 報告後必須補 `## MAINTAINABILITY REVIEW`（Must/Should/Nice；Reviewer 永不改 code）
3. 執行 Checklist：
   - [ ] 無 Hard-code API Key？
   - [ ] 有中文檔案註釋？
   - [ ] 符合 `ivy_house_rules.md`？
   - [ ] 邏輯正確？
   - [ ] **Cross-QA 規則已遵守？**
   - [ ] **若使用新的 CLI 工具，是否已遵循探索流程？**
4. 產出審查報告。

> 💡 **工具探索流程**：首次使用新工具時，必須執行 `<tool> --help` 確認參數，禁止憑經驗臆測。詳見 [`.agent/skills/explore_cli_tool.md`](.agent/skills/explore_cli_tool.md)

> ⚠️ **Cross-QA 違規處理**：如果 `last_change_tool == qa_tool`，必須在 Log 中標記 `qa_compliance: ⚠️ 違規` 並說明原因。

**產出格式**：
```markdown
## ✅ 品管審查報告

### Cross-QA 檢核
- Last Change Tool: [codex-cli | opencode]
- QA Tool: [codex-cli | opencode]
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
1. **建立執行記錄**: 由 Coordinator 產生 `doc/logs/Idx-XXX_log.md`（引用 `doc/plans/Idx-XXX_plan.md`）
2. **保留 Plan 檔案**: `doc/plans/Idx-XXX_plan.md` 不刪除（作為規格與決策留存）
3. **提交變更（選用）**: 是否 `git commit` 由用戶決策

如果 QA 發現問題，請回到 **Step 3 (Engineer)** 修正後再次審查。

> 💡 Log 段落結構示例：`doc/logs/Idx-010_log_template_example.md`

---

## 📊 執行模式比較

| 模式 | 適用情境 | 啟動方式 | 監測 | QA 觸發 |
|------|---------|---------|------|---------|
| Codex CLI（VS Code Terminal） | 批次處理、檔案操作、快速執行 | Coordinator 以 `terminal.sendText` 注入 | Proposed API（終端輸出 + marker） | marker 偵測後 |
| OpenCode CLI（VS Code Terminal） | 需要互動式終端操作/實跑指令 | Coordinator 以 `terminal.sendText` 注入 | Proposed API（終端輸出 + marker） | marker 偵測後 |

---

## ⚠️ 必須遵守的規則
在整個流程中，所有角色都必須嚴格遵守：
- 📜 `ivy_house_rules.md` - 艾薇手工坊系統開發核心守則
