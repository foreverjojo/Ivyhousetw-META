# Idx-030 — Workflow Loop：統一 Completion 判定（Engineer/QA/Fix）為 tail-only + timestamp + nonce（env 注入）

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-01-23 01:41:19+00:00
plan_approved: 2026-01-23 02:07:01+00:00
scope_policy: strict
expert_required: false
expert_conclusion: N/A
scope_exceptions: []

# Engineer 執行
executor_tool: opencode
executor_tool_version: N/A
executor_user: OpenCode CLI
executor_start: [TBD]
executor_end: [TBD]
session_id: [TBD]
last_change_tool: opencode

# QA 執行
qa_tool: codex-cli
qa_tool_version: N/A
qa_user: Codex CLI
qa_start: [TBD]
qa_end: 2026-01-23 03:45:06+00:00
qa_result: PASS
qa_compliance: ok (qa_tool != last_change_tool)

# 收尾
log_file_path: .agent/logs/Idx-030_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

## 📋 SPEC

### Goal
將 VS Code workflow loop 的 completion 判定全面「同規格化」，讓 Engineer/QA/Fix 三段都使用：
- tail-only（只看尾端固定行數，避免歷史輸出/echo 汙染）
- nonce（跨 session 隔離；由 workflow 生成並透過 env 注入）
- timestamp（可追溯、可辨識舊輸出）
並加入「可觀測 near-miss + 有上限的 nudge」避免默默 timeout。

### 與 Idx-029 的關係
- Idx-029：已將 QA 完成判定強化為 tail-only（最後兩個非空白行）+ near-miss/nudge
- Idx-030：在 Idx-029 基礎上，擴展並統一到 Engineer/QA/Fix，且加入 nonce/timestamp 與 env 注入驗證

### Non-goals
- ❌ 不改變 workflow 的整體狀態機（只調整 completion detection / 注入 / nudge 邏輯）
- ❌ 不新增外部服務（不依賴 HTTP endpoint/DB/遠端狀態）
- ❌ 不支援「舊格式 marker」的向後相容（新版必須含 nonce/timestamp）
- ❌ 不擴充到「任意位置出現 marker 就算完成」這類高誤判規則

### Acceptance Criteria
1. ✅ Engineer / QA / Fix 的 completion 判定統一採 tail-only，且使用一致的尾端格式（見下方「標準輸出格式」）。
2. ✅ workflow 啟動時生成 `WORKFLOW_SESSION_NONCE`（建議 8 bytes hex / 16 chars；最少 8 chars），並存入 `workflowLoopState.sessionNonce`。
3. ✅ 對 Codex CLI / OpenCode CLI 終端以 VS Code `createTerminal({ env })` 注入 `WORKFLOW_SESSION_NONCE`。
4. ✅ env 注入驗證採「延遲驗證（不干擾 CLI 初始化）」：
  - 不在 workflow 啟動時對 Codex/OpenCode 終端送出 shell 指令（避免被 CLI 當作任務 prompt，造成干擾）。
  - 於每個 phase 的 completion 解析時進行驗證：
    - 若 `NONCE` 缺失 / 不相符 → 記錄事件 `workflow_env_injection_suspected_failed`（或 phase-specific mismatch event），並觸發 nudge。
    - nudge 需包含「本輪預期 nonce」與「當前 TASK_ID」，讓工具可直接 copy 正確 nonce 值完成輸出。
  - 若連續 3 次 near-miss 仍無法給出正確 nonce → 視同注入/使用失敗，依 AC#7 的上限停止並記錄 exhausted（fail-safe）。
5. ✅ Timestamp 欄位必須為 ISO 8601 UTC（秒級）：`YYYY-MM-DDTHH:mm:ssZ`。
6. ✅ 驗證邏輯必須是「順序嚴格」且「尾端嚴格」：
   - 只允許最後 5 個非空白行用於完成判定
  - 必須嚴格按以下順序：
    - Line 1: 對應 marker（`[ENGINEER_DONE]` / `[QA_DONE]` / `[FIX_DONE]`）
    - Line 2: `TIMESTAMP=...`
    - Line 3: `NONCE=...`
    - Line 4: `TASK_ID=...`
    - Line 5: phase-specific 欄位（`ENGINEER_RESULT` / `QA_RESULT` / `FIX_ROUND`）
7. ✅ near-miss 機制（Engineer/QA/Fix 都要有）：
   - 對 nonce mismatch / timestamp invalid / taskId mismatch / missing field / order swapped 記錄可觀測事件（phase-specific event name）
   - 觸發 nudge，提示正確格式（含「本次預期 nonce」與「當前 TASK_ID」）
  - **每個 phase 獨立計數，每次進入該 phase 時重置為 0；每次最多重試 3 次**。
    - 例：Engineer（重置）→ QA（重置）→ Fix（重置）→ QA（再次重置）
    - Fix Round 2 開始時，Fix 計數器也必須重置
  - 超過上限：記錄 `completion_verification_exhausted` 並停止（不可無限重試）。
8. ✅ 更新文件：
   - `tools/vscode_terminal_orchestrator/README.md`
   - `.agent/roles/engineer.md`
   - `.agent/roles/qa.md`
   - `.agent/workflows/dev-team.md`
   說明新格式、timestamp 產生方式、nonce 來源（env）與常見錯誤。

### 標準輸出格式（嚴格 tail-only：最後 5 行非空白）

> 注意：`NONCE=...` 必須是「實際 nonce 值」。
> - workflow 會透過 env 注入提供 `WORKFLOW_SESSION_NONCE`，但不同 CLI/終端未必會做 shell 展開。
> - 因此請不要輸出字面值 `$WORKFLOW_SESSION_NONCE`；若輸出字面值會觸發 nonceMismatch near-miss。
> - 最穩健的做法：直接 copy workflow nudge 中顯示的預期 nonce。

**Engineer 完成**（最後 5 行必須長這樣）：
```
[ENGINEER_DONE]
TIMESTAMP=2026-01-23T14:35:42Z
NONCE=<SESSION_NONCE>
TASK_ID=Idx-030
ENGINEER_RESULT=COMPLETE
```

ENGINEER_RESULT 說明：
- `COMPLETE`：本輪 Engineer 工作已完成，進入 QA。
- 目前僅用於「欄位一致性/驗證」與未來擴充；不在本任務中改變狀態機分支。

**QA 完成**（最後 5 行必須長這樣）：
```
[QA_DONE]
TIMESTAMP=2026-01-23T14:38:15Z
NONCE=<SESSION_NONCE>
TASK_ID=Idx-030
QA_RESULT=PASS
```

**Fix 完成**（最後 5 行必須長這樣）：
```
[FIX_DONE]
TIMESTAMP=2026-01-23T14:42:30Z
NONCE=<SESSION_NONCE>
TASK_ID=Idx-030
FIX_ROUND=1
```

### Edge cases
- **Nonce 為空**（workflow 未正確初始化 / env 注入失敗）→ fail-fast 停止 workflow，提示用戶關閉/重建終端後再啟動。
- **Terminal 已存在**（先前已啟動的 Codex/OpenCode 終端）→ env 無法 retroactively 注入：
  - 建議策略：workflow 啟動時主動 `dispose()` 舊終端並重建；若不允許，則顯示錯誤要求用戶手動關閉終端再啟動。
- **Timestamp 非 UTC**（沒有 `Z`、或 `+08:00`）→ near-miss + nudge 提示改用 `date -u` 產生。
- **尾端多打文字**（marker 後面又輸出 debug 行）→ tail-only 無法命中：near-miss + nudge 強制只輸出 5 行。
- **TASK_ID 不匹配**（貼上舊 plan 的輸出）→ near-miss + nudge 提示當前 TASK_ID。
- **順序 swapped**（例如先 QA_RESULT 再 QA_DONE）→ near-miss + nudge（提示正確順序）。
- **輸出字面值 `$WORKFLOW_SESSION_NONCE`**（CLI 未做 shell 展開）→ 視同 nonceMismatch，nudge 要求改貼實際 nonce 值。

## 🔍 RESEARCH & ASSUMPTIONS
research_required: true

### Sources
- VS Code Terminal API：`createTerminal({ env })` 支援與限制
  - https://code.visualstudio.com/api/references/vscode-api#Terminal
- Repo 內參考：`tools/vscode_terminal_orchestrator/extension.js`（terminal 建立與 workflow loop 狀態）

### Assumptions
- ✅ VERIFIED：VS Code 1.85+ 支援 `createTerminal({ env: { ... } })`。
- ⚠️ RISK: unverified：既有已開啟的終端是否能被可靠重建且不影響其他工作流程（需在實作時明確提示用戶）。
- ⚠️ RISK: unverified：Codex/OpenCode CLI 是否能讓使用者/工具「方便地取得 env 值」並輸出為 literal nonce（因此採用 AC#4 的延遲驗證 + nudge 提供 nonce 值）。

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `tools/vscode_terminal_orchestrator/extension.js` - 主要：統一 completion parser + env 注入 + 注入驗證 + near-miss 上限
- `tools/vscode_terminal_orchestrator/README.md` - 文件：更新 completion 規範（避免在 README 以「純字面值範例」誤導，需遵循 repo 既有寫法）
- `.agent/roles/engineer.md` - 文件：新增 Idx-030 completion 規範與 timestamp/nonce 指引
- `.agent/roles/qa.md` - 文件：同上（QA_RESULT 規範）
- `.agent/workflows/dev-team.md` - 文件：更新 completion 判定規範與注意事項
- `.agent/plans/Idx-030_plan.md` - 本 plan 文件
- `.agent/Workflow_Plan_index.md` - 新增 Idx-030 追蹤列

### Done 定義
1. ✅ extension 邏輯完成：Engineer/QA/Fix 都改為統一尾端 5 行驗證（含 nonce/timestamp/task_id/phase-field）。
2. ✅ env 注入驗證可通過（延遲驗證）：
  - workflow 確實以 `createTerminal({ env })` 建立終端並注入 `WORKFLOW_SESSION_NONCE`
  - 任一 phase 首次完成輸出時，`NONCE=<nonce>` 能被解析並與 `workflowLoopState.sessionNonce` 相符
3. ✅ near-miss 有上限：故意輸出錯誤 nonce / 錯 timestamp / 錯 task_id / 多打一行字，都會（1）記錄事件（2）nudge（3）最多 3 次後停止並記錄 exhausted。
4. ✅ 文件同步完成。

### Rollback 策略
- **Level**: L2
- **觸發條件**:
  - 實作中確認某些 VS Code 版本/環境下無法可靠注入/使用 nonce（導致 near-miss 無法收斂）
  - QA 發現 completion detection 仍有高誤判/高卡死風險（例如誤判率 > 5% 或經常觸發 exhausted）
  - 用戶要求中止或需求變更
- **前置條件**: 變更範圍必須落在 File whitelist；若超出需先停下來請用戶決策。
- **回滾動作**:
  - `git restore --worktree --staged -- tools/vscode_terminal_orchestrator/extension.js tools/vscode_terminal_orchestrator/README.md .agent/roles/engineer.md .agent/roles/qa.md .agent/workflows/dev-team.md .agent/Workflow_Plan_index.md`
  - 刪除新增的 plan/log（若需要回滾）：`.agent/plans/Idx-030_plan.md`、`.agent/logs/Idx-030_log.md`

### Max rounds
- **估計**: 2 rounds
- **超過處理**: 若 Round 2 仍無法穩定完成判定，需停下來回報：是哪一個 phase/哪一個 edge case 無法收斂，並提出縮 scope 或改規格選項。

## 📁 檔案變更表

| 檔案 | 動作 | 說明 |
|------|------|------|
| tools/vscode_terminal_orchestrator/extension.js | 修改 | 統一 completion 判定：tail-only + nonce + timestamp + task_id + phase-field；新增 env 注入/驗證；加入 near-miss 上限與事件 |
| tools/vscode_terminal_orchestrator/README.md | 修改 | 更新 completion 規範與常見錯誤；與 repo 既有 marker 文檔策略一致 |
| .agent/roles/engineer.md | 修改 | 新增 Idx-030 completion 規範（含 timestamp 產生方式、nonce 來源） |
| .agent/roles/qa.md | 修改 | 新增 Idx-030 completion 規範（含 QA_RESULT 要求） |
| .agent/workflows/dev-team.md | 修改 | 更新 completion 規範：統一尾端 5 行 + nonce/timestamp + 停止條件 |
| .agent/Workflow_Plan_index.md | 修改 | 新增 Idx-030 追蹤列 |
| .agent/logs/Idx-030_log.md | 新增 | QA/驗收 evidence 與事件摘要（實作完成後補） |

## 📝 邏輯細節

### 1) `tools/vscode_terminal_orchestrator/extension.js`

**A. 統一 completion parser（Engineer/QA/Fix）**
- 新增（或重構）成單一可重用的 tail-only parser：
  - 只取最後 5 個非空白行（不可取任意位置）
  - 嚴格驗證行序：marker → TIMESTAMP → NONCE → TASK_ID → phase-specific
  - timestamp regex：`^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`
  - nonce 必須等於 `workflowLoopState.sessionNonce`
  - TASK_ID 必須等於本輪 workflow 的 plan id

**B. 統一 near-miss 事件與 nudge（含上限）**
- 針對每個 phase（engineer/qa/fix）維持獨立計數器：
  - `engineer_completion_near_miss_count` / `qa_completion_near_miss_count` / `fix_completion_near_miss_count`
  - **reset 規則**：每次進入該 phase 時重置為 0；Fix 若進入下一輪（Fix Round 2）也必須重置
  - 每個 phase 最多 3 次
- near-miss 類型至少包含：
  - `nonceMismatch`
  - `timestampInvalid`
  - `taskIdMismatch`
  - `missingField`
  - `orderInvalid`
  - `extraTailNoise`（尾端多餘行）
- 超過上限：記錄 `completion_verification_exhausted`（帶 phase/round）並停止（不可默默等 timeout）。

**C. workflow session nonce 生成與注入**
- workflow 啟動時生成 nonce，寫入 `workflowLoopState.sessionNonce`
- 建立/重建 Codex/OpenCode terminal 時，透過 `createTerminal({ env: { WORKFLOW_SESSION_NONCE: nonce } })` 注入

**D. env 注入驗證：延遲驗證（不干擾 CLI 初始化）**
- 不在 workflow 啟動時對 Codex/OpenCode 終端送出 shell 指令（避免被 CLI 當作 prompt）。
- 將「env 注入是否有效」的驗證併入 completion 解析：
  - 若偵測到 `NONCE` 缺失 / 不相符 / 為字面值 `$WORKFLOW_SESSION_NONCE` → 記錄事件並觸發 nudge（附上預期 nonce）。
  - 連續 3 次仍失敗 → exhausted，停止並提示用戶重建終端後再試。

### 2) 文件更新（README + roles + workflow）

**engineer / qa 文件需補充的重點**
- 新增段落：`### Completion Marker 格式（Idx-030 統一規範）`
- 教學：如何取得 UTC timestamp（可直接複製）：
  - Linux/macOS：`date -u +"%Y-%m-%dT%H:%M:%SZ"`
  - Windows PowerShell：`(Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")`
  - Python（跨平台）：
    - `from datetime import datetime, timezone; print(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))`
- 強調：nonce 需「從環境變數 `WORKFLOW_SESSION_NONCE` 取得」或「直接 copy workflow nudge 提供的值」，不可 hard-code
- 注意：不要輸出字面值 `$WORKFLOW_SESSION_NONCE`，必須輸出實際 nonce 值（例如 `a3f9d8e2`）
- 強調：完成輸出必須是尾端最後 5 行，不可再多輸出其他文字

### Nonce 格式規範（統一）
- **格式**：8~16 chars hex（例如 `a3f9d8e2` 或 `a3f9d8e2c4b5e6f7`）
- **生成方式（建議）**：Node.js 使用 `crypto.randomBytes(4)` 或 `crypto.randomBytes(8)` 後 `.toString("hex")`
- **不建議**：UUID、base64（容易混淆/含特殊字元）、純數字（可讀性差且容易被誤抄）

## 🧪 測試策略（手動 + 整合）

### A) 針對 parser 的手動測試（在實作階段用 replay/直接餵字串）
1. 正常格式（每個 phase）應成功判定
2. nonce 錯誤 → near-miss + nudge + event
3. timestamp 錯誤 → near-miss + nudge + event
4. task_id 錯誤 → near-miss + nudge + event
5. 多打一行尾端文字 → near-miss + nudge + event
6. 連續錯 3 次 → `completion_verification_exhausted` 並停止
7. nonce 取值失敗（輸出 `$WORKFLOW_SESSION_NONCE` 字面值）→ near-miss + nudge（提示改貼實際 nonce）

### B) Workflow 整合測試（人工跑一輪）
- 起一個測試 plan（可用 Idx-030 本 plan）
- 故意在 Engineer/QA/Fix 分別輸出一種錯誤格式，確認 near-miss 能收斂或在上限停止
- 最後以正確格式輸出，確認能 PASS（QA_RESULT=PASS）

## ⚠️ 注意事項
- **向後不相容**：舊格式 marker 將不再被接受；若有進行中的 workflow，merge 後可能 timeout。
  - **影響範圍**：所有使用 workflow loop completion 判定的任務（含工程/QA/fix），特別是仍在進行中的 workflow 任務。
  - **緩解措施**：merge 前確認 `workflowLoopState.active === false`；必要時先停止 workflow 並重建終端。
- **Terminal 生命週期**：env 注入只能在 create 時生效；需要明確策略（重建或 fail-fast 提示關閉終端）。
- **資安**：nonce 不視為 secret，但仍避免把過長 raw log 或敏感內容寫入 events。

## ✅ 用戶確認

- [ ] Spec 已確認，可進入 Tool Selection Gate（選 Engineer/QA 工具）
- [ ] Engineer Tool 已選擇：`[codex-cli|opencode]`
- [ ] QA Tool 已選擇：`[codex-cli|opencode]`（必須 ≠ last_change_tool）
