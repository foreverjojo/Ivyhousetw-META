# Idx-029 執行紀錄

- Plan：`.agent/plans/Idx-029_plan.md`
- 建立時間：2026-01-22
- 結論：✅ PASS（Codex CLI 已依 QA 報告逐條驗收通過；strict scope 通過；已回填 log/index）

---

## Scope Gate（strict scope）

### 白名單檔案
- `tools/vscode_terminal_orchestrator/extension.js`
- `tools/vscode_terminal_orchestrator/README.md`
- `.agent/plans/Idx-029_plan.md`
- `.agent/logs/Idx-029_log.md`
- `.agent/Workflow_Plan_index.md`

### 判定
- Result：PASS（變更範圍符合 plan whitelist）

---

## 蒐證（以 events 為準）

### Workflow run（舊 run：已被判定為不符 SPEC/AC，僅供對照）
- workflowRunId：`wf_20260122215419_f07bf0`
- events 檔：`.service/terminal_capture/workflow_20260122215419_events.jsonl`

### 關鍵事件摘要
- `engineer_done_detected`：已從 Engineer 階段推進到 QA
- `qa_prompt_sentinel_seen`：QA prompt sentinel gating 已生效（避免 prompt echo 汙染判定 buffer）
- `qa_wrong_marker_detected`：QA 階段曾誤出 Engineer marker，系統已送出 corrective prompt
- `qa_pass_detected`：最終成功偵測 PASS
- `workflow_stop`（reason=`PASS`）：workflow loop 已停止

---

## 本次修復摘要（已完成 QA 驗收）

- QA completion 偵測嚴格遵守「最後兩個非空白行」：倒數第二行必須是 done、最後一行必須是 result；不接受 swapped。
- 補齊單行/缺行 near-miss：即使只出現 done 或只出現 result（包含只剩 1 行的情境），也會回傳 near-miss，確保能寫入格式錯誤 events 並觸發 nudge，避免一路等到 timeout。
- wrong-marker 與 near-miss 的 corrective / nudge 皆統一走「prompt sentinel gating」，不再依賴 offset fast-forward。
- 加入 per-round nudge 上限（超限會明確 `workflow_stop` reason=`qa_completion_unstable`），避免默默卡到 timeout。
- 補齊可觀測事件：`qa_completion_format_error_detected`、`qa_wrong_marker_detected`、`qa_fail_detected`。

---

## ✅ Codex CLI QA 報告摘要（2026-01-23）

審查結論：PASS（strict scope 通過）

逐條驗收（摘要）：
- `detectQaCompletion(buf)` 僅取最後兩個非空白行做判定（tail-only）。
- 順序嚴格：只接受「倒數第二行=done、最後一行=result」；swapped 走 near-miss（不判定完成）。
- swapped / missing / 單行（只剩 1 行）皆回傳 near-miss；workflow 會寫入格式錯誤事件並送出 nudge；有上限，超限會停止（不默默等 timeout）。
- QA prompt / corrective / nudge 皆以 sentinel gating 為準：解析前等待 sentinel 並切掉 sentinel 之前內容；不使用 offset fast-forward/清空 buffer 來賭 sentinel。
- README 未出現 completion marker / result 行的字面值示例；僅引用 `WORKFLOW_MARKERS.*`。

證據（QA 輸出尾端）：
```
[QA_DONE]
QA_RESULT=PASS
```

---

## 備註

- `/workflow/status` 的回傳狀態在本次 run 結束後仍可能呈現 stale（已知：非最高真值）；驗收以 events 檔為準。
