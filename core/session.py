"""
檔案用途：Session 狀態管理
職責：
  - 初始化 session state
  - 重置 session lock
  - 載入與儲存 manual inputs
"""

from pathlib import Path

import streamlit as st

from utils.file_io import read_json_if_exists, write_json


def init_session_state() -> None:
    """初始化 session state 的鎖定變數"""
    if "locked_week_id" not in st.session_state:
        st.session_state["locked_week_id"] = None
    if "locked_fp" not in st.session_state:
        st.session_state["locked_fp"] = None
    if "locked_vdir" not in st.session_state:
        st.session_state["locked_vdir"] = None


def reset_session_lock() -> None:
    """重置 session lock（清除所有相關狀態）"""
    for k in [
        "locked_week_id",
        "locked_fp",
        "locked_vdir",
        "report_summary",
        "report_insights",
        "consultant_notes",
        "workflow_state",
        "meeting_md",
        "workflow_state_draft",
        "meeting_md_draft",
        "manual_inputs",
    ]:
        st.session_state.pop(k, None)


def load_or_session(key: str, path: Path) -> dict | None:
    """從 session 或檔案載入資料"""
    if key in st.session_state:
        return st.session_state[key]
    data = read_json_if_exists(path)
    if data:
        st.session_state[key] = data
    return data


def sync_manual_inputs_to_inputs_json(vdir: Path) -> None:
    """將 session 中的 manual_inputs 同步到 inputs.json"""
    if "manual_inputs" not in st.session_state:
        return
    inputs_path = vdir / "inputs.json"
    inputs = read_json_if_exists(inputs_path) or {}
    inputs["manual_inputs"] = st.session_state["manual_inputs"]
    write_json(inputs_path, inputs)
