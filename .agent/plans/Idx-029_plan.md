# Idx-029 — Workflow Loop：QA 完成判定韌性補強（防 wrong marker / 格式近似錯誤導致 timeout）

<!-- EXECUTION_BLOCK_START -->
# Plan 狀態
plan_created: 2026-01-22 21:47:47+00:00
plan_approved: 2026-01-22 21:53:15+00:00
scope_policy: strict
expert_required: false
expert_conclusion: N/A
scope_exceptions: []

# Engineer 執行
executor_tool: opencode
executor_tool_version: N/A
executor_user: OpenCode CLI
executor_start: 2026-01-22 21:54:19+00:00
executor_end: 2026-01-22 22:00:17+00:00
session_id: wf_20260122215419_f07bf0
last_change_tool: opencode

# QA 執行
qa_tool: codex-cli
qa_tool_version: N/A
qa_user: Codex CLI
qa_start: 2026-01-22 22:00:17+00:00
qa_end: 2026-01-22 22:07:27+00:00
qa_result: FAIL
qa_rerun_date: 2026-01-23
qa_rerun_result: PASS
qa_rerun_evidence: .agent/logs/Idx-029_log.md
qa_compliance: ok (qa_tool != last_change_tool)

# 收尾
log_file_path: .agent/logs/Idx-029_log.md
commit_hash: pending
rollback_at: N/A
rollback_reason: N/A
rollback_files: N/A
<!-- EXECUTION_BLOCK_END -->

## 📋 SPEC

### Goal
修補 VS Code workflow loop 在 QA 階段的「完成判定」韌性，避免因：
- QA 誤輸出 Engineer/Fix 的 completion marker（造成 `qa_wrong_marker_detected` 後卡住）
- QA 尾端輸出格式近似但不合規（例如多打一個字元、空白、全形括號等）
而導致 workflow 直到 timeout 都無法產生 `qa_pass_detected` / `qa_fail_detected`。

### Non-goals
- ❌ 不調整本 repo 的 dev-team 治理規則文件（那是 Idx-028 範圍）。
- ❌ 不新增新的外部服務/endpoint 作為 workflow 判定依賴。
- ❌ 不放寬到「在任意位置出現 QA_RESULT 就算 PASS」這類高誤判規則（仍維持 tail-only 的核心精神）。

### Acceptance Criteria
1. ✅ 在 `tools/vscode_terminal_orchestrator/extension.js` 強化 QA 端的「自我修正」能力：
   - 若偵測到 QA tail 出現 Engineer/Fix marker（觸發 wrong-marker），會送出更不易誤解的 corrective prompt。
   - 若偵測到 QA completion 的「近似格式錯誤」（例如 done 行或 result 行尾端多字、空白、全形括號），會寫入 events（例如 `qa_completion_format_error_detected`），並在同一 round 內可控次數地再次提示 QA 只輸出正確尾端。
2. ✅ 任何「提示 QA 補輸出尾端」的 prompt 一律使用同樣的「prompt sentinel gating」策略，避免 prompt echo 汙染 marker buffer（不再依賴不穩定的 offset fast-forward 假設）。
3. ✅ QA completion 判定仍維持 tail-only，但允許低風險的合法變體（需在 plan 內明確定義）：
   - 允許 `QA_RESULT` 行的等號前後空白（例如 `QA_RESULT = PASS`）但仍必須是最後一行，且必須搭配 QA_DONE 行。
   - QA_DONE 行允許常見全形括號變體（若實作成本低且不增加誤判）。
4. ✅ events 可機械化驗收：
   - 遇到 wrong marker 時：必須產生 `qa_wrong_marker_detected`，並可看到後續 `qa_*_detected` 或明確 stop reason（不可默默卡到 timeout）。
   - 遇到格式近似錯誤時：必須產生 `qa_completion_format_error_detected`（或同等可讀事件），且不應無限重試。

### Evidence / 驗收方式
- 使用既有蒐證檔作為 replay 目標（避免依賴 LLM 即時輸出不穩定）：
  - `.service/terminal_capture/qa_20260122121951_raw.log`（含錯誤尾端輸出案例）
  - `.service/terminal_capture/workflow_20260122121951_events.jsonl`（含 `qa_wrong_marker_detected` 與 timeout）
- 在 Project terminal 透過小型 replay 工具/測試（本 plan 允許新增）餵入「尾端樣本字串」，驗證：
  - detectQaCompletion 可接受定義內的合法變體
  - near-miss 會觸發 format error event 並走 nudge

## 🔍 RESEARCH & ASSUMPTIONS
research_required: false
assumptions:
- workflow loop 的最可靠判據仍是 `.service/terminal_capture/workflow_*_events.jsonl`。
- 目前 `qa_wrong_marker_detected` 的觸發條件是「tail-only 命中 Engineer/Fix marker」，因此修正重點在於：
  - corrective prompt 的可理解性
  - retry / gating 的一致性
  - near-miss 的可觀測與可收斂（不無限卡住）

## 🔒 SCOPE & CONSTRAINTS

### File whitelist
- `tools/vscode_terminal_orchestrator/extension.js`
- `tools/vscode_terminal_orchestrator/README.md`（若需同步文件說明）
- `.agent/plans/Idx-029_plan.md`
- `.agent/logs/Idx-029_log.md`
- `.agent/Workflow_Plan_index.md`（新增 Idx-029 列，狀態初始為 ⏳ 待處理）

### Done 定義
1. ✅ 以 replay/測試方式證明：
   - wrong marker 與 near-miss 都能產生明確 events，且不會默默卡到 timeout
   - completion 判定可接受本 plan 定義的合法變體
2. ✅ 若有改 README，內容需避免寫出 completion marker 的「字面值」（僅引用 `WORKFLOW_MARKERS.*` 常數名稱）。

### Rollback
- `git restore --worktree --staged -- tools/vscode_terminal_orchestrator/extension.js tools/vscode_terminal_orchestrator/README.md`
- 回復 `.agent/Workflow_Plan_index.md` 與 Idx-029 log/plan 變更（如有）。

### Max rounds / Timeouts
- 本任務屬 extension 邏輯修補：預期 1–2 rounds 完成。
- 對 QA nudge/format-fix 的重試次數需設上限（例如每 round 最多 2 次），超過則 stop 並在 events 記錄原因。

## 📁 檔案變更表

| 檔案 | 動作 | 說明 |
|------|------|------|
| tools/vscode_terminal_orchestrator/extension.js | 修改 | QA completion 偵測與 corrective/nudge 流程韌性補強（含事件可觀測） |
| tools/vscode_terminal_orchestrator/README.md | 修改（選用） | 同步說明新的判定/重試/驗收方式（避免 marker 字面值） |
| .agent/Workflow_Plan_index.md | 修改 | 新增 Idx-029 追蹤列 |
| .agent/logs/Idx-029_log.md | 新增 | 驗收、evidence、replay/測試結果摘要 |

## 📝 實作草圖（高層）

1. 統一 QA prompt gating：
   - 將「每次送出 QA prompt（包含 corrective）」都附上一個唯一 `promptSentinel`，並在解析前強制等待 sentinel seen。
   - 移除只靠 offset fast-forward 的路徑（降低 race）。

2. 強化 QA completion 判定：
   - 保留 tail-only（最後兩個非空白行）核心策略。
   - 允許低風險變體：`QA_RESULT` 行允許空白；必要時支援全形括號（仍需 line-exact / regex anchored）。

3. 新增 near-miss 偵測與事件：
   - 若 tail 命中「看起來像 QA_DONE / QA_RESULT 但不合規」：
     - 追加 `qa_completion_format_error_detected`（包含 doneLine/resultLine 的摘要或 hash，避免把敏感/過長內容寫進 events）。
     - 送出一則更短、更可 copy 的提示，要求只輸出 2 行且不要加任何字。

4. 防止無限卡住：
   - 增加每 round 的 nudge 次數上限；超過就 stop 並寫入 events（例如 `workflow_stop` reason=`qa_completion_unstable`）。

---

❓ 若你同意這份 plan，我下一步會把 `plan_created` 改成實際時間、把 Idx-029 加到 `.agent/Workflow_Plan_index.md`，再進入 Tool Selection Gate（選 Engineer/QA 工具）。
