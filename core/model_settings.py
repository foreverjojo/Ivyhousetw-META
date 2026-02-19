"""
檔案用途：模型設定單一權威來源（Single Source of Truth）
職責：
  - 集中管理模型 role、環境變數鍵、預設值、可選清單、legacy 映射
    - 集中管理 *_FALLBACK 設定（主模型未設定時作為次要預設）
  - 提供統一讀寫 API，避免各模組分散讀取 os.getenv
"""

from __future__ import annotations

import os
from typing import Literal

ModelRole = Literal[
    "insights",
    "consultant_a",
    "consultant_b",
    "consultant_c",
    "moderator",
]


MODEL_ENV_VARS: dict[ModelRole, str] = {
    "insights": "MODEL_INSIGHTS",
    "consultant_a": "MODEL_CONSULTANT_A",
    "consultant_b": "MODEL_CONSULTANT_B",
    "consultant_c": "MODEL_CONSULTANT_C",
    "moderator": "MODEL_MODERATOR",
}

MODEL_FALLBACK_ENV_VARS: dict[ModelRole, str] = {
    "insights": "MODEL_INSIGHTS_FALLBACK",
    "consultant_a": "MODEL_CONSULTANT_A_FALLBACK",
    "consultant_b": "MODEL_CONSULTANT_B_FALLBACK",
    "consultant_c": "MODEL_CONSULTANT_C_FALLBACK",
    "moderator": "MODEL_MODERATOR_FALLBACK",
}

MODEL_BUILTIN_DEFAULTS: dict[ModelRole, str] = {
    "insights": "openai/gpt-5-mini",
    "consultant_a": "openai/gpt-5.2",
    "consultant_b": "google/gemini-3-flash-preview",
    "consultant_c": "anthropic/claude-sonnet-4.5",
    "moderator": "openai/gpt-5.2-pro",
}

# 定義 UI 可選模型（用於快速切換）
AVAILABLE_MODELS: dict[str, str] = {
    "GPT-5 Mini": "openai/gpt-5-mini",
    "GPT-5.2 Chat": "openai/gpt-5.2-chat",
    "GPT-5.2": "openai/gpt-5.2",
    "GPT-5.2 Pro": "openai/gpt-5.2-pro",
    "Claude 4.5 Sonnet": "anthropic/claude-sonnet-4.5",
    "Claude 4.6 Opus": "anthropic/claude-opus-4.6",
    "Gemini 3 Pro Preview": "google/gemini-3-pro-preview",
    "Gemini 3 Flash Preview": "google/gemini-3-flash-preview",
}

# 舊模型 ID 相容遷移
LEGACY_MODEL_MAP: dict[str, str] = {
    "google/gemini-pro-1.5": "google/gemini-3-pro-preview",
    "google/gemini-flash-1.5": "google/gemini-3-flash-preview",
}


def normalize_model_id(model_id: str) -> str:
    """將模型 ID 做標準化（包含 legacy 映射）。"""
    normalized = (model_id or "").strip()
    if not normalized:
        return ""
    return LEGACY_MODEL_MAP.get(normalized, normalized)


def get_default_model(role: ModelRole) -> str:
    """取得指定角色的預設模型（優先 *_FALLBACK，其次內建預設）。"""
    fallback_env_var = MODEL_FALLBACK_ENV_VARS[role]
    fallback_value = normalize_model_id(os.getenv(fallback_env_var, ""))
    if fallback_value:
        return fallback_value
    return MODEL_BUILTIN_DEFAULTS[role]


def get_model(role: ModelRole) -> str:
    """取得目前生效模型（優先 MODEL_*，其次 MODEL_*_FALLBACK，最後內建預設）。"""
    env_var = MODEL_ENV_VARS[role]
    env_value = normalize_model_id(os.getenv(env_var, ""))
    if env_value:
        return env_value
    return get_default_model(role)


def get_fallback_model(role: ModelRole, primary_model: str | None = None) -> str | None:
    """取得重試用 fallback model（排除與 primary 相同者）。"""
    primary = normalize_model_id(primary_model or "")

    fallback_env_var = MODEL_FALLBACK_ENV_VARS[role]
    fallback_from_env = normalize_model_id(os.getenv(fallback_env_var, ""))
    if fallback_from_env and fallback_from_env != primary:
        return fallback_from_env

    builtin_default = normalize_model_id(MODEL_BUILTIN_DEFAULTS[role])
    if builtin_default and builtin_default != primary:
        return builtin_default

    return None


def get_retry_model_chain(role: ModelRole, primary_model: str | None = None) -> list[str]:
    """取得 API 失敗重試的模型順序（primary -> fallback）。"""
    primary = normalize_model_id(primary_model or "") or get_model(role)
    chain = [primary]

    fallback = get_fallback_model(role, primary_model=primary)
    if fallback and fallback not in chain:
        chain.append(fallback)

    return chain


def set_model(role: ModelRole, model_id: str) -> str:
    """寫入模型到環境變數並回傳最終生效值。"""
    env_var = MODEL_ENV_VARS[role]
    resolved = normalize_model_id(model_id)
    os.environ[env_var] = resolved
    return resolved
