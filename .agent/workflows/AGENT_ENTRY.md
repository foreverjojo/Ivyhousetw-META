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
3. `./docs/implementation_plan_index.md`

> 注意：
> - 「提到」不等於「已讀」。你必須實際打開檔案並萃取重點。
> - 若你沒有讀到其中任何一份檔案，不得進入 Plan 階段。

---

## 2) 已讀驗收回報（必須照格式輸出）
完成三份必讀檔逐檔閱讀後，請輸出 **完全一致** 的段落格式如下（不得省略欄位）：

### ===READ_BACK_REPORT===
- 本機時間（local）：
- 已開啟閱讀的檔案（含路徑）：
  - [ ] ./.agent/workflows/dev-team.md
  - [ ] ./ivy_house_rules.md
  - [ ] ./doc/implementation_plan_index.md

- 從「規則/流程」萃取的 Top 5 硬約束（請用條列）：
  1.
  2.
  3.
  4.
  5.

- 與 Index 對照（implementation_plan_index）：
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
- **Executor（執行者）**：Continue / Copilot / Codex
- **QA（驗收者）**：Continue / Copilot / Codex
  - 原則上 QA 不應與 Executor 同一個（除非 ≤20 行小修且使用者明確允許）

4) **Execute（只允許被選定的 Executor 動手）**
- 僅能依照已核准 Plan 執行
- 變更應最小化，避免無關改動

5) **QA（必須對照 Plan 與硬約束）**
- QA 必須分級：PASS / PASS WITH RISK / FAIL
- 若非 PASS：必須指出風險與原因

6) **Log（QA 後必寫）**
- QA 結束後必須產出 log
- log 若已 commit，需包含 commit hash
- logs 為本機保存、不可提交到 git

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
