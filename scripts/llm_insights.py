"""
檔案用途：Meta 週報分析系統 - LLM 洞察生成模組
職責：
  - 呼叫 OpenRouter API 產生 Meta 廣告成效洞察
  - 將 report_summary 轉換為顧問級 report_insights
  - 提供 JSON 格式的結構化洞察輸出
  - 整合 LLM 呼叫監控 (core.llm_monitor)

注意事項：
  - 此模組「只做判讀」不做數據計算，禁止重算 ROAS/CPC/CTR
  - 輸出必須符合 insights.v1 schema
"""

import json
import os
from typing import Any, Dict, Optional, Tuple, Union

import requests

# LLM Monitor (新增)
from core.llm_monitor import get_monitor, LLMCall, estimate_cost
from utils import now_iso

llm_monitor = get_monitor()


def _openrouter_chat_completion(
    messages,
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 8000,
) -> Tuple[str, Dict[str, int]]:
    """
    呼叫 OpenRouter Chat Completions API。

    Returns:
        (content, usage) 其中 usage 包含 prompt_tokens / completion_tokens / total_tokens
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE") or "https://openrouter.ai/api/v1"
    url = base_url.rstrip("/") + "/chat/completions"

    if not api_key:
        raise RuntimeError("缺少 OPENAI_API_KEY（或 OPENROUTER_API_KEY），請在 Replit Secrets 或環境變數中設定。")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # OpenRouter 建議帶的標頭（不帶也能跑，但帶著更穩）
        "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://replit.com"),
        "X-Title": os.getenv("OPENROUTER_APP_NAME", "ivyhouse-meta-weekly-mvp"),
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        # 移除 response_format 以避免與 OpenRouter Web Search 衝突
        # Prompt 中已明確要求 JSON 格式輸出
    }


    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=90)
    if resp.status_code >= 400:
        raise RuntimeError(f"OpenRouter 錯誤 {resp.status_code}: {resp.text}")

    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"OpenRouter returned non-JSON response: {resp.text[:200]}")

    if "error" in data:
        raise RuntimeError(f"OpenRouter API Error: {json.dumps(data['error'])}")

    usage = data.get("usage", {})
    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens) or 0)
    
    if not data.get("choices"):
        raise RuntimeError(f"OpenRouter returned no choices. Model: {model}. Response: {json.dumps(data)}")

    content = data["choices"][0]["message"].get("content")
    if content is None:
        content = ""
    return (str(content), {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    })


def _try_parse_json(s: str) -> Dict[str, Any]:
    if not s:
        return {"error": "Empty response from LLM", "raw_content": "", "insights_version": "error", "executive_summary": ["Error: Empty response"]}
    s = s.strip()
    # 保險：避免模型加上多餘文字
    first = s.find("{")
    last = s.rfind("}")
    if first != -1 and last != -1 and last > first:
        s = s[first:last + 1]
    
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        return {
            "error": f"JSON parse error: {str(e)}",
            "raw_content": s[:200] + "..." if len(s) > 200 else s,
            "insights_version": "error",
            "executive_summary": [f"Error parsing JSON: {str(e)}"]
        }


def generate_report_insights(
    report_summary: Dict[str, Any],
    model: Optional[str] = None,
    return_usage: bool = False,
    version_fp: Optional[str] = None,
) -> Union[Dict[str, Any], Tuple[Dict[str, Any], Dict[str, int]]]:
    """
    只做「洞察解讀」，不算數字。輸出必須是 JSON object（無 code fence）。
    """
    model = model or os.getenv("MODEL_INSIGHTS") or "openai/gpt-4o-mini"

    # 將輸入控制在「足夠判讀」的大小
    compact_input = {
        "schema_version": report_summary.get("schema_version"),
        "week_id": report_summary.get("week_id"),
        "date_range": report_summary.get("date_range"),
        "kpi": report_summary.get("kpi", {}),
        "tables": report_summary.get("tables", {}),
        "missing_data": report_summary.get("missing_data", {}),
        "manual_inputs": (report_summary.get("_context") or {}).get("manual_inputs") or {},
    }
    skills_ctx = (report_summary.get("_context") or {}).get("skills") or {}
    if isinstance(skills_ctx, dict) and skills_ctx:
        compact_input["skills"] = skills_ctx

    system = (
        "你是艾薇手工坊的高階成效顧問（Meta 投放週會用）。"
        "你只能根據輸入 JSON 做洞察解讀與行動建議；"
        "禁止重新計算或改寫任何數字（包含 ROAS/CPA/CTR 等），只能引用輸入中的數字。"
        "輸出必須是『單一 JSON object』，不要加任何多餘文字、不要用```。"
        "語言用繁體中文，結論務必可直接在週會派工。"
    )

    user = (
        "請根據以下 report_summary（JSON）產出 report_insights（JSON）。\n\n"
        "輸出 JSON 欄位要求：\n"
        "1) insights_version: 固定 'insights.v1'\n"
        "2) week_id, date_range: 直接沿用輸入\n"
        "3) executive_summary: 3-5 條一句話結論（關鍵數字只在此處完整列出，後續欄位請引用「見重點 #N」）\n"
        "4) what_worked: 3-5 條（指出 top adsets/ads 的共同特徵，避免臆測）\n"
        "5) what_didnt: 3-5 條（指出 worst adsets/ads 的共同特徵，避免臆測）\n"
        "6) diagnostics: traffic/conversion/creative 三段，每段 1-2 句，必須包含 ROAS/CTR/CPA/頻次等核心指標；若輸入未提供某指標，請明確標示「未提供」，禁止臆測或重算。\n"
        "7) actions: 固定 6 條可執行任務，每條用模板：{ owner, task(一句), deliverable(一句), why(半句), kpi(一句), stoploss(一句) }\n"
        "8) data_issues: Top 3-5 個（只列會直接影響決策的問題，勿重複 executive_summary）\n"
        "9) open_questions: 3-5 條（勿與 data_issues 重複）\n\n10) strategy_snapshot: 若 manual_inputs 提供 buying_type/optimization_goal/billing_event，請在 diagnostics 或 executive_summary 明確列出（未填則寫『未填』），且不得將其列為 data_issues。\n\n"
        "報告輸入：\n"
        f"{json.dumps(compact_input, ensure_ascii=False)}"
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    def _add_usage(a: Dict[str, int], b: Dict[str, int]) -> Dict[str, int]:
        return {
            "prompt_tokens": int(a.get("prompt_tokens", 0)) + int(b.get("prompt_tokens", 0)),
            "completion_tokens": int(a.get("completion_tokens", 0)) + int(b.get("completion_tokens", 0)),
            "total_tokens": int(a.get("total_tokens", 0)) + int(b.get("total_tokens", 0)),
        }

    content, usage_main = _openrouter_chat_completion(messages, model=model)
    out = _try_parse_json(content)
    total_usage = usage_main

    # 若解析失敗（含 error key），做一次修復重試，並累計 token usage（避免低估成本）
    if isinstance(out, dict) and out.get("error"):
        repair_messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "你上一次輸出不是合法 JSON。請只輸出『單一 JSON object』，不要任何多餘字元。"},
            {"role": "user", "content": content},
        ]
        content2, usage_repair = _openrouter_chat_completion(
            repair_messages,
            model=model,
            temperature=0.0,
            max_tokens=8000,
        )
        total_usage = _add_usage(total_usage, usage_repair)
        out = _try_parse_json(content2)

    # 最小保險：補必要欄位
    out.setdefault("insights_version", "insights.v1")
    out.setdefault("week_id", report_summary.get("week_id"))
    out.setdefault("date_range", report_summary.get("date_range"))

    # 統一在此記錄一次 Step C token usage（包含 repair）
    try:
        week_id = str(report_summary.get("week_id") or "").strip() or None
        llm_monitor.log_call(
            LLMCall(
                timestamp=now_iso(),
                model=model,
                prompt_tokens=int(total_usage.get("prompt_tokens", 0) or 0),
                completion_tokens=int(total_usage.get("completion_tokens", 0) or 0),
                total_tokens=int(total_usage.get("total_tokens", 0) or 0),
                cost_usd=estimate_cost(
                    model,
                    int(total_usage.get("prompt_tokens", 0) or 0),
                    int(total_usage.get("completion_tokens", 0) or 0),
                ),
                function="generate_report_insights",
                week_id=week_id,
                extra={"step": "C", "version_fp": version_fp} if version_fp else {"step": "C"},
            )
        )
    except Exception:
        # log 失敗不應阻斷主流程
        pass

    if return_usage:
        return (out, total_usage)
    return out


