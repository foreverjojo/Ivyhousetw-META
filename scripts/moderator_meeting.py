"""
檔案用途：週會 Markdown 輸出（meeting.md）模組
職責：
  - 將 workflow_state.json + report_summary/report_insights 組裝成可讀的週會紀要
  - 盡量使用 deterministic 方式渲染，避免 LLM 產生的格式飄移
"""

import json
from pathlib import Path
from typing import Any, Dict


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
    weekly_changes = str(weekly_changes).strip() if weekly_changes is not None else ""
    weekly_changes_md = weekly_changes if weekly_changes else "（未填）"

    note = mi.get("note_for_consultants", "")
    note = str(note).strip() if note is not None else ""
    note_md = note if note else "（未填）"

    updated_at = v("updated_at")

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
    guardrail_check = (
        workflow_state.get("guardrail_check", workflow_state.get("guardrails", {})) or {}
    )
    if isinstance(guardrail_check, dict):
        guardrail = guardrail_check.get("guardrails", guardrail_check) or {}
    else:
        guardrail = {}
    decisions = workflow_state.get("decisions", [])
    actions = workflow_state.get("department_actions", {})
    risks = workflow_state.get("risks", [])
    validation = workflow_state.get("validation_plan", {})

    meta = report_summary.get("kpi", {}).get("meta", {}) or {}
    web = report_summary.get("kpi", {}).get("web", {}) or {}

    lines: list[str] = []
    lines.append(f"# Meta 週會｜{week_id}（{date_range}）")
    lines.append("")

    lines.append(_strategy_snapshot_md(report_summary))
    lines.append("")

    lines.append("## Meeting Summary（做 / 不做 / 延後）")
    if isinstance(decisions, list) and decisions:
        for i, d in enumerate(decisions, 1):
            if isinstance(d, dict):
                decision = d.get("decision") or d.get("action") or d.get("item") or d.get("do")
                reason = d.get("reason") or d.get("rationale") or d.get("because")
                impact = d.get("impact") or d.get("result") or d.get("expected_impact")
                parts = [p for p in [decision, reason, impact] if p]
                lines.append(f"- {i}. " + "｜".join([str(p) for p in parts]))
            else:
                lines.append(f"- {i}. {d}")
    else:
        lines.append("- （待補）")
    lines.append("")

    lines.append("## Guardrail Check")
    lines.append("### Tier1（紅線）")
    t1 = guardrail.get("tier1", {})
    if isinstance(t1, dict) and t1:
        for k, v in t1.items():
            lines.append(
                f"- {k}: {v.get('status')}（值={v.get('value')}｜門檻={v.get('threshold')}｜依據={v.get('basis')}）"
            )
    else:
        lines.append("- （待補）")
    lines.append("")

    lines.append("### Tier2（目標）")
    t2 = guardrail.get("tier2", {})
    if isinstance(t2, dict) and t2:
        for k, v in t2.items():
            lines.append(
                f"- {k}: {v.get('status')}（值={v.get('value')}｜門檻={v.get('threshold')}｜依據={v.get('basis')}）"
            )
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
    added = False
    idx = 1
    if isinstance(cs, list) and cs:
        for s in cs[:10]:
            if isinstance(s, str) and s.strip():
                lines.append(f"- {idx}. {s.strip()}")
                idx += 1
                added = True
    elif isinstance(cs, dict):
        consensus = (
            cs.get("consensus")
            or cs.get("summary")
            or cs.get("consensus_points")
            or cs.get("共識")
            or cs.get("共识")
            or ""
        )
        if isinstance(consensus, str) and consensus.strip():
            lines.append(f"- {idx}. {consensus.strip()}")
            idx += 1
            added = True
        elif isinstance(consensus, list) and consensus:
            for it in consensus[:10]:
                if isinstance(it, dict):
                    point = (
                        it.get("point")
                        or it.get("summary")
                        or it.get("item")
                        or it.get("text")
                        or ""
                    )
                    if isinstance(point, str) and point.strip():
                        lines.append(f"- {idx}. {point.strip()}")
                        idx += 1
                        added = True
                elif isinstance(it, str) and it.strip():
                    lines.append(f"- {idx}. {it.strip()}")
                    idx += 1
                    added = True

        divergence = (
            cs.get("divergence")
            or cs.get("disagreements")
            or cs.get("differences")
            or cs.get("分歧")
            or cs.get("分歧點")
            or cs.get("分歧点")
            or []
        )
        if isinstance(divergence, str) and divergence.strip():
            lines.append(f"- {idx}. 分歧：{divergence.strip()}")
            idx += 1
            added = True
        elif isinstance(divergence, list) and divergence:
            for it in divergence[:10]:
                if isinstance(it, dict):
                    point = (
                        it.get("point")
                        or it.get("summary")
                        or it.get("item")
                        or it.get("text")
                        or ""
                    )
                    if isinstance(point, str) and point.strip():
                        lines.append(f"- {idx}. 分歧：{point.strip()}")
                        idx += 1
                        added = True
                elif isinstance(it, str) and it.strip():
                    lines.append(f"- {idx}. 分歧：{it.strip()}")
                    idx += 1
                    added = True

        action_items = cs.get("action_items") or cs.get("items") or []
        if isinstance(action_items, list) and action_items:
            for it in action_items[:10]:
                if isinstance(it, dict):
                    item = it.get("item") or it.get("task") or it.get("title") or ""
                    owner = it.get("owner") or it.get("owner_role") or ""
                    due = it.get("due_by") or it.get("due") or ""
                    parts = [
                        str(p).strip()
                        for p in [
                            item,
                            f"負責：{owner}" if owner else None,
                            f"期限：{due}" if due else None,
                        ]
                        if p
                    ]
                    if parts:
                        lines.append(f"- {idx}. " + "｜".join(parts))
                        idx += 1
                        added = True
                elif isinstance(it, str) and it.strip():
                    lines.append(f"- {idx}. {it.strip()}")
                    idx += 1
                    added = True

        open_questions = cs.get("open_questions") or cs.get("questions") or []
        if isinstance(open_questions, list) and open_questions:
            for q in open_questions[:5]:
                if isinstance(q, str) and q.strip():
                    lines.append(f"- {idx}. 待釐清：{q.strip()}")
                    idx += 1
                    added = True
    elif isinstance(cs, str) and cs.strip():
        lines.append(f"- {idx}. {cs.strip()}")
        added = True

    if not added:
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
        ais = workflow_state.get("action_items")
        if isinstance(ais, list) and ais:
            for it in ais:
                if isinstance(it, dict):
                    lines.append(
                        f"- 任務：{it.get('title')}｜負責：{it.get('owner')}｜狀態：{it.get('status')}｜成功條件：{it.get('success_criteria')}"
                    )
                else:
                    lines.append(f"- {it}")
        else:
            lines.append("- （待補）")
        lines.append("")

    lines.append("## Risks & Alternatives（Top 3）")
    risks_src = risks
    if (not isinstance(risks_src, list) or not risks_src) and isinstance(cs, dict):
        cs_risks = cs.get("risks") or []
        if isinstance(cs_risks, list) and cs_risks:
            risks_src = cs_risks

    if isinstance(risks_src, list) and risks_src:
        for r in risks_src:
            if isinstance(r, dict):
                desc = r.get("description") or r.get("risk") or r
                prob = r.get("probability")
                impact = r.get("impact")
                alt = r.get("alternative")
                parts = [f"風險：{desc}"]
                if prob is not None:
                    parts.append(f"機率：{prob}")
                if impact is not None:
                    parts.append(f"影響：{impact}")
                if alt:
                    parts.append(f"替代：{alt}")
                lines.append("- " + "｜".join([str(p) for p in parts]))
            else:
                lines.append(f"- 風險：{r}")
    else:
        lines.append("- （待補）")
    lines.append("")

    lines.append("## Validation Plan（3天 / 7天 / 14天）")
    if isinstance(validation, dict) and validation:

        def pick_validation(day_key: str):
            day = str(day_key).replace("天", "").strip()
            candidates = [
                day_key,
                f"{day}d",
                f"{day}_days",
                f"{day}days",
                f"day{day}",
                f"day_{day}",
                f"d{day}",
                f"D{day}",
            ]
            for kk in candidates:
                if kk in validation:
                    return validation.get(kk)
            return None

        for k in ["3天", "7天", "14天"]:
            v = pick_validation(k)
            lines.append(f"### {k}")
            if isinstance(v, list) and v:
                for vv in v:
                    if isinstance(vv, dict):
                        # 支援 nested dict 結構
                        indicator = vv.get("indicator", "")
                        threshold = vv.get("threshold", "")
                        ok = vv.get("達標") or vv.get("pass") or vv.get("達成") or ""
                        ng = vv.get("未達") or vv.get("fail") or vv.get("止損") or ""
                        lines.append(
                            f"- 指標：{indicator}｜門檻：{threshold}｜達標：{ok}｜未達：{ng}"
                        )
                    else:
                        lines.append(f"- {vv}")
            elif isinstance(v, dict):
                # 單一 dict 結構（常見 LLM 輸出格式）
                indicator = v.get("indicator", "")
                threshold = v.get("threshold", "")
                ok = v.get("達標") or v.get("pass") or v.get("達成") or ""
                ng = v.get("未達") or v.get("fail") or v.get("止損") or ""
                lines.append(f"- 指標：{indicator}｜門檻：{threshold}｜達標：{ok}｜未達：{ng}")
            elif v:
                lines.append(f"- {v}")
            else:
                lines.append("- （待補）")
    else:
        lines.append("- （待補）")
    lines.append("")

    return "\n".join(lines)


def write_artifacts(hist_dir: Path, meeting_md: str, workflow_state: Dict[str, Any]) -> None:
    (hist_dir / "meeting.md").write_text(meeting_md, encoding="utf-8")
    (hist_dir / "workflow_state.json").write_text(
        json.dumps(workflow_state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
