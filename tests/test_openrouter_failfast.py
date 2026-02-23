"""\
檔案用途：Idx-039 測試 - OpenRouter retry wrapper 與 fail-fast 行為
職責：
  - 驗證 scripts.consultants 的 fallback chain 只在暫時性錯誤才會嘗試 backup model
  - 驗證 E2 交叉審核不再 graceful degradation（任一 reviewer 失敗即中止）

注意：
  - 測試不得真的打外部網路；以 monkeypatch requests.post 模擬。
"""

from __future__ import annotations

import json
from typing import Any

import pytest
import requests

from scripts import consultants
from utils.openrouter_http import OpenRouterTransientError


class _DummyResponse:
    def __init__(self, *, status_code: int, payload: dict[str, Any] | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict[str, Any]:
        return self._payload


def test_fallback_only_on_transient_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setenv("OPENROUTER_MAX_RETRIES", "0")

    attempted_models: list[str] = []

    def fake_post(url: str, *, headers: dict[str, str], data: str, timeout: float):
        payload = json.loads(data)
        model = str(payload.get("model"))
        attempted_models.append(model)

        if model == "primary/model":
            raise requests.exceptions.Timeout("read timeout")

        return _DummyResponse(
            status_code=200,
            payload={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            },
        )

    # 讓 fallback chain 至少包含 primary + backup
    monkeypatch.setattr(
        consultants,
        "get_retry_model_chain",
        lambda role, primary_model: [primary_model, "backup/model"],
    )

    import utils.openrouter_http as openrouter_http

    monkeypatch.setattr(openrouter_http.requests, "post", fake_post)

    content, usage, used_model, retried = consultants._openrouter_chat_completion_with_fallback(
        messages=[{"role": "user", "content": "hi"}],
        model="primary/model",
        role="consultant_a",
    )

    assert content == "ok"
    assert used_model == "backup/model"
    assert retried is True
    assert attempted_models == ["primary/model", "backup/model"]
    assert usage["total_tokens"] == 3


def test_non_transient_error_does_not_try_backup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setenv("OPENROUTER_MAX_RETRIES", "0")

    attempted_models: list[str] = []

    def fake_post(url: str, *, headers: dict[str, str], data: str, timeout: float):
        payload = json.loads(data)
        model = str(payload.get("model"))
        attempted_models.append(model)
        return _DummyResponse(status_code=400, text="bad request")

    monkeypatch.setattr(
        consultants,
        "get_retry_model_chain",
        lambda role, primary_model: [primary_model, "backup/model"],
    )

    import utils.openrouter_http as openrouter_http

    monkeypatch.setattr(openrouter_http.requests, "post", fake_post)

    with pytest.raises(RuntimeError):
        consultants._openrouter_chat_completion_with_fallback(
            messages=[{"role": "user", "content": "hi"}],
            model="primary/model",
            role="consultant_a",
        )

    assert attempted_models == ["primary/model"]


def test_e2_any_reviewer_error_is_fatal(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_single_cross_review(**kwargs: Any) -> dict[str, Any]:
        return {"error": "boom"}

    monkeypatch.setattr(consultants, "_single_cross_review", fake_single_cross_review)

    with pytest.raises(RuntimeError):
        consultants.generate_consultant_cross_reviews(
            report_summary={"week_id": "W1", "date_range": "2026-01-01~2026-01-07"},
            report_insights={},
            consultant_notes={},
        )


def test_e2_transient_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_single_cross_review(**kwargs: Any):
        raise OpenRouterTransientError("timeout")

    monkeypatch.setattr(consultants, "_single_cross_review", fake_single_cross_review)

    with pytest.raises(OpenRouterTransientError):
        consultants.generate_consultant_cross_reviews(
            report_summary={"week_id": "W1", "date_range": "2026-01-01~2026-01-07"},
            report_insights={},
            consultant_notes={},
        )


def test_step_e_consultant_error_is_fatal(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = 0

    def fake_openrouter(*args: Any, **kwargs: Any):
        nonlocal call_count
        call_count += 1
        return "{}", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "m", False

    def fake_parse_or_repair(*args: Any, **kwargs: Any):
        return {"error": "JSON parse error: boom"}, {"total_tokens": 0}, "m", False

    monkeypatch.setattr(consultants, "_openrouter_chat_completion_with_fallback", fake_openrouter)
    monkeypatch.setattr(consultants, "_parse_or_repair", fake_parse_or_repair)

    with pytest.raises(RuntimeError):
        consultants.generate_consultant_notes(
            report_summary={
                "week_id": "W1",
                "date_range": "2026-01-01~2026-01-07",
                "kpi": {"meta": {}, "web": {}},
                "tables": {},
                "missing_data": {},
            },
            report_insights={"executive_summary": [], "actions": []},
        )

    # fail-fast: 只要第一位顧問就 error，就不再繼續呼叫後續顧問
    assert call_count == 1
