"""
檔案用途：Trace ID 追蹤（Correlation ID）
職責：
  - 提供跨模組、跨步驟的 trace_id（同一輪流程共用）
  - 以 contextvars 實作，支援巢狀 context 並可安全還原

設計原則：
  - 不引入第三方依賴
  - 不在此模組做 logging，避免循環依賴

使用範例：
    from core.tracing import trace_context, get_trace_id

    with trace_context():
        do_work()
        print(get_trace_id())
"""

from __future__ import annotations

import contextlib
import contextvars
import uuid
from typing import Dict, Iterator, Optional


_TRACE_ID: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("trace_id", default=None)


def new_trace_id(prefix: str = "") -> str:
    """建立新的 trace_id。

    Args:
        prefix: 可選前綴（例如 "ui" / "job"），會以 "<prefix>_" 接在 UUID 前。

    Returns:
        新的 trace_id 字串。
    """

    tid = uuid.uuid4().hex
    if prefix:
        safe_prefix = prefix.strip().replace(" ", "_")
        return f"{safe_prefix}_{tid}"
    return tid


def get_trace_id() -> Optional[str]:
    """取得目前 context 的 trace_id（若尚未設定則回傳 None）。"""

    return _TRACE_ID.get()


def set_trace_id(trace_id: Optional[str]) -> None:
    """直接設定目前 context 的 trace_id。

    注意：一般建議使用 trace_context() 以確保能自動還原。
    """

    _TRACE_ID.set(trace_id)


def ensure_trace_id(prefix: str = "") -> str:
    """確保目前 context 有 trace_id，若無則建立並設定一個。"""

    current = get_trace_id()
    if current:
        return current
    tid = new_trace_id(prefix=prefix)
    set_trace_id(tid)
    return tid


@contextlib.contextmanager
def trace_context(trace_id: Optional[str] = None, prefix: str = "") -> Iterator[str]:
    """在區塊內注入 trace_id，並於退出時自動還原。

    Args:
        trace_id: 指定 trace_id；若為 None 則自動建立。
        prefix: trace_id 未指定時的前綴。

    Yields:
        區塊內使用的 trace_id。
    """

    tid = trace_id or new_trace_id(prefix=prefix)
    token = _TRACE_ID.set(tid)
    try:
        yield tid
    finally:
        _TRACE_ID.reset(token)


def attach_trace(extra: Optional[Dict] = None) -> Dict:
    """將 trace_id 附加到 extra dict（不會修改原 dict）。

    用途：在不方便改 logging formatter 的情況下，可把 trace_id 顯式帶入。
    """

    payload = dict(extra or {})
    tid = get_trace_id()
    if tid and "trace_id" not in payload:
        payload["trace_id"] = tid
    return payload
