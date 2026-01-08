"""
檔案用途：Ivy House Meta 週報分析系統 - 入口頁面 (Landing Page)
職責：
  - 作為 Streamlit 多頁面應用程式 (Multipage App) 的首頁
  - 初始化系統主題與導航
  - 提供系統簡介與快速連結
"""

import streamlit as st
from pathlib import Path
from core.env_loader import load_environment_variables

# 載入環境變數 (優先讀取 ifp.env)
load_environment_variables()

# 設定頁面配置
st.set_page_config(
    page_title="首頁 | Ivy House Meta",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 載入主題與導航
from ui.theme import apply_ivy_house_theme
from ui.navigation import render_sidebar_navigation
from ui.layout import render_page_header

# 套用品牌主題
apply_ivy_house_theme()

# 渲染側邊欄導航
render_sidebar_navigation()

# ============================================================================
# 主要內容區域
# ============================================================================

render_page_header("Meta 週報分析系統", icon="🏠", subtitle="Ivy House 自動化廣告數據分析平台")

st.markdown("""
<div class="ivy-card" style="margin-bottom: 2rem;">
    <h3>👋 歡迎使用 Ivy House 智慧分析系統</h3>
    <p>本系統整合 Meta 廣告數據與官網銷售數據，透過 AI 顧問團隊提供深度洞察與行動建議。</p>
</div>
""", unsafe_allow_html=True)

# 功能卡片區
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div style="background-color: #fbf7ef; padding: 1.5rem; border-radius: 10px; border: 1px solid #e0e0e0; height: 100%;">
        <h4 style="color: #3f2f24; margin-bottom: 0.5rem;">📊 儀表板</h4>
        <p style="color: #666; font-size: 0.9rem; margin-bottom: 1rem;">查看系統概覽、執行統計與關鍵指標。</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("前往儀表板", use_container_width=True):
        st.switch_page("pages/01_dashboard.py")

with col2:
    st.markdown("""
    <div style="background-color: #fbf7ef; padding: 1.5rem; border-radius: 10px; border: 1px solid #e0e0e0; height: 100%;">
        <h4 style="color: #3f2f24; margin-bottom: 0.5rem;">📝 報告生成</h4>
        <p style="color: #666; font-size: 0.9rem; margin-bottom: 1rem;">上傳本週數據，執行一鍵分析流程 (Step A-F)。</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("前往報告生成", use_container_width=True):
        st.switch_page("pages/02_report_generation.py")

with col3:
    st.markdown("""
    <div style="background-color: #fbf7ef; padding: 1.5rem; border-radius: 10px; border: 1px solid #e0e0e0; height: 100%;">
        <h4 style="color: #3f2f24; margin-bottom: 0.5rem;">📂 歷史檢視</h4>
        <p style="color: #666; font-size: 0.9rem; margin-bottom: 1rem;">瀏覽過往週報、下載最終報告與會議草稿。</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("檢視歷史報告", use_container_width=True):
        st.switch_page("pages/03_history_viewer.py")

with col4:
    st.markdown("""
    <div style="background-color: #fbf7ef; padding: 1.5rem; border-radius: 10px; border: 1px solid #e0e0e0; height: 100%;">
        <h4 style="color: #3f2f24; margin-bottom: 0.5rem;">🤖 AI 助手</h4>
        <p style="color: #666; font-size: 0.9rem; margin-bottom: 1rem;">與 AI 顧問對話，深入探討數據問題與策略。</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("諮詢 AI 助手", use_container_width=True):
        st.switch_page("pages/04_ai_assistant.py")

st.divider()

# 系統資訊
c1, c2 = st.columns([2, 1])
with c1:
    st.markdown("### 🚀 系統功能與流程")
    st.markdown("""
    - **Step A**: 資料上傳與驗證 (Meta & Web CSV/Excel)
    - **Step B**: 數據整合與基礎 KPI 計算 (Deterministic)
    - **Step C**: AI 顧問洞察 (GPT-5, Gemini 3.0, Claude 4.5)
    - **Step D**: 會議草稿生成 (Moderator Draft)
    - **Step E**: 專家策略建議 (Consultants Final Review)
    - **Step F**: 最終會議報告定稿 (Final Meeting Minutes)
    """)

with c2:
    st.markdown("### 🔗 快速連結")
    st.markdown("- [📄 系統文件 (README)](file:///readme.md)")
    st.markdown("- [📋 開發紀錄 (CHANGELOG)](file:///CHANGELOG.md)")
    st.markdown("- [🐛 回報問題](https://github.com/foreverjojo/Ivyhousetw-META/issues)")

st.divider()
st.caption("© 2026 Ivy House Foodie Palace. All Rights Reserved.")
