"""
檔案用途：Streamlit 共用佈局元件
職責：
  - 提供統一的頁面標題樣式
  - 提供卡片式佈局元件
  - 提供指標列顯示元件
  - 提供載入狀態元件
"""

import streamlit as st
from typing import List, Dict, Any, Optional
from ui.theme import Colors


def render_page_header(title: str, icon: str = "📊", subtitle: str = None):
    """
    渲染統一的頁面標題

    參數:
        title: 頁面標題
        icon: 標題圖示（emoji）
        subtitle: 副標題（可選）
    """
    st.markdown(f"# {icon} {title}")
    if subtitle:
        st.markdown(f"*{subtitle}*")
    st.divider()


def render_metric_row(metrics: List[Dict[str, Any]]):
    """
    渲染指標列（使用 st.metric）

    參數:
        metrics: 指標列表，每個元素為 dict:
            - label: 指標名稱
            - value: 指標值
            - delta: 變化值（可選）
            - icon: 圖示（可選）

    範例:
        render_metric_row([
            {"label": "總週報", "value": 12, "icon": "📈"},
            {"label": "待處理", "value": 2, "icon": "⏱️"},
            {"label": "已完成", "value": 10, "icon": "✅"},
        ])
    """
    cols = st.columns(len(metrics))

    for i, metric in enumerate(metrics):
        with cols[i]:
            icon = metric.get("icon", "")
            label = f"{icon} {metric['label']}" if icon else metric['label']
            delta = metric.get("delta")

            st.metric(
                label=label,
                value=metric['value'],
                delta=delta
            )


def render_card(title: str, content: str = None, icon: str = None):
    """
    渲染卡片式區塊

    參數:
        title: 卡片標題
        content: 卡片內容（Markdown 格式）
        icon: 標題圖示
    """
    header = f"{icon} {title}" if icon else title

    with st.container():
        st.markdown(f"### {header}")
        if content:
            st.markdown(content)


def render_action_buttons(buttons: List[Dict[str, Any]]) -> Optional[str]:
    """
    渲染快速操作按鈕列

    參數:
        buttons: 按鈕列表，每個元素為 dict:
            - label: 按鈕文字
            - key: 按鈕 key（唯一識別）
            - icon: 圖示（可選）
            - type: "primary" 或 "secondary"

    回傳:
        被點擊的按鈕 key，若無點擊則回傳 None
    """
    cols = st.columns(len(buttons))
    clicked = None

    for i, btn in enumerate(buttons):
        with cols[i]:
            icon = btn.get("icon", "")
            label = f"{icon} {btn['label']}" if icon else btn['label']
            btn_type = btn.get("type", "primary")

            if st.button(label, key=btn['key'], type=btn_type):
                clicked = btn['key']

    return clicked


def render_loading_state(message: str = "載入中..."):
    """
    渲染載入狀態

    參數:
        message: 載入訊息
    """
    with st.spinner(message):
        return st.empty()


def render_status_badge(status: str) -> str:
    """
    取得狀態標籤的 HTML

    參數:
        status: 狀態字串（"completed", "pending", "error"）

    回傳:
        HTML 格式的狀態標籤
    """
    badges = {
        "completed": f'<span style="background-color: {Colors.success}; color: white; padding: 2px 8px; border-radius: 4px;">✅ 完成</span>',
        "pending": f'<span style="background-color: {Colors.warning}; color: white; padding: 2px 8px; border-radius: 4px;">⏱️ 進行中</span>',
        "error": f'<span style="background-color: {Colors.error}; color: white; padding: 2px 8px; border-radius: 4px;">❌ 錯誤</span>',
    }
    return badges.get(status, status)


def render_recent_runs(runs: List[Dict[str, Any]]):
    """
    渲染最近執行列表

    參數:
        runs: 執行記錄列表，每個元素為 dict:
            - week_id: 週 ID
            - fingerprint: fingerprint
            - status: 狀態
            - timestamp: 時間戳記
    """
    st.markdown("### 📋 最近執行")

    if not runs:
        st.info("尚無執行記錄")
        return

    for run in runs[:5]:  # 最多顯示 5 筆
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{run['week_id']}** | `{run['fingerprint'][:12]}...`")
                st.caption(run['timestamp'])
            with col2:
                status = run.get('status', 'pending')
                if status == 'completed':
                    st.success("✅ 完成")
                else:
                    st.warning("⏱️ 進行中")
            st.divider()
