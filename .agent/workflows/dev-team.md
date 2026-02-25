---
description: 艾薇虛擬開發團隊工作流程 - 自動化 Plan → Consult → Implement → Review
---
# 🤖 艾薇虛擬開發團隊工作流程

當使用者輸入 `/dev`（或相容別名 `/dev-team`）或請求「啟動開發團隊」時，請依照以下步驟執行。

> 📌 **Slash 指令說明**：
> - `/dev` 或 `/dev-team`：啟動本 repo 的 dev-team workflow（Ivy Coordinator 流程）
> - 如果你有個人的 Copilot prompt file 使用 `/dev`，建議改用其他名稱（如 `/devchat`）以避免衝突

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
4. **保存 Spec 為獨立文件**：
   - **Workflow/治理改善任務** → `.agent/plans/Idx-NNN_plan.md`
   - **專案功能開發任務** → `doc/plans/Idx-NNN_plan.md`
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

**執行後端策略（必填）**：
- `extension-sendtext-required`（固定）：命令注入一律使用 IvyHouse Terminal Injector extension 的 sendText 指令（`IvyHouse Injector: Send Text to Codex Terminal` / `IvyHouse Injector: Send Text to OpenCode Terminal`）
- `proposed-primary-with-extension-fallback`（預設）：監測優先 Proposed API；不可用時切換 extension 監測模式（capture/polling，預設不使用 HTTP bridge）

**命令名稱（現行）**：
- Injector：`IvyHouse Injector: Send Text to Codex Terminal` / `IvyHouse Injector: Send Text to OpenCode Terminal`
- Monitor：`IvyHouse Monitor: Capture Codex Output` / `IvyHouse Monitor: Auto-Capture Codex /status` / `IvyHouse Monitor: Verify Codex /status Injection`

**Command IDs（固定引用；新流程只認 Injector + Monitor）**：
- Injector（注入/啟動）：`ivyhouseTerminalInjector.startAll`、`ivyhouseTerminalInjector.sendLiteralToCodex`、`ivyhouseTerminalInjector.sendLiteralToOpenCode`、`ivyhouseTerminalInjector.resetSessionState`
- Monitor（監測/擷取/自檢）：`ivyhouseTerminalMonitor.ping`、`ivyhouseTerminalMonitor.verifyCodexStatusInjection`、`ivyhouseTerminalMonitor.autoCaptureCodexStatus`、`ivyhouseTerminalMonitor.openLastCodexCapture`

**Deprecated（新流程禁止依賴）**：
- Orchestrator（`ivyhouseTerminalOrchestrator.*`）為 legacy 相容套件；不得作為新流程的預設注入/監測路徑。

**Research Gate（條件式，必先完成）**：
- 若 Plan 的 `research_required: true` 或依賴檔案變更（`requirements.txt`、`pyproject.toml`、`*requirements*.txt`）
  - 必須先補齊 Plan 的 `RESEARCH & ASSUMPTIONS`（Link-required；無來源則標 `RISK: unverified`）
  - 未完成不得進入 Engineer 執行

**Plan Validator Gate（必先完成）**：
- 在進入 Engineer 執行前，必須先用 `plan_validator` 驗證 Plan（由 Project terminal 執行）：
  ```bash
  python .agent/skills/plan_validator.py <plan_file_path>
  ```
- 若回傳 `status: fail|error` → 退回 Planner 修正 Plan，未通過不得進入 Engineer

**Preflight Gate（Engineer 注入前必先完成）**：
- 由 Coordinator 在 Project terminal 執行一鍵 preflight：
  ```bash
  python scripts/vscode/workflow_preflight_check.py --json
  ```
- 若本輪啟用 HTTP SendText Bridge（例如採 bridge 送 `/send`），改執行：
  ```bash
  python scripts/vscode/workflow_preflight_check.py --require-bridge --json
  ```
- 進入 Engineer 注入前，至少必須滿足：
  - `checks.proposed_api_true.ok == true`
  - （bridge 模式）`checks.sendtext_bridge_healthz.ok == true` 且 `checks.sendtext_bridge_token.ok == true`
- 任一條件不符：禁止注入 Engineer，先做修復（重啟 VS Code / extension、修正 argv.json、恢復 bridge）

**歷史檔保留 Checkpoint（必檢）**：
- 檢核：`git status --porcelain | awk '{print $2}' | grep -E '^\.agent/(plans|logs)/' || true`
- 規則：若僅為命名一致性調整，禁止改寫 `/.agent/plans/**`、`/.agent/logs/**`；若因法遵/稽核需求必須修改，需先取得 user 明確同意，並在變更說明記錄理由。

**決策選項**:
1. **Codex CLI（VS Code Terminal）**: 執行 / QA
2. **OpenCode CLI（VS Code Terminal）**: 執行 / QA
3. **Copilot Chat（小修正模式）**: 僅限明確滿足小修正條件時才可選擇

**決策因素**:
- 工具可用性（目前哪個 terminal 可用、是否已啟動）
- 任務型態（批次修改 / 需要實際跑指令 / 需要互動式調整）
- Cross-QA（QA 工具必須 ≠ 最後修改程式碼的工具）

**Copilot Chat 小修正條件（全部滿足才可選擇選項 3）**：
1. `copilot_chat_small_fix_allowed: true` 須明確填入 Plan 的 `EXECUTION_BLOCK`
2. staged 變更檔案必須全部符合 `copilot_chat_allowed_path_globs`（例如 `["doc/**", "README.md", "*.md"]`）
3. staged 變更總行數（add+del）≤ `copilot_chat_max_changed_lines`（預設 20）
4. `qa_result` 仍需 `PASS` 或 `PASS_WITH_RISK`

> ⚠️ **注意**：選擇 Copilot Chat 作為 executor_tool 時，`last_change_tool` 欄位應填 `copilot-chat`。
> State Gate 會對此模式執行路徑/行數機械化驗證；不滿足條件時 commit 將被阻擋。

**輸出格式**（寫入 Plan 檔；新 Plan 一律使用 `EXECUTION_BLOCK`）：

```markdown
<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: [YYYY-MM-DD HH:mm:ss]
plan_approved: [YYYY-MM-DD HH:mm:ss]
scope_policy: [strict|flexible]
expert_required: [true|false]
expert_conclusion: [N/A|結論摘要]
execution_backend_policy: [extension-sendtext-required]
scope_exceptions: []

# Engineer 執行
executor_tool: [codex-cli|opencode|copilot-chat]
executor_backend: [ivyhouse_sendtext_extension]
monitor_backend: [proposed_api_monitor|ivyhouse_monitor_extension_fallback|manual_confirmation]
executor_tool_version: [version]
executor_user: [github-account or email]
executor_start: [YYYY-MM-DD HH:mm:ss]
executor_end: [YYYY-MM-DD HH:mm:ss]
session_id: [terminal session ID if available]
last_change_tool: [codex-cli|opencode|copilot-chat]

# Copilot Chat 小修正政策（僅當 executor_tool=copilot-chat 才允許填；其餘 executor 必須保持預設 placeholder）
copilot_chat_small_fix_allowed: [true|false]
copilot_chat_small_fix_reason: [說明小修正理由]
copilot_chat_max_changed_lines: 20
copilot_chat_allowed_path_globs: ["doc/**", "README.md", "CHANGELOG.md", "CHECKLIST.md", "*.md"]

# QA 執行
qa_tool: [codex-cli|opencode]
qa_tool_version: [version]
qa_user: [github-account or email]
qa_start: [YYYY-MM-DD HH:mm:ss]
qa_end: [YYYY-MM-DD HH:mm:ss]
qa_result: [PASS|PASS_WITH_RISK|FAIL]
qa_compliance: [✅ 符合|⚠️ 例外：原因]

# 收尾
log_file_path: [.agent/logs/Idx-XXX_log.md（workflow任務）或 doc/logs/Idx-XXX_log.md（專案任務）]
commit_hash: [pending|hash]
rollback_at: [N/A|YYYY-MM-DD HH:mm:ss]
rollback_reason: [N/A|原因]
rollback_files: [N/A|檔案清單]
<!-- EXECUTION_BLOCK_END -->
```

> ⚠️ **注意**：`executor_tool=opencode|codex-cli` 時，`last_change_tool` 必須等於 executor_tool，不可填 `copilot-chat`。
> `executor_tool=copilot-chat` 時，必須明確填寫 `copilot_chat_small_fix_allowed: true` 及相關欄位，且 State Gate 會自動驗證路徑與行數。

**指令注入策略（固定）**:
- Codex/OpenCode 一律在 VS Code 原生終端中執行（會話自然延續）
- **指令注入**：由 Coordinator 使用 IvyHouse Terminal Injector extension 的 sendText 指令對指定終端送出指令/文字
- **禁止**：用 bash 腳本、TTY 寫入或其他代送機制（可能導致 overlay / TUI 狀態異常）

**監測策略（主從）**:
- **主路徑**：使用 VS Code Proposed API 監測終端輸出（例如 `terminalDataWriteEvent`）
- **Fallback**：僅在 Proposed API 不可用時，切換 extension 監測模式（capture/polling）
- 預設不使用 HTTP SendText Bridge；若要使用，必須有 user 明確同意並記錄於 Plan/Log

---

### Step 3️⃣ 全端工程師 (Engineer)
**角色定義**：參考 `.agent/roles/engineer.md`

**任務**：根據 Planner 的 Spec、Meta Expert 的建議與 Plan 的 `EXECUTION_BLOCK.executor_tool`，由選定的終端工具完成實作。

**執行方式**（由 Step 2.5 決定）：

#### 共同規則（Coordinator 必須落地）
- **Plan 注入方式**：僅使用 extension sendText 對「已啟動的 Codex/OpenCode 終端」送出指令/Plan 文字
- **完成條件（Idx-030 格式）**：Engineer/QA/Fix 結束時在終端輸出 5 行 completion marker：
  ```
  [ENGINEER_DONE] 或 [QA_DONE] 或 [FIX_DONE]
  TIMESTAMP=YYYY-MM-DDTHH:mm:ssZ
  NONCE=<從環境變數 WORKFLOW_SESSION_NONCE 讀取>
  TASK_ID=Idx-XXX
  <角色特定結果行>
  ```
  - Engineer: `ENGINEER_RESULT=COMPLETE`
  - QA: `QA_RESULT=PASS` 或 `QA_RESULT=FAIL`
  - Fix: `FIX_ROUND=N`
  - **⚠️ 硬性規則**：這 5 行必須是輸出的**最後 5 個非空白行**。完成標記後不可再輸出任何文字（包括確認訊息、說明等）。
- **即時監控**：Coordinator 以 Proposed API 監測終端輸出，直到偵測 completion marker 或 timeout
- **監控備援**：若 Proposed API 不可用，先嘗試 `ivyhouse_monitor_extension_fallback`；若仍不可用才改人工回報
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

**Skill Execution Gate（每次變更必執行，且需留證據）**：
- 對每個新建/修改的 `.py` 檔案執行：
  ```bash
  python .agent/skills/code_reviewer.py <file_path>
  ```
- 若專案有測試，執行：
  ```bash
  python .agent/skills/test_runner.py [test_path]
  ```
- **Coordinator 收集流程（Extension 注入 + Proposed API 監測）**：
  - Copilot Chat 透過 extension sendText 對已啟動的 Codex/OpenCode 終端注入指令
  - 使用 VS Code Proposed API 監測終端輸出
  - 若 Proposed API 不可用：先改走 `ivyhouse_monitor_extension_fallback`（extension 監測模式）
  - 從 stdout 擷取 JSON 結果
  - 將結果寫入 Log 的 `## 🛠️ SKILLS_EXECUTION_REPORT` 段落
- **Skills Evaluation（建議每回合一次，產生可追溯統計）**：
  - 若 Log 已包含 `SKILLS_EXECUTION_REPORT`，執行：
    ```bash
    python .agent/skills/skills_evaluator.py <log_file_path>
    ```
  - 將輸出摘要/統計寫入 Log 的 `## 📈 SKILLS_EVALUATION` 段落
- 若 `code_reviewer.py` 回傳 `status: fail`（例如 API key 洩漏）→ 立即停止並回報 user

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
1. **建立執行記錄**: 由 Coordinator 產生執行記錄：
   - **Workflow/治理改善任務** → `.agent/logs/Idx-XXX_log.md`（引用 `.agent/plans/Idx-XXX_plan.md`）
   - **專案功能開發任務** → `doc/logs/Idx-XXX_log.md`（引用 `doc/plans/Idx-XXX_plan.md`）
2. **保留 Plan 檔案**: Plan 檔案不刪除（作為規格與決策留存）
3. **提交變更（選用）**: 是否 `git commit` 由用戶決策

如果 QA 發現問題，請回到 **Step 3 (Engineer)** 修正後再次審查。

> 💡 Log 段落結構示例：`.agent/logs/Idx-010_log_template_example.md`（workflow/治理任務）

---

## 📊 執行模式比較

| 模式 | 適用情境 | 啟動方式 | 監測 | QA 觸發 |
|------|---------|---------|------|---------|
| Codex CLI（VS Code Terminal） | 批次處理、檔案操作、快速執行 | Coordinator 以 extension sendText 注入 | Proposed API（主）→ extension 監測 fallback | marker 偵測後 |
| OpenCode CLI（VS Code Terminal） | 需要互動式終端操作/實跑指令 | Coordinator 以 extension sendText 注入 | Proposed API（主）→ extension 監測 fallback | marker 偵測後 |
| Copilot Chat（小修正模式） | 點單小修正（僅文件/設定，≤20 行，符合路徑 glob） | Copilot Chat 直接在 workspace 修改檔案 | manual_confirmation（人工確認） | 仍需 QA PASS/PASS_WITH_RISK |

> ⚠️ **Copilot Chat 小修正模式** 須滿足 Role Selection Gate 的全部小修正條件，且 State Gate 在 commit 時會機械化驗證（路徑/行數/qa_result）；不符合條件的 commit 將被阻擋。

### 後端策略（主從）

| 後端策略 | 說明 | 何時使用 |
|---------|------|---------|
| `extension-sendtext-required` | 命令注入固定走 IvyHouse Terminal Injector extension sendText | 預設且固定 |
| `proposed_api_monitor` | 監測主路徑使用 VS Code Proposed API | 預設主路徑 |
| `ivyhouse_monitor_extension_fallback` | Proposed API 不可用時，啟用 extension 監測模式 | 條件式啟用 |

**Extension 拆分模型（允許）**：
- `Injector Extension`：只負責 sendText 注入（固定）
- `Monitor Extension`：只負責監測 fallback（僅在 Proposed API 不可用時）

---

## ⚠️ 必須遵守的規則
在整個流程中，所有角色都必須嚴格遵守：
- 📜 `ivy_house_rules.md` - 艾薇手工坊系統開發核心守則
