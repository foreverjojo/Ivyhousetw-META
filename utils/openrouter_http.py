"""
檔案用途：OpenRouter HTTP 呼叫工具
職責：
  - 統一處理 requests 呼叫、timeout、retry/backoff
  - 提供可重用的 Chat Completions POST 工具

注意事項：
  - 不記錄/輸出任何 API key
  - 只處理傳輸層穩定性，不負責內容解析/結構修復
"""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class OpenRouterRetryConfig:
    timeout_s: float = 120.0
    max_retries: int = 2
    backoff_base_s: float = 1.2
    backoff_max_s: float = 8.0


class OpenRouterTransientError(RuntimeError):
    """OpenRouter 或網路暫時性問題（建議稍後重試）。"""


def _env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    try:
        return float(v)
    except Exception:
        return default


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    try:
        return int(v)
    except Exception:
        return default


def get_default_retry_config() -> OpenRouterRetryConfig:
    return OpenRouterRetryConfig(
        timeout_s=_env_float("OPENROUTER_TIMEOUT_S", 120.0),
        max_retries=_env_int("OPENROUTER_MAX_RETRIES", 2),
        backoff_base_s=_env_float("OPENROUTER_BACKOFF_BASE_S", 1.2),
        backoff_max_s=_env_float("OPENROUTER_BACKOFF_MAX_S", 8.0),
    )


def post_chat_completions_json(
    *,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    retry: OpenRouterRetryConfig | None = None,
) -> dict[str, Any]:
    """POST OpenRouter `/chat/completions` 並回傳 JSON dict。

    - 針對 Timeout / ConnectionError 與部分 5xx/429 做 retry。
    - 最終失敗會 raise OpenRouterTransientError（方便上層辨識並提示稍後再試）。
    """

    cfg = retry or get_default_retry_config()
    retry_statuses = {408, 425, 429, 500, 502, 503, 504}
    last_err: Exception | None = None

    for attempt in range(cfg.max_retries + 1):
        try:
            resp = requests.post(
                url,
                headers=headers,
                data=json.dumps(payload),
                timeout=cfg.timeout_s,
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as err:
            last_err = err
            if attempt < cfg.max_retries:
                sleep_s = min(cfg.backoff_max_s, cfg.backoff_base_s * (2**attempt))
                sleep_s += random.uniform(0, 0.4)
                time.sleep(sleep_s)
                continue
            raise OpenRouterTransientError(
                f"OpenRouter 連線逾時或中斷（timeout={cfg.timeout_s}s，已重試 {cfg.max_retries} 次），請稍後再試。"
            ) from err

        if resp.status_code in retry_statuses:
            if attempt < cfg.max_retries:
                sleep_s = min(cfg.backoff_max_s, cfg.backoff_base_s * (2**attempt))
                sleep_s += random.uniform(0, 0.4)
                time.sleep(sleep_s)
                continue
            raise OpenRouterTransientError(
                f"OpenRouter 暫時性錯誤 HTTP {resp.status_code}（已重試 {cfg.max_retries} 次），請稍後再試。"
            )

        if resp.status_code >= 400:
            raise RuntimeError(f"OpenRouter 錯誤 {resp.status_code}: {resp.text}")

        try:
            data = resp.json()
        except Exception as err:
            raise RuntimeError(f"OpenRouter 回傳非 JSON（前 200 字）：{resp.text[:200]}") from err

        if "error" in data:
            # 若 error payload 沒有明確可重試訊號，就當作一般錯誤交給上層處理
            raise RuntimeError(f"OpenRouter API Error: {json.dumps(data['error'])}")

        return data

    # 理論上不會走到這裡
    if last_err is not None:
        raise OpenRouterTransientError("OpenRouter 呼叫失敗，請稍後再試。") from last_err
    raise OpenRouterTransientError("OpenRouter 呼叫失敗，請稍後再試。")
