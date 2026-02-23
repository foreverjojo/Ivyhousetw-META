# Plan: Idx-039

**Index**: Idx-039
**Created**: 2026-02-23
**Planner**: GitHub Copilot (Coordinator)

---

## 🎯 目標

將 OpenRouter 呼叫的 timeout/暫時性錯誤（例如 read timeout、5xx、429）做「一致的 retry/backoff + backup model fallback」，並在「一鍵最終」流程中對 Step E / Step E2 採用 **嚴格停止策略**：

- 一旦顧問輸出中斷（timeout/暫時性錯誤）且已嘗試 primary + backup model 仍失敗 → **直接停止流程並提示稍後再試**
- **不允許**在顧問輸出不完整的情況下繼續跑 Step F 產出報告

---

## 📋 SPEC

### Goal
- 讓 Step E（顧問）與 Step E2（交叉審核）在 OpenRouter timeout/暫時性錯誤時：先走 retry/backoff，再依 fallback chain 嘗試 backup model；仍失敗才中止。

### Non-goals
- ❌ 不改任何 KPI 計算/口徑（ROAS/CPC/CTR/CPM 皆不動）。
- ❌ 不改 meeting summary 的白話風格（已另有分析文件）。
- ❌ 不增加 LLM 呼叫「次數上限」到不可控（本任務只加傳輸層 retry；fallback chain 仍遵循既有 `get_retry_model_chain`）。

### Acceptance Criteria
1. ✅ Step E：遇到 timeout/暫時性錯誤時，會先嘗試 primary + backup model（依 `get_retry_model_chain`），且每個 model 會做 retry/backoff；全部失敗才停止。
2. ✅ Step E2：同上（若 enable_cross_review=ON），全部失敗才停止；不再像現況一樣降級繼續 Step F。
3. ✅ 一鍵最終（B→C→E→E2→F）：只要 E 或 E2 因上述錯誤失敗，流程會中止，且 UI 顯示「請稍後再試」訊息，不會產生新 `meeting.md`。
4. ✅ pipeline_state 可追溯：E/E2 失敗會寫入事件（例如 `E(error)` / `E2(error)`）並包含簡短 details（不得含 token）。
5. ✅ 主要 OpenRouter 呼叫點統一使用共用 wrapper（避免各檔案各自 timeout/retry 不一致）。

### Edge cases
- enable_cross_review=OFF：E2 仍寫入 `E2(skip)`（既有行為），不影響流程。
- 非暫時性錯誤（例如 400、回傳非 JSON）：仍視為顧問輸出失敗 → 停止（避免不完整報告）。
- Step E 已完成、Step E2 失敗：不產 meeting（避免「顧問交叉審核要求已開啟但結果缺失」造成誤導）。

---

## 🔍 RESEARCH & ASSUMPTIONS

research_required: false

### Sources
- repo 既有行為與程式：
  - `scripts/consultants.py` / `scripts/llm_insights.py` / `scripts/moderator.py` / `scripts/multimodal.py`
  - `ui/steps.py`、`pages/02_report_generation.py`
- 既有 fallback model chain：`core/model_settings.py::get_retry_model_chain`

### Assumptions
- ✅ VERIFIED - 一鍵最終頁面已用 try/except 包住整段流程，任何步驟 raise 會中止後續步驟（因此只要 E/E2 會 raise，就能阻止 Step F）。
- ✅ VERIFIED - Step E2 目前有「整體失敗降級略過」邏輯，會導致 E2 失敗仍可進 Step F；本任務要改為「嚴格停止」。

---

## 🔒 SCOPE & CONSTRAINTS

### Scope policy
- strict

### File whitelist
> 注意：先前已新增 `utils/openrouter_http.py`（在啟動 `/dev` 前），使用者已同意「納入白名單並保留」。

- `utils/openrouter_http.py` - OpenRouter retry/backoff 共用 wrapper（已新增；若需微調介面/訊息則在本 Idx 內完成）。
- `scripts/consultants.py` - Step E / Step E2 的 OpenRouter 呼叫改走 wrapper，並確保 fallback chain 會在暫時性錯誤時嘗試 backup model。
- `scripts/multimodal.py` - 多模態 OpenRouter 呼叫改走 wrapper（顧問 B 可能使用）。
- `ui/steps.py` - Step E / Step E2 加入 fail-fast：寫 pipeline_state 後 raise，中止一鍵最終流程。
- `pages/02_report_generation.py` - 僅調整錯誤呈現文案（如需），不改流程順序。
- `pages/04_ai_assistant.py` -（可選）改用 wrapper 統一 timeout/retry（不影響一鍵最終，但降低同類錯誤）。
- `tests/**` - 新增/更新測試，覆蓋「fallback 後仍 timeout 才停止」與「E2 不再降級」。
- `doc/Implementation_Plan_index.md` - 新增 Idx-039 任務列（NEW TASK 登記）。
- `doc/logs/Idx-039_log.md` -（收尾階段）記錄執行與 QA 結果。

### Done 定義
1. ✅ 上述 Acceptance Criteria 全數達成。
2. ✅ Ruff format/check 與 pytest 在本地可執行通過（至少針對新增測試）。

### Rollback 策略
- **Level**: L2
- **前置條件**: worktree 乾淨或已知變更可控
- **回滾動作**:
  - 還原 tracked 變更：`git restore --worktree --staged -- .`
  - 若需保留 wrapper：僅回滾其他檔案；或依使用者指示連同 wrapper 一併回滾

### Max rounds
- **估計**: 2（Engineer 實作 1 回合 + 修正 1 回合）
- **超過處理**: 若牽涉到更大範圍（例如要統一所有 LLM 呼叫策略），拆新 Idx。

---

## 📁 檔案變更

| 檔案 | 動作 | 說明 |
|------|------|------|
| `doc/Implementation_Plan_index.md` | 修改 | 新增 Idx-039 任務列（NEW TASK）。 |
| `doc/plans/Idx-039_plan.md` | 新增 | 本計畫文件。 |
| `utils/openrouter_http.py` | 修改（如需） | 補齊可重用介面/錯誤型別/訊息一致性。 |
| `scripts/consultants.py` | 修改 | OpenRouter 呼叫改走 wrapper；暫時性錯誤會嘗試 backup model；全部失敗才 raise。 |
| `scripts/multimodal.py` | 修改 | OpenRouter 多模態呼叫改走 wrapper。 |
| `ui/steps.py` | 修改 | Step E / E2 在暫時性錯誤時寫 pipeline_state 後 raise，阻止 Step F。 |
| `pages/02_report_generation.py` | 修改（最小） | 顯示「請稍後再試」訊息（沿用 raise 行為中止）。 |
| `pages/04_ai_assistant.py` | 修改（可選） | call_openrouter 改走 wrapper（不影響一鍵最終）。 |
| `tests/test_openrouter_failfast.py`（暫定） | 新增 | 覆蓋 fallback chain + 暫時性錯誤行為與 E2 不降級。 |

---

## 📝 邏輯細節

### 1) `utils/openrouter_http.py`（共用 wrapper）
- 提供 `post_chat_completions_json()`：
  - 針對 Timeout / ConnectionError / 408/429/5xx 做 retry/backoff + jitter
  - 失敗時 raise `OpenRouterTransientError`（讓上層能判斷「請稍後再試」）
- 允許以環境變數調整：
  - `OPENROUTER_TIMEOUT_S`
  - `OPENROUTER_MAX_RETRIES`
  - `OPENROUTER_BACKOFF_BASE_S`
  - `OPENROUTER_BACKOFF_MAX_S`

### 2) `scripts/consultants.py`（Step E / E2 呼叫點）
- `_openrouter_chat_completion()` 由 `requests.post` 改為呼叫 `post_chat_completions_json()`。
- `_openrouter_chat_completion_with_fallback()`：
  - 依 `get_retry_model_chain(role, primary_model=model)` 取得 `[primary, backup1, ...]`
  - 若呼叫拋 `OpenRouterTransientError`：繼續嘗試下一個 candidate（確保「有先試 backup model」）
  - 若候選耗盡：raise `OpenRouterTransientError`（訊息不含任何 key/token）

### 3) `scripts/multimodal.py`
- `openrouter_multimodal_completion()` 改走 wrapper：
  - 仍回傳 `choices[0].message.content`
  - 讓多模態呼叫也具備 retry/backoff

### 4) `ui/steps.py`（嚴格停止）
- `run_step_e()`：包住 `generate_consultant_notes()`
  - 若捕捉到 `OpenRouterTransientError` 或其他 LLM 失敗：
    - `write_pipeline_state(vdir, "E(error)", ...)`（details 含簡短錯誤原因）
    - `st.error("...請稍後再試")`
    - `raise RuntimeError("顧問輸出中斷，請稍後再試")`
- `run_step_e2()`：移除「整體失敗降級略過」策略（對 enable_cross_review=ON 的情況）
  - 同樣寫 `E2(error)` 後 raise

### 5) `pages/02_report_generation.py`
- 保持既有 try/except 行為：任何 step raise 都會中止。
- 需要時調整錯誤文案更白話（不新增新 UI 元件）。

### 6) 測試（pytest）
- 測試重點：
  1. `scripts/consultants.py` 的 fallback chain：primary 觸發 `OpenRouterTransientError` 時會嘗試 backup；backup 成功則回傳，並標示「有重試主模型」。
  2. `ui/steps.py::run_step_e2()`：enable_cross_review=ON 時，若 `generate_consultant_cross_reviews()` 拋 `OpenRouterTransientError`，應寫入 pipeline_state 並 raise（不得降級繼續）。

---

## ⚠️ 注意事項

- **資安**：不得紀錄/輸出任何 API Key；錯誤訊息只輸出 timeout、HTTP code、或短摘要。
- **可觀測性**：pipeline_state 的 details 請裁切長度（例如 200-300 字）避免污染 log。
- **相依性**：不變更 schema；本任務只處理「連線可靠性」與「流程 fail-fast」。

---

## 🔧 執行資訊

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-02-23 17:05:00
plan_approved: 2026-02-23 17:13:49
scope_policy: strict
expert_required: false
expert_conclusion: N/A
execution_backend_policy: extension-sendtext-required
scope_exceptions:
  - "utils/openrouter_http.py 已於 /dev 前新增；用戶允許納入 Idx-039 白名單保留"

# Engineer 執行
executor_tool: opencode
executor_backend: ivyhouse_sendtext_extension
monitor_backend: proposed_api_monitor
executor_tool_version: 1.2.6
executor_user: foreverjojo
executor_start: 2026-02-23 17:21:31
executor_end: 2026-02-23 18:04:18
session_id: N/A
last_change_tool: opencode

# QA 執行
qa_tool: codex-cli
qa_tool_version: 0.104.0
qa_user: foreverjojo
qa_start: 2026-02-23 18:02:55
qa_end: 2026-02-23 18:02:55
qa_result: PASS
qa_compliance: ✅ 符合

# 收尾
log_file_path: doc/logs/Idx-039_log.md
commit_hash: 10e05c2
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

---

## ✅ 用戶確認

- [x] Spec 已確認，可進入 Step 2 (Meta Expert：本任務 expert_required=false，可跳過)
- [x] Engineer Tool 已選擇：`opencode`
- [x] QA Tool 已選擇：`codex-cli`（必須 ≠ last_change_tool）
- [x] Execution Backend Policy 已確認：`extension-sendtext-required`
- [x] Monitor Backend Policy 已確認：`proposed-primary-with-extension-fallback`
