"""
檔案用途：Moderator deterministic fallback（避免 LLM JSON 解析失敗造成 meeting.md 大量（待補））
職責：
  - 當 Moderator LLM 輸出無法解析為合法 JSON 時，改以 deterministic 方式組裝 workflow_state
注意事項：
  - 不重算 KPI，只引用既有輸入內容（report_summary/report_insights/consultant_notes）
  - 產出需符合 meeting renderer（scripts/moderator_meeting.py）的最小可用欄位
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def build_deterministic_workflow_state(
    *,
    report_summary: Dict[str, Any],
    report_insights: Dict[str, Any],
    consultant_notes: Optional[Dict[str, Any]],
    guardrails: Dict[str, Any],
) -> Dict[str, Any]:
    """
    用途：當 Moderator LLM 輸出解析失敗時，改用 deterministic 組裝 workflow_state（避免 meeting.md 大量（待補））
    原則：
      - 不重算 KPI
      - 優先引用 report_insights.actions/data_issues/executive_summary
      - 每個部門至少 1 個任務（可讀且可落地）
    """

    def _safe_list(x: Any) -> list:
        return x if isinstance(x, list) else []

    def _safe_str(x: Any) -> str:
        if x is None:
            return ""
        return str(x).strip()

    exec_sum = _safe_list(report_insights.get("executive_summary"))
    data_issues = _safe_list(report_insights.get("data_issues"))
    actions_src = report_insights.get("actions")
    actions_list = actions_src if isinstance(actions_src, list) else []

    consultant_actions: list[dict[str, Any]] = []
    consultant_risks: list[dict[str, Any]] = []
    consultant_errors: list[str] = []
    if consultant_notes:
        for key in ["consultant_A", "consultant_B", "consultant_C"]:
            c = consultant_notes.get(key)
            if isinstance(c, dict) and c.get("error"):
                consultant_errors.append(f"{key} 輸出失敗：{c.get('error')}")
                continue
            if not isinstance(c, dict):
                continue
            rs = c.get("risks")
            if isinstance(rs, list):
                for r in rs:
                    if not isinstance(r, dict):
                        continue
                    if _safe_str(r.get("risk")) or _safe_str(r.get("description")):
                        consultant_risks.append(r)
            nas = c.get("next_7d_actions")
            if isinstance(nas, list):
                for a in nas:
                    if not isinstance(a, dict):
                        continue
                    if _safe_str(a.get("task") or a.get("title")):
                        consultant_actions.append(a)

    # decisions：以 executive_summary 為主，若不足則補 data_issues
    decisions: list[str] = []
    for s in exec_sum[:6]:
        if _safe_str(s):
            decisions.append(f"做：{_safe_str(s)}")
    if len(decisions) < 3:
        for s in data_issues[: (6 - len(decisions))]:
            if _safe_str(s):
                decisions.append(f"延後/風險：{_safe_str(s)}")
    if not decisions:
        decisions = ["做：優先處理追蹤/口徑一致性，避免 ROAS 判讀失真。"]

    # risks：優先用顧問風險，其次 data_issues
    risks: list[dict[str, Any]] = []
    if consultant_risks:
        risks.extend(consultant_risks[:6])

    if len(risks) < 3:
        for s in data_issues[: (3 - len(risks))]:
            if _safe_str(s):
                risks.append(
                    {
                        "description": _safe_str(s),
                        "probability": "中~高",
                        "impact": "影響決策與預算分配準確性",
                        "mitigation": "以平台口徑 + 官網對帳建立固定欄位，並排查 Pixel/CAPI 回傳",
                        "alternative": "短期以 platform_purchase_value_twd + web revenue_twd 作主口徑",
                    }
                )

    for e in consultant_errors:
        risks.append(
            {
                "description": e,
                "probability": "中",
                "impact": "週會決策資訊不足",
                "mitigation": "下次執行前降低輸出長度/改為分段產出或強化 JSON 修復",
                "alternative": "用 deterministic actions/risk 模板補足",
            }
        )
    if not risks:
        risks = [
            {
                "description": "資料不足導致行動建議過於保守",
                "probability": "中",
                "impact": "錯失擴量時機",
                "mitigation": "補齊缺失欄位與素材版本資訊",
                "alternative": "以小額測試 + 守門值逐步放量",
            }
        ]

    # department_actions：優先使用 report_insights.actions 的 owner/task/why/kpi/stoploss
    required = ["GM", "Finance", "E-commerce", "Marketing", "Fulfillment"]
    dept_actions: dict[str, list[dict[str, Any]]] = {d: [] for d in required}

    def map_dept(owner: str) -> str:
        o = owner or ""
        if any(k in o for k in ["財務", "Finance"]):
            return "Finance"
        if any(k in o for k in ["電商", "營運", "PM", "E-commerce"]):
            return "E-commerce"
        if any(k in o for k in ["投放", "內容", "行銷", "Marketing", "素材", "創意", "設計", "剪輯"]):
            return "Marketing"
        if any(k in o for k in ["倉", "物流", "出貨", "Fulfillment"]):
            return "Fulfillment"
        return "GM"

    tasks_seen: set[str] = set()

    def add_action(
        *,
        owner_role: Any,
        task: Any,
        deliverable: Any,
        due: Any,
        kpi: Any,
        stoploss: Any,
    ) -> None:
        t = _safe_str(task)
        if not t:
            return
        if t in tasks_seen:
            return
        tasks_seen.add(t)
        owner_s = _safe_str(owner_role)
        dept = map_dept(owner_s)
        dept_actions[dept].append(
            {
                "task": t,
                "owner_role": owner_s or "（待補）",
                "deliverable": _safe_str(deliverable) or "（待補）",
                "due": due,
                "kpi": _safe_str(kpi) or "（待補）",
                "stoploss": _safe_str(stoploss) or "（待補）",
            }
        )

    # 優先把顧問 next_7d_actions 納入（通常更完整，包含 deliverable/kpi/stoploss）
    for a in consultant_actions:
        add_action(
            owner_role=a.get("owner_role") or a.get("owner"),
            task=a.get("task") or a.get("title"),
            deliverable=a.get("deliverable"),
            due=a.get("due") or a.get("due_by") or a.get("due"),
            kpi=a.get("kpi"),
            stoploss=a.get("stoploss"),
        )

    for a in actions_list:
        if not isinstance(a, dict):
            continue
        add_action(
            owner_role=a.get("owner"),
            task=a.get("task") or a.get("title"),
            deliverable=a.get("deliverable"),
            due=a.get("due"),
            kpi=a.get("kpi"),
            stoploss=a.get("stoploss"),
        )

    # 若某些部門仍無任務，用最小可用模板補齊（不捏造數字）
    if not dept_actions["GM"]:
        dept_actions["GM"].append(
            {
                "task": "決定本週週會主口徑（平台端 value vs 官網營收），並建立固定週報欄位",
                "owner_role": "GM/COO",
                "deliverable": "一頁式口徑定義與對帳欄位",
                "due": None,
                "kpi": "下週週會不再口徑混淆",
                "stoploss": "若仍無法對齊，短期以平台口徑決策並註記限制",
            }
        )
    if not dept_actions["Finance"]:
        dept_actions["Finance"].append(
            {
                "task": "建立平台端平台回傳金額 vs 官網營收對帳（含差異原因分類）",
                "owner_role": "Finance",
                "deliverable": "對帳表與差異說明",
                "due": None,
                "kpi": "差異原因可追溯",
                "stoploss": "差異無法縮小則改用單一口徑並固定說明",
            }
        )
    if not dept_actions["E-commerce"]:
        dept_actions["E-commerce"].append(
            {
                "task": "排查站內漏斗後段（加車→結帳）主要阻礙並提出最小改版方案",
                "owner_role": "PM/營運",
                "deliverable": "問題清單 + 1~2 個最小改動 A/B",
                "due": None,
                "kpi": "結帳段流失下降",
                "stoploss": "若改版造成營收下滑則立即回退",
            }
        )
    if not dept_actions["Marketing"]:
        dept_actions["Marketing"].append(
            {
                "task": "複製本週有效素材型態做 3 支變體並建立停損規則",
                "owner_role": "投放/內容",
                "deliverable": "素材 brief + 測試計畫",
                "due": None,
                "kpi": "有效素材比例提升",
                "stoploss": "若測試無提升則停止擴量並回收預算",
            }
        )
    if not dept_actions["Fulfillment"]:
        dept_actions["Fulfillment"].append(
            {
                "task": "確認早鳥檔期商品供貨與出貨 SLA，避免擴量後履約問題",
                "owner_role": "倉/物流",
                "deliverable": "庫存/出貨能力確認",
                "due": None,
                "kpi": "出貨延遲率不上升",
                "stoploss": "若供貨吃緊則限制投放放量幅度",
            }
        )

    # 避免回填過多任務（meeting.md 會過長）：各部門最多保留前 5 條
    for d in required:
        if isinstance(dept_actions.get(d), list):
            dept_actions[d] = dept_actions[d][:5]

    # consultant_summary：優先用顧問輸出中的可讀摘要；若缺則補顧問錯誤
    consultant_summary: list[str] = []
    if consultant_notes:
        def pick_readable_text(obj: Any) -> Optional[str]:
            if isinstance(obj, str):
                s = obj.strip()
                return s if s else None
            if isinstance(obj, list):
                for it in obj:
                    s = pick_readable_text(it)
                    if s:
                        return s
            if isinstance(obj, dict):
                for k in [
                    "summary",
                    "executive_summary",
                    "key_takeaways",
                    "overall_health",
                    "overall_theme",
                    "headline",
                    "reason",
                    "next_steps",
                    "recommended_fix",
                    "observations",
                ]:
                    if k in obj:
                        s = pick_readable_text(obj.get(k))
                        if s:
                            return s
                for kk, vv in obj.items():
                    if kk in ["schema", "schema_version", "consultant_type", "consultant_name", "role", "consultant", "report_meta"]:
                        continue
                    s = pick_readable_text(vv)
                    if s:
                        return s
            return None

        for key in ["consultant_A", "consultant_B", "consultant_C"]:
            c = consultant_notes.get(key)
            if isinstance(c, dict) and c.get("error"):
                consultant_summary.append(f"{key} 輸出失敗：{c.get('error')}")
                continue
            s = pick_readable_text(c)
            if s:
                consultant_summary.append(f"{key} 重點：{s}")
    if not consultant_summary:
        consultant_summary = ["顧問摘要：以 deterministic actions 與風險清單補足（本次顧問輸出不足）。"]

    return {
        "schema_version": "workflow_state.v1",
        "week_id": report_summary.get("week_id"),
        "date_range": report_summary.get("date_range"),
        "kpi_snapshot": report_summary.get("kpi", {}),
        "decisions": decisions,
        "guardrail_check": {"guardrails": guardrails},
        "consultant_summary": consultant_summary[:10],
        "department_actions": dept_actions,
        "risks": risks[:6],
        "validation_plan": {
            "3天": "完成追蹤/歸因排查與對帳定義，確認 purchase value 回傳與口徑差異來源。",
            "7天": "以平台口徑為主完成一次結構調整與素材/受眾 A/B，建立停損規則並紀錄。",
            "14天": "在守門值與頻次監控下逐步放量主力組合，同步驗證網站口徑是否已恢復可用。",
        },
    }
