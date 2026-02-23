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
from typing import Any

import requests

# LLM Monitor (新增)
from core.llm_monitor import LLMCall, estimate_cost, get_monitor
from core.model_settings import get_model, get_retry_model_chain
from utils import now_iso

llm_monitor = get_monitor()


def _to_nonempty_str_list(v: Any) -> list[str]:
    """Coerce common LLM outputs into a list[str] with non-empty items."""
    if isinstance(v, list):
        out: list[str] = []
        for it in v:
            if it is None:
                continue
            s = str(it).strip()
            if s:
                out.append(s)
        return out

    if isinstance(v, str):
        s = v.strip()
        return [s] if s else []

    return []


def is_report_insights_renderable(report_insights: Any) -> bool:
    """Minimal contract for meeting/UI rendering.

    We treat report_insights as renderable iff it has a non-empty `executive_summary` list.
    """
    if not isinstance(report_insights, dict):
        return False
    executive = _to_nonempty_str_list(report_insights.get("executive_summary"))
    return len(executive) > 0


def _insights_v1_issues(report_insights: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(report_insights, dict):
        return ["root: not an object"]

    executive = report_insights.get("executive_summary")
    if not isinstance(executive, list):
        issues.append("executive_summary: expected array")
    elif not _to_nonempty_str_list(executive):
        issues.append("executive_summary: empty")

    return issues


def _normalize_insights_v1(
    report_summary: dict[str, Any],
    report_insights: Any,
    *,
    fallback_reason: str | None = None,
) -> dict[str, Any]:
    """Normalize and guarantee minimal fields used by the app.

    Important: This is a deterministic safety net. It does NOT recalc KPIs.
    """
    out: dict[str, Any] = dict(report_insights) if isinstance(report_insights, dict) else {}

    out.setdefault("insights_version", "insights.v1")
    out.setdefault("week_id", report_summary.get("week_id"))
    out.setdefault("date_range", report_summary.get("date_range"))

    executive = _to_nonempty_str_list(out.get("executive_summary"))
    if not executive:
        reason_parts: list[str] = []
        if fallback_reason:
            reason_parts.append(fallback_reason)
        for key in ["message", "error", "code", "status"]:
            v = out.get(key)
            if isinstance(v, str) and v.strip():
                reason_parts.append(f"{key}={v.strip()}")
        reason = "｜".join(reason_parts) if reason_parts else "洞察內容缺失或格式不符"
        out["executive_summary"] = [f"⚠️ Step C 洞察產物異常：{reason}（建議重新執行 Step C）"]
    else:
        out["executive_summary"] = executive

    # Keep other fields present as lists/dicts when possible (best-effort)
    out.setdefault("what_worked", [])
    out.setdefault("what_didnt", [])
    out.setdefault("diagnostics", {})
    out.setdefault("actions", [])
    out.setdefault("data_issues", [])
    out.setdefault("open_questions", [])

    return out


def _openrouter_chat_completion(
    messages,
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 8000,
) -> tuple[str, dict[str, int]]:
    """
    呼叫 OpenRouter Chat Completions API。

    Returns:
        (content, usage) 其中 usage 包含 prompt_tokens / completion_tokens / total_tokens
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    base_url = (
        os.getenv("OPENAI_BASE_URL")
        or os.getenv("OPENAI_API_BASE")
        or "https://openrouter.ai/api/v1"
    )
    url = base_url.rstrip("/") + "/chat/completions"

    if not api_key:
        raise RuntimeError(
            "缺少 OPENAI_API_KEY（或 OPENROUTER_API_KEY），請在 Replit Secrets 或環境變數中設定。"
        )

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
    except Exception as err:
        raise RuntimeError(f"OpenRouter returned non-JSON response: {resp.text[:200]}") from err

    if "error" in data:
        raise RuntimeError(f"OpenRouter API Error: {json.dumps(data['error'])}")

    usage = data.get("usage", {})
    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens) or 0)

    if not data.get("choices"):
        raise RuntimeError(
            f"OpenRouter returned no choices. Model: {model}. Response: {json.dumps(data)}"
        )

    content = data["choices"][0]["message"].get("content")
    if content is None:
        content = ""
    return (
        str(content),
        {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
    )


def _openrouter_chat_completion_with_fallback(
    messages,
    *,
    model: str,
    role: str,
    temperature: float = 0.2,
    max_tokens: int = 8000,
) -> tuple[str, dict[str, int], str, bool]:
    """API 失敗時以 fallback model 重試一次。"""
    retry_chain = get_retry_model_chain(role, primary_model=model)
    errors: list[str] = []

    for idx, candidate in enumerate(retry_chain):
        try:
            content, usage = _openrouter_chat_completion(
                messages,
                model=candidate,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return content, usage, candidate, idx > 0
        except Exception as err:
            errors.append(f"{candidate}: {err}")

    raise RuntimeError("; ".join(errors))


def _try_parse_json(s: str) -> dict[str, Any]:
    if not s:
        return {
            "error": "Empty response from LLM",
            "raw_content": "",
            "insights_version": "error",
            "executive_summary": ["Error: Empty response"],
        }
    s = s.strip()
    # 保險：避免模型加上多餘文字
    first = s.find("{")
    last = s.rfind("}")
    if first != -1 and last != -1 and last > first:
        s = s[first : last + 1]

    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        return {
            "error": f"JSON parse error: {str(e)}",
            "raw_content": s[:200] + "..." if len(s) > 200 else s,
            "insights_version": "error",
            "executive_summary": [f"Error parsing JSON: {str(e)}"],
        }


def generate_report_insights(
    report_summary: dict[str, Any],
    model: str | None = None,
    return_usage: bool = False,
    version_fp: str | None = None,
) -> dict[str, Any] | tuple[dict[str, Any], dict[str, int]]:
    """
    只做「洞察解讀」，不算數字。輸出必須是 JSON object（無 code fence）。
    """
    configured_model = model or get_model("insights")

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

    def _add_usage(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
        return {
            "prompt_tokens": int(a.get("prompt_tokens", 0)) + int(b.get("prompt_tokens", 0)),
            "completion_tokens": int(a.get("completion_tokens", 0))
            + int(b.get("completion_tokens", 0)),
            "total_tokens": int(a.get("total_tokens", 0)) + int(b.get("total_tokens", 0)),
        }

    content, usage_main, active_model, retried_with_fallback_main = (
        _openrouter_chat_completion_with_fallback(
            messages,
            model=configured_model,
            role="insights",
        )
    )
    out = _try_parse_json(content)
    total_usage = usage_main
    retried_with_fallback_repair = False
    schema_repair_attempted = False

    # 若解析失敗（含 error key），做一次修復重試，並累計 token usage（避免低估成本）
    if isinstance(out, dict) and out.get("error"):
        repair_messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": "你上一次輸出不是合法 JSON。請只輸出『單一 JSON object』，不要任何多餘字元。",
            },
            {"role": "user", "content": content},
        ]
        content2, usage_repair, repair_model, retried_with_fallback_repair = (
            _openrouter_chat_completion_with_fallback(
                repair_messages,
                model=active_model,
                role="insights",
                temperature=0.0,
                max_tokens=8000,
            )
        )
        active_model = repair_model
        total_usage = _add_usage(total_usage, usage_repair)
        out = _try_parse_json(content2)

    # 若 JSON 可解析但結構不符（例如回傳 error payload JSON），做一次 schema repair 重試。
    if not is_report_insights_renderable(out):
        schema_repair_attempted = True
        issues = _insights_v1_issues(out)

        # 避免把過長內容塞回 repair prompt 造成 context 超限
        if isinstance(out, dict):
            prev_snippet = json.dumps(out, ensure_ascii=False)
        else:
            prev_snippet = str(out)
        prev_snippet = (
            prev_snippet
            if len(prev_snippet) <= 12000
            else (prev_snippet[:12000] + "\n...[TRUNCATED]...")
        )
        repair_messages2 = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    "你上一次輸出雖然可被 JSON.parse，但結構不符合 insights.v1 欄位要求（"
                    + ", ".join(issues)
                    + "）。"
                    "請重新輸出符合欄位要求的『單一 JSON object』，禁止輸出 error/status 類型回應。"
                    "至少要包含 executive_summary（3-5 條）與 actions（6 條）。"
                    "禁止輸出```或多餘文字。"
                ),
            },
            {"role": "user", "content": "你上一次的輸出（供修正）：\n" + prev_snippet},
        ]

        try:
            content3, usage_repair2, repair_model2, retried2 = (
                _openrouter_chat_completion_with_fallback(
                    repair_messages2,
                    model=active_model,
                    role="insights",
                    temperature=0.0,
                    max_tokens=8000,
                )
            )
            active_model = repair_model2
            retried_with_fallback_repair = retried_with_fallback_repair or retried2
            total_usage = _add_usage(total_usage, usage_repair2)
            out = _try_parse_json(content3)
        except Exception as e:
            out = {
                "error": f"schema repair failed: {type(e).__name__}: {str(e)[:200]}",
                "raw_content": prev_snippet,
            }

    # 最終保底：確保 meeting/UI 至少可渲染 executive_summary，避免顯示（待補）
    out = _normalize_insights_v1(
        report_summary,
        out,
        fallback_reason=("已嘗試結構修復" if schema_repair_attempted else None),
    )

    # 統一在此記錄一次 Step C token usage（包含 repair）
    try:
        week_id = str(report_summary.get("week_id") or "").strip() or None
        llm_monitor.log_call(
            LLMCall(
                timestamp=now_iso(),
                model=active_model,
                prompt_tokens=int(total_usage.get("prompt_tokens", 0) or 0),
                completion_tokens=int(total_usage.get("completion_tokens", 0) or 0),
                total_tokens=int(total_usage.get("total_tokens", 0) or 0),
                cost_usd=estimate_cost(
                    active_model,
                    int(total_usage.get("prompt_tokens", 0) or 0),
                    int(total_usage.get("completion_tokens", 0) or 0),
                ),
                function="generate_report_insights",
                week_id=week_id,
                extra=(
                    {
                        "step": "C",
                        "version_fp": version_fp,
                        "configured_model": configured_model,
                        "used_model": active_model,
                        "fallback_retry_main": retried_with_fallback_main,
                        "fallback_retry_repair": retried_with_fallback_repair,
                        "schema_repair_attempted": schema_repair_attempted,
                    }
                    if version_fp
                    else {
                        "step": "C",
                        "configured_model": configured_model,
                        "used_model": active_model,
                        "fallback_retry_main": retried_with_fallback_main,
                        "fallback_retry_repair": retried_with_fallback_repair,
                        "schema_repair_attempted": schema_repair_attempted,
                    }
                ),
            )
        )
    except Exception:
        # log 失敗不應阻斷主流程
        pass

    if return_usage:
        return (out, total_usage)
    return out
