"""
檔案用途：週會 Markdown 輸出（meeting.md）模組
職責：
  - 將 workflow_state.json + report_summary/report_insights 組裝成可讀的週會紀要
  - 盡量使用 deterministic 方式渲染，避免 LLM 產生的格式飄移
"""

import json
from pathlib import Path
from typing import Any


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        return int(round(float(x)))
    except Exception:
        return default


def _fmt_money_twd(x: Any) -> str:
    v = _safe_float(x, default=0.0)
    return f"{v:,.0f}"


def _fmt_pct(x: Any, digits: int = 1) -> str:
    v = _safe_float(x, default=0.0)
    return f"{v:.{digits}f}%"


def _fmt_ratio(x: float | None, digits: int = 1) -> str:
    if x is None:
        return "（資料不足）"
    return f"{x * 100:.{digits}f}%"


def _is_tracking_suspect(meta: dict[str, Any]) -> bool:
    """判斷官網真值可能失真（常見：回傳為 0）。

    原則：官網回傳為 0 且平台端有值/有購買 → 以平台口徑作暫時排序與判讀。
    """

    truth_value = _safe_float(
        meta.get("website_purchase_value_twd", meta.get("purchase_value_twd"))
    )
    truth_purchases = _safe_int(meta.get("website_purchases", meta.get("purchases")))
    platform_value = _safe_float(meta.get("platform_purchase_value_twd"))
    platform_purchases = _safe_int(meta.get("platform_purchases"))

    if truth_value > 0 or truth_purchases > 0:
        return False
    return (platform_value > 0) or (platform_purchases > 0)


def _pick_sort_key(*, tracking_suspect: bool) -> str:
    return "roas_platform" if tracking_suspect else "roas"


def _extract_adset_rows(report_summary: dict[str, Any]) -> list[dict[str, Any]]:
    tables = report_summary.get("tables") or {}
    top_rows = tables.get("top_adsets_by_roas") if isinstance(tables, dict) else None
    worst_rows = tables.get("worst_adsets_by_roas") if isinstance(tables, dict) else None

    rows: list[dict[str, Any]] = []
    for src in [top_rows, worst_rows]:
        if isinstance(src, list):
            for r in src:
                if isinstance(r, dict):
                    rows.append(r)

    # 去重（以 name 為主）
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for r in rows:
        name = str(r.get("name", "")).strip()
        key = name or json.dumps(r, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return deduped


def _extract_ads_rows(report_summary: dict[str, Any]) -> list[dict[str, Any]]:
    tables = report_summary.get("tables") or {}
    top_rows = tables.get("top_ads_by_roas") if isinstance(tables, dict) else None
    worst_rows = tables.get("worst_ads_by_roas") if isinstance(tables, dict) else None

    rows: list[dict[str, Any]] = []
    for src, tag in [(top_rows, "top"), (worst_rows, "worst")]:
        if isinstance(src, list):
            for r in src:
                if isinstance(r, dict):
                    rr = dict(r)
                    rr["__tag"] = tag
                    rows.append(rr)

    # 去重：同一個 ad 可能同時出現在 top/worst（例如 ROAS 全 0）
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for r in rows:
        name = str(r.get("name", "")).strip()
        key = name or json.dumps(r, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return deduped


def _render_ae_sections(
    *,
    workflow_state: dict[str, Any],
    report_summary: dict[str, Any],
    report_insights: dict[str, Any],
) -> list[str]:
    meta: dict[str, Any] = report_summary.get("kpi", {}).get("meta", {}) or {}
    web: dict[str, Any] = report_summary.get("kpi", {}).get("web", {}) or {}

    spend = _safe_float(meta.get("spend_twd"))
    truth_purchases = _safe_int(meta.get("website_purchases", meta.get("purchases")))
    truth_value = _safe_float(
        meta.get("website_purchase_value_twd", meta.get("purchase_value_twd"))
    )
    roas_truth = _safe_float(meta.get("roas_calc"))
    platform_value = _safe_float(meta.get("platform_purchase_value_twd"))
    platform_roas = _safe_float(meta.get("roas_platform_calc"))

    ctr = _safe_float(meta.get("ctr_link_pct_calc"))
    cpc = _safe_float(meta.get("cpc_calc_twd"))

    funnel = meta.get("funnel") if isinstance(meta.get("funnel"), dict) else {}
    link_clicks = _safe_int(funnel.get("link_clicks"))
    lpv = _safe_int(funnel.get("landing_page_views"))
    lpv_per_click = (lpv / link_clicks) if link_clicks > 0 else None

    tracking_suspect = _is_tracking_suspect(meta)
    sort_key = _pick_sort_key(tracking_suspect=tracking_suspect)

    adset_rows = _extract_adset_rows(report_summary)
    ads_rows = _extract_ads_rows(report_summary)

    # 粗略 frequency：以 AdSet rows 的平均值作提示（避免硬算整體）
    freqs = [
        _safe_float(r.get("frequency"))
        for r in adset_rows
        if r.get("frequency") is not None and _safe_float(r.get("frequency")) > 0
    ]
    freq_avg = (sum(freqs) / len(freqs)) if freqs else None

    lines: list[str] = []

    lines.append("## A. 這週先講重點（1 分鐘版）")
    if tracking_suspect:
        lines.append("- ⚠️ 官網真值回傳為 0 或不足，本週判讀會以『平台口徑』為主，並同步做對帳。")

    lines.append(
        "- 投放："
        f"Spend **{_fmt_money_twd(spend)}**｜購買（官網）**{truth_purchases}**｜官網回傳金額 **{_fmt_money_twd(truth_value)}**｜"
        f"ROAS（官網）**{roas_truth:.2f}**｜ROAS（平台）**{platform_roas:.2f}**"
    )
    lines.append(
        f"- 流量品質：CTR(link) **{_fmt_pct(ctr)}**｜CPC(link) **{_fmt_money_twd(cpc)}**｜LPV/Click **{_fmt_ratio(lpv_per_click)}**"
        + (f"｜頻次（Top AdSet 平均）**{freq_avg:.2f}**" if freq_avg is not None else "")
    )
    lines.append(
        "- 對帳："
        f"平台回傳金額 **{_fmt_money_twd(platform_value)}**｜官網營收 **{_fmt_money_twd(web.get('revenue_twd'))}**｜"
        f"官網訂單 **{_safe_int(web.get('orders'))}**｜客單（官網）**{_fmt_money_twd(web.get('aov_twd_calc'))}**"
    )
    lines.append("")

    # B. AdSet 表現
    lines.append("## B. Ad Set 表現對比")
    if not adset_rows:
        lines.append("- （資料不足，建議重跑 Step B 產生 report_summary.tables）")
        lines.append("")
    else:
        rows = [r for r in adset_rows if _safe_float(r.get("spend_twd")) > 0]
        rows.sort(key=lambda r: _safe_float(r.get(sort_key)), reverse=True)
        rows = rows[:6]

        if tracking_suspect:
            lines.append("- 排序口徑：平台 ROAS（因官網回傳不足）")
        else:
            lines.append("- 排序口徑：官網 ROAS（真值）")

        lines.append(
            "| Ad Set | Spend | Purchases(官網) | ROAS(官網) | ROAS(平台) | CTR | LPV/Click | 頻次 |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        for r in rows:
            name = str(r.get("name", "")).strip() or "（未命名）"
            lpv_click = None
            clicks = _safe_int(r.get("link_clicks"))
            lpv_local = _safe_int(r.get("landing_page_views"))
            if clicks > 0:
                lpv_click = lpv_local / clicks

            lines.append(
                "| "
                + " | ".join(
                    [
                        name.replace("|", " "),
                        _fmt_money_twd(r.get("spend_twd")),
                        str(_safe_int(r.get("purchases"))),
                        f"{_safe_float(r.get('roas')):.2f}",
                        f"{_safe_float(r.get('roas_platform')):.2f}",
                        _fmt_pct(r.get("ctr_link_pct_calc")),
                        _fmt_ratio(lpv_click),
                        f"{_safe_float(r.get('frequency')):.2f}"
                        if r.get("frequency") is not None
                        else "-",
                    ]
                )
                + " |"
            )

        # 每個 adset 一句話判讀（簡短、含門檻）
        lines.append("")
        lines.append("**判讀（每組一句話）**")
        for r in rows:
            name = str(r.get("name", "")).strip() or "（未命名）"
            roas_platform_r = _safe_float(r.get("roas_platform"))
            ctr_r = _safe_float(r.get("ctr_link_pct_calc"))
            freq_r = _safe_float(r.get("frequency")) if r.get("frequency") is not None else None

            # CPP：優先官網 purchases；若為 0，改用平台 purchases。
            spend_r = _safe_float(r.get("spend_twd"))
            purchases_truth_r = _safe_int(r.get("purchases"))
            purchases_platform_r = _safe_int(r.get("platform_purchases"))
            cpp_truth = (spend_r / purchases_truth_r) if purchases_truth_r > 0 else None
            cpp_platform = (spend_r / purchases_platform_r) if purchases_platform_r > 0 else None
            cpp = cpp_truth if cpp_truth is not None else cpp_platform

            clicks = _safe_int(r.get("link_clicks"))
            lpv_local = _safe_int(r.get("landing_page_views"))
            lpv_click = (lpv_local / clicks) if clicks > 0 else None

            ok_roas = roas_platform_r >= 5.0
            ok_ctr = ctr_r >= 2.5
            ok_lpv = (lpv_click is not None) and (lpv_click >= 0.9)
            ok_freq = (freq_r is None) or (freq_r < 2.0)
            ok_cpp = (cpp is not None) and (cpp <= 320.0)

            if ok_roas and ok_ctr and ok_lpv and ok_freq and ok_cpp:
                verdict = "可當主力（符合守門值，可小幅放量）"
                stoploss = "停損：若頻次≥2.0 或 CTR<2.5 先停放量、改素材"
            elif (not ok_roas) and spend_r > 0:
                verdict = "需要處置（平台 ROAS 未達 5，優先降載/調受眾或素材）"
                stoploss = "停損：3 天內 ROAS(平台) 仍 <5 → 先停或只留再行銷"
            else:
                verdict = (
                    "觀察中（先修正資料/追蹤，避免誤判）"
                    if tracking_suspect
                    else "觀察中（數據不足）"
                )
                stoploss = "停損：若關鍵數字無法補齊 → 先對帳再決策"

            reason_bits: list[str] = []
            reason_bits.append(f"ROAS(平台)={roas_platform_r:.2f}")
            reason_bits.append(f"CTR={ctr_r:.1f}%")
            if lpv_click is not None:
                reason_bits.append(f"LPV/Click={lpv_click * 100:.0f}%")
            if cpp is not None:
                reason_bits.append(f"CPP≈{cpp:.0f}")
            if freq_r is not None:
                reason_bits.append(f"Freq={freq_r:.2f}")

            lines.append(f"- {name}：{verdict}（" + "｜".join(reason_bits) + f"｜{stoploss}）")
        lines.append("")

    # B+. Ads
    lines.append("## B+. Ad（素材）表現（按 adset）")
    if not ads_rows:
        lines.append("- （資料不足，建議重跑 Step B 產生 report_summary.tables）")
        lines.append("")
    else:
        # 以 adset_name 分組；若缺少 adset_name，改為不分組列出。
        grouped: dict[str, list[dict[str, Any]]] = {}
        missing_group: list[dict[str, Any]] = []
        for r in ads_rows:
            adset_name = str(r.get("adset_name", "")).strip()
            if not adset_name:
                missing_group.append(r)
                continue
            grouped.setdefault(adset_name, []).append(r)

        if grouped:
            for adset_name, items in list(grouped.items())[:6]:
                lines.append(f"### {adset_name}")
                items.sort(key=lambda rr: _safe_float(rr.get(sort_key)), reverse=True)
                picked = items[:3]
                for rr in picked:
                    tag = rr.get("__tag")
                    prefix = "Top" if tag == "top" else "處置" if tag == "worst" else ""
                    ad_name = str(rr.get("name", "")).strip() or "（未命名）"
                    lines.append(
                        f"- {prefix}：{ad_name}｜ROAS(平台)={_safe_float(rr.get('roas_platform')):.2f}｜CTR={_safe_float(rr.get('ctr_link_pct_calc')):.1f}%"
                    )
                lines.append("")
        else:
            lines.append(
                "- （缺 adset_name，暫不分組：可透過 Idx-040 在 kpi_calc.py 補 adset_name 欄位）"
            )
            missing_group.sort(key=lambda rr: _safe_float(rr.get(sort_key)), reverse=True)
            for rr in missing_group[:5]:
                tag = rr.get("__tag")
                prefix = "Top" if tag == "top" else "處置" if tag == "worst" else ""
                ad_name = str(rr.get("name", "")).strip() or "（未命名）"
                lines.append(
                    f"- {prefix}：{ad_name}｜ROAS(平台)={_safe_float(rr.get('roas_platform')):.2f}｜CTR={_safe_float(rr.get('ctr_link_pct_calc')):.1f}%"
                )
            lines.append("")

    # B2. 盈虧
    lines.append("## B2. 損益平衡點（CPP vs 客單）")
    aov_web = _safe_float(web.get("aov_twd_calc"))
    aov_platform = _safe_float(meta.get("aov_platform_twd_calc"))
    aov = aov_web if aov_web > 0 else aov_platform

    purchases_platform_all = _safe_int(meta.get("platform_purchases"))
    cpp_truth_all = _safe_float(meta.get("cpa_calc_twd")) if truth_purchases > 0 else 0.0
    cpp_platform_all = (spend / purchases_platform_all) if purchases_platform_all > 0 else 0.0
    cpp = cpp_truth_all if truth_purchases > 0 else cpp_platform_all
    cpp_note = "官網 CPP" if truth_purchases > 0 else "平台 CPP（官網回傳不足）"

    if aov <= 0:
        lines.append("- （缺 AOV，無法計算損益平衡點）")
    else:
        cost_ratio = (cpp / aov) if aov > 0 else 0.0
        safety_multiple = (aov / cpp) if cpp > 0 else 0.0
        lines.append(f"- 客單 AOV：{_fmt_money_twd(aov)}（優先官網，其次平台）")
        lines.append(
            f"- {cpp_note}：{_fmt_money_twd(cpp)}｜成本占比 CPP/AOV：{cost_ratio:.2f}｜安全墊 AOV/CPP：{safety_multiple:.2f}"
        )
    lines.append("")

    # C. 立即調整（以模板 + insights.actions 補強，不捏造數字）
    lines.append("## C. 今天立刻要做的調整（照做就好）")
    c_items: list[str] = []
    if tracking_suspect:
        c_items.append(
            "- 動作：先做對帳/追蹤排查（Pixel/CAPI/歸因口徑）｜原因：官網回傳不足會誤判 ROAS｜驗收門檻：官網回傳金額 > 0 且 delta 明顯收斂｜停損：若 7 天仍無法對齊，週會先固定以平台口徑決策並註記限制"
        )

    actions_src = report_insights.get("actions")
    if isinstance(actions_src, list) and actions_src:
        for a in actions_src[:3]:
            if not isinstance(a, dict):
                continue
            task = a.get("task") or a.get("title")
            why = a.get("why") or a.get("reason")
            kpi = a.get("kpi")
            stoploss = a.get("stoploss")
            if task:
                parts = [f"動作：{task}"]
                if why:
                    parts.append(f"原因：{why}")
                if kpi:
                    parts.append(f"驗收門檻：{kpi}")
                if stoploss:
                    parts.append(f"停損：{stoploss}")
                c_items.append("- " + "｜".join([str(p).strip() for p in parts if str(p).strip()]))

    if not c_items:
        c_items.append(
            "- 動作：保留 ROAS(平台) ≥ 5 的主力組合，其餘先降載或改素材｜原因：先把預算留給有效組合｜驗收門檻：CTR ≥ 2.5 且 LPV/Click ≥ 90%｜停損：頻次 ≥ 2.0 或 CTR < 2.5 立即停止放量"
        )

    lines.extend(c_items[:6])
    lines.append("")

    # D. 驗收門檻
    lines.append("## D. 下次回來我看這 5 個數字（驗收門檻）")
    # CPP 以官網優先；官網缺則平台
    cpp_overall = cpp
    lines.append(f"- CPP ≤ 320｜本週：{_fmt_money_twd(cpp_overall)}（{cpp_note}）")
    lines.append(f"- 平台 ROAS ≥ 5｜本週：{platform_roas:.2f}")
    lines.append(f"- CTR(link) ≥ 2.5%｜本週：{ctr:.1f}%")
    lines.append(f"- LPV/Click ≥ 90%｜本週：{_fmt_ratio(lpv_per_click, digits=0)}")
    if freq_avg is not None:
        lines.append(f"- 頻次 < 2.0｜本週：{freq_avg:.2f}（Top AdSet 平均）")
    else:
        lines.append("- 頻次 < 2.0｜本週：（資料不足，請以 AdSet 表格為準）")
    lines.append("")

    # E. 風險檢查
    lines.append("## E. 風險檢查（必做 2 件事）")
    delta_value = _safe_float(meta.get("delta_purchase_value_twd"))
    delta_rate = _safe_float(meta.get("delta_purchase_value_rate"))
    lines.append(
        "- 必做 1｜對帳：平台回傳 vs 官網營收要同時看。"
        f"（差異={_fmt_money_twd(delta_value)}｜差異率={_fmt_pct(delta_rate * 100.0, digits=1)}）"
    )
    lines.append(
        "- 必做 2｜疲勞分級（用頻次 + CTR + LPV/Click）：\n"
        "  - 綠：頻次<2.0 且 CTR≥2.5 且 LPV/Click≥90% → 可維持/小幅放量\n"
        "  - 黃：頻次 2.0~2.5 或 CTR 2.0~2.5 → 控制預算、優先換素材/受眾\n"
        "  - 紅：頻次≥2.5 或 CTR<2.0 → 先降載或停投，避免浪費預算"
    )

    return lines


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
    workflow_state: dict[str, Any],
    report_summary: dict[str, Any],
    report_insights: dict[str, Any],
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

    # === A~E 固定版型（決策導向） ===
    lines.extend(
        _render_ae_sections(
            workflow_state=workflow_state,
            report_summary=report_summary,
            report_insights=report_insights,
        )
    )
    lines.append("")

    lines.append("## 附錄（原始輸出保留）")
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
        msg_parts: list[str] = []
        if isinstance(report_insights, dict):
            for key in ["message", "error", "code", "status"]:
                v = report_insights.get(key)
                if isinstance(v, str) and v.strip():
                    msg_parts.append(f"{key}={v.strip()}")
        msg = "｜".join(msg_parts)
        if msg:
            lines.append(f"- ⚠️ 洞察產物格式異常：{msg}（建議重新執行 Step C）")
        else:
            lines.append("- ⚠️ report_insights.executive_summary 缺失或為空（建議重新執行 Step C）")
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

        # 兼容另一種常見輸出形狀：week_focus / key_observations
        # 目的：避免 workflow_state.consultant_summary 存在但 renderer 不認，導致顯示（待補）。
        week_focus = cs.get("week_focus") or cs.get("weekFocus") or []
        if isinstance(week_focus, str) and week_focus.strip():
            lines.append(f"- {idx}. 共識：{week_focus.strip()}")
            idx += 1
            added = True
        elif isinstance(week_focus, list) and week_focus:
            for it in week_focus[:10]:
                if isinstance(it, str) and it.strip():
                    lines.append(f"- {idx}. 共識：{it.strip()}")
                    idx += 1
                    added = True

        key_observations = (
            cs.get("key_observations") or cs.get("keyObservations") or cs.get("observations")
        )
        if isinstance(key_observations, str) and key_observations.strip():
            lines.append(f"- {idx}. 觀察：{key_observations.strip()}")
            idx += 1
            added = True
        elif isinstance(key_observations, list) and key_observations:
            for it in key_observations[:10]:
                if isinstance(it, str) and it.strip():
                    lines.append(f"- {idx}. 觀察：{it.strip()}")
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


def write_artifacts(hist_dir: Path, meeting_md: str, workflow_state: dict[str, Any]) -> None:
    (hist_dir / "meeting.md").write_text(meeting_md, encoding="utf-8")
    (hist_dir / "workflow_state.json").write_text(
        json.dumps(workflow_state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
