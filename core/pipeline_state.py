"""
檔案用途：Pipeline 狀態管理
職責：
  - 寫入 pipeline_state.json
  - 記錄執行事件與錯誤
  - 從版本目錄還原 session state
"""

from pathlib import Path
from typing import Any

import streamlit as st

from utils.file_io import read_json_if_exists, read_text_if_exists, write_json
from utils.path_utils import now_iso


def write_pipeline_state(
    vdir: Path,
    last_completed_step: str,
    mode: str,
    status: str = "ok",
    error: str | None = None,
    details: list[str] | None = None,
) -> None:
    """
    寫入 pipeline_state.json（events 追溯用）
    - status="error" 時，會確保 details 至少有一條文字，方便之後回溯
    """
    p = vdir / "pipeline_state.json"
    state = read_json_if_exists(p) or {
        "schema_version": "pipeline_state.v1",
        "created_at": now_iso(),
        "events": [],
    }
    state["updated_at"] = now_iso()
    state["last_completed_step"] = last_completed_step
    state["last_mode"] = mode

    ev: dict[str, Any] = {
        "at": now_iso(),
        "mode": mode,
        "step": last_completed_step,
        "status": status,
    }
    if error:
        ev["error"] = error

    if details is not None:
        # 去掉空值，避免存入 [None]
        clean = [d for d in details if isinstance(d, str) and d.strip()]
        ev["details"] = clean
    elif status == "error":
        # 讓 details 一定有內容
        ev["details"] = [error] if error else ["(no details)"]

    state["events"].append(ev)
    write_json(p, state)


def restore_from_version_dir(vdir: Path) -> None:
    """rerun 後從落盤 artifacts 還原 session_state"""
    if not vdir or not vdir.exists():
        return

    rs = read_json_if_exists(vdir / "report_summary.json")
    if rs and "report_summary" not in st.session_state:
        st.session_state["report_summary"] = rs

    ri = read_json_if_exists(vdir / "report_insights.json")
    if ri and "report_insights" not in st.session_state:
        st.session_state["report_insights"] = ri

    cn = read_json_if_exists(vdir / "consultant_notes.json")
    if cn and "consultant_notes" not in st.session_state:
        st.session_state["consultant_notes"] = cn

    ws = read_json_if_exists(vdir / "workflow_state.json")
    if ws and "workflow_state" not in st.session_state:
        st.session_state["workflow_state"] = ws

    md = read_text_if_exists(vdir / "meeting.md")
    if md and "meeting_md" not in st.session_state:
        st.session_state["meeting_md"] = md

    wsd = read_json_if_exists(vdir / "workflow_state_draft.json")
    if wsd and "workflow_state_draft" not in st.session_state:
        st.session_state["workflow_state_draft"] = wsd

    mdd = read_text_if_exists(vdir / "meeting_draft.md")
    if mdd and "meeting_md_draft" not in st.session_state:
        st.session_state["meeting_md_draft"] = mdd

    inputs = read_json_if_exists(vdir / "inputs.json")
    if inputs and "manual_inputs" in inputs and "manual_inputs" not in st.session_state:
        st.session_state["manual_inputs"] = inputs.get("manual_inputs") or {}
