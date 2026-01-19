"""
檔案用途：Ivy House Meta 週報分析系統 - 舊版資料夾遷移工具
職責：
  - 掃描 history/ 下舊命名資料夾（YYYY-W##_date_date 格式）
  - 複製到新結構的 legacy/ 與 versions/
  - 不刪原資料夾（非破壞性遷移）
"""

import json
import re
from pathlib import Path

from core import HISTORY_ROOT
from utils import (
    normalize_week_id,
    now_iso,
    read_json_if_exists,
    sha256_str,
    write_json,
    write_text,
)

LEGACY_RE = re.compile(r"^(?P<wk>[^_]+)_(?P<dr>.+?)(?:_fp-[0-9a-f]{8})?$")


def is_legacy_folder(name: str) -> bool:
    return bool(LEGACY_RE.match(name))


def migrate_one_legacy_dir(
    src: Path,
    week_meta_dir_fn,
    versions_root_fn,
    version_dir_fn,
    read_latest_ptr_fn,
    write_latest_ptr_fn,
    write_week_info_fn,
    ensure_week_meta_dirs_fn,
    fp_short_fn,
) -> dict | None:
    """遷移單一舊版資料夾到新結構。

    參數：
        src: 舊版資料夾路徑
        各 _fn: app.py 的包裝函式（傳入以避免 circular import）
    """
    rs = read_json_if_exists(src / "report_summary.json")
    if not rs:
        return None

    wk_norm = normalize_week_id(rs.get("week_id") or "")
    if not wk_norm:
        return None
    rs["week_id"] = wk_norm

    ensure_week_meta_dirs_fn(wk_norm)

    legacy_dst = week_meta_dir_fn(wk_norm) / "legacy" / src.name
    legacy_dst.mkdir(parents=True, exist_ok=True)

    inp = read_json_if_exists(src / "inputs.json") or {}
    saved_fp = inp.get("fingerprint")
    if isinstance(saved_fp, dict):
        code = fp_short_fn(saved_fp)
    else:
        dumped = json.dumps(rs, ensure_ascii=False, sort_keys=True)
        code = sha256_str(dumped)[:8]

    vdst = version_dir_fn(wk_norm, code)
    vdst.mkdir(parents=True, exist_ok=True)

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

    for fn in files:
        sp = src / fn
        if not sp.exists():
            continue
        dp1 = legacy_dst / fn
        dp2 = vdst / fn
        # 直接複製文本（不重排 JSON）
        write_text(dp1, sp.read_text(encoding="utf-8"))
        write_text(dp2, sp.read_text(encoding="utf-8"))

    write_week_info_fn(wk_norm, rs.get("date_range") or "")
    if not read_latest_ptr_fn(wk_norm):
        write_latest_ptr_fn(wk_norm, code)

    return {
        "src": str(src),
        "week_id": wk_norm,
        "fp": code,
        "version_dir": str(vdst),
        "legacy_dir": str(legacy_dst),
    }


def render_legacy_migration_ui(
    st,
    week_meta_dir_fn,
    version_dir_fn,
    read_latest_ptr_fn,
    write_latest_ptr_fn,
    write_week_info_fn,
    ensure_week_meta_dirs_fn,
    fp_short_fn,
):
    """渲染舊版遷移工具 UI（Streamlit expander）。

    參數：
        st: streamlit 模組
        各 _fn: app.py 的包裝函式（傳入以避免 circular import）
    """
    with st.expander("遷移工具（不丟舊資料夾｜只複製）", expanded=False):
        st.caption(
            "掃描 history/ 下舊命名資料夾（如 2025-W49_2025-12-04_2025-12-09），"
            "複製到新結構的 legacy/ 與 versions/。不刪原資料夾。"
        )
        legacy_candidates = [
            p for p in HISTORY_ROOT.iterdir() if p.is_dir() and is_legacy_folder(p.name)
        ]
        st.write("偵測到 legacy 目錄數：", len(legacy_candidates))

        if legacy_candidates:
            if st.button("開始遷移（只複製，不刪除）", key="btn_migrate"):
                mig_map = read_json_if_exists(HISTORY_ROOT / "MIGRATION_MAP.json") or {
                    "schema_version": "migration_map.v1",
                    "updated_at": now_iso(),
                    "items": [],
                }
                migrated = 0
                skipped = 0

                for src in legacy_candidates:
                    if any(it.get("src") == str(src) for it in mig_map.get("items", [])):
                        skipped += 1
                        continue
                    res = migrate_one_legacy_dir(
                        src,
                        week_meta_dir_fn,
                        None,  # versions_root not used
                        version_dir_fn,
                        read_latest_ptr_fn,
                        write_latest_ptr_fn,
                        write_week_info_fn,
                        ensure_week_meta_dirs_fn,
                        fp_short_fn,
                    )
                    if res:
                        mig_map["items"].append(res)
                        migrated += 1
                    else:
                        skipped += 1

                mig_map["updated_at"] = now_iso()
                write_json(HISTORY_ROOT / "MIGRATION_MAP.json", mig_map)
                st.success(f"遷移完成：migrated={migrated}, skipped={skipped}")
                st.json(mig_map)
