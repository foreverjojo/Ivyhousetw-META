"""
檔案用途：UI 元件
職責：
  - DataFrame 預覽
  - Artifacts 面板
  - 其他 UI 輔助元件
"""

from pathlib import Path
import pandas as pd
import streamlit as st


def preview_df(df: pd.DataFrame, title: str, max_rows: int = 20) -> None:
    """顯示 DataFrame 預覽"""
    st.subheader(title)
    st.write(f"Rows: {len(df):,} | Cols: {df.shape[1]}")
    st.write("Columns:", list(df.columns))
    st.dataframe(df.head(max_rows), use_container_width=True)


def artifacts_panel(vdir: Path) -> None:
    """顯示當前版本資料夾的 artifacts 狀態"""
    st.subheader("Artifacts（當前版本資料夾）")
    files = [
        "inputs.json",
        "pipeline_state.json",
        "report_summary.json",
        "report_insights.json",
        "consultant_notes.json",
        "meeting_draft.md",
        "workflow_state_draft.json",
        "meeting.md",
        "workflow_state.json",
    ]
    checks = {f: (vdir / f).exists() for f in files}
    st.write("Version dir:", str(vdir))
    st.write({k: ("✅" if v else "❌") for k, v in checks.items()})
