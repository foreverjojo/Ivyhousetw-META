"""
檔案用途：Ivy House 品牌主題設定
職責：
  - 定義艾薇手工坊品牌色系（從官網提取的真實色號）
  - 提供 Streamlit 樣式配置
  - 統一全應用程式的視覺風格

品牌色系：
  - 主色 (Cocoa Brown): #3f2f24 - 職人穩重感
  - 強調色 (Gold/Sand): #cea87a - 烘焙金黃質感
  - 背景色 (Warm Cream): #fbf7ef - 極簡溫暖
  - 輔助色 (Deep Gray): #585858 - 次要文字
"""

import streamlit as st

# ============================================================================
# 品牌色系 - 從 www.ivyhousetw.com 提取
# ============================================================================

# 主色系
COCOA_BROWN = "#3f2f24"      # 深可可棕 - 主要文字、導航列、邊框
GOLD_SAND = "#cea87a"        # 金沙色 - 按鈕、圖標、高亮
WARM_CREAM = "#fbf7ef"       # 溫暖米黃 - 全站背景
DEEP_GRAY = "#585858"        # 深灰 - 次要文字

# 輔助色系
WHITE = "#ffffff"            # 純白 - 卡片背景
LIGHT_CREAM = "#faf8f3"      # 淺米黃 - 卡片 hover
SUCCESS_GREEN = "#28a745"    # 成功綠
WARNING_ORANGE = "#fd7e14"   # 警告橘
ERROR_RED = "#dc3545"        # 錯誤紅

# ============================================================================
# Streamlit 主題配置 CSS
# ============================================================================

IVY_HOUSE_CSS = f"""
<style>
    /* 主背景色 */
    .stApp {{
        background-color: {WARM_CREAM};
    }}

    /* 隱藏 Streamlit 預設導航 (上方) */
    [data-testid="stSidebarNav"] {{
        display: none !important;
    }}

    /* 側邊欄背景 */
    [data-testid="stSidebar"] {{
        background-color: {COCOA_BROWN};
    }}

    /* 側邊欄文字顏色 (強制轉為淺色) */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] label {{
        color: {WARM_CREAM} !important;
    }}

    /* Page Link 樣式 */
    a[data-testid="stPageLink-NavLink"] {{
        background-color: transparent;
    }}

    a[data-testid="stPageLink-NavLink"]:hover {{
        background-color: rgba(255, 255, 255, 0.1);
    }}

    a[data-testid="stPageLink-NavLink"] p {{
        font-size: 1.1rem;
        font-weight: 500;
    }}

    /* 標題樣式 (主內容區) */
    .main h1, .main h2, .main h3 {{
        color: {COCOA_BROWN} !important;
    }}

    /* 主要按鈕 */
    .stButton > button {{
        background-color: {GOLD_SAND};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }}

    .stButton > button:hover {{
        background-color: {COCOA_BROWN};
        color: {WARM_CREAM};
    }}

    /* 次要按鈕（外框式） */
    .stButton > button[kind="secondary"] {{
        background-color: transparent;
        color: {COCOA_BROWN};
        border: 2px solid {COCOA_BROWN};
    }}

    /* Metric 卡片 */
    [data-testid="stMetricValue"] {{
        color: {COCOA_BROWN};
    }}

    /* 成功/警告/錯誤訊息 */
    .stSuccess {{
        background-color: #d4edda;
        border-left: 4px solid {SUCCESS_GREEN};
    }}

    .stWarning {{
        background-color: #fff3cd;
        border-left: 4px solid {WARNING_ORANGE};
    }}

    .stError {{
        background-color: #f8d7da;
        border-left: 4px solid {ERROR_RED};
    }}

    /* 檔案上傳器 */
    [data-testid="stFileUploader"] {{
        border: 2px dashed {COCOA_BROWN};
        border-radius: 8px;
        padding: 1rem;
    }}

    /* Expander 標題 */
    .streamlit-expanderHeader {{
        color: {COCOA_BROWN};
        font-weight: 600;
    }}

    /* Chat 訊息樣式 */
    [data-testid="stChatMessage"][data-testid*="user"] {{
        background-color: {COCOA_BROWN};
        color: white;
    }}

    [data-testid="stChatMessage"][data-testid*="assistant"] {{
        background-color: white;
        color: {COCOA_BROWN};
    }}

    /* 修正側邊欄輸入元件的文字顏色 (避免被全域覆蓋) */
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] select,
    [data-testid="stSidebar"] textarea {{
        color: {COCOA_BROWN} !important;
        background-color: {WARM_CREAM} !important;
    }}

    /* Radio Button 選項文字在選中時的顏色 */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {{
        color: {WARM_CREAM} !important;
    }}
</style>
"""


def apply_ivy_house_theme():
    """
    套用艾薇手工坊品牌主題到 Streamlit 應用程式

    使用方式：
        from ui.theme import apply_ivy_house_theme
        apply_ivy_house_theme()
    """
    st.markdown(IVY_HOUSE_CSS, unsafe_allow_html=True)


def get_page_config(page_title: str = "Ivy House Meta 週報"):
    """
    取得標準化的頁面配置

    參數:
        page_title: 頁面標題

    回傳:
        dict: st.set_page_config 的參數
    """
    return {
        "page_title": page_title,
        "page_icon": "🏠",
        "layout": "wide",
        "initial_sidebar_state": "expanded",
    }


# ============================================================================
# 品牌色快捷存取
# ============================================================================

class Colors:
    """品牌色系快捷存取類別"""
    primary = COCOA_BROWN
    accent = GOLD_SAND
    background = WARM_CREAM
    text = COCOA_BROWN
    text_secondary = DEEP_GRAY
    card = WHITE
    success = SUCCESS_GREEN
    warning = WARNING_ORANGE
    error = ERROR_RED
