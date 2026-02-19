"""
檔案用途：Dashboard 頁面 - 系統首頁與快速操作入口
職責：
  - 顯示專案概覽與關鍵指標
  - 提供快速操作按鈕
  - 顯示最近執行記錄
"""

import streamlit as st
from pathlib import Path
import json
from datetime import datetime

# 設定頁面配置
st.set_page_config(
    page_title="儀表板 | Ivy House Meta",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 載入主題與導航
from ui.theme import apply_ivy_house_theme
from ui.navigation import render_sidebar_navigation
from ui.layout import render_page_header, render_metric_row, render_action_buttons, render_recent_runs

# 套用品牌主題
apply_ivy_house_theme()

# 渲染側邊欄導航
render_sidebar_navigation()

# ============================================================================
# 主要內容區域
# ============================================================================

render_page_header("儀表板", icon="📊", subtitle="歡迎回來！以下是系統概覽")

# 載入歷史資料以計算統計
HISTORY_ROOT = Path(__file__).parent.parent / "history"


def get_run_stats():
    """取得執行統計資料"""
    total = 0
    completed = 0
    pending = 0
    recent_runs = []

    if HISTORY_ROOT.exists():
        for week_dir in HISTORY_ROOT.iterdir():
            if week_dir.is_dir() and week_dir.name.startswith("20"):
                # 正確的路徑結構：history/<week_id>/meta/versions/fp-...
                versions_dir = week_dir / "meta" / "versions"
                if not versions_dir.exists():
                    continue

                for version_dir in versions_dir.iterdir():
                    if version_dir.is_dir() and version_dir.name.startswith("fp-"):
                        total += 1

                        # 檢查是否完成（有 meeting.md 或 meeting_final.md）
                        meeting_file = version_dir / "meeting.md"
                        meeting_final = version_dir / "meeting_final.md"

                        if meeting_final.exists() or meeting_file.exists():
                            completed += 1
                            status = "completed"
                        else:
                            pending += 1
                            status = "pending"

                        # 取得時間戳記
                        try:
                            state_file = version_dir / "workflow_state.json"
                            if state_file.exists():
                                state = json.loads(state_file.read_text(encoding="utf-8"))
                                timestamp = state.get("updated_at", "N/A")
                            else:
                                timestamp = datetime.fromtimestamp(version_dir.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                        except Exception:
                            timestamp = "N/A"

                        recent_runs.append({
                            "week_id": week_dir.name,
                            "fingerprint": version_dir.name,
                            "status": status,
                            "timestamp": timestamp
                        })

    # 依時間排序（最新在前）
    recent_runs.sort(key=lambda x: x["timestamp"], reverse=True)

    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "recent_runs": recent_runs[:5]
    }


# 取得統計資料
stats = get_run_stats()

# 指標卡片
render_metric_row([
    {"label": "總週報", "value": stats["total"], "icon": "📈"},
    {"label": "待處理", "value": stats["pending"], "icon": "⏱️"},
    {"label": "已完成", "value": stats["completed"], "icon": "✅"},
])

st.divider()

# 快速操作按鈕
st.markdown("### ⚡ 快速操作")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("➕ 新建週報", key="new_report", use_container_width=True):
        st.switch_page("pages/02_report_generation.py")

with col2:
    if st.button("📂 查看歷史", key="view_history", use_container_width=True):
        st.switch_page("pages/03_history_viewer.py")

with col3:
    if st.button("🤖 開啟 AI 助手", key="open_ai", use_container_width=True):
        st.switch_page("pages/04_ai_assistant.py")

st.divider()

# 最近執行記錄
render_recent_runs(stats["recent_runs"])

# 底部資訊
st.divider()
st.caption("📍 Ivy House Meta 週報分析系統 | 艾薇手工坊")
