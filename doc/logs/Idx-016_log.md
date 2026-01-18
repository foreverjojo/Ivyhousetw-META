# Idx-016 Log｜Trace ID 追蹤（Correlation ID）

**執行日期**：2026-01-18
**執行者**：OpenCode
**狀態**：✅ 已完成

## 1. 任務內容
- 新增 Trace ID（Correlation ID）機制，讓同一輪流程的 log 能跨模組串起來。
- 讓結構化 JSON log 自動包含 `trace_id` 欄位。

## 2. 主要變更
- 新增 `core/tracing.py`
  - `ensure_trace_id()`：確保當前 context 有 trace_id（無則建立）
  - `get_trace_id()`：取得當前 trace_id
  - `trace_context()`：可選的 context manager（本次未強制導入至所有流程）
  - `attach_trace()`：把 trace_id 附加到 extra dict（便於逐步導入）
- 更新 `core/logging.py`
  - JSONFormatter 內嘗試讀取 `core.tracing.get_trace_id()`，若存在則寫入 `trace_id`
  - `extra_data` 存取改用 `getattr(record, "extra_data", None)`，避免屬性不存在造成問題
- 更新 `ui/steps.py`
  - `run_step_b()` 起點呼叫 `ensure_trace_id(prefix="ui")`
  - Step B 開始/結束 log 加入 `step/mode/platform/week_id/vdir`（統一寫入 structured log 的 extra）

## 3. 驗證
- `pytest -q`：PASS（僅既有 golden files 測試依設計 skip）
- `python -m compileall -q core/tracing.py core/logging.py ui/steps.py`：PASS

## 4. 注意事項 / 風險
- `ui/steps.py` 目前仍超過 500 行限制（屬既有狀態，本次僅最小改動導入 trace）。
- Trace ID 導入策略採「可漸進」：先把 `trace_id` 放進 logger formatter，後續可再擴大覆蓋到所有 requests/LLM steps。
