# Plan: Agent Architecture Enhancement - Research/Reviewer/UI-UX Gates

**Index**: Idx-010
**Created**: 2026-01-17
**Planner**: GitHub Copilot (Coordinator Mode)

---

## 🎯 目標

整合 Research、Maintainability Reviewer、UI/UX 三個條件式 Gate 到現有的 VS Code Native 工作流，實現：
1. **不新增 agent 角色文件**（保持 keep it simple 原則）
2. **用固定段落**（Plan/Log 的固定區塊）取代獨立檔案
3. **條件式觸發**（只在真正需要時才執行，避免流程膨脹）
4. **機械化判定**（用硬規則而非「Orchestrator 判斷」，降低摩擦）

---

## 📋 SPEC

### Goal
- 加入 Research Gate（查證外部依賴/API/版本）
- 加入 Maintainability Reviewer（長期代碼質量審查）
- 加入 UI/UX CHECK（用戶體驗底線檢查）
- 保持 Plan + Log（可選 Evidence）的簡潔架構

### Non-goals
- ❌ 不新增 `.agent/roles/research.md`、`.agent/roles/reviewer.md`、`.agent/roles/ux.md`
- ❌ 不產生獨立的 SPEC.md、REVIEW.md、TEST_REPORT.md
- ❌ 不增加終端工具數量（仍然只用 codex-cli / opencode）
- ❌ 不改變現有的 Cross-QA 規則（`qa_tool ≠ last_change_tool`）

### Acceptance Criteria
1. Plan 模板包含 `SPEC`、`RESEARCH & ASSUMPTIONS`、`SCOPE & CONSTRAINTS` 固定段落
2. Coordinator 定義三個 Gate 的觸發條件與輸出位置
3. dev-team 說明三個 Gate 的角色與執行流程
4. Log 模板示例展示完整段落結構（包含 UI/UX CHECK、MAINTAINABILITY REVIEW）
5. 所有觸發條件可機械化判定（不需要「Orchestrator 主觀判斷」）
6. 每個 Gate 的觸發條件都有對應的固定命令/規則可重現判定（例如 `git status --porcelain`、`git diff --numstat`）

### Edge cases
- Research Gate 無可驗證來源時 → 寫入 ASSUMPTIONS + 標注 `RISK: unverified`
- Maintainability Review 變更太小時 → 段落不出現（不寫 N/A）
- UI/UX CHECK 未觸發時 → 段落不出現，但 SCOPE GATE 必須留下 `UI/UX triggered: NO`
- Evidence 產生條件模糊時 → 以固定閾值判定（見下方「Evidence（可選）Gate」）

---

## 🧭 機械化判定（Deterministic Rules）

> 本段落用來把「觸發」變成可重現的硬規則。Coordinator/QA 執行命令並把摘要寫入指定段落即可。
>
> ⚠️ 這些 git 指令只能在 **Project terminal / VS Code SCM** 執行；禁止透過 `terminal.sendText` 注入到 Codex/OpenCode terminal。

### 共用輸入（所有 Gate 都可使用）
- 變更檔案清單：`git status --porcelain`
- 變更行數統計（新增/刪除）：`git diff --numstat`
- 變更摘要：`git diff --stat`

### Research Gate（條件式）
觸發條件（滿足任一即觸發）：
- Plan 內出現 `research_required: true`
- 變更包含依賴檔案：`requirements.txt`、`pyproject.toml`（或新增任何 `*requirements*.txt`）

### Maintainability Gate（條件式）
觸發條件（滿足任一即觸發）：
- **存在程式碼變更**（例如變更檔案包含 `.py`；不含純 `.md/.txt` 文件變更）
  且同時滿足以下任一：
  - 變更總行數 > 50（以 `git diff --numstat` 的新增+刪除加總）
  - 修改到核心路徑：`core/**`、`utils/**`（以 `git status --porcelain` 檔案列表比對；依專案約定可調整）

### UI/UX Gate（條件式）
觸發條件（滿足任一即觸發；以 `git status --porcelain` 檔案列表比對）：
- 路徑匹配：`pages/**/*.py`、`ui/**/*.py`
- 主入口：`app.py`、`main.py`
- 檔名模式：`*_page.py`、`*_ui.py`、`*_component.py`

### Evidence（可選）Gate
只要滿足任一條件，才允許新增 `doc/logs/Idx-XXX_evidence.md`：
- `git diff --numstat` 的新增+刪除加總 > 200
- 需要完整引用終端輸出且引用行數 > 80（以實際貼入文件的行數計）

不滿足以上條件：Log 必須用摘要解釋，不產生 Evidence。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

> 本 Plan 僅涉及文檔與流程規範修改，不涉及新工具/新 API/版本依賴/外部服務整合

### Sources
- 前幾輪與 GPT/Opus 4.5 的討論內容（用戶提供）
- 現有 repo 結構：`../../.agent/roles/coordinator.md`、`Idx-000_plan.template.md`、`../../.agent/workflows/dev-team.md`

### Assumptions
- ✅ Streamlit app 主要用 `.py` 文件（UI/UX 觸發條件基於此假設）
- ✅ Scope Gate 已經在收集變更文件列表（可直接復用）
- ✅ Proposed API 監控機制已經可用（Coordinator 能讀取終端輸出）

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `doc/plans/Idx-000_plan.template.md` - 更新 Plan 模板
- `.agent/roles/coordinator.md` - 補充三個 Gate 規則
- `.agent/workflows/dev-team.md` - 說明三個 Gate 的流程整合
- `doc/logs/Idx-010_log_template_example.md` - 創建 Log 模板示例（新增）
- `doc/logs/Idx-010_log.md` - 本任務實際執行 Log（由 Coordinator 產生）
- `doc/logs/Idx-010_evidence.md` - Evidence（可選，僅在 Evidence Gate 閾值命中時允許產生）

> NOTE: 若 repo 尚未有 `doc/logs/` 目錄，實作時需先建立目錄再新增檔案。

### Done 定義
1. ✅ Plan 模板包含完整的 SPEC/RESEARCH/SCOPE 段落
2. ✅ Coordinator 包含三個 Gate 的硬觸發條件與輸出規則
3. ✅ dev-team 包含三個 Gate 的角色說明與流程位置
4. ✅ Log 模板示例展示所有段落（包含 optional 段落）
5. ✅ 所有規則可被 Orchestrator 機械化執行（無需主觀判斷）

### Rollback 策略
- Level: L2（回滾建議）
- 前置條件：執行前確保 worktree clean（`git status --porcelain` 為空）
- 回滾動作：`git restore --worktree --staged -- doc/ .agent/`

### Max rounds
- 估計：3 rounds（更新 Plan 模板 → 更新 Coordinator/dev-team → 創建 Log 示例）

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `doc/plans/Idx-000_plan.template.md` | 修改 | 加入 SPEC、RESEARCH & ASSUMPTIONS、SCOPE & CONSTRAINTS 段落 |
| `.agent/roles/coordinator.md` | 修改 | 補充 Research Gate、Maintainability Gate、UI/UX Gate 規則 |
| `.agent/workflows/dev-team.md` | 修改 | 說明三個 Gate 的觸發條件與輸出位置 |
| `doc/logs/Idx-010_log_template_example.md` | 新增 | 完整的 Log 模板示例（展示所有段落） |

---

## 📝 邏輯細節

### 0. Gate 輸出規格（避免段落缺失誤判）

- **Plan**：必定包含 `SPEC`、`RESEARCH & ASSUMPTIONS`（至少含 `research_required: true/false`）、`SCOPE & CONSTRAINTS`。其中 `RESEARCH & ASSUMPTIONS` 只有在 Research Gate 觸發時才需要完整填寫 Sources/Assumptions。
- **Log**：
  - 必定包含 `SCOPE GATE`（且固定記錄 `UI/UX triggered: YES/NO`）
  - `UI/UX CHECK`：只在 `UI/UX triggered: YES` 時出現
  - `MAINTAINABILITY REVIEW`：只在 Maintainability Gate 觸發時出現
  - `EVIDENCE`：只在 Evidence Gate 閾值命中時才允許新增對應檔案

### 1. Plan 模板更新（`doc/plans/Idx-000_plan.template.md`）

**在 `## 🎯 目標` 之後、`## 📁 檔案變更` 之前插入：**

```markdown
---

## 📋 SPEC

### Goal
[任務的主要目標，一句話總結]

### Non-goals
[明確排除的範圍，避免 scope 漂移]
- ❌ 不做：[具體排除項目]

### Acceptance Criteria
[可驗收的條件清單]
1. ✅ [驗收條件 1]
2. ✅ [驗收條件 2]

### Edge cases
[需要處理的邊界情況]
- [邊界情況 1] → [處理方式]

---

## 🔍 RESEARCH & ASSUMPTIONS *(optional)*

> ⚠️ 觸發條件（滿足任一即必填）：
> - Plan 出現新 npm/pip/gem 等外部依賴
> - 使用新 API 端點或服務
> - 涉及版本升級
> - 整合外部服務（Meta API、Firebase、Cloud Run 等）

research_required: [true|false]

> Planner 在此明確標記是否需要 Research Gate

### Sources
[僅限 user 提供的官方連結或 repo 內文檔]
- [官方文檔連結]
- [repo 內參考文件路徑]

### Assumptions
[若無可驗證來源，列出假設並標注風險]
- ⚠️ RISK: unverified - [假設內容]
- ✅ VERIFIED - [已驗證的假設]

---

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
[允許變更的文件/目錄清單]
- `path/to/file.py` - [變更原因]
- `path/to/dir/**` - [批次變更原因]

### Done 定義
[完成條件，用於判定任務是否完成]
1. ✅ [條件 1]
2. ✅ [條件 2]

### Rollback 策略
- **Level**: [L1|L2|L3|L4]
- **前置條件**: [執行前必須滿足的條件]
- **回滾動作**: [具體回滾命令或步驟]

### Max rounds
- **估計**: [預估執行回合數]
- **超過處理**: [超過時的處理方式]

---
```

**位置說明**：
- SPEC 段落在目標之後，提供可驗收的規格
- RESEARCH & ASSUMPTIONS 是可選段落，只在 `research_required: true` 時必填
- SCOPE & CONSTRAINTS 在檔案變更之前，提供執行約束

---

### 2. Coordinator 更新（`.agent/roles/coordinator.md`）

**在現有的 ORCH_MODE 規則中，補充三個 Gate 的定義：**

```markdown
#### Research Gate（條件式啟用）

**觸發條件**（滿足任一即觸發）：
- Plan 的 `research_required: true`
- 變更包含依賴檔案：`requirements.txt`、`pyproject.toml`（或新增任何 `*requirements*.txt`）

**執行策略**：
- **Link-required**：sources 只能放 user 提供的官方連結或 repo 內文檔
- 若無可驗證來源 → 一律寫到 assumptions 並標注 `RISK: unverified`
- 輸出位置：回填 Plan 的 `RESEARCH & ASSUMPTIONS` 段落

**FAIL 路由**：
- 若 Research Gate 未通過（research_required: true 但未完成）→ 退回 Planner 補充 Research

---

#### Maintainability Gate（條件式啟用）

**觸發條件**（滿足任一即觸發）：
- **存在程式碼變更**（例如變更檔案包含 `.py`；不含純 `.md/.txt` 文件變更）
  且同時滿足以下任一：
  - 變更超過 50 行（新增+刪除；以 Project terminal / VS Code SCM 的 `git diff --numstat` 統計為準）
  - 修改核心模塊（例如 `core/`、`utils/`、`config.py`，依專案約定）

**執行方式**：
- 由 QA 工具在 QA 報告後補充一段 `MAINTAINABILITY REVIEW`
- 主要是 code review（檢查命名/重複/耦合/邊界/技術債）
- **硬規則**：Reviewer 永不改 code（只評估，不執行）

**輸出位置**：
- 回填 Log 的 `MAINTAINABILITY REVIEW` 段落
- 若未觸發：該段落不出現（不寫 N/A）

**FAIL 路由**：
- Must fix → 退回 Engineer
- 需求不清 → 退回 SPEC_MODE

---

#### UI/UX Gate（條件式啟用）

**觸發時機**：
- 在 Scope Gate 同步判定（基於變更文件列表）

**觸發條件**（滿足任一即觸發）：
- 路徑匹配：`pages/**/*.py`、`ui/**/*.py`
- 主入口文件：`app.py`、`main.py`
- 文件名模式：`*_page.py`、`*_ui.py`、`*_component.py`

**執行方式**：
- 由 QA 工具在 QA 報告後補充一段 `UI/UX CHECK`
- 主要是 code review（檢查空狀態/錯誤提示/Loading/主要操作文案）
- **硬規則**：UI/UX CHECK 是 QA 報告的段落，不是獨立工具執行

**輸出位置**：
- SCOPE GATE 必須固定記錄 `UI/UX triggered: YES/NO`
- 若 YES → Log 必須包含 `UI/UX CHECK` 段落
- 若 NO → 該段落不出現（不寫 N/A）

**FAIL 路由**：
- 缺少必要狀態處理（空狀態/錯誤提示/Loading/主要操作可達）→ 退回 Engineer（預設）
- 需求不清（缺乏驗收條件/邊界情況未定義）→ 退回 SPEC_MODE

---

#### Evidence 產生條件（可選，不強制）

**觸發條件（硬規則）**（滿足任一才允許產生 Evidence 檔案）：
- `git diff --numstat` 的新增+刪除加總 > 200
- 需要完整引用終端輸出且引用行數 > 80（以實際貼入文件的行數計）

**不產生條件**：
- 不滿足上述硬閾值 → 不產生 Evidence（Log 用摘要即可）

**引用格式**：
- Log 中只放摘要 + 指向 Evidence 的連結：`[See Evidence](../logs/Idx-XXX_evidence.md#section-name)`
```

---

### 3. dev-team 更新（`.agent/workflows/dev-team.md`）

**在現有的工作流說明中，補充三個 Gate 的位置：**

```markdown
### Phase 0：定義與查證（輸入正確）

1. **Coordinator (Spec Mode)** → 產出 Plan 的 SPEC 段落
2. **Research Gate（條件式）**：
   - 若 Plan 的 `research_required: true` → 必須完成 Research
   - 輸出：回填 Plan 的 `RESEARCH & ASSUMPTIONS` 段落
   - 策略：Link-required（只接受官方連結或 repo 內文檔）
3. **Planner** → 產出完整 Plan（含 SCOPE & CONSTRAINTS、EXECUTION_BLOCK）
4. 👤 **User 審核點①**：檢查 Plan 是否合理

---

### Phase 1：實作（只改 code）

1. **Engineer** → 依 Plan 實作（交 diff/變更清單）

---

### Phase 2：驗證（可重現）

1. **QA/Verifier** → 跑測試 + 收 log → 產出 QA REPORT 段落
2. **Maintainability Gate（條件式）**：
   - 若變更超過阈值 → QA 工具補充 `MAINTAINABILITY REVIEW` 段落
   - 硬規則：Reviewer 永不改 code
3. **UI/UX Gate（條件式）**：
   - 若 Scope Gate 判定 `UI/UX triggered: YES` → QA 工具補充 `UI/UX CHECK` 段落
   - 主要是 code review（檢查必要狀態處理）

---

### Phase 3：整合裁決（流程控制）

1. **Coordinator (Orchestrator Mode)** → 產出 RUNLOG（回填到 Log）
2. 判斷：
   - ✅ PASS（進下一個 milestone / 合併）
   - 🔁 FAIL → 指派回退：
     - 測試不過 → Engineer
     - 需求不清 → Spec Mode
     - 計畫切片不合理 → Planner
     - UI/UX Must fix → Engineer
     - Maintainability Must fix → Engineer
3. 👤 **User 審核點②**：檢查 RUNLOG 的 Pass/Fail 理由與 Must-fix 清單
```

---

### 4. Log 模板示例（`doc/logs/Idx-010_log_template_example.md`）

**創建新文件，展示完整的 Log 段落結構：**

```markdown
# Execution Log: Idx-XXX

**Plan**: [doc/plans/Idx-XXX_plan.md](../plans/Idx-XXX_plan.md)
**Created**: YYYY-MM-DD HH:mm:ss
**Status**: IN_PROGRESS | COMPLETED | FAILED

---

## EXECUTION TIMELINE

| Round | Tool | Command | Result | Timestamp |
|-------|------|---------|--------|-----------|
| 1 | codex-cli | [prompt/action] | SUCCESS | 2026-01-17 10:30:15 |
| 2 | codex-cli | [prompt/action] | SUCCESS | 2026-01-17 10:35:42 |
| 3 | opencode | [prompt/action] | SUCCESS | 2026-01-17 10:40:01 |

---

## SCOPE GATE

### Files changed
```
git status --porcelain
M  pages/meta_export.py
M  ui/form_builder.py
A  utils/validation.py
```

### Whitelist compliance
- ✅ PASS
- All files within whitelist: `pages/**`, `ui/**`, `utils/**`

### UI/UX triggered
- ✅ **YES**
- Triggered files: `pages/meta_export.py`, `ui/form_builder.py`
- Reason: Path matches `pages/**/*.py`, `ui/**/*.py`

---

## QA REPORT

### Test results
```bash
pytest tests/ -v
======================= test session starts ========================
collected 15 items

tests/test_meta_export.py::test_empty_data PASSED           [  6%]
tests/test_meta_export.py::test_valid_data PASSED           [ 13%]
tests/test_form_builder.py::test_render PASSED              [ 20%]
...
======================= 15 passed in 2.34s =========================
```

### Cross-QA compliance
- **qa_tool**: opencode
- **last_change_tool**: codex-cli
- **Valid**: ✅ YES

### Conclusion
- **Result**: PASS
- **Summary**: All tests passed, no breaking changes detected

---

## UI/UX CHECK *(triggered)*

> ⚠️ 本段落僅在 Scope Gate 判定 `UI/UX triggered: YES` 時出現

**觸發原因**: 變更文件包含 `pages/meta_export.py`, `ui/form_builder.py`

### 檢核範圍

#### UX（流程/文案）
- ✅ **空狀態處理**: 有文案 "尚無數據，請上傳 CSV" + 引導上傳按鈕
- ✅ **錯誤提示**: try/except + st.error with context message
- ⚠️ **Loading 狀態**: 部分長操作（data processing）缺 st.spinner
- ✅ **主要操作**: 按鈕文案清晰（"確認送出廣告數據" vs "提交"）

#### UI（一致性/基本可及性）
- ✅ **按鈕狀態一致**: disabled 時有 help text 說明原因
- ⚠️ **顏色對比**: success/warning 在淺色模式下對比可能不足（需人工驗證）
- ✅ **鍵盤操作**: 表單支持 Enter 提交

### Result
- **Conclusion**: PASS_WITH_RISK
- **Route on FAIL**: N/A（未 FAIL）
- **Must fix**: N/A
- **Should fix**:
  - 補充長操作的 Loading 狀態（data processing 步驟）
- **Manual spot-check needed**:
  - 淺色模式下 success/warning 顏色對比
  - 超長文本的換行表現

---

## MAINTAINABILITY REVIEW *(triggered)*

> ⚠️ 本段落僅在變更超過阈值時出現

**觸發原因**: 變更超過 50 行（實際變更 87 行）

### 審查結果

#### Code Quality
- ✅ **命名**: 函數/變數命名清晰一致
- ⚠️ **重複**: `validate_csv_format` 與 `check_csv_structure` 邏輯重複度高
- ✅ **耦合**: 模組間依賴清晰，無循環依賴

#### Technical Debt
- ⚠️ **TODO**: `meta_export.py:45` 留有 TODO 註解（處理超大文件）
- ✅ **測試覆蓋**: 新增函數皆有對應測試

### Result
- **Must fix**: N/A
- **Should fix**:
  - 重構 `validate_csv_format` 與 `check_csv_structure` 為單一函數
  - 移除或實作 TODO（處理超大文件）
- **Nice to have**:
  - 補充 type hints 到所有函數參數

---

## IF FAIL *(僅在 Conclusion=FAIL 時出現)*

> ⚠️ 本示例為 PASS_WITH_RISK，此段落不出現

**Reason**: [QA FAIL | UI/UX FAIL | Scope violation | Maintainability Must-fix]

**Route back to**: [Engineer | SPEC_MODE | Planner]

**Next action**: [具體修正內容或回退步驟]

---

## EVIDENCE *(optional)*

> ⚠️ 本回合未產生 Evidence（Log 可簡潔總結所有內容）
> 若需要產生，文件路徑為 `doc/logs/Idx-XXX_evidence.md`

---

## FINAL STATUS

- **Conclusion**: PASS_WITH_RISK
- **Commit hash**: `abc123def456` (pending merge)
- **Next milestone**: Idx-011 (廣告數據匯出優化)
- **Risks**:
  - UI 顏色對比需人工驗證
  - 長操作缺 Loading 提示（用戶體驗）
  - 重複邏輯待重構（長期維護性）

---

**Log Version**: 1.0.0
**Last Updated**: 2026-01-17 HH:mm:ss
**Synced With**: doc/plans/Idx-XXX_plan.md
```

---

## ⚠️ 注意事項

### 風險提示
- **文檔一致性**：所有現有 Plans 不會自動更新為新格式，只影響未來新建的 Plans
- **學習曲線**：Planner 需要理解何時填寫 `research_required: true`
- **段落缺失誤判**：需明確"未觸發不出現"與"忘記填寫"的區別（靠 SCOPE GATE 判定）

### 資安考量
- N/A（僅涉及文檔與流程修改，無 API Key 或敏感資料）

### 相依性
- 依賴 Scope Gate 能正確讀取變更文件列表（`git status --porcelain`）
- 依賴 Proposed API 監控機制已可用
- 若 Scope Gate 未實現，UI/UX Gate 無法正常觸發

---

## 🔗 相關資源

- 前幾輪討論內容（用戶提供的 GPT/Opus 4.5 分析）
- 現有文檔：
  - `../../.agent/roles/coordinator.md`
  - `../../.agent/workflows/dev-team.md`
  - `Idx-000_plan.template.md`

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-01-17 11:00:00
plan_approved: 2026-01-17 14:30:00
scope_policy: strict
expert_required: false
expert_conclusion: N/A
scope_exceptions: []

# Engineer 執行
executor_tool: GitHub Copilot
executor_tool_version: Claude Sonnet 4.5
executor_user: foreverjojo
executor_start: 2026-01-17 11:00:00
executor_end: 2026-01-17 13:45:00
session_id: N/A
last_change_tool: GitHub Copilot

# QA 執行
qa_tool: GitHub Copilot
qa_tool_version: Claude Sonnet 4.5
qa_user: foreverjojo
qa_start: 2026-01-17 13:45:00
qa_end: 2026-01-17 14:30:00
qa_result: PASS
qa_compliance: ⚠️ 例外（文檔修正）- 檔案：僅 .md 文檔變更，無程式碼實作

# 收尾
log_file_path: doc/logs/Idx-010_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

---

## ✅ 用戶確認

> 🛑 **必要停頓點**：Planner 產出 Spec 後，必須等待用戶確認才能進入執行階段。

- [x] SPEC 已確認，可進入執行階段
- [x] Engineer Tool 已選擇：`GitHub Copilot`（並已寫入 EXECUTION_BLOCK）
- [x] QA Tool 已選擇：`GitHub Copilot`（必須 ≠ last_change_tool，並已寫入 EXECUTION_BLOCK）
- [x] 理解"條件式段落"規則：
  - Research: 只在 `research_required: true` 或依賴檔案變更（`requirements.txt`/`pyproject.toml`）時必填
  - Maintainability Review: 只在變更超過阈值時出現
  - UI/UX CHECK: 只在 `UI/UX triggered: YES` 時出現
  - Evidence: 只在 Evidence Gate 閾值命中時允許產生

---

## 📊 總結：三個 Gate 的完整規格

| Gate | 觸發條件 | 執行者 | 輸出位置 | 硬規則 | 新增文件？ |
|------|---------|--------|---------|--------|-----------|
| **Research** | `research_required: true` 或依賴檔案變更 | Planner/Coordinator | Plan 的 `RESEARCH & ASSUMPTIONS` | Link-required | ❌ |
| **Maintainability** | 存在程式碼變更 且（變更 > 50 行 或 核心模組）| QA 工具（補充段落） | Log 的 `MAINTAINABILITY REVIEW` | Reviewer 永不改 code | ❌ |
| **UI/UX** | 變更文件匹配 UI 路徑 | QA 工具（補充段落） | Log 的 `UI/UX CHECK` | 是 QA 報告的段落，不是獨立工具 | ❌ |
| **Evidence** | diff/輸出超過閾值 | Coordinator | `doc/logs/Idx-XXX_evidence.md` | 只在閾值命中時允許產生 | ✅（可選）|

### 關鍵設計原則（符合 keep it simple）
1. ✅ **不新增 agent 角色文件**：Research/Reviewer/UI-UX 都是 ORCH_MODE 的 Gate
2. ✅ **用固定段落取代獨立檔案**：Plan 吃 SPEC/Research，Log 吃 QA/Reviewer/UI-UX
3. ✅ **條件式觸發**：未觸發的段落不出現（避免每回合都寫一堆 N/A）
4. ✅ **機械化判定**：所有觸發條件可用硬規則判定（不需要 Orchestrator 主觀判斷）
5. ✅ **責任歸屬明確**：FAIL 時用 `Route on FAIL` 字段明確指定退回對象

---

**Plan Version**: 1.0.3
**Target Template Version**: 2.3.0 (with SPEC/RESEARCH/SCOPE sections)
**Last Updated**: 2026-01-17
**Synced With**: .agent/roles/coordinator.md (pending update)
