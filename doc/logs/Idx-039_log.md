# Task Execution Log: Idx-039

**Index**: Idx-039
**Plan Version**: 2026-02-23-v1
**Task Description**: OpenRouter timeout 重試 + backup model fallback；Step E / Step E2 嚴格停止（顧問失敗不產報告）

---

## 📋 Original Plan Summary

> 來源：`doc/plans/Idx-039_plan.md`

- 統一 OpenRouter 呼叫的 retry/backoff 行為，並在暫時性錯誤時依既有 `get_retry_model_chain` 嘗試 backup model。
- 一鍵最終流程中，Step E（顧問）/ Step E2（交叉審核）只要失敗（暫時性或非暫時性）就中止，避免 Step F 產出不完整 `meeting.md`。

---

## Metadata

- **Engineer Tool**: OpenCode CLI `1.2.6`
- **QA Tool**: Codex CLI `0.104.0`
- **Python**: 3.11（venv）

---

## Key Changes

- `utils/openrouter_http.py`
  - 新增/統一 `post_chat_completions_json()`：Timeout / ConnectionError / 408/429/5xx retry/backoff + jitter；最終拋 `OpenRouterTransientError`。
- `scripts/consultants.py`
  - OpenRouter chat completions 改走 wrapper。
  - fallback chain 僅針對暫時性錯誤（避免非暫時性錯誤下產出不完整報告）。
  - Step E 顧問輸出若解析失敗（含 `error`）即 fail-fast（raise）。
  - Step E2 任一 reviewer 失敗即 fail-fast（raise）。
- `ui/steps.py`
  - Step E / Step E2 捕捉暫時性錯誤與一般錯誤：寫入 `pipeline_state`（`E(error)` / `E2(error)`）並 raise 中止。
  - 若已有落盤 artifact 含 `error`（或 `error_count>0`），要求 Force re-run，避免用壞檔繼續。
- `pages/02_report_generation.py`
  - 一鍵最終中斷時，針對顧問/E2 類錯誤顯示更明確的「請稍後再試」。
- `pages/04_ai_assistant.py`
  - AI 助手 OpenRouter 呼叫改走 wrapper；對一般例外訊息加上長度截斷避免 UI 噴出過大內容。
- `tests/test_openrouter_failfast.py`
  - 新增測試覆蓋 fallback、非暫時性錯誤不 fallback、E2 fail-fast、E2 暫時性錯誤傳遞、Step E 解析錯誤 fail-fast。

---

## QA Status

- **Status**: ✅ PASS
- **QA Notes**:
  - `codex review --uncommitted` exit code `0`，結論未發現明確行為回歸。
  - 本地驗證：
    - `ruff check . --select=E9,F63,F7,F82 --target-version=py311` ✅
    - `ruff format --check scripts/consultants.py scripts/multimodal.py utils/openrouter_http.py tests/test_openrouter_failfast.py` ✅
    - `ruff check scripts/consultants.py scripts/multimodal.py utils/openrouter_http.py tests/test_openrouter_failfast.py --target-version=py311` ✅
    - `pytest -q tests/test_openrouter_failfast.py` ✅

---

## Evidence

- Commit: `10e05c2`
