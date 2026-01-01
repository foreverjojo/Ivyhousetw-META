import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests


def _get_manual_inputs(report_summary: dict) -> dict:
    """
    優先讀取 app.py 注入的 report_summary["_context"]["manual_inputs"]
    其次讀取 report_summary["manual_inputs"]（保險）
    """
    if not isinstance(report_summary, dict):
        return {}

    ctx = report_summary.get("_context") or {}
    mi = ctx.get("manual_inputs")
    if isinstance(mi, dict) and mi:
        return mi

    mi2 = report_summary.get("manual_inputs")
    if isinstance(mi2, dict) and mi2:
        return mi2

    return {}


def _strategy_snapshot_md(report_summary: dict) -> str:
    """
    固定格式的「策略快照段落」
    - 若全空：仍輸出段落，但標註未填，避免會議漏上下文
    """
    mi = _get_manual_inputs(report_summary)

    def v(key: str) -> str:
        val = mi.get(key, "")
        if val is None:
            val = ""
        val = str(val).strip()
        return val if val else "（未填）"

    buying_type = v("buying_type")
    optimization_goal = v("optimization_goal")
    billing_event = v("billing_event")
    weekly_changes = mi.get("weekly_changes", "")
    weekly_changes = (str(weekly_changes).strip() if weekly_changes is not None else "")
    weekly_changes_md = weekly_changes if weekly_changes else "（未填）"

    note = mi.get("note_for_consultants", "")
    note = (str(note).strip() if note is not None else "")
    note_md = note if note else "（未填）"

    updated_at = v("updated_at")

    # 多行文字用 markdown blockquote，閱讀體驗最好
    def to_blockquote(text: str) -> str:
        lines = [ln.rstrip() for ln in str(text).splitlines()]
        lines = [ln for ln in lines if ln.strip() != ""]
        if not lines:
            return "> （未填）"
        return "\n".join([f"> {ln}" for ln in lines])

    snapshot = f"""## 策略快照（本週手動輸入）

- Buying type：**{buying_type}**
- Optimization goal：**{optimization_goal}**
- Billing event：**{billing_event}**
- 更新時間：{updated_at}

**本週重大調整**
{to_blockquote(weekly_changes_md)}

**給顧問/主持人的備註（上下文）**
{to_blockquote(note_md)}
"""
    return snapshot


def _openrouter_chat_completion(
    messages,
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 2200,
) -> str:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE") or "https://openrouter.ai/api/v1"
    url = base_url.rstrip("/") + "/chat/completions"

    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY (or OPENROUTER_API_KEY). Please set it in Replit Secrets.")

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
        # 讓 workflow_state 100% 可 parse（OpenAI/部分路由支援）
        "response_format": {"type": "json_object"},
    }

    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
    if resp.status_code >= 400:
        raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text}")

    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _try_parse_json(s: str) -> Dict[str, Any]:
    s = s.strip()
    first = s.find("{")
    last = s.rfind("}")
    if first != -1 and last != -1 and last > first:
        s = s[first:last + 1]
    return json.loads(s)


def _guardrail_check(report_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    用你專案的硬護欄口徑做最基本判斷（只用輸入數字，不重算）。
    目前：Meta ROAS、官網 AOV 兩個示範欄位。
    """
    meta = report_summary.get("kpi", {}).get("meta", {}) or {}
    web = report_summary.get("kpi", {}).get("web", {}) or {}

    roas = meta.get("roas_calc", 0.0) or 0.0
    web_aov = web.get("aov_twd_calc", 0.0) or 0.0

    tier1 = {
        "meta_roas_break_even": {
            "threshold": 1.90,
            "value": roas,
            "status": "pass" if float(roas) >= 1.90 else "fail",
            "basis": "官網損益兩平 ROAS=1.90（專案真值口徑）",
        }
    }

    tier2 = {
        "meta_roas_target": {
            "threshold": 3.5,
            "value": roas,
            "status": "pass" if float(roas) >= 3.5 else "fail",
            "basis": "Tier2 目標 ROAS≥3.5（專案口徑）",
        },
        "web_aov_target": {
            "threshold": 1650,
            "value": web_aov,
            "status": "pass" if float(web_aov) >= 1650 else "fail",
            "basis": "Tier2 目標 客單≥$1,650（專案口徑）",
        },
    }

    return {"tier1": tier1, "tier2": tier2}


def build_workflow_state(
    report_summary: Dict[str, Any],
    report_insights: Dict[str, Any],
    consultant_notes: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Moderator 輸出 workflow_state.json（乾淨 JSON）
    - 只引用輸入中的數字，不重算 KPI
    - 可選整合三顧問 consultant_notes
    """
    model = model or os.getenv("OPENROUTER_MODEL_MODERATOR") or "openai/gpt-4o-mini"

    guardrails = _guardrail_check(report_summary)

    compact_input = {
        "week_id": report_summary.get("week_id"),
        "date_range": report_summary.get("date_range"),
        "kpi": report_summary.get("kpi", {}),
        "tables": report_summary.get("tables", {}),
        "missing_data": report_summary.get("missing_data", {}),
        "consultants": consultant_notes or {},
        "insights": report_insights,
        "guardrails": guardrails,
    }

    system = (
        "你是艾薇手工坊的週會 Moderator（決策與交辦）。"
        "你只能引用輸入中的數字，不可重新計算或改寫 KPI。"
        "你要輸出『單一 JSON object』作為 workflow_state.json。"
        "禁止輸出```，禁止多餘文字。語言繁中。"
        "輸出必須可被 JSON.parse。"
    )

    user = (
        "請根據輸入 JSON 產出 workflow_state.json，欄位要求：\n"
        "1) schema_version: 'workflow_state.v1'\n"
        "2) week_id, date_range\n"
        "3) kpi_snapshot: 直接放入 meta/web 的 KPI（沿用輸入）\n"
        "4) decisions: 3-6 條（做/不做/延後 + 理由 + 影響）\n"
        "5) guardrail_check: 直接沿用輸入 guardrails（可補充風險等級與替代方案文字）\n"
        "6) consultant_summary: 摘要三顧問『共識』與『分歧』，各 3-6 條（每條附依據，依據可引用 consultants/insights/tables）\n"
        "7) department_actions: 必含 GM/Finance/E-commerce/Marketing/Fulfillment，每個部門 2-5 任務\n"
        "   每個任務包含：task, owner_role, deliverable, due, kpi, stoploss\n"
        "8) risks: Top3（描述/機率/影響/緩解/替代方案）\n"
        "9) validation_plan: 3天/7天/14天（指標/門檻/達標→下一步/未達→止損）\n"
        "10) artifacts: 檔名清單（inputs.json, report_summary.json, report_insights.json, consultant_notes.json, meeting.md, workflow_state.json）\n\n"
        "輸入：\n"
        f"{json.dumps(compact_input, ensure_ascii=False)}"
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    content = _openrouter_chat_completion(messages, model=model, temperature=0.2, max_tokens=2400)

    try:
        out = _try_parse_json(content)
    except Exception:
        repair_messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "你上一次輸出不是合法 JSON。請只輸出『單一 JSON object』，不要任何多餘字元。"},
            {"role": "user", "content": content},
        ]
        content2 = _openrouter_chat_completion(repair_messages, model=model, temperature=0.0, max_tokens=2400)
        out = _try_parse_json(content2)

    out.setdefault("schema_version", "workflow_state.v1")
    out.setdefault("week_id", report_summary.get("week_id"))
    out.setdefault("date_range", report_summary.get("date_range"))
    return out


def build_meeting_markdown(
    workflow_state: Dict[str, Any],
    report_summary: Dict[str, Any],
    report_insights: Dict[str, Any],
) -> str:
    """
    meeting.md：人看的週會紀要（Markdown）
    deterministic 組裝，避免 markdown 被 LLM 截斷或格式亂飄。
    """
    week_id = workflow_state.get("week_id", "")
    date_range = workflow_state.get("date_range", "")
    guardrail = workflow_state.get("guardrail_check", workflow_state.get("guardrails", {})) or {}
    decisions = workflow_state.get("decisions", [])
    actions = workflow_state.get("department_actions", {})
    risks = workflow_state.get("risks", [])
    validation = workflow_state.get("validation_plan", {})

    meta = report_summary.get("kpi", {}).get("meta", {}) or {}
    web = report_summary.get("kpi", {}).get("web", {}) or {}

    lines = []
    lines.append(f"# Meta 週會｜{week_id}（{date_range}）")
    lines.append("")

    # ✅ 新增：策略快照段落（固定輸出）
    lines.append(_strategy_snapshot_md(report_summary))
    lines.append("")

    lines.append("## Meeting Summary（做 / 不做 / 延後）")
    if isinstance(decisions, list) and decisions:
        for i, d in enumerate(decisions, 1):
            lines.append(f"- {i}. {d}")
    else:
        lines.append("- （待補）")
    lines.append("")

    lines.append("## Guardrail Check")
    lines.append("### Tier1（紅線）")
    t1 = guardrail.get("tier1", {})
    if isinstance(t1, dict) and t1:
        for k, v in t1.items():
            lines.append(f"- {k}: {v.get('status')}（值={v.get('value')}｜門檻={v.get('threshold')}｜依據={v.get('basis')}）")
    else:
        lines.append("- （待補）")
    lines.append("")

    lines.append("### Tier2（目標）")
    t2 = guardrail.get("tier2", {})
    if isinstance(t2, dict) and t2:
        for k, v in t2.items():
            lines.append(f"- {k}: {v.get('status')}（值={v.get('value')}｜門檻={v.get('threshold')}｜依據={v.get('basis')}）")
    else:
        lines.append("- （待補）")
    lines.append("")

    lines.append("## KPI Snapshot（輸入真值）")
    lines.append(f"- Meta Spend (TWD): {meta.get('spend_twd')}")
    lines.append(f"- Meta Purchase Value (TWD): {meta.get('purchase_value_twd')}")
    lines.append(f"- Meta ROAS (calc): {meta.get('roas_calc')}")
    lines.append(f"- Meta Purchases: {meta.get('purchases')}")
    lines.append(f"- Web Revenue (TWD): {web.get('revenue_twd')}")
    lines.append(f"- Web Orders: {web.get('orders')}")
    lines.append(f"- Web AOV (calc): {web.get('aov_twd_calc')}")
    lines.append("")

    lines.append("## Key Insights（來自 report_insights.json）")
    exec_sum = report_insights.get("executive_summary", [])
    if isinstance(exec_sum, list) and exec_sum:
        for i, s in enumerate(exec_sum, 1):
            lines.append(f"- {i}. {s}")
    else:
        lines.append("- （待補）")
    lines.append("")

    lines.append("## 三顧問摘要（共識 / 分歧）")
    cs = workflow_state.get("consultant_summary", [])
    if isinstance(cs, list) and cs:
        for i, s in enumerate(cs, 1):
            lines.append(f"- {i}. {s}")
    else:
        lines.append("- （待補）")
    lines.append("")

    lines.append("## Department Actions（核心 5 主管）")
    if isinstance(actions, dict) and actions:
        for dept, items in actions.items():
            lines.append(f"### {dept}")
            if isinstance(items, list) and items:
                for it in items:
                    lines.append(
                        f"- 任務：{it.get('task')}｜交付物：{it.get('deliverable')}｜截止：{it.get('due')}｜KPI：{it.get('kpi')}｜止損：{it.get('stoploss')}"
                    )
            else:
                lines.append("- （待補）")
            lines.append("")
    else:
        lines.append("- （待補）")
        lines.append("")

    lines.append("## Risks & Alternatives（Top 3）")
    if isinstance(risks, list) and risks:
        for r in risks:
            lines.append(f"- 風險：{r}")
    else:
        lines.append("- （待補）")
    lines.append("")

    lines.append("## Validation Plan（3天 / 7天 / 14天）")
    if isinstance(validation, dict) and validation:
        for k in ["3天", "7天", "14天"]:
            v = validation.get(k) or validation.get(k.replace("天", "d")) or None
            lines.append(f"### {k}")
            lines.append(f"- {v}" if v else "- （待補）")
    else:
        lines.append("- （待補）")
    lines.append("")

    return "\n".join(lines)


def write_artifacts(hist_dir: Path, meeting_md: str, workflow_state: Dict[str, Any]) -> None:
    (hist_dir / "meeting.md").write_text(meeting_md, encoding="utf-8")
    (hist_dir / "workflow_state.json").write_text(
        json.dumps(workflow_state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
