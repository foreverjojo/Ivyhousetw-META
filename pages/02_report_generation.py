"""
檔案用途：Report Generation 頁面 - 週報生成功能
職責：
  - 提供 CSV/Excel 檔案上傳介面
  - 執行 B→C→D (快篩) 或 B→C→E→F (最終) 流程
  - 顯示執行狀態與結果

注意：此頁面重新包裝 app.py 的核心功能，保持向後相容
"""

import streamlit as st
from pathlib import Path
from typing import List, Optional
import pandas as pd

# 設定頁面配置（必須在最前面）
st.set_page_config(
    page_title="報告生成 | Ivy House Meta",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 載入環境變數
from core import load_environment_variables
load_environment_variables()

# 載入主題與導航
from ui.theme import apply_ivy_house_theme
from ui.navigation import render_sidebar_navigation, render_sidebar_settings
from ui.layout import render_page_header

# 套用品牌主題
apply_ivy_house_theme()

# 渲染側邊欄導航
render_sidebar_navigation()

# 側邊欄設定
settings = render_sidebar_settings()
detail_level = settings["detail_level"]
force_rerun = settings["force_rerun"]
auto_new_version = settings["auto_new_version"]

# 匯入核心模組
from core import (
    HISTORY_ROOT,
    restore_from_version_dir,
)
from utils import (
    read_csv,
    compute_inputs_fingerprint,
    fp_short as utils_fp_short,
    now_iso,
    read_json_if_exists,
)
from ui.components import preview_df, artifacts_panel
from ui.steps import (
    run_step_b,
    run_step_c,
    run_step_d_draft,
    run_step_e,
    run_step_f_final,
    run_step_g,
)
from core.logging import get_logger

logger = get_logger(__name__)

# ============================================================================
# 包裝函式（與 app.py 相同的邏輯）
# ============================================================================

def fp_short(d: dict) -> str:
    """產生短版 fingerprint"""
    return utils_fp_short(d)


# ============================================================================
# 主要內容區域
# ============================================================================

render_page_header("週報生成", icon="📝", subtitle="上傳檔案並執行分析流程")

# 側邊欄狀態顯示 (移除)
# status_container = st.sidebar.container()


def render_status(week_id: Optional[str], vdir: Optional[Path]) -> None:
    """渲染狀態（主畫面水平佈局）"""
    # 使用全域 placeholder
    if "main_status_placeholder" not in globals():
        return

    with main_status_placeholder.container():
        # 清空舊內容是自動的，因為我們是在同一個 placeholder container 內寫入？
        # 不，with placeholder.container() 是 append。
        # 正解：placeholder.write(...) 或 placeholder.markdown(...) 會替換。
        # 但我們要複雜佈局。
        # Hack: 每次呼叫前，Streamlit 的 execution flow 是線性的。
        # 但若是 callback，則會即時寫入。
        
        # 為了確保「替換」，我們應該在外部定義 placeholder，然後這裡用:
        # with main_status_placeholder.container(): ...
        # 但 Streamlit 的 placeholder.container() 行為是：
        # "Inserts a container into your app. If used as a context manager, anything written inside the block will be appended to the container."
        # 如果要替換內容，必須用 placeholder.empty() 先清空？不，container 不能被 empty()。
        
        # 修正策略：render_status 透過 st.empty() 每次重新輸出。
        pass

    # 實作：
    # 我們假設全域有一個 main_status_placeholder = st.empty()
    if week_id is None and vdir is None:
        main_status_placeholder.empty()
        return

    with main_status_placeholder.container():
        st.markdown("---")
        st.subheader(f"📋 流程狀態 (Week: {week_id or '?'})")
        # st.caption(f"Dir: {vdir}")
        
        if not vdir:
            st.info("尚未建立版本目錄")
            return

        def ok(name: str) -> bool:
            return (vdir / name).exists()

        cols = st.columns(5)
        steps = [
            ("B", "report_summary.json", "數據整合"),
            ("C", "report_insights.json", "AI 洞察"),
            ("D", "meeting_draft.md", "草稿"),
            ("E", "consultant_notes.json", "三顧問"),
            ("F", "meeting.md", "最終會議"),
        ]
        
        for i, (step_char, filename, label) in enumerate(steps):
            is_ok = ok(filename)
            with cols[i]:
                st.metric(
                    label=f"{step_char}. {label}", 
                    value="✅ 完成" if is_ok else "⋯", 
                    delta="OK" if is_ok else None,
                    delta_color="normal"
                )


# Session 鎖定
if "locked_week_id" not in st.session_state:
    st.session_state["locked_week_id"] = None
if "locked_fp" not in st.session_state:
    st.session_state["locked_fp"] = None
if "locked_vdir" not in st.session_state:
    st.session_state["locked_vdir"] = None


def reset_session_lock() -> None:
    """重置 Session 鎖定"""
    for k in [
        "locked_week_id", "locked_fp", "locked_vdir",
        "report_summary", "report_insights", "consultant_notes",
        "workflow_state", "meeting_md", "workflow_state_draft",
        "meeting_md_draft", "manual_inputs",
    ]:
        st.session_state.pop(k, None)


# Reset 按鈕
with st.sidebar:
    st.divider()
    if st.button("🔄 重置工作階段", key="btn_reset_report"):
        reset_session_lock()
        st.rerun()

# ============================================================================
# Step A｜上傳檔案
# ============================================================================

# Platform Selector
st.markdown("### 1. 選擇資料來源")
col_platform, _ = st.columns([2, 2])
with col_platform:
    platform_map = {
        "Meta (Facebook/Instagram)": "Meta",
        "Shopee (蝦皮)": "Shopee",
        "Momo (Momo Ads)": "Momo"
    }
    selected_platform_label = st.radio(
        "選擇平台",
        options=list(platform_map.keys()),
        index=0,
        key="platform_selector",
        horizontal=True,
        label_visibility="collapsed"
    )
    platform = platform_map[selected_platform_label]

# File Variables
meta_adset_file = None
meta_ads_file = None
web_excel_file = None
shopee_file = None
momo_file = None

can_run = False
missing = []

with st.expander("▼ Step A｜上傳檔案 + 預覽", expanded=True):
    if platform == "Meta":
        c1, c2, c3 = st.columns(3)
        with c1:
            meta_adset_file = st.file_uploader("Meta 廣告組合 CSV", type=["csv"], key="uploader_meta_adset")
        with c2:
            meta_ads_file = st.file_uploader("Meta 廣告 CSV", type=["csv"], key="uploader_meta_ads")
        with c3:
            web_excel_file = st.file_uploader("官網 Excel", type=["xlsx", "xls"], key="uploader_web_excel")

        if meta_adset_file is None: missing.append("Meta Adset CSV")
        if meta_ads_file is None: missing.append("Meta Ads CSV")
        if web_excel_file is None: missing.append("官網 Excel")

        if not missing:
            try:
                adset_df = read_csv(meta_adset_file)
                ads_df = read_csv(meta_ads_file)
                xls = pd.ExcelFile(web_excel_file)
                web_df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
                st.success("✅ Meta 檔案讀取成功")
                t1, t2, t3 = st.tabs(["Meta Adset", "Meta Ads", "官網 Excel"])
                with t1: preview_df(adset_df, "Meta Adset")
                with t2: preview_df(ads_df, "Meta Ads")
                with t3: preview_df(web_df, "官網資料")
                can_run = True
            except Exception as e:
                st.error(f"讀取失敗：{e}")

    elif platform == "Shopee":
        shopee_file = st.file_uploader("蝦皮廣告成效報表 (CSV)", type=["csv"], key="uploader_shopee")
        if shopee_file is None:
            missing.append("蝦皮廣告成效報表")
        else:
            can_run = True
            st.success("✅ 蝦皮檔案已上傳")
            
    elif platform == "Momo":
        momo_file = st.file_uploader("MOMO 廣告素材報表 (XLSX)", type=["xlsx"], key="uploader_momo")
        if momo_file is None:
            missing.append("MOMO 廣告素材報表")
        else:
            can_run = True
            st.success("✅ MOMO 檔案已上傳")

    if missing:
        can_run = False
        st.warning("請先上傳缺少的檔案：" + "、".join(missing))

# ============================================================================
# Step A+｜媒體素材上傳 (Optional)
# ============================================================================
with st.expander("▼ Step A+｜媒體素材上傳 (Optional)", expanded=False):
    uploaded_media = st.file_uploader(
        "上傳圖片/影片 (支援 jpg, png, mp4)",
        type=["jpg", "png", "mp4", "jpeg"],
        accept_multiple_files=True,
        key="uploader_media"
    )
    if uploaded_media:
        media_root = Path("uploaded_media")
        media_root.mkdir(exist_ok=True)
        saved_count = 0
        for f in uploaded_media:
             # simple save
             (media_root / f.name).write_bytes(f.getvalue())
             saved_count += 1
        st.success(f"已儲存 {saved_count} 個檔案至 uploaded_media/")

# ============================================================================
# Manual Inputs
# ============================================================================

with st.expander("▼ Manual Inputs（人工快照）", expanded=False):
    default_manual = st.session_state.get("manual_inputs") or {}
    col1, col2, col3 = st.columns(3)

    with col1:
        buying_type_options = ["", "AUCTION", "RESERVATION", "MIXED", "UNKNOWN"]
        default_buying_type = (
            st.session_state.get("mi_buying_type")
            or default_manual.get("buying_type")
            or ""
        )
        if default_buying_type not in buying_type_options:
            default_buying_type = ""
        
        buying_type = st.selectbox(
            "購買類型",
            options=buying_type_options,
            index=buying_type_options.index(default_buying_type),
            key="mi_buying_type"
        )
    with col2:
        optimization_goal_options = [
            "", 
            "OFFSITE_CONVERSIONS (網站轉換)", 
            "LANDING_PAGE_VIEWS (到達頁面瀏覽)", 
            "LINK_CLICKS (連結點擊)", 
            "IMPRESSIONS (曝光)", 
            "REACH (觸及)", 
            "THRUPLAY (影片完整觀看)", 
            "VALUE (價值)", 
            "APP_INSTALLS (應用程式安裝)", 
            "LEAD_GENERATION (名單型)", 
            "VISIT_INSTAGRAM_PROFILE (IG 個人檔案瀏覽)"
        ]
        default_optimization_goal = (
            st.session_state.get("mi_optimization_goal")
            or default_manual.get("optimization_goal")
            or ""
        )
        if default_optimization_goal not in optimization_goal_options:
            default_optimization_goal = ""
            
        optimization_goal = st.selectbox(
            "優化目標",
            options=optimization_goal_options,
            index=optimization_goal_options.index(default_optimization_goal),
            key="mi_optimization_goal"
        )
    with col3:
        billing_event_options = [
            "", 
            "IMPRESSIONS (曝光)", 
            "LINK_CLICKS (連結點擊)", 
            "THRUPLAY (影片完整觀看)", 
            "APP_INSTALLS (安裝)"
        ]
        default_billing_event = (
            st.session_state.get("mi_billing_event")
            or default_manual.get("billing_event")
            or ""
        )
        if default_billing_event not in billing_event_options:
            default_billing_event = ""
            
        billing_event = st.selectbox(
            "計費事件",
            options=billing_event_options,
            index=billing_event_options.index(default_billing_event),
            key="mi_billing_event"
        )

    weekly_changes = st.text_area("本週重大調整", height=100, key="mi_weekly_changes")
    st.caption(
        "提醒：若本週 `website_purchase_value_twd=0`（站內回傳異常），投放決策請以 Meta 平台口徑 `platform_purchase_value_twd` / `roas_platform` 為主；官網 `revenue_twd` 用於整體營收對帳。"
    )
    note_for_consultants = st.text_area("給顧問的備註", height=100, key="mi_note_for_consultants")

    st.session_state["manual_inputs"] = {
        "schema_version": "manual_inputs.v1",
        "updated_at": now_iso(),
        "buying_type": buying_type,
        "optimization_goal": optimization_goal,
        "billing_event": billing_event,
        "weekly_changes": weekly_changes,
        "note_for_consultants": note_for_consultants,
    }

# ============================================================================
# Fingerprint 預覽
# ============================================================================

current_fp: Optional[dict] = None
fp_code: Optional[str] = None

if can_run:
    if platform == "Meta":
        current_fp = compute_inputs_fingerprint(meta_adset_file, meta_ads_file, web_excel_file, detail_level)
    else:
        # Simple fingerprint for other platforms
        import hashlib
        content = b""
        if shopee_file: content += shopee_file.getvalue()
        if momo_file: content += momo_file.getvalue()
        fp_hash = hashlib.md5(content).hexdigest()[:8]
        current_fp = {"platform": platform, "hash": fp_hash}
    
    fp_code = fp_short(current_fp)

with st.expander("▼ Fingerprint（版本碼）", expanded=False):
    if current_fp:
        st.json(current_fp)
        st.caption(f"fp short: {fp_code}")
    else:
        st.info("請先完成 Step A 上傳")

# 初始側邊欄狀態 (移除，移到後面)
# locked_week = st.session_state.get("locked_week_id")
# locked_vdir = st.session_state.get("locked_vdir")
# render_status(locked_week, Path(locked_vdir) if locked_vdir else None)

# ============================================================================
# 一鍵流程按鈕
# ============================================================================

st.divider()
st.markdown("### ⚡ 一鍵流程")

col1, col2 = st.columns(2)
with col1:
    btn_quick = st.button(
        "⚡ 一鍵快篩（B→C→D draft）",
        type="secondary",
        disabled=not can_run,
        use_container_width=True
    )
with col2:
    btn_final = st.button(
        "🚀 一鍵最終（B→C→E→F final）",
        type="primary",
        disabled=not can_run,
        use_container_width=True
    )

# 定義主畫面的狀態顯示區域 (Placeholder)
main_status_placeholder = st.empty()

# 頁面載入時，若有鎖定狀態，立即顯示
locked_week = st.session_state.get("locked_week_id")
locked_vdir = st.session_state.get("locked_vdir")
if locked_week or locked_vdir:
    render_status(locked_week, Path(locked_vdir) if locked_vdir else None)

# 導入模型配置
import os
from core.config import (
    MODEL_INSIGHTS,
    MODEL_CONSULTANT_A, MODEL_CONSULTANT_B, MODEL_CONSULTANT_C,
    MODEL_MODERATOR
)

def get_active_model(env_var: str, default: str) -> str:
    """取得當前生效的模型 ID"""
    return os.getenv(env_var) or default

if btn_quick:
    mode = "oneclick_quick_BCD"
    try:
        # 使用 st.status 取代 spinner 以顯示詳細進度
        with st.status("🚀 啟動一鍵快篩流程...", expanded=True) as status:
            
            # Step B
            status.write("執行 Step B: 數據計算與指標聚合...")
            week_id, resolved_fp, vdir, prev_ctx = run_step_b(
                mode, can_run, current_fp, fp_code, 
                meta_adset_file=meta_adset_file, 
                meta_ads_file=meta_ads_file, 
                web_excel_file=web_excel_file,
                shopee_file=shopee_file,
                momo_file=momo_file,
                platform=platform,
                force_rerun=force_rerun, 
                auto_new_version=auto_new_version, 
                render_sidebar_status_fn=render_status
            )
            restore_from_version_dir(vdir)
            status.update(label="✅ Step B 完成，進入 AI 分析...", state="running")

            # Step C
            model_c_name = get_active_model("MODEL_INSIGHTS", MODEL_INSIGHTS)
            status.write(f"執行 Step C: LLM 洞察生成 (使用模型: **{model_c_name}**)...")
            run_step_c(mode, week_id, vdir, prev_ctx, resolved_fp, current_fp, force_rerun, render_status)
            restore_from_version_dir(vdir)
            
            # Step D
            model_d_name = get_active_model("MODEL_MODERATOR", MODEL_MODERATOR)
            status.write(f"執行 Step D: 草擬會議記錄 (使用模型: **{model_d_name}**)...")
            run_step_d_draft(mode, week_id, vdir, prev_ctx, resolved_fp, current_fp, force_rerun, render_status)
            restore_from_version_dir(vdir)

            status.update(label="✅ 一鍵快篩完成！", state="complete", expanded=False)

        st.success("✅ 一鍵快篩完成（B→C→D draft）")
        artifacts_panel(vdir)
    except Exception as e:
        st.error(f"一鍵快篩中斷：{e}")

if btn_final:
    mode = "oneclick_final_BCEF"
    try:
        with st.status("🚀 啟動一鍵最終流程...", expanded=True) as status:
            
            # Step B
            status.write("執行 Step B: 數據計算與指標聚合...")
            week_id, resolved_fp, vdir, prev_ctx = run_step_b(
                mode, can_run, current_fp, fp_code, 
                meta_adset_file=meta_adset_file, 
                meta_ads_file=meta_ads_file, 
                web_excel_file=web_excel_file,
                shopee_file=shopee_file,
                momo_file=momo_file,
                platform=platform,
                force_rerun=force_rerun, 
                auto_new_version=auto_new_version, 
                render_sidebar_status_fn=render_status
            )
            restore_from_version_dir(vdir)
            status.update(label="✅ Step B 完成，進入 AI 分析...", state="running")

            # 建立即時預覽區塊
            with st.expander("📖 即時分析預覽", expanded=True):
                step_c_display = st.container()
                st.divider()
                step_e_display = st.container()

            # Step C
            model_c_name = get_active_model("MODEL_INSIGHTS", MODEL_INSIGHTS)
            status.write(f"執行 Step C: LLM 洞察生成 (使用模型: **{model_c_name}**)...")
            run_step_c(mode, week_id, vdir, prev_ctx, resolved_fp, current_fp, force_rerun, render_status, realtime_container=step_c_display)
            restore_from_version_dir(vdir)

            # Step E
            model_ea = get_active_model("MODEL_CONSULTANT_A", MODEL_CONSULTANT_A)
            model_eb = get_active_model("MODEL_CONSULTANT_B", MODEL_CONSULTANT_B)
            model_ec = get_active_model("MODEL_CONSULTANT_C", MODEL_CONSULTANT_C)
            status.write(f"執行 Step E: 三顧問諮詢...")
            status.caption(f"- 顧問 A (成效): **{model_ea}**\n- 顧問 B (圖文): **{model_eb}**\n- 顧問 C (策略): **{model_ec}**")
            
            def consultant_callback(name, model):
                role_map = {"A": "成效顧問 A", "B": "視覺顧問 B", "C": "策略顧問 C"}
                icon_map = {"A": "📊", "B": "🎨", "C": "🧠"}
                role = role_map.get(name, f"顧問 {name}")
                icon = icon_map.get(name, "🤖")
                status.write(f"{icon} {role} 正在思考... (Model: **{model}**)")
            
            run_step_e(mode, week_id, vdir, prev_ctx, resolved_fp, current_fp, force_rerun, render_status, status_callback=consultant_callback, realtime_container=step_e_display)
            restore_from_version_dir(vdir)

            # Step F
            model_f_name = get_active_model("MODEL_MODERATOR", MODEL_MODERATOR)
            status.write(f"執行 Step F: 最終會議總結 (使用模型: **{model_f_name}**)...")
            run_step_f_final(mode, week_id, vdir, prev_ctx, resolved_fp, current_fp, force_rerun, render_status)
            restore_from_version_dir(vdir)


            status.update(label="✅ 一鍵最終完成！", state="complete", expanded=False)

        st.success("✅ 一鍵最終完成（B→C→E→F final）")
        artifacts_panel(vdir)
        
        # Step G: 技能包管理員 (New Feature) - 在 status 外部渲染
        run_step_g(st.session_state)
    except Exception as e:
        st.error(f"一鍵最終中斷：{e}")

# ============================================================================
# 底部資訊
# ============================================================================

st.divider()
st.caption("📍 Ivy House Meta 週報分析系統 | 艾薇手工坊")
