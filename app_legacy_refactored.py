"""
檔案用途：Ivy House Meta 週報分析系統 - 主程式
職責：
  - 提供 Streamlit Web UI
  - 處理 CSV 上傳與 Schema 驗證
  - 呼叫 scripts/ 下的 KPI 計算、LLM 分析、顧問模組
  - 管理 history/ 資料夾的版本與產出

注意：此檔案已經過模組化重構，使用 utils/, core/, ui/ 模組
"""

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

# 載入環境變數
from core import load_environment_variables

load_environment_variables()

# 從新模組 import
from core import (
    HISTORY_ROOT,
    SCHEMAS_DIR,
    TAIPEI_TZ,
    SchemaValidationError,
    write_pipeline_state,
    restore_from_version_dir,
)

# Import validate_report_summary separately to create wrapper
from core.validation import validate_report_summary as _validate_report_summary_raw
from core.session import (
    init_session_state,
    reset_session_lock,
    load_or_session,
    sync_manual_inputs_to_inputs_json,
)
from utils import (
    read_json_if_exists,
    write_json,
    read_text_if_exists,
    write_text,
    read_csv,
    sha256_str,
    compute_inputs_fingerprint,
    fingerprint_key_for_version,
    fp_short as utils_fp_short,
    normalize_week_id,
    parse_week_id,
    now_iso,
    week_meta_dir as utils_week_meta_dir,
    versions_root as utils_versions_root,
    version_dir as utils_version_dir,
    read_latest_ptr as utils_read_latest_ptr,
    write_latest_ptr as utils_write_latest_ptr,
    write_week_info as utils_write_week_info,
    ensure_week_meta_dirs as utils_ensure_week_meta_dirs,
    staging_version_dir,
    WEEK_RE,
)

# 從 utils 導入需要 history_root 的函式，稍後建立包裝
from utils.week_utils import get_prev_week_id as _get_prev_week_id_raw
from utils.week_utils import list_week_ids_on_disk as _list_week_ids_on_disk_raw
from ui.components import preview_df, artifacts_panel
from ui.steps import (
    run_step_b,
    run_step_c,
    run_step_d_draft,
    run_step_e,
    run_step_e2,
    run_step_f_final,
)

# Scripts imports
from scripts.kpi_calc import build_report_summary
from scripts.llm_insights import generate_report_insights
from scripts.consultants import run_three_consultants
from scripts.moderator import build_workflow_state, build_meeting_markdown, write_artifacts
from scripts.media_uploader import upload_media_assets

# Logging (新增)
from core.logging import get_logger

logger = get_logger(__name__)

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="Ivy House - Meta Weekly MVP", layout="wide")
st.title("Ivy House｜Meta 週會 MVP（Week 主鍵 + FP 版本 + Auto Prev Week）")
st.caption(
    "快篩：B→C→D（draft）｜最終：B→C→E→F（final）。"
    "主鍵=week_id；版本=fp；"
    "Force=覆蓋本次 fp（不覆蓋別的 fp）；"
    "Auto new version=只有 mismatch 才新版本。"
)

#  ===以上函式已模組化至 utils/, core/, ui/===


# =========================
# App 層級的包裝函式（自動傳入 HISTORY_ROOT）
# =========================
def list_week_ids_on_disk() -> List[str]:
    """包裝函式：自動傳入 HISTORY_ROOT"""
    return _list_week_ids_on_disk_raw(HISTORY_ROOT)


def get_prev_week_id(current_week_id: str) -> Optional[str]:
    """包裝函式：自動傳入 HISTORY_ROOT"""
    return _get_prev_week_id_raw(current_week_id, HISTORY_ROOT)


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


# =========================
# 指紋碼計算（App 專用的包裝函式）
# =========================
def compute_file_fp(uploaded_file) -> dict:
    """計算上傳檔案的指紋（包含檔名）"""
    b = uploaded_file.getvalue()
    from utils.hash_utils import sha256_bytes

    return {"name": getattr(uploaded_file, "name", ""), "size": len(b), "sha256": sha256_bytes(b)}


def fp_short(current_fp: dict) -> str:
    """取得指紋碼的短版本（用於顯示）"""
    import json

    dumped = json.dumps(fingerprint_key_for_version(current_fp), ensure_ascii=False, sort_keys=True)
    return sha256_str(dumped)[:8]


# =========================
# pipeline_state + 側邊欄狀態
# =========================
# 以上函式已模組化至 core/pipeline_state.py 和 utils/path_utils.py


# =========================
# Sidebar (互斥模式：用 radio，避免死鎖)
# =========================
st.sidebar.header("設定（MVP）")
detail_level = st.sidebar.selectbox(
    "Detail Level", ["default", "adset+ads"], index=1, key="detail_level"
)
validate_schema = st.sidebar.checkbox(
    "Step B 後 Schema Validate（強制）",
    value=True,
    key="validate_schema",
    help="用 schemas/report_summary.v1.json 強制驗證 Step B 產物，避免口徑漂移。",
)


def safe_stamp() -> str:
    """filesystem-safe stamp for staging folders."""
    if TAIPEI_TZ:
        return datetime.now(TAIPEI_TZ).strftime("%Y%m%d_%H%M%S")
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def staging_version_dir(fp_code: str) -> Path:
    """A staging vdir to record early Step-B errors before week_id/vdir is resolved."""
    return HISTORY_ROOT / "_staging" / safe_stamp() / "meta" / "versions" / f"fp-{fp_code}"


def _cleanup_staging_on_success(stage_vdir: Path) -> None:
    """Delete only the single staging run folder (<stamp>) after Step B succeeds.

    Expected structure:
      history/_staging/<stamp>/meta/versions/fp-xxxxxxxx  <-- stage_vdir
    We delete:
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


st.sidebar.divider()
st.sidebar.caption("版本模式（互斥）")

mode_choice = st.sidebar.radio(
    "Version Mode",
    options=[
        "Auto new version（mismatch 才新版本）",
        "Force re-run（覆蓋重跑，不新建版本）",
    ],
    index=0,
    key="version_mode_choice",
)
force_rerun = mode_choice.startswith("Force")
auto_new_version = mode_choice.startswith("Auto")

st.sidebar.divider()
status_ph = st.sidebar.empty()


def render_sidebar_status(week_id: Optional[str], vdir: Optional[Path]) -> None:
    with status_ph.container():
        st.subheader("流程狀態（逐步更新）")
        st.write("week_id:", week_id or "（未鎖定）")
        st.write("version_dir:", str(vdir) if vdir else "（未鎖定）")

        if not vdir:
            return

        def ok(name: str) -> bool:
            try:
                return (vdir / name).exists()
            except Exception:
                return False

        st.write(("✅ " if ok("report_summary.json") else "❌ ") + "B report_summary.json")
        st.write(("✅ " if ok("report_insights.json") else "❌ ") + "C report_insights.json")
        st.write(("✅ " if ok("meeting_draft.md") else "❌ ") + "D meeting_draft.md")
        st.write(
            ("✅ " if ok("workflow_state_draft.json") else "❌ ") + "D workflow_state_draft.json"
        )
        st.write(("✅ " if ok("consultant_notes.json") else "❌ ") + "E consultant_notes.json")
        st.write(("✅ " if ok("meeting.md") else "❌ ") + "F meeting.md")
        st.write(("✅ " if ok("workflow_state.json") else "❌ ") + "F workflow_state.json")

        ps = read_json_if_exists(vdir / "pipeline_state.json")
        if ps:
            st.caption(
                f"last_completed_step: {ps.get('last_completed_step')}｜mode: {ps.get('last_mode')}"
            )


# =========================
# Session 鎖定
# =========================
if "locked_week_id" not in st.session_state:
    st.session_state["locked_week_id"] = None
if "locked_fp" not in st.session_state:
    st.session_state["locked_fp"] = None
if "locked_vdir" not in st.session_state:
    st.session_state["locked_vdir"] = None


def reset_session_lock() -> None:
    for k in [
        "locked_week_id",
        "locked_fp",
        "locked_vdir",
        "report_summary",
        "report_insights",
        "consultant_notes",
        "workflow_state",
        "meeting_md",
        "workflow_state_draft",
        "meeting_md_draft",
        "manual_inputs",
    ]:
        st.session_state.pop(k, None)


if st.sidebar.button("Reset（清除 session lock，不刪 history）", key="btn_reset"):
    reset_session_lock()
    st.rerun()


# =========================
# Step A｜上傳與預覽
# =========================
st.divider()
with st.expander("Step A｜上傳檔案 + 預覽（必做）", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        meta_adset_file = st.file_uploader(
            "Meta Adset CSV（廣告組合層）", type=["csv"], key="uploader_meta_adset"
        )
    with c2:
        meta_ads_file = st.file_uploader(
            "Meta Ads CSV（廣告層）", type=["csv"], key="uploader_meta_ads"
        )
    with c3:
        web_excel_file = st.file_uploader(
            "官網 Excel（BVshop/後台匯出）", type=["xlsx", "xls"], key="uploader_web_excel"
        )

    can_run = True
    missing: List[str] = []
    if meta_adset_file is None:
        missing.append("Meta Adset CSV")
    if meta_ads_file is None:
        missing.append("Meta Ads CSV")
    if web_excel_file is None:
        missing.append("官網 Excel")

    if missing:
        can_run = False
        st.warning("請先上傳缺少的檔案：" + "、".join(missing))
    else:
        # --- Step A+ 素材上傳 (Optional) ---
        st.divider()
        st.subheader("Step A+｜媒體素材上傳 (Optional)")
        media_files = st.file_uploader(
            "上傳圖片或影片素材（將自動存入 attached_assets/）",
            type=["jpg", "jpeg", "png", "gif", "webp", "mp4", "mov", "avi"],
            accept_multiple_files=True,
            key="uploader_media_assets",
        )
        if media_files:
            from core.config import MEDIA_ASSETS_DIR
            import re as _re

            MEDIA_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
            saved_count = 0
            for mf in media_files:
                # 檔名正規化：移除路徑分隔符與危險字元
                safe_name = _re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", mf.name)
                safe_name = safe_name.strip(". ")  # 避免以點或空白開頭/結尾
                if not safe_name:
                    safe_name = "unnamed_asset"
                target_path = MEDIA_ASSETS_DIR / safe_name
                if not target_path.exists():
                    with open(target_path, "wb") as f:
                        f.write(mf.getbuffer())
                    saved_count += 1
            if saved_count > 0:
                st.toast(f"✅ 已存入 {saved_count} 個新素材至 {MEDIA_ASSETS_DIR.name}")
        # ---------------------------------

        try:
            adset_df = read_csv(meta_adset_file)
            ads_df = read_csv(meta_ads_file)
        except Exception as e:
            can_run = False
            st.error(f"讀取 Meta CSV 失敗：{e}")

        if can_run:
            try:
                xls = pd.ExcelFile(web_excel_file)
                sheet = xls.sheet_names[0]
                web_df = pd.read_excel(xls, sheet_name=sheet)
            except Exception as e:
                can_run = False
                st.error(f"讀取官網 Excel 失敗：{e}")

        if can_run:
            st.success("✅ 檔案讀取成功（可進入一鍵流程）")
            t1, t2, t3 = st.tabs(["Meta Adset 預覽", "Meta Ads 預覽", "官網 Excel 預覽"])
            with t1:
                preview_df(adset_df, "Meta Adset（廣告組合層）")
            with t2:
                preview_df(ads_df, "Meta Ads（廣告層）")
            with t3:
                preview_df(web_df, "官網資料（第一個工作表）")


# =========================
# Manual inputs（每週人工快照）
# =========================
with st.expander("Inputs 快照（每週人工填一次｜補 Meta 匯出缺欄位）", expanded=False):
    default_manual = st.session_state.get("manual_inputs") or {}
    colm1, colm2, colm3 = st.columns(3)
    with colm1:
        buying_type = st.selectbox(
            "Buying type",
            options=["", "AUCTION", "RESERVATION", "MIXED", "UNKNOWN"],
            index=(
                ["", "AUCTION", "RESERVATION", "MIXED", "UNKNOWN"].index(
                    default_manual.get("buying_type", "")
                )
                if default_manual.get("buying_type", "")
                in ["", "AUCTION", "RESERVATION", "MIXED", "UNKNOWN"]
                else 0
            ),
            key="mi_buying_type",
        )
    with colm2:
        optimization_goal = st.text_input(
            "Optimization goal",
            value=str(default_manual.get("optimization_goal", "")),
            key="mi_optimization_goal",
        )
    with colm3:
        billing_event = st.text_input(
            "Billing event",
            value=str(default_manual.get("billing_event", "")),
            key="mi_billing_event",
        )

    weekly_changes = st.text_area(
        "本週重大調整",
        value=str(default_manual.get("weekly_changes", "")),
        height=110,
        key="mi_weekly_changes",
    )
    note_for_consultants = st.text_area(
        "給顧問/主持人的備註",
        value=str(default_manual.get("note_for_consultants", "")),
        height=110,
        key="mi_note_for_consultants",
    )

    st.session_state["manual_inputs"] = {
        "schema_version": "manual_inputs.v1",
        "updated_at": now_iso(),
        "buying_type": buying_type,
        "optimization_goal": optimization_goal,
        "billing_event": billing_event,
        "weekly_changes": weekly_changes,
        "note_for_consultants": note_for_consultants,
    }
    st.caption("會寫入 inputs.json，並在 meeting.md 的「策略快照」固定輸出。")


# =========================
# 指紋碼預覽
# =========================
current_fp: Optional[dict] = None
fp_code: Optional[str] = None
if can_run:
    current_fp = compute_inputs_fingerprint(
        meta_adset_file, meta_ads_file, web_excel_file, detail_level
    )
    fp_code = fp_short(current_fp)

with st.expander("防呆｜Fingerprint（deterministic version code）", expanded=False):
    if current_fp:
        st.json(current_fp)
        st.caption(f"fp short (deterministic): {fp_code}")
    else:
        st.info("請先完成 Step A 上傳後才會產生 fingerprint。")


# =========================
# 步驟處理器已移至 ui/steps.py
# =========================


# =========================
# 舊版遷移（非破壞性）
# =========================
from utils.legacy_migration import render_legacy_migration_ui

render_legacy_migration_ui(
    st,
    week_meta_dir,
    version_dir,
    read_latest_ptr,
    write_latest_ptr,
    write_week_info,
    ensure_week_meta_dirs,
    fp_short,
)


# 初始側邊欄狀態（已鎖定或未鎖定）
locked_week = st.session_state.get("locked_week_id")
locked_vdir = st.session_state.get("locked_vdir")
render_sidebar_status(locked_week, Path(locked_vdir) if locked_vdir else None)


# =========================
# 一鍵按鈕
# =========================
st.divider()
st.subheader("一鍵流程（兩顆按鈕）")

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    btn_quick = st.button("⚡ 一鍵快篩（B→C→D draft）", type="secondary", disabled=not can_run)
with col2:
    btn_final = st.button("🚀 一鍵最終（B→C→E→F final）", type="primary", disabled=not can_run)
with col3:
    st.write("prev_week 只靠 week_id 排序（YYYY-Www），不使用 date_range 推導。")

if btn_quick:
    mode = "oneclick_quick_BCD"
    try:
        week_id, resolved_fp, vdir, prev_ctx = run_step_b(
            mode,
            can_run,
            current_fp,
            fp_code,
            meta_adset_file,
            meta_ads_file,
            web_excel_file,
            force_rerun,
            auto_new_version,
            render_sidebar_status,
        )
        restore_from_version_dir(vdir)

        run_step_c(
            mode,
            week_id,
            vdir,
            prev_ctx,
            resolved_fp,
            current_fp,
            force_rerun,
            render_sidebar_status,
        )
        restore_from_version_dir(vdir)

        run_step_d_draft(
            mode,
            week_id,
            vdir,
            prev_ctx,
            resolved_fp,
            current_fp,
            force_rerun,
            render_sidebar_status,
        )
        restore_from_version_dir(vdir)

        st.success("✅ 一鍵快篩完成（B→C→D draft）")
        artifacts_panel(vdir)
    except Exception as e:
        st.error(f"一鍵快篩中斷：{e}")
        st.stop()

if btn_final:
    mode = "oneclick_final_BCEF"
    try:
        week_id, resolved_fp, vdir, prev_ctx = run_step_b(
            mode,
            can_run,
            current_fp,
            fp_code,
            meta_adset_file,
            meta_ads_file,
            web_excel_file,
            force_rerun,
            auto_new_version,
            render_sidebar_status,
        )
        restore_from_version_dir(vdir)

        run_step_c(
            mode,
            week_id,
            vdir,
            prev_ctx,
            resolved_fp,
            current_fp,
            force_rerun,
            render_sidebar_status,
        )
        restore_from_version_dir(vdir)

        run_step_e(
            mode,
            week_id,
            vdir,
            prev_ctx,
            resolved_fp,
            current_fp,
            force_rerun,
            render_sidebar_status,
        )
        restore_from_version_dir(vdir)

        # Step E2（可選）：三顧問交叉審核
        # 一律呼叫，讓 pipeline_state 可追溯；是否啟用由 ui.steps.run_step_e2 內部判斷。
        run_step_e2(
            mode,
            week_id,
            vdir,
            render_sidebar_status,
            status_callback=None,
            force_rerun=force_rerun,
        )
        restore_from_version_dir(vdir)

        run_step_f_final(
            mode,
            week_id,
            vdir,
            prev_ctx,
            resolved_fp,
            current_fp,
            force_rerun,
            render_sidebar_status,
        )
        restore_from_version_dir(vdir)

        st.success("✅ 一鍵最終完成（B→C→E→F final）")
        artifacts_panel(vdir)
    except Exception as e:
        st.error(f"一鍵最終中斷：{e}")
        st.stop()


# =========================
# 快速檢視
# =========================
st.divider()
st.subheader("快速檢視（當前 session）")

if st.session_state.get("locked_week_id") and st.session_state.get("locked_vdir"):
    st.write("🔒 Locked week:", st.session_state["locked_week_id"])
    st.write("🔒 Locked version dir:", st.session_state["locked_vdir"])

    prev = get_prev_week_id(st.session_state["locked_week_id"])
    st.caption(f"Auto prev_week_id: {prev or '（找不到）'}")

colv1, colv2 = st.columns(2)
with colv1:
    st.markdown("### Draft（快篩）")
    if "meeting_md_draft" in st.session_state:
        st.text_area("meeting_draft.md（預覽）", st.session_state["meeting_md_draft"], height=220)
    if "workflow_state_draft" in st.session_state:
        st.json(st.session_state["workflow_state_draft"])

with colv2:
    st.markdown("### Final（最終）")
    if "meeting_md" in st.session_state:
        st.text_area("meeting.md（預覽）", st.session_state["meeting_md"], height=220)
    if "workflow_state" in st.session_state:
        st.json(st.session_state["workflow_state"])

# =========================
# Step G｜雲端同步 (Phase 2.3)
# =========================
st.divider()
with st.expander("Step G｜雲端同步 (Google Drive)", expanded=True):
    st.write("將 attached_assets/ 內的圖片與影片素材同步至 Google Drive。")

    if st.session_state.get("locked_vdir"):
        c_sync1, c_sync2 = st.columns([1, 2])
        with c_sync1:
            btn_sync = st.button("☁️ 上傳素材至雲端", type="secondary", key="btn_cloud_sync")

        if btn_sync:
            with st.spinner("🚀 正在同步至雲端..."):
                try:
                    # 1. 執行掃描與上傳
                    from scripts.media_uploader import upload_media_assets

                    sync_results = upload_media_assets(dry_run=False)

                    st.success("✅ 雲端同步完成！")
                    st.json(sync_results)
                except Exception as e:
                    st.error(f"雲端同步失敗：{e}")
    else:
        st.info("請先執行 Step B 產生版本後，才能同步雲端。")

st.info(
    "行為規則：\n"
    "1) 主鍵=week_id（YYYY-Www，W 自動補零）。\n"
    "2) 版本=fp-xxxxxxxx（只由檔案 sha/size + detail_level 決定）。\n"
    "3) Force re-run：永遠覆蓋『本次 fp』對應資料夾（若不存在就建立），不覆蓋其他 fp。\n"
    "4) Auto new version：只有 mismatch（latest.fp != 本次 fp）才新建版本。\n"
    "5) prev_week：只靠 week_id 排序找上一週，完全不靠 date_range 字串。\n"
    "6) latest.json 存相對路徑 rel_path=versions/fp-xxxx，避免搬環境不穩。\n"
    "7) 時間欄位固定用台北時間（Asia/Taipei）。"
)
