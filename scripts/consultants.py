"""
scripts/consultants.py
=====================================
用途：三顧問系統核心模組
職責：
  - 透過 OpenRouter API 呼叫三位 AI 顧問
  - 顧問 A (成效): GPT-5.2 - 數據分析與擴量建議
  - 顧問 B (效率): Gemini 3.0 Pro - 風險控管與效率優化
  - 顧問 C (創意): Claude 4.5 - 素材與轉換策略
=====================================
"""

import json
import os
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any

import requests

from core.llm_monitor import LLMCall, estimate_cost, get_monitor
from core.model_settings import ModelRole, get_model, get_retry_model_chain
from scripts.media_scanner import get_top_images, scan_media_assets
from scripts.multimodal import create_image_content, openrouter_multimodal_completion
from utils import now_iso

llm_monitor = get_monitor()


def _openrouter_chat_completion(
    messages, model: str, temperature: float = 0.2, max_tokens: int = 8000
) -> tuple[str, dict[str, int]]:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    base_url = (
        os.getenv("OPENAI_BASE_URL")
        or os.getenv("OPENAI_API_BASE")
        or "https://openrouter.ai/api/v1"
    )
    url = base_url.rstrip("/") + "/chat/completions"

    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY (or OPENROUTER_API_KEY).")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://replit.com"),
        "X-Title": os.getenv("OPENROUTER_APP_NAME", "ivyhouse-meta-weekly-mvp"),
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        # 移除 response_format 以避免與 OpenRouter Web Search 衝突
    }

    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
    if resp.status_code >= 400:
        raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text}")

    try:
        data = resp.json()
    except Exception as err:
        raise RuntimeError(f"OpenRouter returned non-JSON response: {resp.text[:200]}") from err

    if "error" in data:
        raise RuntimeError(f"OpenRouter API Error: {json.dumps(data['error'])}")

    if not data.get("choices"):
        raise RuntimeError(
            f"OpenRouter returned no choices. Model: {model}. Response: {json.dumps(data)}"
        )

    content = data["choices"][0]["message"].get("content")
    if content is None:
        content = ""

    usage = data.get("usage", {}) or {}
    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens) or 0)

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
        return {"error": "Empty response from LLM", "raw_content": ""}
    s = s.strip()
    first, last = s.find("{"), s.rfind("}")
    if first != -1 and last != -1 and last > first:
        s = s[first : last + 1]

    try:
        # 使用 raw_decode 容忍「多個 JSON object 串接」或尾端雜訊（常見於 LLM 輸出）
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(s)
        return obj
    except Exception as e:
        return {
            "error": f"JSON parse error: {str(e)}",
            "raw_content": s[:4000] + "..." if len(s) > 4000 else s,
        }


def _days_in_range(date_range: str) -> int:
    try:
        a, b = date_range.split("~")
        da = datetime.fromisoformat(a)
        db = datetime.fromisoformat(b)
        return max(1, (db - da).days + 1)
    except Exception:
        return 1


def _compact_inputs(
    report_summary: dict[str, Any], report_insights: dict[str, Any]
) -> dict[str, Any]:
    meta = report_summary.get("kpi", {}).get("meta", {})
    web = report_summary.get("kpi", {}).get("web", {})
    date_range = report_summary.get("date_range", "")
    days = _days_in_range(date_range)
    spend = float(meta.get("spend_twd") or 0)
    avg_daily_spend = round(spend / days, 2) if days > 0 else 0.0

    out = {
        "week_id": report_summary.get("week_id"),
        "date_range": date_range,
        "meta_kpi": meta,
        "web_kpi": web,
        "tables": report_summary.get("tables", {}),
        "missing_data": report_summary.get("missing_data", {}),
        "insights_executive_summary": report_insights.get("executive_summary", []),
        "insights_actions": report_insights.get("actions", []),
        "meta_avg_daily_spend_twd_calc": avg_daily_spend,
        "budget_definition": {
            "overall_daily_budget_meaning": "本週/本區間『全帳戶平均每日花費節奏』= Meta Spend ÷ 天數（不是單一 adset）",
            "adset_budget_actions": "若要落地執行，需列出要加碼/降碼的 adset/ads（依 tables 的 top/bottom）",
        },
        "hard_rules": {
            "no_recalc_numbers": True,
            "language": "zh-TW",
            "must_output_valid_json": True,
        },
    }
    skills_ctx = (report_summary.get("_context") or {}).get("skills") or {}
    if isinstance(skills_ctx, dict) and skills_ctx:
        out["skills"] = skills_ctx
    return out


def _consultant_prompt(role_name: str, focus: str) -> str:
    return (
        f"你是艾薇手工坊三顧問系統之一：{role_name}。\n"
        f"你的焦點：{focus}\n\n"
        "硬規則：\n"
        "1) 只能引用輸入 JSON 的數字，不可重新計算或改寫任何 KPI。\n"
        "2) 輸出必須是『單一 JSON object』，不要```、不要多餘文字。\n"
        "3) 每個結論都要寫『依據』：引用輸入中的哪個欄位/表格/現象。\n"
        "4) 若輸入中有 'skills' 欄位（Metric Tree/Fatigue/Budget），請優先參考其診斷結果作為依據。\n"
        "5) 必須包含『整體日預算動作』：針對『全帳戶平均每日花費節奏』，輸出 increase/hold/decrease + change_pct。\n"
        "5) 也必須包含『adset/ads 層級動作』（加碼/降碼/停用建議），依 tables 的 top/bottom。\n"
    )


def _consultant_task(role_key: str) -> str:
    return (
        "請輸出 JSON，欄位如下：\n"
        f"- consultant_key: '{role_key}'\n"
        "- summary: 3-6 條一句話結論（每條附依據）\n"
        "- opportunities: 3-6 條（可擴量/可優化點，每條附依據）\n"
        "- risks: 2-4 條（risk/probability/impact/mitigation/alternative）\n"
        "- overall_budget_action: {action: increase|hold|decrease, change_pct: 整數(例如 10), rationale: 1-3句(含依據)}\n"
        "- adset_ads_actions: 4-10 條（每條包含 level: adset|ad, name, action, why(含依據), kpi, stoploss）\n"
        "- next_7d_actions: 3-6 條任務（task/owner_role/deliverable/due/kpi/stoploss/why(含依據)）\n"
        "- questions: 3-6 條（下次週會要確認）\n"
    )


def _prepare_context(report_summary: dict[str, Any], report_insights: dict[str, Any]) -> str:
    """
    用途：組裝三顧問共用的 Context 字串（給 LLM 的 user content）
    原則：
      - 只做「整理與壓縮輸入」，不做任何 KPI 重算
      - 回傳單一 JSON 字串，供模型直接引用欄位與數字
    """
    payload = _compact_inputs(report_summary, report_insights)
    payload["context_version"] = "consultant_context.v1"
    return json.dumps(payload, ensure_ascii=False)


def _parse_or_repair(
    content: str,
    usage: dict[str, int],
    model: str,
    role: str,
    system: str,
) -> tuple[dict[str, Any], dict[str, int], str, bool]:
    """
    用途：解析模型輸出；若不是合法 JSON，會自動做一次「修復重試」。
    注意：_try_parse_json 解析失敗時會回傳含 error 的 dict（不會丟例外），因此需同時檢查 error key。
    """
    try:
        parsed = _try_parse_json(content)
    except Exception:
        parsed = {"error": "unexpected_parse_exception", "raw_content": str(content)[:200]}

    if isinstance(parsed, dict) and "error" not in parsed:
        return parsed, usage, model, False

    content_snippet = (
        content if len(content) <= 12000 else (content[:12000] + "\n...[TRUNCATED]...")
    )
    repair, usage_repair, repair_model, retried_with_fallback = (
        _openrouter_chat_completion_with_fallback(
            [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        "你上一次輸出不是合法 JSON。請重新輸出『單一 JSON object』，且：\n"
                        "- 禁止 ```\n"
                        "- 禁止多餘文字（包含前後說明、註解、…）\n"
                        "- 不要輸出多個 JSON\n"
                        "- 確保逗號/括號配對正確\n"
                    ),
                },
                {"role": "user", "content": content_snippet},
            ],
            model=model,
            role=role,
            temperature=0.0,
            max_tokens=8000,
        )
    )
    total_usage = {
        "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0)
        + int(usage_repair.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(usage.get("completion_tokens", 0) or 0)
        + int(usage_repair.get("completion_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0)
        + int(usage_repair.get("total_tokens", 0) or 0),
    }
    return _try_parse_json(repair), total_usage, repair_model, retried_with_fallback


def generate_consultant_notes(
    report_summary: dict[str, Any],
    report_insights: dict[str, Any],
    model_a: str | None = None,
    model_b: str | None = None,
    model_c: str | None = None,
    status_callback: Callable[[str, str], None] | None = None,
    on_consultant_done: Callable[[str, dict[str, Any]], None] | None = None,
    version_fp: str | None = None,
) -> dict[str, Any]:
    """
    分別呼叫三位顧問（A:成效, B:視覺/文案, C:策略），回傳各自的 JSON。

    參數:
        on_consultant_done: 顧問完成時的回呼 (role, parsed_json)，用於即時 UI 更新
    """
    configured_model_a = model_a or get_model("consultant_a")
    configured_model_b = model_b or get_model("consultant_b")
    configured_model_c = model_c or get_model("consultant_c")

    # Prepare Context
    ctx_str = _prepare_context(report_summary, report_insights)
    # 注意：回傳欄位需要引用 compact 後的結果，因此另外保留 payload（僅做整理，不重算 KPI）
    payload = _compact_inputs(report_summary, report_insights)

    # Prompts
    sys_a = (
        "你是艾薇手工坊三顧問系統之一：顧問A｜成效與數據分析專家。\n"
        "任務：分析 Meta 廣告數據，找出成效優異與落後的廣告/組合，並給出調整建議。\n"
        "輸出：單一 JSON object（schema: consultant_a.v1）。\n"
    )
    sys_b = (
        "你是艾薇手工坊三顧問系統之一：顧問B｜創意與內容優化專家。\n"
        "任務：分析廣告素材文案與視覺（從數據推論），提出創意優化方向。\n"
        "輸出：單一 JSON object（schema: consultant_b.v1）。\n"
    )
    sys_c = (
        "你是艾薇手工坊三顧問系統之一：顧問C｜行銷策略與市場專家。\n"
        "任務：結合成效與創意，提供宏觀策略建議（預算分配、受眾拓展、促銷活動）。\n"
        "輸出：單一 JSON object（schema: consultant_c.v1）。\n"
    )

    # Execute
    # 明確提供欄位要求，降低模型輸出非 JSON 或 schema 漂移機率
    task_a = _consultant_task("A")
    task_b = _consultant_task("B")
    task_c = _consultant_task("C")

    msgs_a = [
        {"role": "system", "content": sys_a},
        {"role": "user", "content": task_a},
        {"role": "user", "content": ctx_str},
    ]
    msgs_b = [
        {"role": "system", "content": sys_b},
        {"role": "user", "content": task_b},
        {"role": "user", "content": ctx_str},
    ]
    msgs_c = [
        {"role": "system", "content": sys_c},
        {"role": "user", "content": task_c},
        {"role": "user", "content": ctx_str},
    ]

    if status_callback:
        status_callback("A", configured_model_a)
    out_a, usage_a, model_a_used, retried_with_fallback_main_a = (
        _openrouter_chat_completion_with_fallback(
            msgs_a,
            model=configured_model_a,
            role="consultant_a",
            temperature=0.2,
            max_tokens=8000,
        )
    )
    j_a, usage_a_total, model_a_final, retried_with_fallback_repair_a = _parse_or_repair(
        out_a,
        usage_a,
        model_a_used,
        "consultant_a",
        sys_a,
    )
    try:
        week_id = str(report_summary.get("week_id") or "").strip() or None
        llm_monitor.log_call(
            LLMCall(
                timestamp=now_iso(),
                model=model_a_final,
                prompt_tokens=int(usage_a_total.get("prompt_tokens", 0) or 0),
                completion_tokens=int(usage_a_total.get("completion_tokens", 0) or 0),
                total_tokens=int(usage_a_total.get("total_tokens", 0) or 0),
                cost_usd=estimate_cost(
                    model_a_final,
                    int(usage_a_total.get("prompt_tokens", 0) or 0),
                    int(usage_a_total.get("completion_tokens", 0) or 0),
                ),
                function="generate_consultant_notes",
                week_id=week_id,
                extra={
                    "step": "E",
                    "consultant": "A",
                    "version_fp": version_fp,
                    "configured_model": configured_model_a,
                    "used_model": model_a_final,
                    "fallback_retry_main": retried_with_fallback_main_a,
                    "fallback_retry_repair": retried_with_fallback_repair_a,
                }
                if version_fp
                else {
                    "step": "E",
                    "consultant": "A",
                    "configured_model": configured_model_a,
                    "used_model": model_a_final,
                    "fallback_retry_main": retried_with_fallback_main_a,
                    "fallback_retry_repair": retried_with_fallback_repair_a,
                },
            )
        )
    except Exception:
        pass
    if on_consultant_done:
        on_consultant_done("A", j_a)

    if status_callback:
        status_callback("B", configured_model_b)
    out_b, usage_b, model_b_used, retried_with_fallback_main_b = (
        _openrouter_chat_completion_with_fallback(
            msgs_b,
            model=configured_model_b,
            role="consultant_b",
            temperature=0.2,
            max_tokens=8000,
        )
    )
    j_b, usage_b_total, model_b_final, retried_with_fallback_repair_b = _parse_or_repair(
        out_b,
        usage_b,
        model_b_used,
        "consultant_b",
        sys_b,
    )
    try:
        week_id = str(report_summary.get("week_id") or "").strip() or None
        llm_monitor.log_call(
            LLMCall(
                timestamp=now_iso(),
                model=model_b_final,
                prompt_tokens=int(usage_b_total.get("prompt_tokens", 0) or 0),
                completion_tokens=int(usage_b_total.get("completion_tokens", 0) or 0),
                total_tokens=int(usage_b_total.get("total_tokens", 0) or 0),
                cost_usd=estimate_cost(
                    model_b_final,
                    int(usage_b_total.get("prompt_tokens", 0) or 0),
                    int(usage_b_total.get("completion_tokens", 0) or 0),
                ),
                function="generate_consultant_notes",
                week_id=week_id,
                extra={
                    "step": "E",
                    "consultant": "B",
                    "version_fp": version_fp,
                    "configured_model": configured_model_b,
                    "used_model": model_b_final,
                    "fallback_retry_main": retried_with_fallback_main_b,
                    "fallback_retry_repair": retried_with_fallback_repair_b,
                }
                if version_fp
                else {
                    "step": "E",
                    "consultant": "B",
                    "configured_model": configured_model_b,
                    "used_model": model_b_final,
                    "fallback_retry_main": retried_with_fallback_main_b,
                    "fallback_retry_repair": retried_with_fallback_repair_b,
                },
            )
        )
    except Exception:
        pass
    if on_consultant_done:
        on_consultant_done("B", j_b)

    if status_callback:
        status_callback("C", configured_model_c)
    out_c, usage_c, model_c_used, retried_with_fallback_main_c = (
        _openrouter_chat_completion_with_fallback(
            msgs_c,
            model=configured_model_c,
            role="consultant_c",
            temperature=0.2,
            max_tokens=8000,
        )
    )
    j_c, usage_c_total, model_c_final, retried_with_fallback_repair_c = _parse_or_repair(
        out_c,
        usage_c,
        model_c_used,
        "consultant_c",
        sys_c,
    )
    try:
        week_id = str(report_summary.get("week_id") or "").strip() or None
        llm_monitor.log_call(
            LLMCall(
                timestamp=now_iso(),
                model=model_c_final,
                prompt_tokens=int(usage_c_total.get("prompt_tokens", 0) or 0),
                completion_tokens=int(usage_c_total.get("completion_tokens", 0) or 0),
                total_tokens=int(usage_c_total.get("total_tokens", 0) or 0),
                cost_usd=estimate_cost(
                    model_c_final,
                    int(usage_c_total.get("prompt_tokens", 0) or 0),
                    int(usage_c_total.get("completion_tokens", 0) or 0),
                ),
                function="generate_consultant_notes",
                week_id=week_id,
                extra={
                    "step": "E",
                    "consultant": "C",
                    "version_fp": version_fp,
                    "configured_model": configured_model_c,
                    "used_model": model_c_final,
                    "fallback_retry_main": retried_with_fallback_main_c,
                    "fallback_retry_repair": retried_with_fallback_repair_c,
                }
                if version_fp
                else {
                    "step": "E",
                    "consultant": "C",
                    "configured_model": configured_model_c,
                    "used_model": model_c_final,
                    "fallback_retry_main": retried_with_fallback_main_c,
                    "fallback_retry_repair": retried_with_fallback_repair_c,
                },
            )
        )
    except Exception:
        pass
    if on_consultant_done:
        on_consultant_done("C", j_c)

    return {
        "consultants_version": "consultants.v1",
        "week_id": report_summary.get("week_id"),
        "date_range": report_summary.get("date_range"),
        "avg_daily_spend_twd_calc": payload.get("meta_avg_daily_spend_twd_calc"),
        "consultant_A": j_a,
        "consultant_B": j_b,
        "consultant_C": j_c,
    }


# ---------------------------------------------------------------------------
# E2 schema normalizer
# ---------------------------------------------------------------------------

_EVIDENCE_REF_RE = re.compile(
    r"^source:[A-Za-z0-9_]+(?:\[[0-9]+\])?(?:\.[A-Za-z0-9_]+(?:\[[0-9]+\])?)+$"
)


def _coerce_evidence_ref(raw: Any, targets: list[str]) -> str:
    """
    把任意 evidence_ref 原始值強制轉為符合 schema pattern 的字串。
    pattern: ^source:[A-Za-z0-9_]+(?:\\[[0-9]+\\])?(?:\\.[A-Za-z0-9_]+(?:\\[[0-9]+\\])?)+$
    """

    def _fallback() -> str:
        fallback_target = targets[0] if targets else "B"
        return f"source:consultant_{fallback_target}.summary[0]"

    if not isinstance(raw, str) or not raw.strip():
        # 沒有任何可用資訊 → 使用 targets[0] 產生安全預設值
        return _fallback()

    candidate = raw.strip()

    # 若已符合 pattern，直接用
    if _EVIDENCE_REF_RE.match(candidate) and len(candidate) <= 200:
        return candidate

    # 嘗試：若以 "source:" 開頭，去除多餘中文/全形字符後再試
    if candidate.startswith("source:"):
        # 移除 source: 之後的非 ASCII 字元（只保留 A-Za-z0-9_.[]）
        cleaned = "source:" + re.sub(r"[^A-Za-z0-9_.\[\]]", "_", candidate[7:])
        # 確保至少有一個 . 分隔（schema 要求至少兩段）
        if "." not in cleaned[7:]:
            cleaned = cleaned + ".ref"
        if _EVIDENCE_REF_RE.match(cleaned) and len(cleaned) <= 200:
            return cleaned

    # 嘗試：若不以 source: 開頭但包含有意義文字，加上 source: 前綴
    ascii_slug = re.sub(r"[^A-Za-z0-9_.\[\]]", "_", candidate)
    if ascii_slug and ascii_slug[0].isalpha():
        with_prefix = "source:" + ascii_slug
        if "." not in ascii_slug:
            with_prefix = with_prefix + ".ref"
        if _EVIDENCE_REF_RE.match(with_prefix) and len(with_prefix) <= 200:
            return with_prefix

    # 最終 fallback
    return _fallback()


def _coerce_strength_item(item: Any) -> str | None:
    """把 strength 項目（可能是 str 或含 point/evidence/依據 的 dict）轉為 str。"""
    if isinstance(item, str):
        return item.strip() or None
    if isinstance(item, dict):
        parts: list[str] = []
        point = item.get("point") or item.get("論點") or ""
        evidence = item.get("evidence") or item.get("依據") or item.get("evidence_ref") or ""
        if point:
            parts.append(str(point).strip())
        if evidence:
            parts.append(str(evidence).strip())
        combined = "：".join(parts) if parts else ""
        return combined or None
    return None


def normalize_consultant_cross_review(
    review: Any,
    reviewer: str,
    targets: list[str],
) -> dict[str, Any]:
    """
    把任意 LLM 輸出（含多餘 key、錯誤型別）正規化為嚴格符合
    consultant_cross_review.v1 schema 的 dict。

    規則：
    - 只保留 schema 允許的頂層 key（additionalProperties=false）
    - 強制填充所有 required 欄位
    - review_version / reviewer / reviewed_targets 固定由參數決定
    - strengths: list[str] 1..3，dict item 合併為字串
    - critical_issues: list[dict] 1..3，只保留 issue/evidence_ref/impact/severity/suggested_fix
    - assumptions_to_validate: list[dict] 0..2，只保留 assumption/validation_step
    - recommended_edits: list[str] 1..3
    - stoploss_or_guardrails: list[str] 1..2
    - confidence: float in [0,1]
    - why: str <=300
    """
    if not isinstance(review, dict):
        review = {}

    # ---- reviewed_targets (must satisfy schema constraints) ----
    allowed_roles = {"A", "B", "C"}
    canonical_targets_map: dict[str, list[str]] = {
        "A": ["B", "C"],
        "B": ["A", "C"],
        "C": ["A", "B"],
    }
    cleaned_targets = [
        t for t in targets if isinstance(t, str) and t in allowed_roles and t != reviewer
    ]
    cleaned_targets = list(dict.fromkeys(cleaned_targets))
    if len(cleaned_targets) == 2:
        reviewed_targets = cleaned_targets
    else:
        reviewed_targets = (
            canonical_targets_map.get(reviewer) or [t for t in allowed_roles if t != reviewer][:2]
        )

    # ---- strengths ----
    raw_strengths = review.get("strengths") or []
    coerced_strengths: list[str] = []
    if isinstance(raw_strengths, list):
        for item in raw_strengths:
            s = _coerce_strength_item(item)
            if s:
                coerced_strengths.append(s[:300])
    elif isinstance(raw_strengths, str) and raw_strengths.strip():
        coerced_strengths.append(raw_strengths.strip()[:300])

    # 至少 1 條
    if not coerced_strengths:
        coerced_strengths = ["分析架構完整，有助於後續決策參考。"]
    strengths = coerced_strengths[:3]

    # ---- critical_issues ----
    raw_ci = review.get("critical_issues") or []
    coerced_ci: list[dict[str, Any]] = []
    if isinstance(raw_ci, list):
        for item in raw_ci:
            if not isinstance(item, dict):
                continue
            # 取 issue
            issue_val = item.get("issue") or item.get("問題") or item.get("critical_issue") or ""
            issue_str = str(issue_val).strip()[:300] if issue_val else ""
            if not issue_str:
                continue

            # 取 evidence_ref（優先用 evidence_ref，其次用 依據/evidence）
            raw_ref = item.get("evidence_ref") or item.get("依據") or item.get("evidence") or ""
            evidence_ref = _coerce_evidence_ref(raw_ref, targets)

            ci_obj: dict[str, Any] = {"issue": issue_str, "evidence_ref": evidence_ref}
            # 可選欄位
            for opt_key in ("impact", "severity", "suggested_fix"):
                val = item.get(opt_key)
                if val is not None:
                    limit = 300 if opt_key != "suggested_fix" else 400
                    ci_obj[opt_key] = str(val).strip()[:limit]
            coerced_ci.append(ci_obj)

    # 至少 1 條
    if not coerced_ci:
        fallback_target = targets[0] if targets else "B"
        coerced_ci = [
            {
                "issue": "建議缺乏明確的止損條件，需補充觸發門檻。",
                "evidence_ref": f"source:consultant_{fallback_target}.summary[0]",
            }
        ]
    critical_issues = coerced_ci[:3]

    # ---- assumptions_to_validate ----
    raw_atv = review.get("assumptions_to_validate") or []
    coerced_atv: list[dict[str, Any]] = []
    if isinstance(raw_atv, list):
        for item in raw_atv:
            if not isinstance(item, dict):
                continue
            assumption = str(item.get("assumption") or "").strip()[:300]
            validation_step = str(item.get("validation_step") or "").strip()[:300]
            if assumption and validation_step:
                coerced_atv.append({"assumption": assumption, "validation_step": validation_step})
    # 最多 2 條，可為空 []
    assumptions_to_validate = coerced_atv[:2]

    # ---- recommended_edits ----
    raw_re = review.get("recommended_edits") or []
    coerced_re: list[str] = []
    if isinstance(raw_re, list):
        for item in raw_re:
            s = str(item).strip()[:400] if item else ""
            if s:
                coerced_re.append(s)
    elif isinstance(raw_re, str) and raw_re.strip():
        coerced_re.append(raw_re.strip()[:400])
    if not coerced_re:
        coerced_re = ["建議補充每條行動項目的明確 KPI 門檻與負責角色。"]
    recommended_edits = coerced_re[:3]

    # ---- stoploss_or_guardrails ----
    raw_sg = review.get("stoploss_or_guardrails") or []
    coerced_sg: list[str] = []
    if isinstance(raw_sg, list):
        for item in raw_sg:
            s = str(item).strip()[:300] if item else ""
            if s:
                coerced_sg.append(s)
    elif isinstance(raw_sg, str) and raw_sg.strip():
        coerced_sg.append(raw_sg.strip()[:300])
    if not coerced_sg:
        coerced_sg = ["若 ROAS 連續 3 日低於 1.5，暫停追加預算。"]
    stoploss_or_guardrails = coerced_sg[:2]

    # ---- confidence ----
    raw_conf = review.get("confidence")
    confidence: float = 0.5
    if isinstance(raw_conf, (int, float)) and not isinstance(raw_conf, bool):
        confidence = float(raw_conf)
    elif isinstance(raw_conf, str):
        cleaned_conf = raw_conf.strip().rstrip("%")
        try:
            val = float(cleaned_conf)
            confidence = val / 100.0 if val > 1.0 else val
        except ValueError:
            confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    # ---- why ----
    raw_why = review.get("why") or review.get("reason") or review.get("rationale") or ""
    why_str = str(raw_why).strip()[:300] if raw_why else ""
    if not why_str:
        why_str = "原始輸出未符合 schema，已自動正規化。"

    return {
        "review_version": "consultant_cross_review.v1",
        "reviewer": reviewer,
        "reviewed_targets": reviewed_targets,
        "strengths": strengths,
        "critical_issues": critical_issues,
        "assumptions_to_validate": assumptions_to_validate,
        "recommended_edits": recommended_edits,
        "stoploss_or_guardrails": stoploss_or_guardrails,
        "confidence": confidence,
        "why": why_str,
    }


def _compact_consultant_note(note: dict[str, Any], max_chars: int = 2000) -> dict[str, Any]:
    """
    壓縮單位顧問 E1 輸出，避免 E2 prompt token 爆炸。
    只保留最重要的欄位，其餘截斷或省略。
    """
    if not isinstance(note, dict) or "error" in note:
        return {"error": note.get("error", "invalid") if isinstance(note, dict) else "invalid"}

    compact: dict[str, Any] = {}
    # 保留關鍵欄位
    for key in [
        "consultant_key",
        "summary",
        "opportunities",
        "risks",
        "overall_budget_action",
        "next_7d_actions",
    ]:
        val = note.get(key)
        if val is not None:
            if isinstance(val, str) and len(val) > 500:
                compact[key] = val[:500] + "…"
            elif isinstance(val, list):
                compact[key] = val[:4]  # 最多 4 條
            else:
                compact[key] = val

    # 確保不超過 max_chars
    raw = json.dumps(compact, ensure_ascii=False)
    if len(raw) > max_chars:
        # 逐步移除非關鍵欄位
        for key in ["next_7d_actions", "opportunities"]:
            compact.pop(key, None)
            if len(json.dumps(compact, ensure_ascii=False)) <= max_chars:
                break

    return compact


def _cross_review_system_prompt(reviewer: str) -> str:
    """為交叉審核顧問建立 system prompt。"""
    role_names = {
        "A": "顧問A｜成效與數據分析專家",
        "B": "顧問B｜創意與內容優化專家",
        "C": "顧問C｜行銷策略與市場專家",
    }
    role_name = role_names.get(reviewer, f"顧問{reviewer}")
    targets = [t for t in ["A", "B", "C"] if t != reviewer]
    target_str = "、".join(f"顧問{t}" for t in targets)
    return (
        f"你是艾薇手工坊三顧問系統之一：{role_name}。\n"
        f"你現在要執行「交叉審核（E2）」：審核{target_str}的建議。\n\n"
        "硬規則：\n"
        "1) 只能引用輸入 JSON 的數字，不可重新計算或改寫任何 KPI。\n"
        "2) 輸出必須是『單一 JSON object』，不要```、不要多餘文字。\n"
        "3) 只能輸出 schema 允許的 key（review_version/reviewer/reviewed_targets/"
        "strengths/critical_issues/assumptions_to_validate/recommended_edits/"
        "stoploss_or_guardrails/confidence/why），禁止輸出任何其他 key。\n"
        "4) 禁止新增名為「依據」或「reason」或「conclusions」或「next_steps」"
        "或「task」或「status」或「reviewer_role」或「required_input_fields」的 key。\n"
        "5) strengths 必須是字串陣列（array of strings），禁止輸出物件。\n"
        "6) evidence_ref 只能出現在 critical_issues[].evidence_ref，"
        "格式必須是 'source:consultant_X.欄位名稱'（例如 source:consultant_B.risks[0].risk）。\n"
    )


def _cross_review_task_prompt(reviewer: str, targets: list[str]) -> str:
    """建立交叉審核的 task prompt。"""
    targets_str = " 和 ".join(f"顧問{t}" for t in targets)
    example_target = targets[0] if targets else "B"
    example_json = json.dumps(
        {
            "review_version": "consultant_cross_review.v1",
            "reviewer": reviewer,
            "reviewed_targets": targets,
            "strengths": ["顧問X的分析邏輯清晰，論點有數據支撐。"],
            "critical_issues": [
                {
                    "issue": "預算建議缺乏明確止損條件",
                    "evidence_ref": f"source:consultant_{example_target}.risks[0].risk",
                    "impact": "可能在 ROAS 低迷時持續加碼",
                    "severity": "medium",
                    "suggested_fix": "補充 stoploss_kpi 欄位",
                }
            ],
            "assumptions_to_validate": [
                {
                    "assumption": "下週歸因設定不變",
                    "validation_step": "確認 Meta 事件管理員設定",
                }
            ],
            "recommended_edits": ["建議補充每條行動的明確 KPI 門檻"],
            "stoploss_or_guardrails": ["若 ROAS 低於 1.9 立即暫停追加預算"],
            "confidence": 0.8,
            "why": "審核核心關切：缺乏明確的止損機制。",
        },
        ensure_ascii=False,
        indent=2,
    )
    return (
        f"請針對{targets_str}的建議進行交叉審核，輸出符合以下規範的單一 JSON object：\n\n"
        "【必須輸出的欄位（不多、不少）】\n"
        f"- review_version: 固定為 'consultant_cross_review.v1'\n"
        f"- reviewer: 固定為 '{reviewer}'\n"
        f"- reviewed_targets: 固定為 {json.dumps(targets)}\n"
        "- strengths: array of strings，1-3 條，每條為純字串（不是物件），內容說明值得肯定的論點\n"
        "- critical_issues: array of objects，1-3 條，每條包含:\n"
        "    issue (string), evidence_ref (string, 格式: source:consultant_X.欄位名稱),\n"
        "    impact (string, 可選), severity (string, 可選), suggested_fix (string, 可選)\n"
        "- assumptions_to_validate: array of objects，0-2 條，每條包含 assumption + validation_step\n"
        "- recommended_edits: array of strings，1-3 條\n"
        "- stoploss_or_guardrails: array of strings，1-2 條\n"
        "- confidence: number，0.0 到 1.0 之間\n"
        "- why: string，說明本次審核核心關切\n\n"
        "【嚴格禁止】\n"
        "- 禁止輸出任何其他 key（包含 依據、reason、conclusions、next_steps、"
        "task、status、reviewer_role、required_input_fields 等）\n"
        "- strengths 的每個 item 必須是字串，禁止用物件格式\n"
        "- evidence_ref 只能用 source:consultant_X.欄位名稱 的格式（X=A/B/C）\n\n"
        f"【合法輸出範例】\n{example_json}\n"
    )


_REVIEWER_ROLE_MAP: dict[str, "ModelRole"] = {
    "A": "consultant_a",
    "B": "consultant_b",
    "C": "consultant_c",
}


def _single_cross_review(
    reviewer: str,
    targets: list[str],
    report_summary: dict[str, Any],
    report_insights: dict[str, Any],
    consultant_notes: dict[str, Any],
    version_fp: str | None = None,
) -> dict[str, Any]:
    """
    執行單位顧問的交叉審核（E2）。
    失敗時回傳含 error 的 dict，不拋出例外（graceful degradation）。
    """
    role_key = _REVIEWER_ROLE_MAP.get(reviewer, "consultant_a")
    model = get_model(role_key)
    system = _cross_review_system_prompt(reviewer)
    task = _cross_review_task_prompt(reviewer, targets)

    # 組裝被審核顧問的壓縮輸出
    reviewed_notes: dict[str, Any] = {}
    for t in targets:
        raw_note = consultant_notes.get(f"consultant_{t}")
        reviewed_notes[f"consultant_{t}"] = _compact_consultant_note(
            raw_note if isinstance(raw_note, dict) else {}
        )

    # 組裝 context（壓縮報表 + 被審核顧問輸出）
    compact_report = _compact_inputs(report_summary, report_insights)
    context_payload = {
        "report_context": {
            "week_id": compact_report.get("week_id"),
            "date_range": compact_report.get("date_range"),
            "meta_kpi": compact_report.get("meta_kpi"),
            "web_kpi": compact_report.get("web_kpi"),
        },
        "consultant_notes_to_review": reviewed_notes,
    }
    ctx_str = json.dumps(context_payload, ensure_ascii=False)

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": task},
        {"role": "user", "content": ctx_str},
    ]

    try:
        content, usage, model_used, retried_main = _openrouter_chat_completion_with_fallback(
            messages,
            model=model,
            role=role_key,
            temperature=0.2,
            max_tokens=3000,
        )
        parsed, usage_total, model_final, retried_repair = _parse_or_repair(
            content, usage, model_used, role_key, system
        )

        # 若解析/修復仍失敗，保持 error 結構走 graceful degradation（避免吞成假成功）
        if isinstance(parsed, dict) and "error" in parsed:
            return {
                "error": f"E2 reviewer {reviewer} JSON 解析失敗：{str(parsed.get('error'))[:200]}",
                "reviewer": reviewer,
                "reviewed_targets": targets,
            }

        # 正規化輸出，確保符合 consultant_cross_review.v1 schema
        parsed = normalize_consultant_cross_review(parsed, reviewer, targets)

        # 記錄 LLM 監控
        try:
            week_id = str(report_summary.get("week_id") or "").strip() or None
            llm_monitor.log_call(
                LLMCall(
                    timestamp=now_iso(),
                    model=model_final,
                    prompt_tokens=int(usage_total.get("prompt_tokens", 0) or 0),
                    completion_tokens=int(usage_total.get("completion_tokens", 0) or 0),
                    total_tokens=int(usage_total.get("total_tokens", 0) or 0),
                    cost_usd=estimate_cost(
                        model_final,
                        int(usage_total.get("prompt_tokens", 0) or 0),
                        int(usage_total.get("completion_tokens", 0) or 0),
                    ),
                    function="generate_consultant_cross_reviews",
                    week_id=week_id,
                    extra={
                        "step": "E2",
                        "reviewer": reviewer,
                        "reviewed_targets": targets,
                        "version_fp": version_fp,
                        "configured_model": model,
                        "used_model": model_final,
                        "fallback_retry_main": retried_main,
                        "fallback_retry_repair": retried_repair,
                    },
                )
            )
        except Exception:
            pass

        return parsed

    except Exception as e:
        return {
            "error": f"E2 reviewer {reviewer} 失敗：{str(e)[:300]}",
            "reviewer": reviewer,
            "reviewed_targets": targets,
        }


def generate_consultant_cross_reviews(
    report_summary: dict[str, Any],
    report_insights: dict[str, Any],
    consultant_notes: dict[str, Any],
    status_callback: Callable[[str, str], None] | None = None,
    version_fp: str | None = None,
) -> dict[str, Any]:
    """
    E2 交叉審核：三位顧問各自審核另外兩位的 E1 結論。
    - reviewer A → reviewed_targets: [B, C]
    - reviewer B → reviewed_targets: [A, C]
    - reviewer C → reviewed_targets: [A, B]

    失敗策略（graceful degradation）：
    - 若某位 reviewer 失敗，以含 error 的 dict 記錄，不阻擋整體流程。
    - 若三位均失敗，仍回傳結構（每位各有 error），讓 Step F 可繼續。

    參數:
        status_callback: 開始審核某 reviewer 時的回呼 (reviewer_key, model)
    """
    reviewer_targets: dict[str, list[str]] = {
        "A": ["B", "C"],
        "B": ["A", "C"],
        "C": ["A", "B"],
    }

    reviews: dict[str, Any] = {}
    for reviewer, targets in reviewer_targets.items():
        if status_callback:
            role_key = _REVIEWER_ROLE_MAP.get(reviewer, "consultant_a")
            status_callback(f"E2-{reviewer}", get_model(role_key))

        review = _single_cross_review(
            reviewer=reviewer,
            targets=targets,
            report_summary=report_summary,
            report_insights=report_insights,
            consultant_notes=consultant_notes,
            version_fp=version_fp,
        )
        reviews[f"reviewer_{reviewer}"] = review

    # 統計成功/失敗
    success_count = sum(1 for r in reviews.values() if isinstance(r, dict) and "error" not in r)
    error_count = len(reviews) - success_count

    return {
        "cross_reviews_version": "consultant_cross_reviews.v1",
        "week_id": report_summary.get("week_id"),
        "date_range": report_summary.get("date_range"),
        "success_count": success_count,
        "error_count": error_count,
        "reviews": reviews,
    }


def run_visual_consultant(
    *,
    max_images: int = 6,
    model_b: str | None = None,
) -> dict[str, Any]:
    """
    視覺顧問（顧問 B）：自動讀取 `attached_assets/` 素材，交由多模態模型進行分析。

    - 目前僅將「圖片」送入多模態分析；影片會被掃描並回報數量，但不會上傳給模型。
    """
    media = scan_media_assets()
    images = get_top_images(media.images, n=max_images)
    model = model_b or get_model("consultant_b")

    if not images:
        return {
            "visual_consultant_version": "visual_consultant.v1",
            "model": model,
            "images_sent": 0,
            "videos_found": len(media.videos),
            "result": {
                "summary": ["未在 attached_assets/ 找到可分析的圖片素材。"],
                "notes": ["支援 jpg/png/gif/webp；影片（mp4/mov）目前僅掃描不分析。"],
            },
        }

    system = (
        "你是艾薇手工坊三顧問系統之一：顧問B｜視覺與素材分析。\n"
        "你的任務：針對輸入的廣告素材圖片，提供可執行的視覺洞察與優化建議。\n\n"
        "硬規則：\n"
        "1) 輸出必須是『單一 JSON object』，不要```、不要多餘文字。\n"
        "2) 每個結論都要寫『依據』：指出你在圖片中看到的具體元素（例如文案、構圖、主體、顏色、版位、CTA）。\n"
        "3) 請避免臆測不存在的商業數據；你只能針對素材內容提出分析。\n"
    )

    user_text = (
        "請分析以下素材圖片，輸出 JSON（單一 object），欄位如下：\n"
        "- assets: [{filename, key_visual, message, cta, audience_guess, issues, strengths}]\n"
        "- cross_asset_patterns: 3-8 條（跨素材共通模式與一致性/不一致性）\n"
        "- quick_wins: 5-10 條（最快能做、可 A/B 的改動，含依據）\n"
        "- risks: 2-6 條（視覺層級風險，例如資訊過載、違規風險線索、訊息不清）\n"
        "- next_7d_test_plan: 3-6 條（test/hypothesis/change/metric/stoploss）\n"
        "- questions: 3-6 條（下次週會要補齊的素材資訊）\n"
    )

    content_parts = [{"type": "text", "text": user_text}]
    for image_path in images:
        content_parts.append({"type": "text", "text": f"素材檔名：{image_path.name}"})
        content_parts.append(create_image_content(image_path))

    raw = openrouter_multimodal_completion(
        [{"role": "system", "content": system}, {"role": "user", "content": content_parts}],
        model=model,
        temperature=0.2,
        max_tokens=1800,
    )

    parsed, _, _, _ = _parse_or_repair(
        raw,
        {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        model,
        "consultant_b",
        system,
    )
    return {
        "visual_consultant_version": "visual_consultant.v1",
        "model": model,
        "images_sent": len(images),
        "videos_found": len(media.videos),
        "image_files": [p.name for p in images],
        "result": parsed,
    }
