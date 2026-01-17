"""
檔案用途：LLM 呼叫監控與成本追蹤
職責：
  - 記錄每次 LLM API 呼叫的 token 使用量
  - 計算呼叫成本（基於 OpenRouter 定價）
  - 產出成本報表與統計摘要
  - 支援按 week_id 過濾

使用範例：
    from core.llm_monitor import get_monitor, LLMCall

    monitor = get_monitor()

    # 記錄單次呼叫
    monitor.log_call(LLMCall(
        timestamp=now_iso(),
        model="openai/gpt-5.2",
        prompt_tokens=1500,
        completion_tokens=500,
        total_tokens=2000,
        cost_usd=0.05,
        function="generate_report_insights",
        week_id="2025-W52"
    ))

    # 取得成本摘要
    summary = monitor.get_summary(week_id="2025-W52")
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.config import TAIPEI_TZ


@dataclass
class LLMCall:
    """單次 LLM 呼叫記錄"""

    timestamp: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    function: str  # 呼叫的函式名稱（如 "generate_report_insights"）
    week_id: Optional[str] = None
    extra: Optional[Dict] = None  # 額外資訊（如 step, mode）


class LLMMonitor:
    """LLM 呼叫監控器"""

    def __init__(self, log_file: Path):
        """
        Args:
            log_file: JSONL 格式的 log 檔案路徑（每行一個 JSON）
        """
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_call(self, call: LLMCall) -> None:
        """
        記錄單次 LLM 呼叫

        Args:
            call: LLMCall 實例
        """
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(call), ensure_ascii=False) + "\n")

    def load_calls(self, week_id: Optional[str] = None) -> List[LLMCall]:
        """
        載入所有呼叫記錄（可選按 week_id 過濾）

        Args:
            week_id: 若指定，只回傳該週的記錄

        Returns:
            LLMCall 物件列表
        """
        if not self.log_file.exists():
            return []

        calls: List[LLMCall] = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line.strip())
                call = LLMCall(**data)

                # 過濾條件
                if week_id and call.week_id != week_id:
                    continue

                calls.append(call)

        return calls

    def get_summary(self, week_id: Optional[str] = None) -> Dict:
        """
        取得成本摘要統計

        Args:
            week_id: 若指定，只統計該週

        Returns:
            {
                "total_calls": int,
                "total_tokens": int,
                "total_prompt_tokens": int,
                "total_completion_tokens": int,
                "total_cost_usd": float,
                "calls_by_model": {...},
                "calls_by_function": {...}
            }
        """
        calls = self.load_calls(week_id)

        if not calls:
            return {
                "total_calls": 0,
                "total_tokens": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_cost_usd": 0.0,
                "calls_by_model": {},
                "calls_by_function": {},
            }

        total_tokens = sum(c.total_tokens for c in calls)
        total_prompt_tokens = sum(c.prompt_tokens for c in calls)
        total_completion_tokens = sum(c.completion_tokens for c in calls)
        total_cost = sum(c.cost_usd for c in calls)

        # 按 model 分組
        calls_by_model: Dict[str, Dict] = {}
        for call in calls:
            if call.model not in calls_by_model:
                calls_by_model[call.model] = {"count": 0, "tokens": 0, "cost_usd": 0.0}
            calls_by_model[call.model]["count"] += 1
            calls_by_model[call.model]["tokens"] += call.total_tokens
            calls_by_model[call.model]["cost_usd"] += call.cost_usd

        # 按 function 分組
        calls_by_function: Dict[str, Dict] = {}
        for call in calls:
            if call.function not in calls_by_function:
                calls_by_function[call.function] = {"count": 0, "tokens": 0, "cost_usd": 0.0}
            calls_by_function[call.function]["count"] += 1
            calls_by_function[call.function]["tokens"] += call.total_tokens
            calls_by_function[call.function]["cost_usd"] += call.cost_usd

        return {
            "week_id": week_id,
            "total_calls": len(calls),
            "total_tokens": total_tokens,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_cost_usd": round(total_cost, 4),
            "calls_by_model": calls_by_model,
            "calls_by_function": calls_by_function,
        }


# 全域 monitor 實例
_monitor_instance: Optional[LLMMonitor] = None


def get_monitor() -> LLMMonitor:
    """
    取得全域 LLMMonitor 實例（單例模式）

    Returns:
        LLMMonitor 實例
    """
    global _monitor_instance
    if _monitor_instance is None:
        log_file = Path("logs") / "llm_calls.jsonl"
        _monitor_instance = LLMMonitor(log_file)
    return _monitor_instance


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    估算 LLM 呼叫成本（基於 OpenRouter 定價）

    Args:
        model: 模型名稱（如 "openai/gpt-5.2"）
        prompt_tokens: 輸入 tokens
        completion_tokens: 輸出 tokens

    Returns:
        成本（USD）

    Note:
        定價來源：https://openrouter.ai/models
        此為估算值，實際成本以 OpenRouter 帳單為準
    """
    # 定價表（每 1M tokens 的成本，USD）
    pricing = {
        "openai/gpt-5.2": {"prompt": 10.0, "completion": 30.0},
        "google/gemini-3.0-pro": {"prompt": 3.5, "completion": 10.5},
        "anthropic/claude-opus-4.5": {"prompt": 15.0, "completion": 75.0},
        # Fallback
        "default": {"prompt": 5.0, "completion": 15.0},
    }

    model_pricing = pricing.get(model, pricing["default"])

    prompt_cost = (prompt_tokens / 1_000_000) * model_pricing["prompt"]
    completion_cost = (completion_tokens / 1_000_000) * model_pricing["completion"]

    return round(prompt_cost + completion_cost, 6)
