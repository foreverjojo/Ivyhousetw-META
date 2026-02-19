# AGENT_ENTRY.md（VS Code 多代理 Workflow 唯一入口）

> 本檔案是此 repo 的「唯一入口文件」。
> 任何工作在開始 **產出 Plan** 前，必須先完成「必讀檔案逐檔閱讀」並回報「已讀驗收回報」。
> 未完成者：不得出 Plan、不得執行、不得 QA。

---

## 0) 一條不可妥協的鐵律
**在你完成「1) 必讀檔案」並輸出「2) 已讀驗收回報」之前，禁止產出任何 Plan。**

若任一必讀檔找不到：必須立刻停下並詢問使用者確認檔名/路徑（不得自行猜測或跳過）。

---

## 1) 必讀檔案（必須逐檔「開啟並閱讀」，不可只提到檔名）
請依序「開啟並閱讀」以下檔案：

1. `./.agent/workflows/dev-team.md`
2. `./ivy_house_rules.md`
3. **Index 檔案（根據任務類型選擇）**：
   - 若任務是 **workflow/治理改善**（涉及 `.agent/**` 檔案、dev-team 流程、CI/CD、工具鏈等）→ 必讀 **`./.agent/Workflow_Plan_index.md`**
   - 若任務是 **專案功能開發**（Meta 分析、報表、UI、多通路整合等）→ 必讀 **`./doc/Implementation_Plan_index.md`**

> 注意：
> - 「提到」不等於「已讀」。你必須實際打開檔案並萃取重點。
> - 若你沒有讀到其中任何一份檔案，不得進入 Plan 階段。
> - 若不確定任務類型，請先詢問使用者或檢查變更檔案路徑。

---

## 2) 已讀驗收回報（必須照格式輸出）
完成三份必讀檔逐檔閱讀後，請輸出 **完全一致** 的段落格式如下（不得省略欄位）：

### ===READ_BACK_REPORT===
- 本機時間（local）：
- 已開啟閱讀的檔案（含路徑）：
  - [ ] ./.agent/workflows/dev-team.md
  - [ ] ./ivy_house_rules.md
  - [ ] ./.agent/Workflow_Plan_index.md（workflow 任務）或 ./doc/Implementation_Plan_index.md（專案任務）

- 從「規則/流程」萃取的 Top 5 硬約束（請用條列）：
  1.
  2.
  3.
  4.
  5.

- 與 Index 對照（根據任務類型選擇對應 Index）：
  - 這次任務是否已存在於 Index？（YES / NO / UNCLEAR）
  - 若 YES：請寫出 Index 中的 Task ID / Task 名稱（照 Index 原文）
  - 若 NO：請寫「NEW TASK - 需先登記 Index 才能進入執行」

- 風險旗標（若有）：
  - None /（列出風險）

### ===END_READ_BACK_REPORT===

**輸出後必須停下，等待使用者確認/回覆**（不得自行進入 Plan）。

---

## 3) Workflow 合約（高層流程，不等於可跳過 Gate）
在使用者確認 READ_BACK_REPORT 後，才可依序執行：

1) **Plan**
- 輸出可審核、可落地的計畫（可含里程碑與驗收條件）
- 此階段不得改 code、不得下執行命令

2) **Approve Gate（使用者審核）**
- 必須詢問使用者：Approve / Reject / Revise
- 未明確 Approve：不得執行

3) **角色選擇 Gate**
必須詢問使用者選擇：
- **Engineer Tool（執行者）**：`codex-cli` / `opencode`（VS Code Terminals）
- **QA Tool（驗收者）**：`codex-cli` / `opencode`（VS Code Terminals）
  - **Cross-QA 硬規則**：`qa_tool ≠ last_change_tool`（例外需記錄在 `qa_compliance` 並由 user 明確允許）
- **Execution Backend Policy（執行後端策略）**：`extension-sendtext-required`
  - `extension-sendtext-required`（固定）：命令注入一律使用 IvyHouse Terminal Injector extension sendText（`IvyHouse Injector: Send Text to Codex Terminal` / `IvyHouse Injector: Send Text to OpenCode Terminal`）
- **Monitor Backend Policy（監測後端策略）**：`proposed-primary-with-extension-fallback`
  - `proposed-primary-with-extension-fallback`（預設）：可用時使用 Proposed API；不可用時改用 extension 監測模式（預設不使用 HTTP bridge）
  - 監測命令範例：`IvyHouse Monitor: Capture Codex Output`、`IvyHouse Monitor: Auto-Capture Codex /status`
  - 允許拆分為兩個 extension：Injector（sendText）與 Monitor（監測 fallback）

> Gate 完成後，必須在 Plan 的 `EXECUTION_BLOCK` 回填：
> `execution_backend_policy`、`executor_backend`、`monitor_backend`。

> Execute 前必跑 preflight（Project terminal）：
> - 一般模式：`python scripts/vscode/workflow_preflight_check.py --json`
> - bridge 模式：`python scripts/vscode/workflow_preflight_check.py --require-bridge --json`
> - 未達 `status=pass`：不得進入 Engineer 注入。

> 注意：GitHub Copilot Chat 固定為 Coordinator（只做討論/分派/監控/回填 Plan），不作為 Engineer/QA 工具，也不得直接改 code。

4) **Execute（只允許被選定的 Executor 動手）**
- 僅能依照已核准 Plan 執行
- 變更應最小化，避免無關改動

5) **QA（必須對照 Plan 與硬約束）**
- QA 必須分級：PASS / PASS WITH RISK / FAIL
- 若非 PASS：必須指出風險與原因

6) **Log（QA 後必寫）**
- QA 結束後必須產出 log
- log 若已 commit，需包含 commit hash
- 是否提交（含 log）由使用者決策；若有提交，Log 應與變更一起納入版本控管以利稽核追蹤

7) **Close**
- 總結完成內容、變更範圍、風險、後續事項

---

## 4) Scope Break（停止條件）
若執行中出現「Plan 未包含的新需求」：
- 立即停止
- 回報：`SCOPE BREAK`
- 詢問使用者決策：
  - 回到原 scope，或
  - 新增/更新 Index 並開新 plan

---

## 5) 並行任務（停止條件）
**一個任務 = 一份 plan = 一份 log = 一組（或一串）commit。**
不得把不同任務混寫在同一份 plan/log/commit 鏈。

---

## 6) 小修正例外（暫定政策，稍後用 git hooks / lint-staged 落地）
小修正可能允許「較簡化流程」，但需同時符合：
- 變更行數 ≤ 20 行
- 僅限 doc / README / 註解 / formatting
- 仍需使用者明確允許（例如使用者說「這次是小修正可簡化」）

> 之後會用 git hooks / lint-staged 在 commit 時做硬性卡控。
