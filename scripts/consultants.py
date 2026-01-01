import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

import requests


def _openrouter_chat_completion(messages, model: str, temperature: float = 0.2, max_tokens: int = 1600) -> str:
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
        "response_format": {"type": "json_object"},
    }

    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
    if resp.status_code >= 400:
        raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text}")

    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _try_parse_json(s: str) -> Dict[str, Any]:
    s = s.strip()
    first, last = s.find("{"), s.rfind("}")
    if first != -1 and last != -1 and last > first:
        s = s[first:last + 1]
    return json.loads(s)


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

    return {
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


def _consultant_prompt(role_name: str, focus: str) -> str:
    return (
        f"你是艾薇手工坊三顧問系統之一：{role_name}。\n"
        f"你的焦點：{focus}\n\n"
        "硬規則：\n"
        "1) 只能引用輸入 JSON 的數字，不可重新計算或改寫任何 KPI。\n"
        "2) 輸出必須是『單一 JSON object』，不要```、不要多餘文字。\n"
        "3) 每個結論都要寫『依據』：引用輸入中的哪個欄位/表格/現象。\n"
        "4) 必須包含『整體日預算動作』：針對『全帳戶平均每日花費節奏』，輸出 increase/hold/decrease + change_pct。\n"
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


def _parse_or_repair(content: str, model: str, system: str) -> Dict[str, Any]:
    try:
        return _try_parse_json(content)
    except Exception:
        repair = _openrouter_chat_completion(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": "你上一次輸出不是合法 JSON。請只輸出單一 JSON object，不要任何多餘字元。"},
                {"role": "user", "content": content},
            ],
            model=model,
            temperature=0.0,
            max_tokens=1600,
        )
        return _try_parse_json(repair)


def run_three_consultants(
    report_summary: Dict[str, Any],
    report_insights: Dict[str, Any],
    model_a: Optional[str] = None,
    model_b: Optional[str] = None,
    model_c: Optional[str] = None,
) -> Dict[str, Any]:
    model_a = model_a or os.getenv("OPENROUTER_MODEL_CONSULTANT_A") or "openai/gpt-4o-mini"
    model_b = model_b or os.getenv("OPENROUTER_MODEL_CONSULTANT_B") or "openai/gpt-4o-mini"
    model_c = model_c or os.getenv("OPENROUTER_MODEL_CONSULTANT_C") or "openai/gpt-4o-mini"

    payload = _compact_inputs(report_summary, report_insights)

    # A：成效與擴量
    sys_a = _consultant_prompt("顧問A｜成效與擴量", "在不踩紅線下提高 ROAS 與可控擴量；提出預算與結構調整。")
    usr_a = _consultant_task("A") + "\n輸入：\n" + json.dumps(payload, ensure_ascii=False)
    out_a = _openrouter_chat_completion([{"role": "system", "content": sys_a}, {"role": "user", "content": usr_a}], model=model_a)

    # B：效率與風險控管
    sys_b = _consultant_prompt("顧問B｜效率與風險控管", "用護欄/止損線確保不踩紅線；指出數據缺口與審計點。")
    usr_b = _consultant_task("B") + "\n輸入：\n" + json.dumps(payload, ensure_ascii=False)
    out_b = _openrouter_chat_completion([{"role": "system", "content": sys_b}, {"role": "user", "content": usr_b}], model=model_b)

    # C：創意與轉換
    sys_c = _consultant_prompt("顧問C｜創意與轉換", "用素材與 CRO 提升轉換；針對 Ads 層 ranking/訊息/落地頁給行動。")
    usr_c = _consultant_task("C") + "\n輸入：\n" + json.dumps(payload, ensure_ascii=False)
    out_c = _openrouter_chat_completion([{"role": "system", "content": sys_c}, {"role": "user", "content": usr_c}], model=model_c)

    j_a = _parse_or_repair(out_a, model_a, sys_a)
    j_b = _parse_or_repair(out_b, model_b, sys_b)
    j_c = _parse_or_repair(out_c, model_c, sys_c)

    return {
        "consultants_version": "consultants.v1",
        "week_id": report_summary.get("week_id"),
        "date_range": report_summary.get("date_range"),
        "avg_daily_spend_twd_calc": payload.get("meta_avg_daily_spend_twd_calc"),
        "consultant_A": j_a,
        "consultant_B": j_b,
        "consultant_C": j_c,
    }
