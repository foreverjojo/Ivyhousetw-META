"""
檔案用途：週會 Moderator（決策與派工）輸出模組
職責：
  - 依 report_summary / report_insights / consultant_notes 產出 workflow_state.json
  - 將 workflow_state.json 轉為 meeting.md（週會可讀 Markdown）
注意事項：
  - 僅引用輸入數字，不重算任何 KPI（ROAS/CPC/CTR 等）
  - 需避免缺欄位導致 meeting.md 顯示大量「（待補）」
"""

import json
import os
from typing import Any, Dict, Optional, Tuple

import requests

from core.config import MODEL_MODERATOR
from core.llm_monitor import LLMCall, estimate_cost, get_monitor
from scripts.moderator_meeting import build_meeting_markdown, write_artifacts
from scripts.moderator_fallback import build_deterministic_workflow_state
from utils import now_iso

llm_monitor = get_monitor()


def _openrouter_chat_completion(
    messages,
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 10000,
) -> Tuple[str, Dict[str, int]]:
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

    usage = data.get("usage", {}) or {}
    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens) or 0)

    content = data["choices"][0]["message"].get("content")
    if content is None:
        content = ""
    return str(content), {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": total_tokens}


def _try_parse_json(s: str) -> Dict[str, Any]:
    if not s:
        return {"error": "Empty response from LLM", "raw_content": "", "decisions": ["Error: Empty response"]}
    s = s.strip()
    first = s.find("{")
    last = s.rfind("}")
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
            "raw_content": s[:4000] + "..." if len(s) > 4000 else s,
            "decisions": [f"Error parsing JSON: {str(e)}"]
        }


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
    *,
    step: str = "F",
    version_fp: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Moderator 輸出 workflow_state.json（乾淨 JSON）
    - 只引用輸入中的數字，不重算 KPI
    - 可選整合三顧問 consultant_notes
    """
    model = model or os.getenv("MODEL_MODERATOR") or MODEL_MODERATOR

    guardrails = _guardrail_check(report_summary)

    compact_input = {
        "week_id": report_summary.get("week_id"),
        "date_range": report_summary.get("date_range"),
        "kpi": report_summary.get("kpi", {}),
        "tables": report_summary.get("tables", {}),
        "missing_data": report_summary.get("missing_data", {}),
        "consultants": consultant_notes or {},
        "insights": report_insights,
        "skills": (report_summary.get("_context") or {}).get("skills") or {},
        "guardrails": guardrails,
    }

    system = (
        "你是艾薇手工坊的週會 Moderator（決策與交辦）。"
        "你只能引用輸入中的數字，不可重新計算或改寫 KPI。"
        "若輸入含 'skills' (Metric Tree/Fatigue/Budget)，請摘要其觸發的警告與建議。"
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
        f"{json.dumps(compact_input, ensure_ascii=False)}"
    )

    if consultant_notes:
        errs = []
        for k, v in consultant_notes.items():
             if isinstance(v, dict) and "error" in v:
                 errs.append(f"{k}: {v['error']}")
        if errs:
            user += f"\n\n[SYSTEM WARNING] Consultants returned errors: {'; '.join(errs)}. Please explicitly state these errors in 'consultant_summary' and 'risks' instead of hallucinating content."

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    total_usage: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    try:
        content, usage_main = _openrouter_chat_completion(messages, model=model, temperature=0.2, max_tokens=2400)
        total_usage = usage_main
    except Exception as e:
        # OpenRouter 失敗（常見：context 超限/網路問題），直接改走 deterministic 組裝，避免整段報告缺失
        try:
            llm_monitor.log_call(
                LLMCall(
                    timestamp=now_iso(),
                    model=model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    cost_usd=0.0,
                    function="build_workflow_state",
                    week_id=str(report_summary.get("week_id") or "").strip() or None,
                    extra=(
                        {"step": step, "version_fp": version_fp, "fallback": True, "error": str(e)[:200]}
                        if version_fp
                        else {"step": step, "fallback": True, "error": str(e)[:200]}
                    ),
                )
            )
        except Exception:
            pass
        return build_deterministic_workflow_state(
            report_summary=report_summary,
            report_insights=report_insights,
            consultant_notes=consultant_notes,
            guardrails=guardrails,
        )

    out = _try_parse_json(content)
    if "error" in out:  # 如果第一次解析失敗（包含 error key），嘗試修復
        # 避免把超長 raw content 全塞回 repair prompt 導致 context 超限
        content_snippet = content if len(content) <= 12000 else (content[:12000] + "\n...[TRUNCATED]...")
        repair_messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "你上一次輸出不是合法 JSON。請只輸出『單一 JSON object』，不要任何多餘字元。"},
            {"role": "user", "content": content_snippet},
        ]
        try:
            content2, usage_repair = _openrouter_chat_completion(repair_messages, model=model, temperature=0.0, max_tokens=2400)
            total_usage = {
                "prompt_tokens": int(total_usage.get("prompt_tokens", 0) or 0) + int(usage_repair.get("prompt_tokens", 0) or 0),
                "completion_tokens": int(total_usage.get("completion_tokens", 0) or 0) + int(usage_repair.get("completion_tokens", 0) or 0),
                "total_tokens": int(total_usage.get("total_tokens", 0) or 0) + int(usage_repair.get("total_tokens", 0) or 0),
            }
            out = _try_parse_json(content2)
        except Exception:
            return build_deterministic_workflow_state(
                report_summary=report_summary,
                report_insights=report_insights,
                consultant_notes=consultant_notes,
                guardrails=guardrails,
            )

    try:
        llm_monitor.log_call(
            LLMCall(
                timestamp=now_iso(),
                model=model,
                prompt_tokens=int(total_usage.get("prompt_tokens", 0) or 0),
                completion_tokens=int(total_usage.get("completion_tokens", 0) or 0),
                total_tokens=int(total_usage.get("total_tokens", 0) or 0),
                cost_usd=estimate_cost(
                    model,
                    int(total_usage.get("prompt_tokens", 0) or 0),
                    int(total_usage.get("completion_tokens", 0) or 0),
                ),
                function="build_workflow_state",
                week_id=str(report_summary.get("week_id") or "").strip() or None,
                extra={"step": step, "version_fp": version_fp} if version_fp else {"step": step},
            )
        )
    except Exception:
        pass

    # 若仍解析失敗，直接改走 deterministic 組裝，避免 meeting.md 大量空白
    if isinstance(out, dict) and out.get("error"):
        return build_deterministic_workflow_state(
            report_summary=report_summary,
            report_insights=report_insights,
            consultant_notes=consultant_notes,
            guardrails=guardrails,
        )

    out.setdefault("schema_version", "workflow_state.v1")
    out.setdefault("week_id", report_summary.get("week_id"))
    out.setdefault("date_range", report_summary.get("date_range"))

    # 保險：避免模型少輸欄位，導致 meeting.md 從「三顧問摘要」開始大量顯示（待補）
    # guardrail_check 若缺失，meeting renderer 會顯示 Tier1/Tier2 為「（待補）」
    if "guardrail_check" not in out and "guardrails" not in out:
        out["guardrail_check"] = guardrails
    out.setdefault("consultant_summary", [])
    out.setdefault("department_actions", {})
    out.setdefault("risks", [])
    out.setdefault("validation_plan", {})
    out.setdefault("guardrail", guardrails)

    # 次級保險：若模型仍輸出為空，從既有輸入做最小可用的 fallback（不憑空捏造數字）
    if consultant_notes and not out.get("consultant_summary"):
        def _sanitize_summary_text(s: str) -> str:
            """
            避免三顧問摘要直接露出 snake_case 技術欄位（例如 platform_purchase_value_twd）。
            只做輕量替換與截斷，不改寫數字本體。
            """
            s = (s or "").strip().replace("\n", " ")
            replacements = {
                "meta_kpi.": "Meta KPI：",
                "web_kpi.": "Web KPI：",
                "tables.": "表格：",
                "platform_purchase_value_twd": "平台回傳成交額（TWD）",
                "website_purchase_value_twd": "網站回傳成交額（TWD）",
                "purchase_value_twd": "成交額（TWD）",
                "platform_purchases": "平台購買數",
                "website_purchases": "網站購買數",
                "roas_platform_calc": "平台 ROAS",
                "roas_calc": "ROAS",
                "cpa_platform_calc_twd": "平台 CPA（TWD）",
                "cpa_calc_twd": "CPA（TWD）",
            }
            for k, v in replacements.items():
                s = s.replace(k, v)
            return s[:240] + ("…" if len(s) > 240 else "")

        def _is_good_text(s: str) -> bool:
            s = (s or "").strip()
            if not s:
                return False
            if s in {"A", "B", "C"}:
                return False
            if len(s) <= 2:
                return False
            # 避免把技術欄位 key 當成摘要（snake_case / dot.path）
            has_cjk = any("\u4e00" <= ch <= "\u9fff" for ch in s)
            if not has_cjk:
                if ("_" in s or "." in s) and all(ch.isalnum() or ch in "._-" for ch in s):
                    return False
            # 避免把整段 JSON / raw dump 當摘要
            if len(s) > 400 and ("{" in s and "}" in s):
                return False
            return True

        def pick_first_text(obj: Any) -> Optional[str]:
            if isinstance(obj, str):
                s = obj.strip()
                return s if _is_good_text(s) else None
            if isinstance(obj, list):
                for it in obj:
                    s = pick_first_text(it)
                    if s:
                        return s
            if isinstance(obj, dict):
                status = str(obj.get("status") or "").strip().lower()
                if status in {"awaiting_data_input", "needs_data", "need_data"}:
                    s = pick_first_text(obj.get("message")) or pick_first_text(obj.get("next_step"))
                    if s:
                        return f"資料不足：{s}"
                # 優先常見欄位，避免遍歷整包資料太耗
                for k in [
                    "summary",
                    "executive_summary",
                    "key_takeaways",
                    "opportunities",
                    "next_7d_actions",
                    "message",
                    "next_step",
                    "title",
                ]:
                    if k in obj:
                        s = pick_first_text(obj.get(k))
                        if s:
                            return s
                for kk, v in obj.items():
                    # 避免把 schema/型別等技術欄位當成「重點」
                    if kk in [
                        "schema",
                        "schema_version",
                        "context_version",
                        "consultant_type",
                        "consultant_name",
                        "consultant_key",
                        "model",
                        "role",
                        "consultant",
                        "report_meta",
                        # 常見「技術描述」欄位，避免抓到變數/欄位名稱
                        "issue",
                        "overall_assessment",
                        "overall_health",
                        "overall_theme",
                        "trend",
                        "trends",
                        "raw_content",
                        "error",
                        "errors",
                        "usage",
                        "prompt_tokens",
                        "completion_tokens",
                        "total_tokens",
                    ]:
                        continue
                    s = pick_first_text(v)
                    if s:
                        return s
            return None

        bullets: list[str] = []
        for key in ["consultant_A", "consultant_B", "consultant_C"]:
            c = consultant_notes.get(key)
            if isinstance(c, dict) and c.get("error"):
                bullets.append(f"{key} 輸出失敗：{c.get('error')}")
                continue
            s = pick_first_text(c)
            if s:
                bullets.append(f"{key} 重點：{_sanitize_summary_text(s)}")
            else:
                bullets.append(f"{key} 重點：（未提供有效摘要；請查看該顧問輸出）")
        out["consultant_summary"] = bullets[:10]

    det: Optional[Dict[str, Any]] = None

    def _get_det() -> Dict[str, Any]:
        nonlocal det
        if det is None:
            det = build_deterministic_workflow_state(
                report_summary=report_summary,
                report_insights=report_insights,
                consultant_notes=consultant_notes,
                guardrails=guardrails,
            )
        return det

    required = ["GM", "Finance", "E-commerce", "Marketing", "Fulfillment"]

    def _is_missing(v: Any) -> bool:
        if v is None:
            return True
        s = str(v).strip()
        return (s == "") or (s == "（待補）")

    def _dept_needs_fallback(items: Any) -> bool:
        if not isinstance(items, list) or not items:
            return True
        for it in items:
            if not isinstance(it, dict):
                return False
            if any(not _is_missing(it.get(k)) for k in ["owner_role", "deliverable", "kpi", "stoploss", "due"]):
                return False
        return True

    # 讓 meeting.md 盡量不要出現大量（待補）：缺部門/全空/只剩 task 的情況就用 deterministic 補齊
    da = out.get("department_actions")
    if not isinstance(da, dict) or not da:
        out["department_actions"] = _get_det()["department_actions"]
    else:
        for d in required:
            if d not in da or not isinstance(da.get(d), list):
                da[d] = []
            if _dept_needs_fallback(da.get(d)):
                da[d] = _get_det()["department_actions"].get(d, []) or da.get(d, [])

    # risks：常見漂移是被塞進 consultant_summary.risks，或乾脆缺欄位
    risks_out = out.get("risks")
    if not isinstance(risks_out, list) or not risks_out:
        cs = out.get("consultant_summary")
        if isinstance(cs, dict):
            cs_risks = cs.get("risks")
            if isinstance(cs_risks, list) and cs_risks:
                out["risks"] = cs_risks[:6]
        if not out.get("risks"):
            out["risks"] = _get_det()["risks"]

    if not out.get("decisions"):
        out["decisions"] = _get_det()["decisions"]

    if not out.get("validation_plan"):
        out["validation_plan"] = {
            "3天": "完成追蹤/歸因排查與對帳定義，確認 purchase value 回傳與口徑差異來源。",
            "7天": "以平台口徑為主完成一次結構調整與素材/受眾 A/B，建立停損規則並紀錄。",
            "14天": "在守門值與頻次監控下逐步放量主力組合，同步驗證網站口徑是否已恢復可用。",
        }
    return out
