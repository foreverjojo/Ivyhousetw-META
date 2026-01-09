"""
檔案用途：Ivy House Meta 週報分析系統 - 技能包管理員 UI 元件
職責：
  - 顯示已執行技能清單與狀態 (Metric Tree / Creative Fatigue / Budget Rules)
  - 視覺化呈現：漏斗圖 (Plotly)、Top/Worst 廣告表格
  - 與 ui/steps.py 解耦，專責渲染 Step G 大表板
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from typing import Dict, Any, List

# 工具函式匯入
from utils import read_json_if_exists

# 品牌色系 Theme Colors
COLOR_BROWN = "#3f2f24"
COLOR_GOLD = "#cea87a"
COLOR_CREAM = "#fbf7ef"
COLOR_RED_ALERT = "#e74c3c"
COLOR_GREEN_OK = "#27ae60"

def render_skill_manager(skills_context: Dict[str, Any]) -> None:
    """
    渲染技能包管理員主畫面
    input: skills_context (來自 report_summary['_context']['skills'])
    """
    st.markdown("### 🛠️ 技能包管理員 (Skill Manager)")

    # 1. 技能執行狀態摘要
    _render_status_summary(skills_context)

    # 2. Top 1: Metric Tree 漏斗圖
    if "metric_tree_diagnostic" in skills_context:
        with st.expander("Top 1: 全漏斗指標樹診斷 (Metric Tree Diagnostic)", expanded=True):
            _render_metric_tree_viz(skills_context["metric_tree_diagnostic"])

    # 3. Top 2: Creative Fatigue
    if "creative_fatigue" in skills_context:
        with st.expander("Top 2: 素材疲乏偵測 (Creative Fatigue)", expanded=True):
            _render_creative_fatigue_viz(skills_context["creative_fatigue"])

    # 4. Top 3: Budget Rules
    if "budget_rules" in skills_context:
        with st.expander("Top 3: 預算配置規則 (Budget Rules)", expanded=False):
            _render_budget_rules_viz(skills_context["budget_rules"])


def _render_status_summary(skills: Dict[str, Any]) -> None:
    """顯示技能執行狀態表格"""
    status_data = []

    # 定義技能清單
    skill_defs = [
        ("metric_tree_diagnostic", "Top 1: 指標樹"),
        ("creative_fatigue", "Top 2: 素材疲乏"),
        ("budget_rules", "Top 3: 預算規則"),
    ]

    for key, label in skill_defs:
        data = skills.get(key, {})
        triggered = data.get("triggered", False)
        warn_cnt = len(data.get("warnings", []))
        rec_cnt = len(data.get("recommendations", []))

        status_icon = "🟢" if not triggered else "🔴"
        if warn_cnt > 0:
            status_icon = "⚠️"

        status_data.append({
            "技能名稱": label,
            "狀態": "已觸發" if triggered else "正常",
            "警告數": warn_cnt,
            "建議數": rec_cnt,
            "燈號": status_icon
        })

    df = pd.DataFrame(status_data)
    st.dataframe(
        df,
        column_config={
            "燈號": st.column_config.TextColumn("狀態燈號", width="small"),
            "警告數": st.column_config.NumberColumn("⚠️ 警告", format="%d"),
            "建議數": st.column_config.NumberColumn("💡 建議", format="%d"),
        },
        hide_index=True,
        use_container_width=True
    )


def _render_metric_tree_viz(data: Dict[str, Any]) -> None:
    """渲染漏斗圖"""
    rates = data.get("funnel_rates", {})
    if not rates:
        st.info("無漏斗數據")
        return

    # 依序: Click -> LPV -> ATC -> IC -> Purchase
    # 這裡的 rates 是 "X_per_Y"，無法直接畫絕對值漏斗，改畫轉換率橫條圖更直觀

    # 準備數據
    stages = [
        ("連結點擊率 (CTR)", rates.get("ctr_link_pct", 0), 1.0), # 基準參考
        ("點擊 -> LPV", rates.get("lpv_per_click", 0), 0.6),
        ("LPV -> ATC", rates.get("atc_per_lpv", 0), 0.08),
        ("ATC -> 結帳", rates.get("ic_per_atc", 0), 0.35),
        ("結帳 -> 購買", rates.get("purchase_per_ic", 0), 0.25)
    ]

    # 繪製 Plotly Bar Chart
    labels = [s[0] for s in stages]
    values = [s[1] * 100 for s in stages]  # 轉 %
    benchmarks = [s[2] * 100 for s in stages]

    fig = go.Figure()

    # 實際值
    fig.add_trace(go.Bar(
        x=labels,
        y=values,
        name='實際轉換率 (%)',
        marker_color=COLOR_GOLD
    ))

    # 基準線 (用 Line 或是 Bar 對比)
    fig.add_trace(go.Scatter(
        x=labels,
        y=benchmarks,
        name='基準值 (Benchmark)',
        mode='lines+markers',
        line=dict(color=COLOR_BROWN, width=2, dash='dot')
    ))

    fig.update_layout(
        title="全漏斗轉換率檢視",
        xaxis_title="轉換階段",
        yaxis_title="轉換率 (%)",
        template="plotly_white",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)

    # 顯示瓶頸結論
    if bottleneck := data.get("suspected_bottleneck"):
        st.error(f"🚫 偵測到瓶頸：{bottleneck}")


def _render_creative_fatigue_viz(data: Dict[str, Any]) -> None:
    """渲染疲乏與潛力廣告表格"""

    c1, c2 = st.columns(2)

    # 1. 疲乏廣告 (Fatigue)
    with c1:
        st.subheader("🛑 疲乏/衰退廣告 (建議暫停)")
        fatigue_ads = data.get("fatigue_ads", [])
        if fatigue_ads:
            df_bad = pd.DataFrame(fatigue_ads)
            # 簡化欄位顯示（欄位名稱匹配 creative_fatigue.py 輸出）
            available_cols = [c for c in ["ad_name", "frequency", "ctr_pct", "reason"] if c in df_bad.columns]
            st.dataframe(
                df_bad[available_cols] if available_cols else df_bad,
                column_config={
                    "ad_name": "廣告名稱",
                    "frequency": st.column_config.NumberColumn("頻率", format="%.2f"),
                    "ctr_pct": st.column_config.NumberColumn("CTR(%)", format="%.2f%%"),
                    "reason": "診斷原因"
                },
                hide_index=True
            )
        else:
            st.success("✅ 目前無明顯疲乏廣告")

    # 2. 高潛力廣告 (High Potential)
    with c2:
        st.subheader("🚀 高潛力廣告 (建議擴量)")
        good_ads = data.get("high_potential_ads", [])
        if good_ads:
            df_good = pd.DataFrame(good_ads)
            # 欄位名稱匹配 creative_fatigue.py 輸出
            available_cols = [c for c in ["ad_name", "hook_rate", "hold_rate", "reason"] if c in df_good.columns]
            st.dataframe(
                df_good[available_cols] if available_cols else df_good,
                column_config={
                    "ad_name": "廣告名稱",
                    "hook_rate": st.column_config.NumberColumn("Hook", format="%.2f%%"),
                    "hold_rate": st.column_config.NumberColumn("Hold", format="%.2f%%"),
                    "reason": "推薦原因"
                },
                hide_index=True
            )
        else:
            st.info("ℹ️ 暫無高潛力特徵廣告")


def _render_budget_rules_viz(data: Dict[str, Any]) -> None:
    """渲染預算建議"""
    actions = data.get("actions", [])

    if not actions:
        st.info("無預算調整建議")
        return

    for action in actions:
        act_type = action.get("action", "HOLD")
        msg = f"**[{act_type}]** {action.get('reason', '')}"

        if act_type == "KILL":
            st.error(msg)
        elif act_type == "SCALE_UP":
            st.warning(msg)  # 用黃色表示機會
        elif act_type == "SCALE_DOWN":
            st.info(msg)
        else:
            st.write(msg)


# ============================================================================
# 歷史檢視用：從檔案讀取技能結果
# ============================================================================

def render_skill_manager_from_files(version_path: Path) -> None:
    """
    從版本目錄讀取 skill_*.json 並渲染
    適用於歷史檢視頁面，重現報告生成時的技能分析結果

    Args:
        version_path: 版本目錄路徑（如 history/2025-W49/meta/versions/fp-xxxxxxxx）
    """
    skills_ctx: Dict[str, Any] = {}

    # 定義技能檔案對應
    files_map = {
        "metric_tree_diagnostic": "skill_metric_tree_diagnostic.json",
        "creative_fatigue": "skill_creative_fatigue.json",
        "budget_rules": "skill_budget_rules.json",
    }

    # 讀取各技能 JSON
    for key, filename in files_map.items():
        filepath = version_path / filename
        data = read_json_if_exists(filepath)
        if data:
            skills_ctx[key] = data

    # 無技能資料時顯示提示
    if not skills_ctx:
        st.info("ℹ️ 此版本無技能分析記錄（可能是舊版報告或技能功能尚未啟用）。")
        return

    # 呼叫既有渲染函式
    render_skill_manager(skills_ctx)
