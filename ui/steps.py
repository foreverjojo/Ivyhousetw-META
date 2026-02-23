"""
檔案用途：Ivy House Meta 週報分析系統 - Streamlit UI 步驟處理器
職責：
  - 封裝 Step B~F 的執行邏輯
  - 處理 pipeline state 管理
  - 提供 session 同步與版本控制
  - 與 app.py 解耦，降低主程式複雜度
"""

import json
import shutil
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import streamlit as st

# Core imports
from core import (
    HISTORY_ROOT,
    SCHEMAS_DIR,
    TAIPEI_TZ,
    SchemaValidationError,
    write_pipeline_state,
)
from core.validation import validate_report_summary as _validate_report_summary_raw
from core.logging import get_logger

# Utils imports
from utils import (
    read_json_if_exists,
    write_json,
    read_text_if_exists,
    write_text,
    sha256_str,
    normalize_week_id,
    now_iso,
    week_meta_dir as utils_week_meta_dir,
    versions_root as utils_versions_root,
    version_dir as utils_version_dir,
    read_latest_ptr as utils_read_latest_ptr,
    write_latest_ptr as utils_write_latest_ptr,
    write_week_info as utils_write_week_info,
    ensure_week_meta_dirs as utils_ensure_week_meta_dirs,
)
from utils.week_utils import get_prev_week_id as _get_prev_week_id_raw

# Scripts imports
from scripts.kpi_calc import build_report_summary
from scripts.llm_insights import generate_report_insights
from scripts.consultants import generate_consultant_notes, generate_consultant_cross_reviews
from scripts.moderator import build_workflow_state
from scripts.moderator_meeting import build_meeting_markdown, write_artifacts
from scripts.adapters.shopee_adapter import adapt_shopee_ad_csv
from scripts.adapters.momo_adapter import adapt_momo_ad_report
from scripts.json_to_readable import (
    render_report_insights,
    render_consultant_note,
    render_skeleton_insight,
)

logger = get_logger(__name__)


# =========================
# 包裝函式（自動傳入 HISTORY_ROOT 等參數）
# =========================


def week_meta_dir(week_id: str) -> Path:
    """包裝函式：自動傳入 HISTORY_ROOT"""
    return utils_week_meta_dir(week_id, HISTORY_ROOT)


def versions_root(week_id: str) -> Path:
    """包裝函式：自動傳入 HISTORY_ROOT"""
    return utils_versions_root(week_id, HISTORY_ROOT)


def version_dir(week_id: str, fp_code: str) -> Path:
    """包裝函式：自動傳入 HISTORY_ROOT"""
    return utils_version_dir(week_id, fp_code, HISTORY_ROOT)


def read_latest_ptr(week_id: str) -> Optional[dict]:
    """包裝函式：自動傳入 HISTORY_ROOT"""
    return utils_read_latest_ptr(week_id, HISTORY_ROOT)


def write_latest_ptr(week_id: str, fp_code: str) -> None:
    """包裝函式：自動傳入 HISTORY_ROOT"""
    utils_write_latest_ptr(week_id, fp_code, HISTORY_ROOT)


def write_week_info(week_id: str, date_range: str) -> None:
    """包裝函式：自動傳入 HISTORY_ROOT"""
    utils_write_week_info(week_id, date_range, HISTORY_ROOT)


def ensure_week_meta_dirs(week_id: str) -> None:
    """包裝函式：自動傳入 HISTORY_ROOT"""
    utils_ensure_week_meta_dirs(week_id, HISTORY_ROOT)


def validate_report_summary(rs: dict) -> None:
    """包裝函式：自動傳入 SCHEMAS_DIR"""
    _validate_report_summary_raw(rs, SCHEMAS_DIR)


def get_prev_week_id(current_week_id: str) -> Optional[str]:
    """包裝函式：自動傳入 HISTORY_ROOT"""
    return _get_prev_week_id_raw(current_week_id, HISTORY_ROOT)


# =========================
# 輔助函式
# =========================


def safe_stamp() -> str:
    """檔名安全時間戳（用於 staging 資料夾）"""
    if TAIPEI_TZ:
        return datetime.now(TAIPEI_TZ).strftime("%Y%m%d_%H%M%S")
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def staging_version_dir(fp_code: str) -> Path:
    """暫存版本目錄：用於記錄 week_id/vdir 確定前的 Step B 早期錯誤"""
    return HISTORY_ROOT / "_staging" / safe_stamp() / "meta" / "versions" / f"fp-{fp_code}"


def _cleanup_staging_on_success(stage_vdir: Path) -> None:
    """Step B 成功後清理單一 staging 執行資料夾

    預期結構：
      history/_staging/<stamp>/meta/versions/fp-xxxxxxxx  <-- stage_vdir
    刪除：
      history/_staging/<stamp>
    """
    try:
        p = str(stage_vdir).replace("\\", "/")
        if "/_staging/" not in p:
            return

        stamp_dir = None
        for parent in stage_vdir.parents:
            if parent.parent and parent.parent.name == "_staging":
                stamp_dir = parent
                break

        if not stamp_dir:
            return
        if stamp_dir.name in ("", "_staging"):
            return

        shutil.rmtree(stamp_dir, ignore_errors=True)
    except Exception:
        pass


def step_exists(vdir: Path, filename: str) -> bool:
    return (vdir / filename).exists()


def load_or_session(key: str, path: Path):
    if key in st.session_state:
        return st.session_state[key]
    obj = read_json_if_exists(path)
    if obj is not None:
        st.session_state[key] = obj
    return st.session_state.get(key)


def sync_manual_inputs_to_inputs_json(vdir: Path) -> None:
    p = vdir / "inputs.json"
    if not p.exists():
        return
    obj = read_json_if_exists(p) or {}
    obj["manual_inputs"] = st.session_state.get("manual_inputs") or {}
    obj["updated_at"] = now_iso()
    write_json(p, obj)


def load_prev_week_context(curr_week_id: str) -> dict:
    prev = get_prev_week_id(curr_week_id)
    if not prev:
        return {"prev_week_id": None, "prev_meta": None}

    ptr = read_latest_ptr(prev)
    if not ptr or "fp" not in ptr:
        return {"prev_week_id": prev, "prev_meta": None}

    prev_vdir = version_dir(prev, ptr["fp"])
    prev_ws = read_json_if_exists(prev_vdir / "workflow_state.json")
    prev_rs = read_json_if_exists(prev_vdir / "report_summary.json")
    return {
        "prev_week_id": prev,
        "prev_meta": {
            "week_id": prev,
            "fp": ptr["fp"],
            "workflow_state": prev_ws,
            "report_summary": prev_rs,
        },
    }


def detect_mismatch_vs_latest(week_id: str, fp_code_: str) -> Tuple[bool, Optional[str]]:
    """mismatch 第一真值：latest_ptr.fp 是否等於 current fp_code。"""
    ptr = read_latest_ptr(week_id)
    if not ptr or "fp" not in ptr:
        return (False, None)
    latest_fp = ptr["fp"]
    return (latest_fp != fp_code_, latest_fp)


def choose_version_dir_for_run(
    report_summary: dict,
    fp_code_: str,
    force_rerun: bool,
    auto_new_version: bool,
) -> Tuple[str, Path]:
    """
    回傳： (resolved_fp_code, vdir)

    ✅ 語意（可驗收）：
    - Force re-run：
        * 永遠覆蓋「本次 fp_code」對應資料夾（若不存在就建立）
        * 絕不覆蓋不同 fp 的 latest（避免資料夾名與 fingerprint 失配）
    - 非 Force：
        - 若本週尚無 latest：建立本 fp
        - 若 latest.fp != 本 fp：
            * auto_new_version=True -> 建本 fp
            * 否則停下（避免用錯資料）
        - 若 latest.fp == 本 fp：用本 fp（若資料夾不存在就建立）
    """
    week_id_raw = report_summary.get("week_id") or ""
    week_id = normalize_week_id(week_id_raw)
    if not week_id:
        raise RuntimeError(f"report_summary.week_id 不合法：{week_id_raw}（需 YYYY-Www）")

    ensure_week_meta_dirs(week_id)
    write_week_info(week_id, report_summary.get("date_range") or "")

    fp_vdir = version_dir(week_id, fp_code_)
    mismatch, latest_fp = detect_mismatch_vs_latest(week_id, fp_code_)

    if force_rerun:
        fp_vdir.mkdir(parents=True, exist_ok=True)
        return (fp_code_, fp_vdir)

    if latest_fp is None:
        fp_vdir.mkdir(parents=True, exist_ok=True)
        return (fp_code_, fp_vdir)

    if mismatch:
        if auto_new_version:
            fp_vdir.mkdir(parents=True, exist_ok=True)
            return (fp_code_, fp_vdir)
        raise RuntimeError(
            "偵測到與本週 latest.fp 不一致，且未啟用 Auto new version / Force，已停止以避免用錯資料。"
        )

    fp_vdir.mkdir(parents=True, exist_ok=True)
    return (fp_code_, fp_vdir)


def build_inputs_snapshot(
    report_summary: dict,
    current_fp_: dict,
    fp_code_: str,
    meta_adset_file_,
    meta_ads_file_,
    web_excel_file_,
    prev_ctx: dict,
) -> dict:
    return {
        "schema_version": "inputs_snapshot.v3",
        "created_at": now_iso(),
        "week_id": report_summary.get("week_id"),
        "date_range": report_summary.get("date_range"),
        "uploaded_files": {
            "meta_adset": getattr(meta_adset_file_, "name", ""),
            "meta_ads": getattr(meta_ads_file_, "name", ""),
            "web_excel": getattr(web_excel_file_, "name", ""),
        },
        "fingerprint": current_fp_,
        "fp_short": fp_code_,
        "manual_inputs": st.session_state.get("manual_inputs") or {},
        "prev_week": {"week_id": prev_ctx.get("prev_week_id")},
    }


def rs_with_context(rs: dict, current_fp_: dict, fp_code_: str, prev_ctx: dict) -> dict:
    enriched = dict(rs or {})
    enriched["_context"] = {
        "fingerprint": current_fp_,
        "fp_short": fp_code_,
        "manual_inputs": st.session_state.get("manual_inputs") or {},
        "skills": st.session_state.get("skills_context") or {},
        "prev_week": prev_ctx,
        "time": {"tz": "Asia/Taipei", "now": now_iso()},
    }
    return enriched


# =========================
# Step Handlers
# =========================


def run_step_b(
    mode_label: str,
    can_run: bool,
    current_fp: dict,
    fp_code: str,
    meta_adset_file=None,
    meta_ads_file=None,
    web_excel_file=None,
    shopee_file=None,
    momo_file=None,
    platform: str = "Meta",
    force_rerun: bool = False,
    auto_new_version: bool = False,
    render_sidebar_status_fn=None,
):
    """
    Step B: 資料整合與基礎 KPI 計算 (Deterministic)

    支援多平台：
      - Meta: 使用舊有邏輯 (kpi_calc.build_report_summary)
      - Shopee: 使用 adapt_shopee_ad_csv -> 統一格式 -> Aggregate -> Report Summary
      - Momo: 使用 adapt_momo_ad_xlsx -> 統一格式 -> Aggregate -> Report Summary
    """
    if not can_run:
        return None, None, None, None

    from core.tracing import ensure_trace_id

    # Step B 是整個流程的起點：若尚未有 trace_id，這裡建立一個，並延續到後續步驟
    ensure_trace_id(prefix="ui")
    logger.info(
        f"[{mode_label}] Starting Step B... (Platform: {platform})",
        step="B",
        mode=mode_label,
        platform=platform,
    )

    # === 第一步：生成 report_summary（需要先有 week_id 才能建立版本目錄） ===

    report_summary = {}

    if platform.startswith("Shopee") and shopee_file:
        st.info("🛒 執行蝦皮數據轉換 (Adapter)...")
        # 暫時使用 staging 目錄
        staging_dir = staging_version_dir(fp_code)
        staging_dir.mkdir(parents=True, exist_ok=True)
        temp_shopee_path = staging_dir / "raw_shopee_report.csv"
        with open(temp_shopee_path, "wb") as f:
            f.write(shopee_file.getvalue())

        # 呼叫 Adapter
        unified_payload = adapt_shopee_ad_csv(temp_shopee_path)
        unified_data = unified_payload.get("data", [])

        # 簡易 Aggregation
        total_spend = sum(d["metrics"]["spend"] for d in unified_data)
        total_rev = sum(d["metrics"]["conversions"]["platform"]["value"] for d in unified_data)

        from datetime import datetime

        now_iso = datetime.now().isoformat()

        report_summary = {
            "platform": "Shopee",
            "currency": "TWD",
            "date_range": "Unknown",
            "schema_version": "report_summary.v1",
            "generated_at": now_iso,
            "kpi": {
                "meta": {
                    "spend_twd": total_spend,
                    "purchase_value_twd": total_rev,
                    "purchases": 0,
                    "roas_calc": 0,
                    "cpa_calc_twd": 0,
                    "funnel": {
                        "link_clicks": 0,
                        "landing_page_views": 0,
                        "add_to_cart": 0,
                        "initiate_checkout": 0,
                    },
                    "ads_has_rankings": False,
                },
                "web": {"orders": 0, "revenue_twd": 0, "aov_twd_calc": 0, "columns": []},
            },
            "tables": {
                "top_adsets_by_roas": [],
                "worst_adsets_by_roas": [],
                "top_ads_by_roas": [],
                "worst_ads_by_roas": [],
            },
            "missing_data": {"meta_unavailable_fields": [], "note": ""},
            "kpi_truth_source": "shopee_adapter",
            "ad_diagnostics_source": "shopee_adapter",
            "roas": total_rev / total_spend if total_spend > 0 else 0,
            "unified_data_count": len(unified_data),
            "week_id": f"Shopee_{now_iso[:10]}",
        }
        st.write(f"Parsed {len(unified_data)} records from Shopee.")

    elif platform.startswith("Momo") and momo_file:
        st.info("🛍️ 執行 Momo 數據轉換 (Adapter)...")
        # 暫時使用 staging 目錄
        staging_dir = staging_version_dir(fp_code)
        staging_dir.mkdir(parents=True, exist_ok=True)
        temp_momo_path = staging_dir / "raw_momo_report.xlsx"
        with open(temp_momo_path, "wb") as f:
            f.write(momo_file.getvalue())

        # 呼叫 Adapter
        unified_payload = adapt_momo_ad_report(temp_momo_path)
        unified_data = unified_payload.get("data", [])

        # 簡易 Aggregation
        total_spend = sum(d["metrics"]["spend"] for d in unified_data)
        total_rev = sum(d["metrics"]["conversions"]["platform"]["value"] for d in unified_data)

        from datetime import datetime

        now_iso = datetime.now().isoformat()

        report_summary = {
            "platform": "Momo",
            "currency": "TWD",
            "date_range": "Unknown",
            "schema_version": "report_summary.v1",
            "generated_at": now_iso,
            "kpi": {
                "meta": {
                    "spend_twd": total_spend,
                    "purchase_value_twd": total_rev,
                    "purchases": 0,
                    "roas_calc": 0,
                    "cpa_calc_twd": 0,
                    "funnel": {
                        "link_clicks": 0,
                        "landing_page_views": 0,
                        "add_to_cart": 0,
                        "initiate_checkout": 0,
                    },
                    "ads_has_rankings": False,
                },
                "web": {"orders": 0, "revenue_twd": 0, "aov_twd_calc": 0, "columns": []},
            },
            "tables": {
                "top_adsets_by_roas": [],
                "worst_adsets_by_roas": [],
                "top_ads_by_roas": [],
                "worst_ads_by_roas": [],
            },
            "missing_data": {"meta_unavailable_fields": [], "note": ""},
            "kpi_truth_source": "momo_adapter",
            "ad_diagnostics_source": "momo_adapter",
            "roas": total_rev / total_spend if total_spend > 0 else 0,
            "unified_data_count": len(unified_data),
            "week_id": f"Momo_{now_iso[:10]}",
        }
        st.write(f"Parsed {len(unified_data)} records from Momo.")

    else:
        # Default: Meta
        st.info("執行 Meta KPI 計算...")

        # 讀檔為 bytes (build_report_summary 期望 bytes 輸入)
        meta_adset_file.seek(0)
        meta_ads_file.seek(0)
        web_excel_file.seek(0)

        meta_adset_bytes = meta_adset_file.read()
        meta_ads_bytes = meta_ads_file.read()
        web_excel_bytes = web_excel_file.read()

        report_summary = build_report_summary(meta_adset_bytes, meta_ads_bytes, web_excel_bytes)

    # === 第二步：有了 report_summary，現在可以取得/建立版本目錄 ===

    resolved_fp_code, vdir = choose_version_dir_for_run(
        report_summary, fp_code, force_rerun, auto_new_version
    )

    # 確保目錄存在
    vdir.mkdir(parents=True, exist_ok=True)

    # === 第三步：儲存產出物 ===

    # 儲存 Report Summary
    (vdir / "report_summary.json").write_text(
        json.dumps(report_summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 載入前一週 Context
    week_id = report_summary.get("week_id", "Unknown")
    prev_ctx = load_prev_week_context(week_id)

    # 儲存 Inputs Snapshot
    snapshot_inputs = {
        "platform": platform,
        "fp_code": fp_code,
        "files": {
            "meta_adset": meta_adset_file.name if meta_adset_file else None,
            "shopee": shopee_file.name if shopee_file else None,
            "momo": momo_file.name if momo_file else None,
        },
    }
    (vdir / "inputs.json").write_text(
        json.dumps(snapshot_inputs, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 更新 Sidebar
    if render_sidebar_status_fn:
        render_sidebar_status_fn(week_id, vdir)

    logger.info(
        f"[{mode_label}] Step B Done. WeekID: {week_id}, VDir: {vdir}",
        step="B",
        week_id=week_id,
        mode=mode_label,
        vdir=str(vdir),
    )
    return week_id, resolved_fp_code, vdir, prev_ctx


def run_step_c(
    mode_label: str,
    week_id: str,
    vdir: Path,
    prev_ctx: dict,
    resolved_fp: str,
    current_fp: dict,
    force_rerun: bool,
    render_sidebar_status_fn,
    realtime_container=None,
) -> None:
    """
    Step C: LLM 洞察生成

    參數:
        realtime_container: Streamlit 容器，用於即時顯示可讀摘要
    """
    logger.info("Step C 開始", week_id=week_id, mode=mode_label)
    sync_manual_inputs_to_inputs_json(vdir)

    if (not force_rerun) and step_exists(vdir, "report_insights.json"):
        ri = load_or_session("report_insights", vdir / "report_insights.json")
        if ri:
            # 即使 skip，仍可顯示既有結果
            if realtime_container is not None:
                try:
                    readable = render_report_insights(ri)
                    realtime_container.markdown(readable)
                except Exception:
                    pass  # 容許渲染失敗，不影響流程
            write_pipeline_state(vdir, "C1(skip)", mode_label)
            render_sidebar_status_fn(week_id, vdir)
            return

    with st.status(f"{mode_label}｜Step C：LLM 洞察生成中...", expanded=True) as status:
        if realtime_container is not None:
            realtime_container.markdown(render_skeleton_insight())

        status.write("🔍 正在分析本週 KPI...")
        rs = load_or_session("report_summary", vdir / "report_summary.json")
        if not rs:
            raise RuntimeError("缺少 report_summary（Step B 未成功）")

        # Optional: project skills (deterministic) - driven by manual command
        # Execute Agent Skills (Top 1/2/3)
        mi = st.session_state.get("manual_inputs") or {}
        skills_ctx: Dict[str, Any] = {}
        skills_errors: list[dict] = []

        # Skill 1: Metric Tree Diagnostic (Top 1)
        # 診斷 KPI 樹狀結構與異常歸因
        try:
            from scripts.skills.metric_tree_diagnostic import run_metric_tree_diagnostic

            skill_t1 = run_metric_tree_diagnostic(rs)
            skills_ctx["metric_tree_diagnostic"] = skill_t1
            write_json(vdir / "skill_metric_tree_diagnostic.json", skill_t1)
        except Exception as e:
            logger.error(f"Skill metric_tree_diagnostic failed: {e}")
            skills_errors.append(
                {
                    "skill": "metric_tree_diagnostic",
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                }
            )

        # Skill 2: Creative Fatigue (Top 2)
        # 偵測素材疲乏與高潛力素材
        # 注意：因架構限制，我們使用 report_summary 中的 top/worst tables 作為樣本
        # 這可能漏掉中間層廣告，但在 MVP 階段可接受
        try:
            from scripts.skills.creative_fatigue import run_creative_fatigue_diagnostic

            ads_samples = []
            if "tables" in rs:
                ads_samples.extend(rs["tables"].get("top_ads_by_roas", []))
                ads_samples.extend(rs["tables"].get("worst_ads_by_roas", []))

            skill_t2 = run_creative_fatigue_diagnostic(rs, ads_samples)
            skills_ctx["creative_fatigue"] = skill_t2
            write_json(vdir / "skill_creative_fatigue.json", skill_t2)
        except Exception as e:
            logger.error(f"Skill creative_fatigue failed: {e}")
            skills_errors.append(
                {
                    "skill": "creative_fatigue",
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                }
            )

        # Skill 3: Budget Rules (Top 3)
        # 預算配置規則與建議
        try:
            from scripts.skills.budget_rules import run_budget_rules

            skill_t3 = run_budget_rules(rs, mi)
            skills_ctx["budget_rules"] = skill_t3
            write_json(vdir / "skill_budget_rules.json", skill_t3)
        except Exception as e:
            logger.error(f"Skill budget_rules failed: {e}")
            skills_errors.append(
                {
                    "skill": "budget_rules",
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                }
            )

        if skills_errors:
            try:
                write_json(
                    vdir / "skill_execution_error.json",
                    {
                        "schema_version": "skill_execution_error.v1",
                        "generated_at": now_iso(),
                        "week_id": week_id,
                        "version_fp": vdir.name,
                        "errors": skills_errors,
                    },
                )
            except Exception:
                pass

        # Store in session for subsequent steps
        st.session_state["skills_context"] = skills_ctx

        status.write("🤖 LLM 正在生成洞察...")
        insights = generate_report_insights(
            rs_with_context(rs, current_fp, resolved_fp, prev_ctx),
            version_fp=vdir.name,
        )  # type: ignore[arg-type]

        status.write("💾 儲存結果...")
        write_json(vdir / "report_insights.json", insights)
        st.session_state["report_insights"] = insights

        if realtime_container is not None:
            try:
                readable = render_report_insights(insights)
                realtime_container.markdown(readable)
            except Exception as e:
                logger.warning("即時渲染失敗", error=str(e))

        status.update(label=" Step C：洞察分析完成", state="complete")

    write_pipeline_state(vdir, "C1", mode_label)
    logger.info("Step C 完成", week_id=week_id, mode=mode_label)
    render_sidebar_status_fn(week_id, vdir)


def run_step_d_draft(
    mode_label: str,
    week_id: str,
    vdir: Path,
    prev_ctx: dict,
    resolved_fp: str,
    current_fp: dict,
    force_rerun: bool,
    render_sidebar_status_fn,
) -> None:
    logger.info("Step D (draft) 開始", week_id=week_id, mode=mode_label)
    sync_manual_inputs_to_inputs_json(vdir)

    if (
        (not force_rerun)
        and step_exists(vdir, "meeting_draft.md")
        and step_exists(vdir, "workflow_state_draft.json")
    ):
        wsd = read_json_if_exists(vdir / "workflow_state_draft.json")
        if wsd:
            st.session_state["workflow_state_draft"] = wsd
            mdd = read_text_if_exists(vdir / "meeting_draft.md")
            if mdd:
                st.session_state["meeting_md_draft"] = mdd
            write_pipeline_state(vdir, "D(draft)(skip)", mode_label)
            render_sidebar_status_fn(week_id, vdir)
            return

    with st.spinner(
        f"{mode_label}｜Step D：Moderator draft -> meeting_draft/workflow_state_draft..."
    ):
        rs = load_or_session("report_summary", vdir / "report_summary.json")
        ri = load_or_session("report_insights", vdir / "report_insights.json")
        if not rs or not ri:
            raise RuntimeError("缺少 report_summary/report_insights（Step B/C 未成功）")

        rs_ctx = rs_with_context(rs, current_fp, resolved_fp, prev_ctx)  # type: ignore[arg-type]
        ws = build_workflow_state(rs_ctx, ri, step="D", version_fp=vdir.name)
        md = build_meeting_markdown(ws, rs_ctx, ri)

        write_text(vdir / "meeting_draft.md", md)
        write_json(vdir / "workflow_state_draft.json", ws)

        st.session_state["workflow_state_draft"] = ws
        st.session_state["meeting_md_draft"] = md

    write_pipeline_state(vdir, "D(draft)", mode_label)
    logger.info("Step D (draft) 完成", week_id=week_id, mode=mode_label)
    render_sidebar_status_fn(week_id, vdir)


def run_step_e(
    mode_label: str,
    week_id: str,
    vdir: Path,
    prev_ctx: dict,
    resolved_fp: str,
    current_fp: dict,
    force_rerun: bool,
    render_sidebar_status_fn,
    status_callback=None,
    realtime_container=None,
) -> None:
    """
    Step E: 三顧問分析

    參數:
        status_callback: 顧問開始處理時的回呼 (role, model)
        realtime_container: Streamlit 容器，用於即時顯示顧問分析結果
    """
    logger.info("Step E (三顧問) 開始", week_id=week_id, mode=mode_label)
    sync_manual_inputs_to_inputs_json(vdir)

    if (not force_rerun) and step_exists(vdir, "consultant_notes.json"):
        cn = read_json_if_exists(vdir / "consultant_notes.json")
        if cn:
            st.session_state["consultant_notes"] = cn

            # 若先前版本尚未寫入自然語句檔，補寫到 history（不影響流程）
            try:
                notes = {
                    "A": cn.get("consultant_A") or {},
                    "B": cn.get("consultant_B") or {},
                    "C": cn.get("consultant_C") or {},
                }
                for role, note in notes.items():
                    p = vdir / f"consultant_{role}.md"
                    if p.exists():
                        continue
                    readable = render_consultant_note(
                        role, note if isinstance(note, dict) else {"error": "invalid_note_type"}
                    )
                    write_text(p, readable)
            except Exception as e:
                logger.warning("補寫顧問自然語句失敗", error=str(e))

            write_pipeline_state(vdir, "E(skip)", mode_label)
            render_sidebar_status_fn(week_id, vdir)
            return

    with st.spinner(f"{mode_label}｜Step E：三顧問 -> consultant_notes.json..."):
        rs = load_or_session("report_summary", vdir / "report_summary.json")
        ri = load_or_session("report_insights", vdir / "report_insights.json")
        if not rs or not ri:
            raise RuntimeError("缺少 report_summary/report_insights（Step B/C 未成功）")

        rs_ctx = rs_with_context(rs, current_fp, resolved_fp, prev_ctx)  # type: ignore[arg-type]
        cn = generate_consultant_notes(
            rs_ctx,
            ri,
            status_callback=status_callback,
            on_consultant_done=None,  # Step E 移除即時渲染（避免被 Step F 覆蓋且意義不大）
            version_fp=vdir.name,
        )
        write_json(vdir / "consultant_notes.json", cn)
        st.session_state["consultant_notes"] = cn

        # 將三位顧問的自然語句（Markdown）落盤到 history 版本資料夾，便於 QA/回溯
        try:
            notes = {
                "A": cn.get("consultant_A") or {},
                "B": cn.get("consultant_B") or {},
                "C": cn.get("consultant_C") or {},
            }
            for role, note in notes.items():
                readable = render_consultant_note(
                    role, note if isinstance(note, dict) else {"error": "invalid_note_type"}
                )
                write_text(vdir / f"consultant_{role}.md", readable)
        except Exception as e:
            logger.warning("寫入顧問自然語句失敗", error=str(e))

    write_pipeline_state(vdir, "E", mode_label)
    logger.info("Step E (三顧問) 完成", week_id=week_id, mode=mode_label)
    render_sidebar_status_fn(week_id, vdir)


def run_step_e2(
    mode_label: str,
    week_id: str,
    vdir: Path,
    render_sidebar_status_fn,
    status_callback=None,
    force_rerun: bool = False,
) -> None:
    """
    Step E2: 三顧問交叉審核（可選，預設 OFF）

    E2 邏輯：A 審核 B/C，B 審核 A/C，C 審核 A/B。
    落盤產物：consultant_cross_reviews.json

    降級策略：
    - E2 失敗（任一 reviewer 或全部）：記錄 error，不阻擋 Step F。
    - schema 驗證失敗：以警告顯示，仍可繼續。
    """
    from core.validation import validate_consultant_cross_review
    from core import SCHEMAS_DIR, SchemaValidationError

    logger.info("Step E2 (交叉審核) 開始", week_id=week_id, mode=mode_label)

    # 若使用者未啟用 E2，直接略過（但仍落 pipeline_state，讓流程可追溯）
    if not bool(st.session_state.get("enable_cross_review")):
        write_pipeline_state(
            vdir,
            "E2(skip)",
            mode_label,
            details=["disabled by user (enable_cross_review=OFF)"],
        )
        render_sidebar_status_fn(week_id, vdir)
        logger.info("Step E2 略過（使用者未啟用）", week_id=week_id)
        return

    # 若 E2 落盤已存在，且不強制重跑，直接略過
    cross_review_file = vdir / "consultant_cross_reviews.json"
    if (not force_rerun) and cross_review_file.exists():
        cr = read_json_if_exists(cross_review_file)
        if cr:
            # 若已有舊版落盤（可能含不合 schema 的欄位），在 skip 時也做 deterministic normalize
            # 目的：避免「看起來沒跑 E2」其實是用到舊檔案，且不增加任何 LLM 呼叫。
            try:
                from scripts.consultants import normalize_consultant_cross_review

                reviewer_targets: dict[str, list[str]] = {
                    "A": ["B", "C"],
                    "B": ["A", "C"],
                    "C": ["A", "B"],
                }

                reviews = cr.get("reviews") if isinstance(cr, dict) else None
                if isinstance(reviews, dict):
                    changed = False
                    for reviewer, targets in reviewer_targets.items():
                        reviewer_key = f"reviewer_{reviewer}"
                        raw_review = reviews.get(reviewer_key)

                        if not isinstance(raw_review, dict):
                            reviews[reviewer_key] = {
                                "error": "legacy_cross_review_missing_or_invalid",
                                "reviewer": reviewer,
                                "reviewed_targets": targets,
                            }
                            changed = True
                            continue

                        if "error" in raw_review:
                            continue

                        # 舊格式常見：status=failed / task / reason / required_input_fields
                        if str(raw_review.get("status") or "").lower() == "failed":
                            reason = str(raw_review.get("reason") or "legacy_failed")[:200]
                            reviews[reviewer_key] = {
                                "error": f"legacy_cross_review_failed: {reason}",
                                "reviewer": reviewer,
                                "reviewed_targets": targets,
                            }
                            changed = True
                            continue

                        normalized = normalize_consultant_cross_review(raw_review, reviewer, targets)
                        if normalized != raw_review:
                            reviews[reviewer_key] = normalized
                            changed = True

                    # 更新 success/error count（讓 Step F 與 artifact 更一致）
                    success_count = sum(
                        1
                        for r in reviews.values()
                        if isinstance(r, dict) and "error" not in r
                    )
                    error_count = len(reviews) - success_count
                    cr["success_count"] = success_count
                    cr["error_count"] = error_count

                    if changed:
                        write_json(cross_review_file, cr)

                    # 即使 skip，也做一次 schema 驗證，避免靜默使用壞檔
                    validation_errors: list[str] = []
                    for reviewer_key, review in reviews.items():
                        if isinstance(review, dict) and "error" in review:
                            continue
                        try:
                            validate_consultant_cross_review(review, SCHEMAS_DIR)
                        except SchemaValidationError as ve:
                            validation_errors.append(f"{reviewer_key} schema 驗證失敗：{ve}")

                    if validation_errors:
                        st.warning(
                            "⚠️ E2 已有落盤，但內容仍有 schema 問題（建議開啟 Force re-run 重新產生）：\n"
                            + "\n".join(f"- {e}" for e in validation_errors)
                        )
            except Exception as e:
                logger.warning("Step E2 skip normalize 失敗", week_id=week_id, error=str(e)[:200])

            st.session_state["consultant_cross_reviews"] = cr
            write_pipeline_state(vdir, "E2(skip)", mode_label)
            render_sidebar_status_fn(week_id, vdir)
            logger.info("Step E2 略過（已有落盤）", week_id=week_id)
            return

    # 讀取 E1 consultant_notes
    cn = load_or_session("consultant_notes", vdir / "consultant_notes.json")
    if not cn:
        st.warning("⚠️ Step E2：找不到 E1 consultant_notes，跳過交叉審核。")
        logger.warning("Step E2 跳過：缺少 consultant_notes", week_id=week_id)
        write_pipeline_state(
            vdir,
            "E2(skip)",
            mode_label,
            details=["missing consultant_notes (Step E not completed or artifact missing)"]
        )
        render_sidebar_status_fn(week_id, vdir)
        return

    rs = load_or_session("report_summary", vdir / "report_summary.json")
    ri = load_or_session("report_insights", vdir / "report_insights.json")
    if not rs or not ri:
        st.warning("⚠️ Step E2：缺少 report_summary/report_insights，跳過交叉審核。")
        logger.warning("Step E2 跳過：缺少 report_summary 或 report_insights", week_id=week_id)
        write_pipeline_state(
            vdir,
            "E2(skip)",
            mode_label,
            details=["missing report_summary/report_insights (Step B/C not completed or artifact missing)"]
        )
        render_sidebar_status_fn(week_id, vdir)
        return

    with st.spinner(f"{mode_label}｜Step E2：三顧問交叉審核（共 3 次 API 呼叫）..."):
        try:
            cross_reviews = generate_consultant_cross_reviews(
                report_summary=rs,
                report_insights=ri,
                consultant_notes=cn,
                status_callback=status_callback,
                version_fp=vdir.name,
            )
        except Exception as e:
            # E2 整體失敗：記錄 error 但不阻擋 Step F
            err_msg = str(e)[:300]
            logger.warning("Step E2 整體失敗，降級略過", week_id=week_id, error=err_msg)
            st.warning(f"⚠️ E2 交叉審核整體失敗（降級，不影響 Step F）：{err_msg}")
            write_pipeline_state(vdir, "E2(error)", mode_label)
            render_sidebar_status_fn(week_id, vdir)
            return

        # Schema 驗證（逐筆，失敗只警告不阻擋）
        validation_errors: list[str] = []
        reviews = cross_reviews.get("reviews", {})
        for reviewer_key, review in reviews.items():
            if isinstance(review, dict) and "error" in review:
                validation_errors.append(f"{reviewer_key}: {review['error']}")
                continue
            try:
                validate_consultant_cross_review(review, SCHEMAS_DIR)
            except SchemaValidationError as ve:
                validation_errors.append(f"{reviewer_key} schema 驗證失敗：{ve}")
                logger.warning(
                    "E2 reviewer schema 驗證失敗",
                    reviewer=reviewer_key,
                    error=str(ve)[:200],
                )

        # 落盤（無論部分失敗，仍落盤）
        write_json(cross_review_file, cross_reviews)
        st.session_state["consultant_cross_reviews"] = cross_reviews

        # 顯示驗證結果
        success_count = cross_reviews.get("success_count", 0)
        error_count = cross_reviews.get("error_count", 0)

        if validation_errors:
            st.warning(
                f"⚠️ E2 部分審核有問題（{error_count} 失敗）：\n"
                + "\n".join(f"- {e}" for e in validation_errors)
            )
        else:
            st.success(f"✅ E2 交叉審核完成（{success_count}/3 成功）")

    write_pipeline_state(vdir, "E2", mode_label)
    logger.info("Step E2 (交叉審核) 完成", week_id=week_id, mode=mode_label,
                success_count=success_count, error_count=error_count)
    render_sidebar_status_fn(week_id, vdir)


def run_step_f_final(
    mode_label: str,
    week_id: str,
    vdir: Path,
    prev_ctx: dict,
    resolved_fp: str,
    current_fp: dict,
    force_rerun: bool,
    render_sidebar_status_fn,
) -> None:
    logger.info("Step F (final) 開始", week_id=week_id, mode=mode_label)
    sync_manual_inputs_to_inputs_json(vdir)

    if (
        (not force_rerun)
        and step_exists(vdir, "meeting.md")
        and step_exists(vdir, "workflow_state.json")
    ):
        ws = read_json_if_exists(vdir / "workflow_state.json")
        if ws:
            st.session_state["workflow_state"] = ws
            md = read_text_if_exists(vdir / "meeting.md")
            if md:
                st.session_state["meeting_md"] = md
            write_pipeline_state(vdir, "F(final)(skip)", mode_label)
            render_sidebar_status_fn(week_id, vdir)
            return

    with st.spinner(f"{mode_label}｜Step F：Moderator final -> meeting/workflow_state..."):
        rs = load_or_session("report_summary", vdir / "report_summary.json")
        ri = load_or_session("report_insights", vdir / "report_insights.json")
        cn = load_or_session("consultant_notes", vdir / "consultant_notes.json")
        if not rs or not ri or not cn:
            raise RuntimeError(
                "缺少 report_summary/report_insights/consultant_notes（Step B/C/E 未成功）"
            )

        # 嘗試讀取 E2 交叉審核產物（若有則傳給 Moderator；若無則正常執行）
        enable_cross_review = bool(st.session_state.get("enable_cross_review"))
        cross_reviews = (
            load_or_session("consultant_cross_reviews", vdir / "consultant_cross_reviews.json")
            if enable_cross_review
            else None
        )

        rs_ctx = rs_with_context(rs, current_fp, resolved_fp, prev_ctx)  # type: ignore[arg-type]
        ws = build_workflow_state(
            rs_ctx,
            ri,
            consultant_notes=cn,
            step="F",
            version_fp=vdir.name,
            cross_reviews=cross_reviews if isinstance(cross_reviews, dict) else None,
        )
        md = build_meeting_markdown(ws, rs_ctx, ri)
        write_artifacts(vdir, md, ws)

        st.session_state["workflow_state"] = ws
        st.session_state["meeting_md"] = md

    write_pipeline_state(vdir, "F(final)", mode_label)
    render_sidebar_status_fn(week_id, vdir)


# -------------------------
# Step G: 技能包管理員 (New Feature)
# -------------------------
def run_step_g(session_state: Dict[str, Any]) -> None:
    """
    執行 Step G：顯示技能包管理員與可視化結果
    """
    st.header("Step G: 技能包管理員 (Skill Manager)")

    # 從 session_state 讀取技能結果（Step C 寫入的位置）
    skills_context = session_state.get("skills_context", {})

    if not skills_context:
        st.info("ℹ️ 本次執行尚未包含技能分析結果 (可能是舊版報告或未開啟技能)。")
        return

    # 呼叫獨立 UI 模組渲染
    from ui.skill_manager import render_skill_manager

    render_skill_manager(skills_context)
