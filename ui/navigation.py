"""
檔案用途：Streamlit 多頁面導航元件
職責：
  - 提供統一的側邊欄導航
  - 顯示應用程式版本資訊
  - 提供頁面快速連結
"""

from pathlib import Path

import streamlit as st

# 讀取版本號
VERSION_FILE = Path(__file__).parent.parent / "VERSION"
try:
    VERSION = VERSION_FILE.read_text().strip()
except Exception:
    VERSION = "0.3.0"


def render_sidebar_navigation():
    """
    渲染側邊欄導航選單

    此函式應在每個頁面的開頭呼叫，以確保導航一致性
    """
    with st.sidebar:
        # 品牌標題
        st.markdown("## 🏠 艾薇手工坊")
        st.markdown("**Meta 週報分析系統**")
        st.caption(f"版本: {VERSION}")

        st.divider()

        # 導航連結
        st.markdown("### 📍 導航")

        # 使用 page_link 確保正確的頁面跳轉
        st.page_link("app.py", label="🏠 首頁", icon="🏠")
        st.page_link("pages/01_dashboard.py", label="儀表板", icon="📊")
        st.page_link("pages/02_report_generation.py", label="報告生成", icon="📝")
        st.page_link("pages/03_history_viewer.py", label="歷史檢視", icon="📂")
        st.page_link("pages/04_ai_assistant.py", label="AI 助手", icon="🤖")


def render_sidebar_status(status_dict: dict = None):
    """
    渲染側邊欄狀態資訊

    參數:
        status_dict: 狀態字典，例如 {"Step B": True, "Step C": False}
    """
    if status_dict is None:
        return

    with st.sidebar:
        st.divider()
        st.markdown("### 📋 狀態")

        for step_name, is_complete in status_dict.items():
            icon = "✅" if is_complete else "❌"
            st.markdown(f"{icon} {step_name}")


def render_sidebar_settings():
    """
    渲染側邊欄設定選項

    回傳:
        dict: 包含所有設定值的字典
    """
    with st.sidebar:
        st.divider()
        st.markdown("### ⚙️ 設定")

        detail_level = st.radio(
            "詳細程度",
            options=["default", "adset+ads"],
            index=1,
            help="選擇報告詳細程度"
        )

        schema_validate = st.checkbox(
            "Schema 驗證",
            value=True,
            help="是否驗證上傳檔案的 Schema"
        )

        version_mode = st.radio(
            "版本模式",
            options=["auto_new_version", "force_rerun"],
            format_func=lambda x: "自動新版本" if x == "auto_new_version" else "強制重跑",
            help="版本管理模式"
        )

        st.divider()
        st.markdown("### 🤖 AI 模型配置")

        from core.model_settings import (
            AVAILABLE_MODELS,
            get_model,
            normalize_model_id,
            set_model,
        )

        def model_selector(label, key, role):
            options = list(AVAILABLE_MODELS.keys()) + ["自定義..."]
            current_id = st.session_state.get(f"model_id_{key}") or get_model(role)
            current_id = normalize_model_id(current_id)

            if current_id != st.session_state.get(f"model_id_{key}"):
                st.session_state[f"model_id_{key}"] = current_id

            display_name = next((k for k, v in AVAILABLE_MODELS.items() if v == current_id), "自定義...")
            idx = options.index(display_name) if display_name in options else len(options)-1
            selected_label = st.selectbox(label, options, index=idx, key=f"sel_{key}")

            if selected_label == "自定義...":
                final_id = st.text_input(f"輸入 {label} ID", value=current_id if display_name == "自定義..." else "", key=f"custom_{key}", placeholder="openai/gpt-5")
            else:
                final_id = AVAILABLE_MODELS[selected_label]

            final_id = normalize_model_id(final_id)
            st.session_state[f"model_id_{key}"] = final_id
            return final_id

        insights_model = set_model(
            "insights",
            model_selector("C. 洞察分析 (Insights)", "insights", "insights"),
        )
        consultant_a = set_model(
            "consultant_a",
            model_selector("E. 成效顧問 (A)", "consultant_a", "consultant_a"),
        )
        consultant_b = set_model(
            "consultant_b",
            model_selector("E. 視覺顧問 (B)", "consultant_b", "consultant_b"),
        )
        consultant_c = set_model(
            "consultant_c",
            model_selector("E. 策略顧問 (C)", "consultant_c", "consultant_c"),
        )
        moderator = set_model(
            "moderator",
            model_selector("D/F. 會議主持 (Moderator)", "moderator", "moderator"),
        )

        st.divider()
        st.markdown("### 🔍 E2 交叉審核設定")

        enable_cross_review = st.checkbox(
            "啟用 E2 交叉審核",
            value=False,
            key="enable_cross_review",
            help=(
                "E2 交叉審核：A/B/C 三位顧問各自審核另外兩位的分析結論。\n"
                "⚠️ 將增加 3 次 LLM 呼叫，延遲約增加 30-90 秒。預設關閉。"
            ),
        )
        if enable_cross_review:
            st.caption("✅ E2 交叉審核已啟用（每次執行增加 3 次 API 呼叫）")
        else:
            st.caption("💡 E2 交叉審核關閉（Step F 直接使用 E1 結論）")

        return {
            "detail_level": detail_level,
            "schema_validate": schema_validate,
            "version_mode": version_mode,
            "force_rerun": version_mode == "force_rerun",
            "auto_new_version": version_mode == "auto_new_version",
            "enable_cross_review": enable_cross_review,
            "models": {
                "insights": insights_model,
                "consultant_a": consultant_a,
                "consultant_b": consultant_b,
                "consultant_c": consultant_c,
                "moderator": moderator
            }
        }
