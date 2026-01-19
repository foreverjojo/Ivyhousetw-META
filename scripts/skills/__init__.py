"""
Ivy House Meta Ad Analyzer - Agent Skills Package
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def now_taipei_iso() -> str:
    """回傳 Asia/Taipei 的 ISO8601 timestamp（若不可用則回退為本機時區）"""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Taipei")).isoformat()
    except Exception:
        return datetime.now().astimezone().isoformat()


def build_standard_skill_contract(
    *,
    schema_version: str,
    inputs: dict[str, Any],
    thresholds: dict[str, Any],
    results: dict[str, Any],
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """
    統一 Skill 輸出合約（以相容性為優先）：
    - 保留既有欄位（由呼叫者 merge 回原結果）
    - 僅補上通用欄位，方便後續 schema 驗證與 QA 回溯
    """
    return {
        "schema_version": schema_version,
        "generated_at": now_taipei_iso(),
        "inputs": inputs,
        "thresholds": thresholds,
        "results": results,
        "warnings": warnings or [],
    }
