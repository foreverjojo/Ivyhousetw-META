import json
import os
from typing import Any, Dict, Optional

import requests


def _openrouter_chat_completion(
    messages,
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 1200,
) -> str:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE") or "https://openrouter.ai/api/v1"
    url = base_url.rstrip("/") + "/chat/completions"

    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY (or OPENROUTER_API_KEY). Please set it in Replit Secrets.")

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
        "response_format": {"type": "json_object"},
    }

    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=90)
    if resp.status_code >= 400:
        raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text}")

    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _try_parse_json(s: str) -> Dict[str, Any]:
    s = s.strip()
    # 保險：避免模型加上多餘文字
    first = s.find("{")
    last = s.rfind("}")
    if first != -1 and last != -1 and last > first:
        s = s[first:last + 1]
    return json.loads(s)


def generate_report_insights(
    report_summary: Dict[str, Any],
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    只做「洞察解讀」，不算數字。輸出必須是 JSON object（無 code fence）。
    """
    model = model or os.getenv("OPENROUTER_MODEL_INSIGHTS") or "openai/gpt-4o-mini"

    # 將輸入控制在「足夠判讀」的大小
    compact_input = {
        "schema_version": report_summary.get("schema_version"),
        "week_id": report_summary.get("week_id"),
        "date_range": report_summary.get("date_range"),
        "kpi": report_summary.get("kpi", {}),
        "tables": report_summary.get("tables", {}),
        "missing_data": report_summary.get("missing_data", {}),
    }

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
        "3) executive_summary: 3-6 條一句話結論（可引用輸入數字）\n"
        "4) what_worked: 3-6 條（指出 top adsets/ads 的共同特徵，避免臆測）\n"
        "5) what_didnt: 3-6 條（指出 worst adsets/ads 的共同特徵，避免臆測）\n"
        "6) diagnostics: traffic/conversion/creative 三段，各 2-4 句（只做判讀，不算數字）\n"
        "7) actions: 5-10 條可執行任務，每條包含 owner/task/why/kpi/stoploss\n"
        "8) data_issues: 缺欄位/可疑空值/需要固定命名規則的提醒\n"
        "9) open_questions: 3-6 條（下次週會要確認的事）\n\n"
        "報告輸入：\n"
        f"{json.dumps(compact_input, ensure_ascii=False)}"
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    content = _openrouter_chat_completion(messages, model=model)

    try:
        out = _try_parse_json(content)
    except Exception:
        # 失敗就做一次修復重試
        repair_messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "你上一次輸出不是合法 JSON。請只輸出『單一 JSON object』，不要任何多餘字元。"},
            {"role": "user", "content": content},
        ]
        content2 = _openrouter_chat_completion(repair_messages, model=model, temperature=0.0, max_tokens=1200)
        out = _try_parse_json(content2)

    # 最小保險：補必要欄位
    out.setdefault("insights_version", "insights.v1")
    out.setdefault("week_id", report_summary.get("week_id"))
    out.setdefault("date_range", report_summary.get("date_range"))
    return out
