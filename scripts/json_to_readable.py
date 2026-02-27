# 用途：將 Step C/E 產出的 JSON 轉為使用者可讀的自然語句｜scripts/json_to_readable.py
"""
職責：
  - render_report_insights(): 將 report_insights.json 轉為摘要段落
  - render_consultant_note(): 將單一顧問的 JSON 轉為可讀分析
原則：
  - 純 deterministic，無 LLM 呼叫
  - 所有輸出為繁體中文
  - 輸出格式為 Markdown（供 Streamlit 渲染）
"""

from typing import Any


def _looks_like_consultant_task_v1(note: dict[str, Any]) -> bool:
    if not isinstance(note, dict):
        return False
    for k in [
        "overall_budget_action",
        "adset_ads_actions",
        "next_7d_actions",
        "opportunities",
        "questions",
    ]:
        if k in note:
            return True
    return False


def _safe_text(v: Any) -> str:
    s = "" if v is None else str(v)
    return s.strip()


def _pick_text(item: Any) -> str:
    if item is None:
        return ""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for k in ["text", "point", "item", "summary", "conclusion", "why", "rationale"]:
            t = _safe_text(item.get(k))
            if t:
                return t
        return _safe_text(item)
    return _safe_text(item)


def _as_lines(value: Any, *, max_items: int = 8) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        t = value.strip()
        return [t] if t else []
    if isinstance(value, list):
        out: list[str] = []
        for it in value[:max_items]:
            t = _pick_text(it)
            if t:
                out.append(t)
        return out
    t = _pick_text(value)
    return [t] if t else []


def _render_consultant_task_v1(note: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    summary = _as_lines(note.get("summary"), max_items=6)
    if summary:
        lines.append("### 結論摘要")
        for s in summary:
            lines.append(f"- {s}")
        lines.append("")

    opp = _as_lines(note.get("opportunities"), max_items=6)
    if opp:
        lines.append("### 擴量 / 優化機會")
        for s in opp:
            lines.append(f"- {s}")
        lines.append("")

    oba = note.get("overall_budget_action")
    if isinstance(oba, dict) and oba:
        action = _safe_text(oba.get("action"))
        change_pct = oba.get("change_pct")
        rationale = _safe_text(oba.get("rationale"))
        headline_parts = [
            p for p in [action, f"{change_pct}%" if change_pct is not None else ""] if p
        ]
        headline = " ".join(headline_parts) if headline_parts else "（未提供）"
        lines.append("### 整體日預算動作（全帳戶平均每日花費節奏）")
        lines.append(f"- 建議：{headline}")
        if rationale:
            lines.append(f"- 依據：{rationale}")
        lines.append("")

    actions = note.get("adset_ads_actions")
    if isinstance(actions, list) and actions:
        lines.append("### Adset / Ad 層級動作")
        for it in actions[:10]:
            if not isinstance(it, dict):
                t = _pick_text(it)
                if t:
                    lines.append(f"- {t}")
                continue
            level = _safe_text(it.get("level"))
            name = _safe_text(it.get("name"))
            action = _safe_text(it.get("action"))
            why = _safe_text(it.get("why"))
            kpi = _safe_text(it.get("kpi"))
            stoploss = _safe_text(it.get("stoploss"))

            head = " ".join([p for p in [f"[{level}]" if level else "", name, action] if p]).strip()
            if not head:
                head = _safe_text(it)
            if not head:
                continue
            tail_parts = []
            if why:
                tail_parts.append(f"Why：{why}")
            if kpi:
                tail_parts.append(f"KPI：{kpi}")
            if stoploss:
                tail_parts.append(f"止損：{stoploss}")
            tail = "；".join(tail_parts)
            lines.append(f"- {head}" + (f"（{tail}）" if tail else ""))
        lines.append("")

    next7 = note.get("next_7d_actions")
    if isinstance(next7, list) and next7:
        lines.append("### 接下來 7 天待辦")
        for it in next7[:6]:
            if not isinstance(it, dict):
                t = _pick_text(it)
                if t:
                    lines.append(f"- {t}")
                continue
            task = _safe_text(it.get("task") or it.get("title"))
            owner = _safe_text(it.get("owner_role") or it.get("owner"))
            deliverable = _safe_text(it.get("deliverable"))
            due = _safe_text(it.get("due"))
            kpi = _safe_text(it.get("kpi"))
            stoploss = _safe_text(it.get("stoploss"))
            why = _safe_text(it.get("why"))
            head = "｜".join([p for p in [owner, task] if p]) or task or _safe_text(it)
            if not head:
                continue
            extras = []
            if deliverable:
                extras.append(f"交付物：{deliverable}")
            if due:
                extras.append(f"截止：{due}")
            if kpi:
                extras.append(f"KPI：{kpi}")
            if stoploss:
                extras.append(f"止損：{stoploss}")
            if why:
                extras.append(f"Why：{why}")
            lines.append(f"- {head}" + (f"（{'；'.join(extras)}）" if extras else ""))
        lines.append("")

    risks = note.get("risks")
    if isinstance(risks, list) and risks:
        lines.append("### 風險與備援")
        for it in risks[:4]:
            if not isinstance(it, dict):
                t = _pick_text(it)
                if t:
                    lines.append(f"- {t}")
                continue
            risk = _safe_text(it.get("risk") or it.get("description"))
            prob = _safe_text(it.get("probability"))
            impact = _safe_text(it.get("impact"))
            mitigation = _safe_text(it.get("mitigation"))
            alt = _safe_text(it.get("alternative"))
            head = risk or _safe_text(it)
            if not head:
                continue
            tail = "；".join(
                [
                    p
                    for p in [
                        f"機率：{prob}" if prob else "",
                        f"影響：{impact}" if impact else "",
                        f"緩解：{mitigation}" if mitigation else "",
                        f"替代：{alt}" if alt else "",
                    ]
                    if p
                ]
            )
            lines.append(f"- {head}" + (f"（{tail}）" if tail else ""))
        lines.append("")

    qs = note.get("questions")
    if isinstance(qs, list) and qs:
        lines.append("### 下次週會要確認")
        for q in qs[:6]:
            t = _pick_text(q)
            if t:
                lines.append(f"- {t}")
        lines.append("")

    return lines


def render_skeleton_insight() -> str:
    """生成 Step C 的骨架屏（Skeleton Screen）"""
    return """
## 📊 本週洞察摘要

_ AI 正在分析您的廣告數據..._

### 🔍 關鍵發現
- 正在生成中...

###  有效策略
- 正在生成中...

###  需改善項目
- 正在生成中...

### 📋 行動建議 (6 項)
- 正在生成中...
"""


def render_report_insights(ri: dict[str, Any]) -> str:
    """
    將 report_insights.json 轉為自然語句摘要

    參數:
        ri: report_insights.json 的內容

    回傳:
        Markdown 格式的可讀摘要

    範例輸出:
        📊 本週洞察摘要
        - 總曝光量：1,234,567 次
        - 最佳廣告組：「夏季促銷」，ROAS 達 3.45
    """
    if isinstance(ri, dict) and "executive_summary" in ri:
        return _render_report_insights_v1(ri)

    lines = ["## 📊 本週洞察摘要\n"]

    # 提取 summary（若存在）
    summary = ri.get("summary", "")
    if summary:
        lines.append(f"_{summary}_\n")

    # 提取 key_insights
    key_insights = ri.get("key_insights", [])
    if key_insights:
        lines.append("### 🔍 關鍵發現")
        for i, insight in enumerate(key_insights[:5], 1):
            if isinstance(insight, str):
                lines.append(f"{i}. {insight}")
            elif isinstance(insight, dict):
                text = insight.get("text") or insight.get("insight") or str(insight)
                lines.append(f"{i}. {text}")

    # 提取 recommendations（若存在）
    recommendations = ri.get("recommendations", [])
    if recommendations:
        lines.append("\n### 💡 建議行動")
        for rec in recommendations[:3]:
            if isinstance(rec, str):
                lines.append(f"- {rec}")
            elif isinstance(rec, dict):
                text = rec.get("text") or rec.get("action") or str(rec)
                lines.append(f"- {text}")

    # 提取 performance_highlights（若存在）
    highlights = ri.get("performance_highlights", {})
    if highlights:
        lines.append("\n### 📈 績效亮點")
        for key, value in list(highlights.items())[:5]:
            label = _translate_key(key)
            formatted_value = _format_value(value)
            lines.append(f"- **{label}**：{formatted_value}")

    # 若幾乎沒有內容，提供 fallback
    if len(lines) <= 2:
        lines.append("_洞察內容正在生成中..._")

    return "\n".join(lines)


def _render_report_insights_v1(ri: dict[str, Any]) -> str:
    """支援 insights.v1 結構的可讀轉換（deterministic，不做任何 KPI 重算）。"""
    week_id = str(ri.get("week_id") or "").strip()
    date_range = str(ri.get("date_range") or "").strip()

    title = "## 📊 本週洞察摘要"
    if week_id or date_range:
        meta = "｜".join([x for x in [week_id, date_range] if x])
        title = f"{title}（{meta}）"

    lines = [title, ""]

    executive = ri.get("executive_summary") or []
    if isinstance(executive, list) and executive:
        lines.append("### 🔍 關鍵發現")
        for i, it in enumerate(executive[:5], 1):
            lines.append(f"{i}. {_safe_str(it)}")
        lines.append("")

    what_worked = ri.get("what_worked") or []
    if isinstance(what_worked, list) and what_worked:
        lines.append("### ✅ 有效策略")
        for i, it in enumerate(what_worked[:5], 1):
            lines.append(f"{i}. {_safe_str(it)}")
        lines.append("")

    what_didnt = ri.get("what_didnt") or []
    if isinstance(what_didnt, list) and what_didnt:
        lines.append("### ⚠️ 需改善項目")
        for i, it in enumerate(what_didnt[:5], 1):
            lines.append(f"{i}. {_safe_str(it)}")
        lines.append("")

    diagnostics = ri.get("diagnostics") or {}
    if isinstance(diagnostics, dict) and diagnostics:
        lines.append("### 🧪 診斷")
        for key, label in [("traffic", "流量"), ("conversion", "轉換"), ("creative", "素材")]:
            v = diagnostics.get(key)
            if v is None:
                continue
            if isinstance(v, list):
                text = "；".join(_safe_str(x) for x in v if _safe_str(x))
            else:
                text = _safe_str(v)
            if text:
                lines.append(f"- **{label}**：{text}")
        lines.append("")

    actions = ri.get("actions") or []
    if isinstance(actions, list) and actions:
        lines.append("### 📋 行動建議")
        for i, a in enumerate(actions[:6], 1):
            if isinstance(a, dict):
                owner = _safe_str(a.get("owner"))
                task = _safe_str(a.get("task"))
                why = _safe_str(a.get("why"))
                kpi = _safe_str(a.get("kpi"))
                stoploss = _safe_str(a.get("stoploss"))

                headline = "｜".join([x for x in [owner, task] if x])
                if not headline:
                    headline = _safe_str(a)
                lines.append(f"{i}. {headline}")
                extra = []
                if why:
                    extra.append(f"Why：{why}")
                if kpi:
                    extra.append(f"KPI：{kpi}")
                if stoploss:
                    extra.append(f"止損：{stoploss}")
                if extra:
                    lines.append("   - " + "；".join(extra))
            else:
                lines.append(f"{i}. {_safe_str(a)}")
        lines.append("")

    data_issues = ri.get("data_issues") or []
    if isinstance(data_issues, list) and data_issues:
        lines.append("### 🧯 資料問題")
        for i, it in enumerate(data_issues[:5], 1):
            lines.append(f"{i}. {_safe_str(it)}")
        lines.append("")

    open_questions = ri.get("open_questions") or []
    if isinstance(open_questions, list) and open_questions:
        lines.append("### ❓ 下週要問")
        for i, it in enumerate(open_questions[:5], 1):
            lines.append(f"{i}. {_safe_str(it)}")
        lines.append("")

    if len(lines) <= 2:
        return "## 📊 本週洞察摘要\n\n_洞察內容正在生成中..._"

    return "\n".join(lines).rstrip() + "\n"


def _safe_str(v: Any) -> str:
    s = "" if v is None else str(v)
    return s.strip()


def render_consultant_note(role: str, note: dict[str, Any]) -> str:
    """
    將單一顧問的 JSON 轉為可讀分析

    參數:
        role: "A" | "B" | "C"
        note: 該顧問的 JSON 輸出

    回傳:
        Markdown 格式的顧問分析摘要
    """
    role_info = {
        "A": {"name": "成效顧問", "icon": "📊", "focus": "數據分析與擴量建議"},
        "B": {"name": "視覺顧問", "icon": "🎨", "focus": "素材與文案優化"},
        "C": {"name": "策略顧問", "icon": "🧠", "focus": "整體策略與風險控管"},
    }

    info = role_info.get(role, {"name": f"顧問 {role}", "icon": "🤖", "focus": "分析"})

    # 檢查錯誤
    if "error" in note:
        return f"{info['icon']} **{info['name']}**\n\n⚠️ 分析失敗：{note['error']}"

    lines = [f"## {info['icon']} {info['name']}\n", f"_專注：{info['focus']}_\n"]

    # 新版顧問輸出（consultant_task.v1）：優先渲染，避免舊 renderer 欄位對不上
    if _looks_like_consultant_task_v1(note):
        lines.extend(_render_consultant_task_v1(note))
        return "\n".join(lines).rstrip() + "\n"

    # 根據不同顧問提取不同欄位
    if role == "A":
        lines.extend(_render_consultant_a(note))
    elif role == "B":
        lines.extend(_render_consultant_b(note))
    elif role == "C":
        lines.extend(_render_consultant_c(note))
    else:
        # 通用處理
        lines.extend(_render_generic_note(note))

    return "\n".join(lines)


def _render_consultant_a(note: dict[str, Any]) -> list:
    """渲染成效顧問 A 的輸出"""
    lines = []

    # performance_summary
    perf_summary = note.get("performance_summary") or note.get("summary", "")
    if perf_summary:
        lines.append(f"### 績效總結\n{perf_summary}\n")

    # key_observations
    observations = note.get("key_observations") or note.get("observations", [])
    if observations:
        lines.append("### 🔍 關鍵觀察")
        for obs in observations[:4]:
            text = obs if isinstance(obs, str) else obs.get("text", str(obs))
            lines.append(f"- {text}")

    # scaling_suggestions
    suggestions = note.get("scaling_suggestions") or note.get("suggestions", [])
    if suggestions:
        lines.append("\n### 📈 擴量建議")
        for sug in suggestions[:3]:
            text = sug if isinstance(sug, str) else sug.get("text", str(sug))
            lines.append(f"- {text}")

    # budget_recommendations
    budget = note.get("budget_recommendations") or note.get("budget", [])
    if budget:
        lines.append("\n### 💰 預算建議")
        for b in budget[:3]:
            text = b if isinstance(b, str) else b.get("text", str(b))
            lines.append(f"- {text}")

    return lines


def _render_consultant_b(note: dict[str, Any]) -> list:
    """渲染視覺顧問 B 的輸出"""
    lines = []

    # creative_review
    creative = note.get("creative_review") or note.get("visual_summary", "")
    if creative:
        lines.append(f"### 素材評析\n{creative}\n")

    # top_performers
    top = note.get("top_performers") or note.get("best_creatives", [])
    if top:
        lines.append("### 🏆 表現最佳素材")
        for t in top[:3]:
            text = t if isinstance(t, str) else t.get("name", str(t))
            lines.append(f"- {text}")

    # copy_suggestions
    copy = note.get("copy_suggestions") or note.get("copywriting", [])
    if copy:
        lines.append("\n### ✍️ 文案建議")
        for c in copy[:3]:
            text = c if isinstance(c, str) else c.get("text", str(c))
            lines.append(f"- {text}")

    # visual_recommendations
    visual = note.get("visual_recommendations") or note.get("design_tips", [])
    if visual:
        lines.append("\n### 🎨 視覺建議")
        for v in visual[:3]:
            text = v if isinstance(v, str) else v.get("text", str(v))
            lines.append(f"- {text}")

    return lines


def _render_consultant_c(note: dict[str, Any]) -> list:
    """渲染策略顧問 C 的輸出"""
    lines = []

    # strategy_overview
    strategy = note.get("strategy_overview") or note.get("strategic_summary", "")
    if strategy:
        lines.append(f"### 策略總覽\n{strategy}\n")

    # market_insights
    market = note.get("market_insights") or note.get("market_analysis", [])
    if market:
        lines.append("### 🌐 市場洞察")
        for m in market[:3]:
            text = m if isinstance(m, str) else m.get("text", str(m))
            lines.append(f"- {text}")

    # action_items
    actions = note.get("action_items") or note.get("next_steps", [])
    if actions:
        lines.append("\n### 🎯 行動項目")
        for a in actions[:4]:
            text = a if isinstance(a, str) else a.get("text", str(a))
            lines.append(f"- {text}")

    # risks
    risks = note.get("risks") or note.get("risk_factors", [])
    if risks:
        lines.append("\n### ⚠️ 風險提醒")
        for r in risks[:3]:
            text = r if isinstance(r, str) else r.get("text", str(r))
            lines.append(f"- {text}")

    return lines


def _render_generic_note(note: dict[str, Any]) -> list:
    """通用顧問輸出渲染（fallback）"""
    lines = []

    # 嘗試提取常見欄位
    for key in ["summary", "analysis", "recommendations", "suggestions"]:
        value = note.get(key)
        if value:
            label = _translate_key(key)
            if isinstance(value, str):
                lines.append(f"### {label}\n{value}\n")
            elif isinstance(value, list):
                lines.append(f"### {label}")
                for item in value[:5]:
                    text = item if isinstance(item, str) else str(item)
                    lines.append(f"- {text}")

    if not lines:
        lines.append("_分析內容正在整理中..._")

    return lines


def _translate_key(key: str) -> str:
    """將英文欄位名翻譯為繁體中文"""
    translations = {
        "summary": "摘要",
        "analysis": "分析",
        "recommendations": "建議",
        "suggestions": "建議",
        "performance": "績效",
        "insights": "洞察",
        "observations": "觀察",
        "highlights": "亮點",
        "total_spend": "總花費",
        "total_impressions": "總曝光",
        "total_clicks": "總點擊",
        "total_conversions": "總轉換",
        "average_cpm": "平均 CPM",
        "average_cpc": "平均 CPC",
        "average_roas": "平均 ROAS",
        "top_adset": "最佳廣告組",
        "top_ad": "最佳廣告",
    }
    return translations.get(key, key.replace("_", " ").title())


def _format_value(value: Any) -> str:
    """格式化數值為可讀字串"""
    if value is None:
        return "N/A"

    if isinstance(value, bool):
        return "是" if value else "否"

    if isinstance(value, float):
        if value >= 1000000:
            return f"{value / 1000000:.2f}M"
        elif value >= 1000:
            return f"{value / 1000:.1f}K"
        else:
            return f"{value:.2f}"

    if isinstance(value, int):
        if value >= 1000000:
            return f"{value / 1000000:.2f}M"
        elif value >= 1000:
            return f"{value:,}"
        else:
            return str(value)

    return str(value)
