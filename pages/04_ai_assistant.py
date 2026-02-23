"""
檔案用途：AI Assistant 頁面 - Crew Console 對話介面
職責：
  - 提供 AI 顧問即時對話介面
  - 支援角色切換（數據/視覺/策略顧問）
  - 整合 OpenRouter API 呼叫
  - 管理對話歷史
"""

import streamlit as st
from pathlib import Path

from datetime import datetime
from typing import List, Dict, Any, Optional
import os

# 設定頁面配置
st.set_page_config(
    page_title="AI 助手 | Ivy House Meta",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 載入環境變數
from core import load_environment_variables
load_environment_variables()

# 載入主題與導航
from ui.theme import apply_ivy_house_theme, Colors
from ui.navigation import render_sidebar_navigation
from ui.layout import render_page_header

# 套用品牌主題
apply_ivy_house_theme()

# 渲染側邊欄導航
render_sidebar_navigation()

# ============================================================================
# 配置
# ============================================================================

CONSULTANTS = {
    "data": {
        "name": "數據顧問 (GPT-5)",
        "icon": "📈",
        "model": "openai/gpt-5",
        "system_prompt": """你是 Ivy House 的數據分析顧問。
你的職責是分析 Meta 廣告數據，提供 KPI 洞察、ROAS 優化建議。
請用繁體中文回答，風格專業但友善。""",
    },
    "visual": {
        "name": "視覺顧問 (Gemini 3)",
        "icon": "🎨",
        "model": "google/gemini-3-pro",
        "system_prompt": """你是 Ivy House 的視覺設計顧問。
你的職責是分析廣告素材（圖片、影片），提供視覺優化建議。
請用繁體中文回答，注重美學與品牌一致性。""",
    },
    "strategy": {
        "name": "策略顧問 (Claude 4.5)",
        "icon": "🎯",
        "model": "anthropic/claude-4.5-opus",
        "system_prompt": """你是 Ivy House 的行銷策略顧問。
你的職責是提供市場洞察、受眾分析、文案建議。
請用繁體中文回答，風格有創意且具執行性。""",
    },
    "moderator": {
        "name": "主持人 (GPT-5)",
        "icon": "🎙️",
        "model": "openai/gpt-5",
        "system_prompt": """你是 Ivy House 週會的主持人。
你的職責是彙整各顧問的意見，產出週會摘要。
請用繁體中文回答，風格簡潔明瞭。""",
    },
}


# ============================================================================
# Session State 初始化
# ============================================================================

if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = []

if "selected_consultant" not in st.session_state:
    st.session_state["selected_consultant"] = "data"

if "chat_histories" not in st.session_state:
    st.session_state["chat_histories"] = {}


# ============================================================================
# 工具函式
# ============================================================================

def call_openrouter(messages: List[Dict], model: str) -> str:
    """呼叫 OpenRouter API"""
    from utils.openrouter_http import OpenRouterRetryConfig, OpenRouterTransientError, post_chat_completions_json

    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "⚠️ 錯誤：缺少 OPENROUTER_API_KEY 環境變數"

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000,
    }

    try:
        data = post_chat_completions_json(
            url=url,
            headers=headers,
            payload=payload,
            retry=OpenRouterRetryConfig(timeout_s=60.0, max_retries=1),
        )
        if not data.get("choices"):
            return "⚠️ API 回傳空結果（choices 為空）"
        return str(data["choices"][0]["message"].get("content") or "")
    except OpenRouterTransientError as e:
        return f"⚠️ OpenRouter 暫時性錯誤，請稍後再試：{str(e)[:200]}"
    except Exception as e:
        msg = str(e)
        if len(msg) > 300:
            msg = msg[:300] + "..."
        return f"⚠️ 請求失敗：{msg}"


def save_chat_history(name: str):
    """儲存對話歷史"""
    st.session_state["chat_histories"][name] = {
        "messages": st.session_state["chat_messages"].copy(),
        "consultant": st.session_state["selected_consultant"],
        "timestamp": datetime.now().isoformat(),
    }


def load_chat_history(name: str):
    """載入對話歷史"""
    if name in st.session_state["chat_histories"]:
        history = st.session_state["chat_histories"][name]
        st.session_state["chat_messages"] = history["messages"]
        st.session_state["selected_consultant"] = history["consultant"]


def clear_chat():
    """清除對話"""
    st.session_state["chat_messages"] = []


# ============================================================================
# 主要內容區域
# ============================================================================

render_page_header("AI 助手", icon="🤖", subtitle="顧問諮詢台 - 與 AI 顧問即時對話")

# ============================================================================
# 側邊欄設定
# ============================================================================

with st.sidebar:
    st.divider()
    st.markdown("### 🎭 角色選擇")

    consultant_options = list(CONSULTANTS.keys())
    consultant_labels = [f"{CONSULTANTS[k]['icon']} {CONSULTANTS[k]['name']}" for k in consultant_options]

    selected_idx = st.radio(
        "選擇顧問",
        range(len(consultant_options)),
        format_func=lambda i: consultant_labels[i],
        key="consultant_radio",
        index=consultant_options.index(st.session_state["selected_consultant"])
    )
    st.session_state["selected_consultant"] = consultant_options[selected_idx]

    st.divider()
    st.markdown("### 💬 對話管理")

    # 對話歷史列表
    if st.session_state["chat_histories"]:
        st.markdown("**歷史對話：**")
        for name in st.session_state["chat_histories"]:
            if st.button(f"💬 {name}", key=f"load_{name}"):
                load_chat_history(name)
                st.rerun()

    # 新對話按鈕
    if st.button("➕ 新對話", key="new_chat"):
        # 儲存當前對話（如果有內容）
        if st.session_state["chat_messages"]:
            save_name = f"對話 {datetime.now().strftime('%H:%M')}"
            save_chat_history(save_name)
        clear_chat()
        st.rerun()

    st.divider()
    st.markdown("### ⚙️ 設定")

    # 技能啟用
    st.checkbox("📊 資料分析", value=True, key="skill_data")
    st.checkbox("🖼️ 圖片分析", value=True, key="skill_image")
    st.checkbox("🎬 影片分析", value=False, key="skill_video")

# ============================================================================
# 對話區域
# ============================================================================

current_consultant = CONSULTANTS[st.session_state["selected_consultant"]]

# 顯示當前顧問
st.markdown(f"**當前顧問：** {current_consultant['icon']} {current_consultant['name']}")

# 對話訊息容器
chat_container = st.container()

with chat_container:
    # 顯示歷史訊息
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"], avatar=msg.get("avatar")):
            st.markdown(msg["content"])

# 輸入區域
user_input = st.chat_input("輸入訊息...")

if user_input:
    # 添加使用者訊息
    st.session_state["chat_messages"].append({
        "role": "user",
        "content": user_input,
        "avatar": "👤"
    })

    # 顯示使用者訊息
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    # 準備 API 呼叫
    api_messages = [
        {"role": "system", "content": current_consultant["system_prompt"]}
    ]

    # 添加歷史訊息（最多保留 10 輪）
    for msg in st.session_state["chat_messages"][-20:]:
        api_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # 呼叫 API
    with st.spinner("思考中..."):
        response = call_openrouter(api_messages, current_consultant["model"])

    # 添加助手回覆
    st.session_state["chat_messages"].append({
        "role": "assistant",
        "content": response,
        "avatar": current_consultant["icon"]
    })

    # 顯示助手回覆
    with st.chat_message("assistant", avatar=current_consultant["icon"]):
        st.markdown(response)

    # 重新渲染
    st.rerun()

# ============================================================================
# 快速操作
# ============================================================================

st.divider()
st.markdown("### 💡 快速提問")

quick_prompts = [
    "分析本週 ROAS 表現",
    "給我素材優化建議",
    "本週應該調整什麼策略？",
    "彙整週會重點",
]

cols = st.columns(len(quick_prompts))
for i, prompt in enumerate(quick_prompts):
    with cols[i]:
        if st.button(prompt, key=f"quick_{i}", use_container_width=True):
            # 模擬使用者輸入
            st.session_state["chat_messages"].append({
                "role": "user",
                "content": prompt,
                "avatar": "👤"
            })
            st.rerun()

# ============================================================================
# 底部資訊
# ============================================================================

st.divider()
st.caption("📍 Ivy House Meta 週報分析系統 | 艾薇手工坊 | 由 OpenRouter 提供技術支援")
