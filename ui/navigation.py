"""
檔案用途：Streamlit 多頁面導航元件
職責：
  - 提供統一的側邊欄導航
  - 顯示應用程式版本資訊
  - 提供頁面快速連結
"""

import streamlit as st
from pathlib import Path

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
        
        from core.config import AVAILABLE_MODELS, MODEL_INSIGHTS, MODEL_CONSULTANT_A, MODEL_CONSULTANT_B, MODEL_CONSULTANT_C, MODEL_MODERATOR
        import os
        
        def model_selector(label, key, default_id):
            options = list(AVAILABLE_MODELS.keys()) + ["自定義..."]
            current_id = st.session_state.get(f"model_id_{key}", default_id)
            display_name = next((k for k, v in AVAILABLE_MODELS.items() if v == current_id), "自定義...")
            idx = options.index(display_name) if display_name in options else len(options)-1
            selected_label = st.selectbox(label, options, index=idx, key=f"sel_{key}")
            
            if selected_label == "自定義...":
                final_id = st.text_input(f"輸入 {label} ID", value=current_id if display_name == "自定義..." else "", key=f"custom_{key}", placeholder="openai/gpt-5")
            else:
                final_id = AVAILABLE_MODELS[selected_label]
            
            st.session_state[f"model_id_{key}"] = final_id
            return final_id

        insights_model = model_selector("C. 洞察分析 (Insights)", "insights", MODEL_INSIGHTS)
        consultant_a = model_selector("E. 成效顧問 (A)", "consultant_a", MODEL_CONSULTANT_A)
        consultant_b = model_selector("E. 視覺顧問 (B)", "consultant_b", MODEL_CONSULTANT_B)
        consultant_c = model_selector("E. 策略顧問 (C)", "consultant_c", MODEL_CONSULTANT_C)
        moderator = model_selector("D/F. 會議主持 (Moderator)", "moderator", MODEL_MODERATOR)

        os.environ["MODEL_INSIGHTS"] = insights_model
        os.environ["MODEL_CONSULTANT_A"] = consultant_a
        os.environ["MODEL_CONSULTANT_B"] = consultant_b
        os.environ["MODEL_CONSULTANT_C"] = consultant_c
        os.environ["MODEL_MODERATOR"] = moderator

        return {
            "detail_level": detail_level,
            "schema_validate": schema_validate,
            "version_mode": version_mode,
            "force_rerun": version_mode == "force_rerun",
            "auto_new_version": version_mode == "auto_new_version",
            "models": {
                "insights": insights_model,
                "consultant_a": consultant_a,
                "consultant_b": consultant_b,
                "consultant_c": consultant_c,
                "moderator": moderator
            }
        }
