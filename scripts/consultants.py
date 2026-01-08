# -*- coding: utf-8 -*-
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
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple

import requests

from core.config import MODEL_CONSULTANT_A, MODEL_CONSULTANT_B, MODEL_CONSULTANT_C
from core.llm_monitor import LLMCall, estimate_cost, get_monitor
from utils import now_iso

from scripts.media_scanner import get_top_images, scan_media_assets
from scripts.multimodal import create_image_content, openrouter_multimodal_completion


llm_monitor = get_monitor()


def _openrouter_chat_completion(
    messages, model: str, temperature: float = 0.2, max_tokens: int = 8000
) -> Tuple[str, Dict[str, int]]:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE") or "https://openrouter.ai/api/v1"
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
    except Exception:
        raise RuntimeError(f"OpenRouter returned non-JSON response: {resp.text[:200]}")

    if "error" in data:
        raise RuntimeError(f"OpenRouter API Error: {json.dumps(data['error'])}")

    if not data.get("choices"):
        raise RuntimeError(f"OpenRouter returned no choices. Model: {model}. Response: {json.dumps(data)}")
        
    content = data["choices"][0]["message"].get("content")
    if content is None:
        content = ""

    usage = data.get("usage", {}) or {}
    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens) or 0)

    return (
        str(content),
        {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": total_tokens},
    )


def _try_parse_json(s: str) -> Dict[str, Any]:
    if not s:
        return {"error": "Empty response from LLM", "raw_content": ""}
    s = s.strip()
    first, last = s.find("{"), s.rfind("}")
    if first != -1 and last != -1 and last > first:
        s = s[first:last + 1]
    
    try:
        # 使用 raw_decode 容忍「多個 JSON object 串接」或尾端雜訊（常見於 LLM 輸出）
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(s)
        return obj
    except Exception as e:
        return {
            "error": f"JSON parse error: {str(e)}",
            "raw_content": s[:4000] + "..." if len(s) > 4000 else s
        }


def _days_in_range(date_range: str) -> int:
    try:
        a, b = date_range.split("~")
        da = datetime.fromisoformat(a)
        db = datetime.fromisoformat(b)
        return max(1, (db - da).days + 1)
    except Exception:
        return 1


def _compact_inputs(report_summary: Dict[str, Any], report_insights: Dict[str, Any]) -> Dict[str, Any]:
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
            "adset_budget_actions": "若要落地執行，需列出要加碼/降碼的 adset/ads（依 tables 的 top/bottom）"
        },
        "hard_rules": {
            "no_recalc_numbers": True,
            "language": "zh-TW",
            "must_output_valid_json": True
        }
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


def _prepare_context(report_summary: Dict[str, Any], report_insights: Dict[str, Any]) -> str:
    """
    用途：組裝三顧問共用的 Context 字串（給 LLM 的 user content）
    原則：
      - 只做「整理與壓縮輸入」，不做任何 KPI 重算
      - 回傳單一 JSON 字串，供模型直接引用欄位與數字
    """
    payload = _compact_inputs(report_summary, report_insights)
    payload["context_version"] = "consultant_context.v1"
    return json.dumps(payload, ensure_ascii=False)


def _parse_or_repair(content: str, usage: Dict[str, int], model: str, system: str) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """
    用途：解析模型輸出；若不是合法 JSON，會自動做一次「修復重試」。
    注意：_try_parse_json 解析失敗時會回傳含 error 的 dict（不會丟例外），因此需同時檢查 error key。
    """
    try:
        parsed = _try_parse_json(content)
    except Exception:
        parsed = {"error": "unexpected_parse_exception", "raw_content": str(content)[:200]}

    if isinstance(parsed, dict) and "error" not in parsed:
        return parsed, usage

    content_snippet = content if len(content) <= 12000 else (content[:12000] + "\n...[TRUNCATED]...")
    repair, usage_repair = _openrouter_chat_completion(
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
        temperature=0.0,
        max_tokens=8000,
    )
    total_usage = {
        "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0) + int(usage_repair.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(usage.get("completion_tokens", 0) or 0) + int(usage_repair.get("completion_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0) + int(usage_repair.get("total_tokens", 0) or 0),
    }
    return _try_parse_json(repair), total_usage


def generate_consultant_notes(
    report_summary: Dict[str, Any],
    report_insights: Dict[str, Any],
    model_a: Optional[str] = None,
    model_b: Optional[str] = None,
    model_c: Optional[str] = None,
    status_callback: Optional[Callable[[str, str], None]] = None,
    on_consultant_done: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    version_fp: Optional[str] = None,
) -> Dict[str, Any]:
    """
    分別呼叫三位顧問（A:成效, B:視覺/文案, C:策略），回傳各自的 JSON。
    
    參數:
        on_consultant_done: 顧問完成時的回呼 (role, parsed_json)，用於即時 UI 更新
    """
    model_a = model_a or os.getenv("MODEL_CONSULTANT_A") or MODEL_CONSULTANT_A
    model_b = model_b or os.getenv("MODEL_CONSULTANT_B") or MODEL_CONSULTANT_B
    model_c = model_c or os.getenv("MODEL_CONSULTANT_C") or MODEL_CONSULTANT_C

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
        status_callback("A", model_a)
    out_a, usage_a = _openrouter_chat_completion(msgs_a, model=model_a, temperature=0.2, max_tokens=8000)
    j_a, usage_a_total = _parse_or_repair(out_a, usage_a, model_a, sys_a)
    try:
        week_id = str(report_summary.get("week_id") or "").strip() or None
        llm_monitor.log_call(
            LLMCall(
                timestamp=now_iso(),
                model=model_a,
                prompt_tokens=int(usage_a_total.get("prompt_tokens", 0) or 0),
                completion_tokens=int(usage_a_total.get("completion_tokens", 0) or 0),
                total_tokens=int(usage_a_total.get("total_tokens", 0) or 0),
                cost_usd=estimate_cost(
                    model_a,
                    int(usage_a_total.get("prompt_tokens", 0) or 0),
                    int(usage_a_total.get("completion_tokens", 0) or 0),
                ),
                function="generate_consultant_notes",
                week_id=week_id,
                extra={"step": "E", "consultant": "A", "version_fp": version_fp} if version_fp else {"step": "E", "consultant": "A"},
            )
        )
    except Exception:
        pass
    if on_consultant_done:
        on_consultant_done("A", j_a)

    if status_callback:
        status_callback("B", model_b)
    out_b, usage_b = _openrouter_chat_completion(msgs_b, model=model_b, temperature=0.2, max_tokens=8000)
    j_b, usage_b_total = _parse_or_repair(out_b, usage_b, model_b, sys_b)
    try:
        week_id = str(report_summary.get("week_id") or "").strip() or None
        llm_monitor.log_call(
            LLMCall(
                timestamp=now_iso(),
                model=model_b,
                prompt_tokens=int(usage_b_total.get("prompt_tokens", 0) or 0),
                completion_tokens=int(usage_b_total.get("completion_tokens", 0) or 0),
                total_tokens=int(usage_b_total.get("total_tokens", 0) or 0),
                cost_usd=estimate_cost(
                    model_b,
                    int(usage_b_total.get("prompt_tokens", 0) or 0),
                    int(usage_b_total.get("completion_tokens", 0) or 0),
                ),
                function="generate_consultant_notes",
                week_id=week_id,
                extra={"step": "E", "consultant": "B", "version_fp": version_fp} if version_fp else {"step": "E", "consultant": "B"},
            )
        )
    except Exception:
        pass
    if on_consultant_done:
        on_consultant_done("B", j_b)

    if status_callback:
        status_callback("C", model_c)
    out_c, usage_c = _openrouter_chat_completion(msgs_c, model=model_c, temperature=0.2, max_tokens=8000)
    j_c, usage_c_total = _parse_or_repair(out_c, usage_c, model_c, sys_c)
    try:
        week_id = str(report_summary.get("week_id") or "").strip() or None
        llm_monitor.log_call(
            LLMCall(
                timestamp=now_iso(),
                model=model_c,
                prompt_tokens=int(usage_c_total.get("prompt_tokens", 0) or 0),
                completion_tokens=int(usage_c_total.get("completion_tokens", 0) or 0),
                total_tokens=int(usage_c_total.get("total_tokens", 0) or 0),
                cost_usd=estimate_cost(
                    model_c,
                    int(usage_c_total.get("prompt_tokens", 0) or 0),
                    int(usage_c_total.get("completion_tokens", 0) or 0),
                ),
                function="generate_consultant_notes",
                week_id=week_id,
                extra={"step": "E", "consultant": "C", "version_fp": version_fp} if version_fp else {"step": "E", "consultant": "C"},
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


def run_visual_consultant(
    *,
    max_images: int = 6,
    model_b: Optional[str] = None,
) -> Dict[str, Any]:
    """
    視覺顧問（顧問 B）：自動讀取 `attached_assets/` 素材，交由多模態模型進行分析。

    - 目前僅將「圖片」送入多模態分析；影片會被掃描並回報數量，但不會上傳給模型。
    """
    media = scan_media_assets()
    images = get_top_images(media.images, n=max_images)
    model = model_b or os.getenv("MODEL_CONSULTANT_B") or MODEL_CONSULTANT_B

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

    parsed, _ = _parse_or_repair(raw, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, model, system)
    return {
        "visual_consultant_version": "visual_consultant.v1",
        "model": model,
        "images_sent": len(images),
        "videos_found": len(media.videos),
        "image_files": [p.name for p in images],
        "result": parsed,
    }
