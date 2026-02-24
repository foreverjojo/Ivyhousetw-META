"""AI Assistant 頁面（已停用）

此功能已整合至「歷史檢視」頁面內的「AI 助手」分頁。
本頁保留以避免舊書籤/連結導致迷路。
"""

import streamlit as st

from core import load_environment_variables
from ui.layout import render_page_header
from ui.navigation import render_sidebar_navigation
from ui.theme import apply_ivy_house_theme

st.set_page_config(
    page_title="AI 助手 | Ivy House Meta",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_environment_variables()

apply_ivy_house_theme()
render_sidebar_navigation()

render_page_header("AI 助手", icon="🤖", subtitle="已整合至『歷史檢視』頁面")
st.info("AI 助手已整合至『歷史檢視』頁面內，請到該頁的『AI 助手』分頁使用。")
st.page_link("pages/03_history_viewer.py", label="前往 歷史檢視", icon="📂")
st.stop()
