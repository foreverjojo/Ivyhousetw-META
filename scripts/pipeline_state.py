"""
scripts/pipeline_state.py

Single place to read/write pipeline_state.json and append events.
All timestamps are Asia/Taipei to avoid drift across environments.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# =========================
# Timezone（固定台北時間）
# =========================
try:
    from zoneinfo import ZoneInfo  # py3.9+
    TAIPEI_TZ = ZoneInfo("Asia/Taipei")
except Exception:
    TAIPEI_TZ = None  # fallback: naive local time


def now_iso() -> str:
    """Fixed to Asia/Taipei (timespec=seconds)."""
    if TAIPEI_TZ:
        return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")
    return datetime.now().isoformat(timespec="seconds")


def read_json_if_exists(p: Path) -> Optional[Dict[str, Any]]:
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def write_json(p: Path, obj: Dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def pipeline_state_path(vdir: Path) -> Path:
    return vdir / "pipeline_state.json"


def init_pipeline_state() -> Dict[str, Any]:
    return {
        "schema_version": "pipeline_state.v1",
        "created_at": now_iso(),
        "events": [],
    }


def append_event(
    state: Dict[str, Any],
    *,
    step: str,
    mode: str,
    status: str,
    error: Optional[str] = None,
    details: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    ev: Dict[str, Any] = {"at": now_iso(), "mode": mode, "step": step, "status": status}
    if error:
        ev["error"] = error

    if details is not None:
        clean = [d for d in details if isinstance(d, str) and d.strip()]
        ev["details"] = clean
    elif status == "error":
        ev["details"] = [error] if error else ["(no details)"]

    if extra:
        for k, v in extra.items():
            ev[k] = v

    state.setdefault("events", []).append(ev)


def write_pipeline_state(
    vdir: Path,
    last_completed_step: str,
    mode: str,
    *,
    status: str = "ok",
    error: Optional[str] = None,
    details: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Write/append pipeline_state.json.

    Contract (stable):
    - state.last_completed_step, state.last_mode updated each call
    - events[] appended with:
        at, mode, step, status, (error), (details[])
    """
    p = pipeline_state_path(vdir)
    state = read_json_if_exists(p) or init_pipeline_state()

    state["updated_at"] = now_iso()
    state["last_completed_step"] = last_completed_step
    state["last_mode"] = mode

    append_event(
        state,
        step=last_completed_step,
        mode=mode,
        status=status,
        error=error,
        details=details,
        extra=extra,
    )

    write_json(p, state)
