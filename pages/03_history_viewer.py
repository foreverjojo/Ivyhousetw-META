"""
檔案用途：History Viewer 頁面 - 瀏覽歷史週報
職責：
  - 列出所有歷史週報（按 week_id 排序）
  - 顯示每週的所有版本（按 fingerprint）
  - 查看報告詳細內容（meeting.md, workflow_state.json）
"""

import streamlit as st
from pathlib import Path
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# 設定頁面配置
st.set_page_config(
    page_title="歷史檢視 | Ivy House Meta",
    page_icon="📂",
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

# 匯入工具
from utils import read_json_if_exists, read_text_if_exists

# ============================================================================
# 配置
# ============================================================================

HISTORY_ROOT = Path(__file__).parent.parent / "history"
LLM_LOG_FILE = Path(__file__).parent.parent / "logs" / "llm_calls.jsonl"


# ============================================================================
# 工具函式
# ============================================================================

def get_all_weeks() -> List[str]:
    """取得所有週報 ID（降序）"""
    weeks = []
    if HISTORY_ROOT.exists():
        for week_dir in HISTORY_ROOT.iterdir():
            if week_dir.is_dir() and week_dir.name.startswith("20"):
                weeks.append(week_dir.name)
    return sorted(weeks, reverse=True)


def get_versions_for_week(week_id: str) -> List[Dict[str, Any]]:
    """取得指定週的所有版本"""
    versions = []
    week_dir = HISTORY_ROOT / week_id / "meta" / "versions"
    
    if week_dir.exists():
        for version_dir in week_dir.iterdir():
            if version_dir.is_dir() and version_dir.name.startswith("fp-"):
                # 讀取 pipeline_state.json 取得詳細資訊
                ps = read_json_if_exists(version_dir / "pipeline_state.json")
                ws = read_json_if_exists(version_dir / "workflow_state.json")
                
                # 判斷是否為 latest
                latest_file = HISTORY_ROOT / week_id / "meta" / "latest.json"
                latest_data = read_json_if_exists(latest_file)
                is_latest = latest_data and latest_data.get("rel_path", "").endswith(version_dir.name)
                
                # 取得時間戳記
                if ps and ps.get("updated_at"):
                    timestamp = ps["updated_at"]
                elif ws and ws.get("created_at"):
                    timestamp = ws["created_at"]
                else:
                    try:
                        timestamp = datetime.fromtimestamp(version_dir.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        timestamp = "N/A"
                
                # 判斷狀態
                has_meeting = (version_dir / "meeting.md").exists() or (version_dir / "meeting_final.md").exists()
                status = "completed" if has_meeting else "pending"
                
                versions.append({
                    "fingerprint": version_dir.name,
                    "path": version_dir,
                    "is_latest": is_latest,
                    "timestamp": timestamp,
                    "status": status,
                    "last_step": ps.get("last_completed_step") if ps else "N/A",
                    "mode": ps.get("last_mode") if ps else "N/A",
                })
    
    # 按時間戳記降序排列
    versions.sort(key=lambda x: x["timestamp"], reverse=True)
    return versions


def get_version_details(version_path: Path) -> Dict[str, Any]:
    """取得版本詳細資訊"""
    details = {
        "pipeline_state": read_json_if_exists(version_path / "pipeline_state.json"),
        "workflow_state": read_json_if_exists(version_path / "workflow_state.json"),
        "report_summary": read_json_if_exists(version_path / "report_summary.json"),
        "meeting_md": read_text_if_exists(version_path / "meeting.md"),
        "meeting_draft_md": read_text_if_exists(version_path / "meeting_draft.md"),
    }
    return details


def load_token_usage(version_fp: str) -> List[Dict[str, Any]]:
    """
    讀取 logs/llm_calls.jsonl，過濾出指定版本（version_fp，例如 fp-xxxxxxxx）的 token usage。
    只依賴 LLMCall.extra.version_fp，不掃描 history 內容，避免 I/O 過重。
    """
    if not LLM_LOG_FILE.exists():
        return []

    out: List[Dict[str, Any]] = []
    try:
        with LLM_LOG_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                extra = rec.get("extra") or {}
                if isinstance(extra, dict) and extra.get("version_fp") == version_fp:
                    out.append(rec)
    except Exception:
        return []
    return out


def summarize_token_usage(calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    彙總 Step C/E/F token usage；Step E 依 consultant 拆分 A/B/C。
    若同一版本同一步驟有多次記錄（重跑），以 timestamp 最新的一筆為主，並顯示 Runs。
    """
    latest: Dict[str, Dict[str, Any]] = {}
    runs: Dict[str, int] = {}
    for c in calls:
        extra = c.get("extra") or {}
        if not isinstance(extra, dict):
            continue
        step = extra.get("step")
        if step not in ("C", "E", "F"):
            continue

        consultant = extra.get("consultant") if step == "E" else None
        label = f"E-{consultant}" if step == "E" else str(step)

        runs[label] = runs.get(label, 0) + 1

        ts = str(c.get("timestamp") or "")
        prev = latest.get(label)
        if prev is None or str(prev.get("timestamp") or "") <= ts:
            latest[label] = c

    rows: List[Dict[str, Any]] = []
    order = ["C", "E-A", "E-B", "E-C", "F"]
    for k in order:
        if k in latest:
            c = latest[k]
            rows.append(
                {
                    "Step": k,
                    "Model": str(c.get("model") or "N/A"),
                    "Runs": runs.get(k, 1),
                    "Prompt": int(c.get("prompt_tokens", 0) or 0),
                    "Completion": int(c.get("completion_tokens", 0) or 0),
                    "Total": int(c.get("total_tokens", 0) or 0),
                    "Cost (USD)": round(float(c.get("cost_usd", 0.0) or 0.0), 6),
                }
            )
    return rows


# ============================================================================
# 主要內容區域
# ============================================================================

render_page_header("歷史檢視", icon="📂", subtitle="瀏覽所有歷史週報與版本")

# 取得所有週報
weeks = get_all_weeks()

if not weeks:
    st.info("📭 尚無歷史週報記錄。請先執行「報告生成」建立週報。")
    st.stop()

# ============================================================================
# 側邊欄：週報列表
# ============================================================================

with st.sidebar:
    st.divider()
    st.markdown("### 📅 週報列表")
    
    # 搜尋篩選
    search_query = st.text_input("🔍 搜尋 Week ID", placeholder="例如：2026-W01")
    
    # 篩選週報
    filtered_weeks = [w for w in weeks if search_query.lower() in w.lower()] if search_query else weeks
    
    # 選擇週報
    selected_week = st.radio(
        "選擇週報",
        options=filtered_weeks,
        index=0 if filtered_weeks else None,
        key="selected_week"
    )

# ============================================================================
# 主區域：版本列表與詳細資訊
# ============================================================================

if selected_week:
    st.markdown(f"## 📅 {selected_week}")
    
    # 讀取 week_info
    week_info = read_json_if_exists(HISTORY_ROOT / selected_week / "meta" / "week_info.json")
    if week_info:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("日期範圍", week_info.get("date_range", "N/A"))
        with col2:
            # 建立時間優先使用 created_at，備份使用 updated_at
            created_time = week_info.get("created_at") or week_info.get("updated_at") or "N/A"
            # 若是 ISO 格式，取前 10 碼 (日期)
            display_time = created_time[:10] if len(created_time) >= 10 else created_time
            st.metric("建立時間", display_time)
    
    st.divider()
    
    # 取得版本列表
    versions = get_versions_for_week(selected_week)
    
    if not versions:
        st.warning("此週報尚無版本記錄。")
    else:
        st.markdown(f"### 📦 版本列表 ({len(versions)} 個)")
        
        # 版本選擇
        version_options = [
            f"{'⭐ ' if v['is_latest'] else ''}{v['fingerprint']} | {v['timestamp']}"
            for v in versions
        ]
        
        selected_version_idx = st.selectbox(
            "選擇版本",
            range(len(versions)),
            format_func=lambda i: version_options[i],
            key="selected_version"
        )
        
        selected_version = versions[selected_version_idx]
        
        # 版本狀態
        col1, col2, col3 = st.columns(3)
        with col1:
            if selected_version["status"] == "completed":
                st.success("✅ 已完成")
            else:
                st.warning("⏱️ 進行中")
        with col2:
            st.metric("最後步驟", selected_version["last_step"])
        with col3:
            st.metric("模式", selected_version["mode"])
        
        st.divider()

        # Token usage（移出 02_report_generation，改在 history viewer 顯示）
        st.markdown("### 🧮 Token Usage")
        usage_calls = load_token_usage(selected_version["fingerprint"])
        usage_rows = summarize_token_usage(usage_calls)
        if not usage_rows:
            st.info("此版本尚未記錄 token 用量（舊版本或未重跑 Step C/E/F）。")
        else:
            total_tokens = sum(int(r["Total"]) for r in usage_rows)
            total_cost = sum(float(r["Cost (USD)"]) for r in usage_rows)
            m1, m2 = st.columns(2)
            with m1:
                st.metric("Total Tokens", f"{total_tokens:,}")
            with m2:
                st.metric("Total Cost (USD)", f"{total_cost:.6f}")
            st.dataframe(usage_rows, use_container_width=True)
        
        # 版本詳細資訊
        details = get_version_details(selected_version["path"])
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 會議摘要", "📊 KPI 彙總", "🛠️ 技能分析", "⚙️ 工作流程狀態", "📋 管線狀態"])
        
        with tab1:
            meeting_content = details["meeting_md"] or details["meeting_draft_md"]
            if meeting_content:
                st.markdown(meeting_content)
            else:
                st.info("尚無 meeting.md 內容")
        
        with tab2:
            if details["report_summary"]:
                rs = details["report_summary"]
                
                # 顯示關鍵 KPI
                if "total" in rs:
                    t = rs["total"]
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("總花費", f"${t.get('spend', 0):,.2f}")
                    with c2:
                        st.metric("總營收", f"${t.get('revenue', 0):,.2f}")
                    with c3:
                        roas = t.get("roas", 0)
                        st.metric("ROAS", f"{roas:.2f}x" if roas else "N/A")
                    with c4:
                        st.metric("CPA", f"${t.get('cpa', 0):,.2f}")
                
                # 完整 JSON
                with st.expander("完整 JSON"):
                    st.json(rs)
            else:
                st.info("尚無 report_summary.json")
        
        with tab3:
            # 技能分析 Tab（新增）
            from ui.skill_manager import render_skill_manager_from_files
            render_skill_manager_from_files(selected_version["path"])
        
        with tab4:
            if details["workflow_state"]:
                st.json(details["workflow_state"])
            else:
                st.info("尚無 workflow_state.json")
        
        with tab5:
            if details["pipeline_state"]:
                st.json(details["pipeline_state"])
            else:
                st.info("尚無 pipeline_state.json")

# ============================================================================
# 底部資訊
# ============================================================================

st.divider()
st.caption("📍 Ivy House Meta 週報分析系統 | 艾薇手工坊")
