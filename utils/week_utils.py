"""
檔案用途：週次 ID 處理工具
職責：
  - Week ID 正規化（YYYY-Www 格式）
  - Week ID 解析
  - 取得磁碟上的 week_id 列表
  - 計算前一週的 week_id
"""

import re
from pathlib import Path

# Week ID 正則表達式
WEEK_RE = re.compile(r"^(?P<y>\d{4})-W(?P<w>\d{1,2})$")


def normalize_week_id(week_id: str) -> str | None:
    """
    將 week_id 正規化成 YYYY-Www（W 補零）
    例：2025-W49 -> 2025-W49；2025-W1 -> 2025-W01
    """
    if not isinstance(week_id, str):
        return None
    m = WEEK_RE.match(week_id.strip())
    if not m:
        return None
    y = int(m.group("y"))
    w = int(m.group("w"))
    return f"{y}-W{w:02d}"


def parse_week_id(week_id: str) -> tuple[int, int] | None:
    """解析 week_id 為 (year, week) tuple"""
    n = normalize_week_id(week_id)
    if not n:
        return None
    m = WEEK_RE.match(n)
    return (int(m.group("y")), int(m.group("w")))


def list_week_ids_on_disk(history_root: Path) -> list[str]:
    """列出 history/ 下所有合法的 week_id 資料夾"""
    out: list[str] = []
    for p in history_root.iterdir():
        if p.is_dir() and parse_week_id(p.name):
            out.append(p.name)

    def key(wk: str):
        y, w = parse_week_id(wk)  # type: ignore[misc]
        return (y, w)

    return sorted(out, key=key)


def get_prev_week_id(current_week_id: str, history_root: Path) -> str | None:
    """取得前一週的 week_id（從磁碟上的資料夾列表）"""
    cur = parse_week_id(current_week_id)
    if not cur:
        return None
    weeks = list_week_ids_on_disk(history_root)
    cur_y, cur_w = cur
    prev: str | None = None
    for wk in weeks:
        y, w = parse_week_id(wk)  # type: ignore[misc]
        if (y, w) < (cur_y, cur_w):
            prev = wk
        else:
            break
    return prev
