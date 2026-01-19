"""
檔案用途：OpenRouter 多模態（圖片）呼叫工具
職責：
  - 將圖片編碼為 base64 並建立 OpenRouter / OpenAI 相容的 messages content
  - 呼叫 OpenRouter Chat Completions（支援圖片輸入）
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import requests


def encode_image_to_base64(image_path: str | Path) -> str:
    """
    將圖片檔案編碼為 base64 字串（不含 data: 前綴）。
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"找不到圖片檔案：{path}")
    data = path.read_bytes()
    return base64.b64encode(data).decode("utf-8")


def get_image_media_type(image_path: str | Path) -> str:
    """
    根據圖片副檔名判斷 MIME 類型。
    """
    suffix = Path(image_path).suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".gif":
        return "image/gif"
    if suffix == ".webp":
        return "image/webp"
    raise ValueError(f"不支援的圖片格式：{suffix}")


def create_image_content(image_path: str | Path) -> dict[str, Any]:
    """
    建立 OpenRouter（OpenAI 相容）messages content 的圖片區塊。
    """
    media_type = get_image_media_type(image_path)
    b64 = encode_image_to_base64(image_path)
    return {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}}


def openrouter_multimodal_completion(
    messages: list[dict[str, Any]],
    model: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 1600,
    response_format: str | dict[str, Any] | None = None,
    timeout_s: int = 120,
) -> str:
    """
    多模態 API 呼叫主函式（支援圖片）。

    - messages：OpenAI Chat Completions 格式
    - model：例如 "google/gemini-3.0-pro"
    - response_format：可傳入 "json_object" 或 dict（例如 {"type": "json_object"}）
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    base_url = (
        os.getenv("OPENAI_BASE_URL")
        or os.getenv("OPENAI_API_BASE")
        or "https://openrouter.ai/api/v1"
    )
    url = base_url.rstrip("/") + "/chat/completions"

    if not api_key:
        raise RuntimeError("缺少 OPENAI_API_KEY（或 OPENROUTER_API_KEY）。")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://replit.com"),
        "X-Title": os.getenv("OPENROUTER_APP_NAME", "ivyhouse-meta-weekly-mvp"),
    }

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if response_format is not None:
        if isinstance(response_format, str):
            payload["response_format"] = {"type": response_format}
        else:
            payload["response_format"] = response_format

    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout_s)
    if resp.status_code >= 400:
        raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text}")

    data = resp.json()
    return data["choices"][0]["message"]["content"]
