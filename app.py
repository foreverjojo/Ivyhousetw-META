import json
import hashlib
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from scripts.kpi_calc import build_report_summary
from scripts.llm_insights import generate_report_insights
from scripts.consultants import run_three_consultants
from scripts.moderator import build_workflow_state, build_meeting_markdown, write_artifacts

# Schema validation (Step B 後強制驗證)
from jsonschema import validators

# =========================
# Timezone（固定台北時間）
# =========================
try:
    from zoneinfo import ZoneInfo  # py3.9+
    TAIPEI_TZ = ZoneInfo("Asia/Taipei")
except Exception:
    TAIPEI_TZ = None  # fallback: naive local time


# =========================
# Page config
# =========================
st.set_page_config(page_title="Ivy House - Meta Weekly MVP", layout="wide")
st.title("Ivy House｜Meta 週會 MVP（Week 主鍵 + FP 版本 + Auto Prev Week）")
st.caption(
    "快篩：B→C→D（draft）｜最終：B→C→E→F（final）。"
    "主鍵=week_id；版本=fp；"
    "Force=覆蓋本次 fp（不覆蓋別的 fp）；"
    "Auto new version=只有 mismatch 才新版本。"
)

HISTORY_ROOT = Path("history")
HISTORY_ROOT.mkdir(parents=True, exist_ok=True)


# =========================
# Helpers (IO / Hash)
# =========================
def now_iso() -> str:
    """固定用台北時間（Asia/Taipei）。"""
    if TAIPEI_TZ:
        return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")
    return datetime.now().isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def sha256_str(s: str) -> str:
    return sha256_bytes(s.encode("utf-8"))


def read_json_if_exists(p: Path) -> Optional[dict]:
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def write_json(p: Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def read_text_if_exists(p: Path) -> Optional[str]:
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None


def write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


# =========================
# Schema validate (Step B)
# =========================
SCHEMAS_DIR = Path("schemas")


def _load_schema(schema_filename: str) -> dict:
    sp = SCHEMAS_DIR / schema_filename
    if not sp.exists():
        raise RuntimeError(f"找不到 schema 檔案：{sp}（請確認已放在 schemas/）")
    return json.loads(sp.read_text(encoding="utf-8"))


class SchemaValidationError(RuntimeError):
    """給 pipeline_state.json 落盤用：保留可讀錯誤清單在 details。"""

    def __init__(self, message: str, details: Optional[List[str]] = None):
        super().__init__(message)
        self.details: List[str] = details or []


def validate_json(instance: dict, schema: dict, *, label: str = "") -> None:
    """使用 schema 的 $schema 自動選對 validator，並輸出可讀錯誤。"""
    ValidatorCls = validators.validator_for(schema)
    ValidatorCls.check_schema(schema)
    v = ValidatorCls(schema)

    errors = sorted(v.iter_errors(instance), key=lambda e: list(e.path))
    if not errors:
        return

    # 只列前 20 條，避免 UI / log 爆炸
    lines: List[str] = []
    for e in errors[:20]:
        path = ".".join(str(p) for p in e.path) or "(root)"
        lines.append(f"- {path}: {e.message}")

    hint = f"\n（還有 {len(errors)-20} 條未顯示）" if len(errors) > 20 else ""
    name = f"[{label}] " if label else ""
    msg = name + "Schema validate 失敗：\n" + "\n".join(lines) + hint
    raise SchemaValidationError(msg, details=lines)


def validate_report_summary(rs: dict) -> None:
    schema = _load_schema("report_summary.v1.json")
    validate_json(rs, schema, label="report_summary.v1")


# =========================
# CSV / preview
# =========================
def read_csv(uploaded_file) -> pd.DataFrame:
    raw = uploaded_file.getvalue()
    for enc in ["utf-8-sig", "utf-8", "cp950", "big5"]:
        try:
            return pd.read_csv(pd.io.common.BytesIO(raw), encoding=enc)
        except Exception:
            continue
    return pd.read_csv(pd.io.common.BytesIO(raw))


def preview_df(df: pd.DataFrame, title: str, max_rows: int = 20) -> None:
    st.subheader(title)
    st.write(f"Rows: {len(df):,} | Cols: {df.shape[1]}")
    st.write("Columns:", list(df.columns))
    st.dataframe(df.head(max_rows), use_container_width=True)


# =========================
# Week ID parsing (no date_range guessing) + normalize
# =========================
WEEK_RE = re.compile(r"^(?P<y>\d{4})-W(?P<w>\d{1,2})$")


def normalize_week_id(week_id: str) -> Optional[str]:
    """
    將 week_id 正規化成 YYYY-Www（W 補零）。
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


def parse_week_id(week_id: str) -> Optional[Tuple[int, int]]:
    n = normalize_week_id(week_id)
    if not n:
        return None
    m = WEEK_RE.match(n)
    return (int(m.group("y")), int(m.group("w")))


def list_week_ids_on_disk() -> List[str]:
    """只列出 history/ 下資料夾名本身就是 week_id 的資料夾（YYYY-Www 或 YYYY-Ww）。"""
    out: List[str] = []
    for p in HISTORY_ROOT.iterdir():
        if p.is_dir() and parse_week_id(p.name):
            out.append(p.name)

    def key(wk: str):
        y, w = parse_week_id(wk)  # type: ignore[misc]
        return (y, w)

    return sorted(out, key=key)


def get_prev_week_id(current_week_id: str) -> Optional[str]:
    cur = parse_week_id(current_week_id)
    if not cur:
        return None
    weeks = list_week_ids_on_disk()
    cur_y, cur_w = cur
    prev: Optional[str] = None
    for wk in weeks:
        y, w = parse_week_id(wk)  # type: ignore[misc]
        if (y, w) < (cur_y, cur_w):
            prev = wk
        else:
            break
    return prev


# =========================
# Fingerprint (deterministic)
# =========================
def compute_file_fp(uploaded_file) -> dict:
    b = uploaded_file.getvalue()
    return {"name": getattr(uploaded_file, "name", ""), "size": len(b), "sha256": sha256_bytes(b)}


def compute_inputs_fingerprint(meta_adset_file, meta_ads_file, web_excel_file, detail_level: str) -> dict:
    # generated_at 僅顯示用，不進版本碼
    return {
        "schema_version": "inputs_fingerprint.v2",
        "generated_at": now_iso(),
        "config": {"detail_level": detail_level or ""},
        "files": {
            "meta_adset": compute_file_fp(meta_adset_file),
            "meta_ads": compute_file_fp(meta_ads_file),
            "web_excel": compute_file_fp(web_excel_file),
        },
    }


def fingerprint_key_for_version(current_fp: dict) -> dict:
    # ✅ 只取 deterministic 欄位（不含 generated_at / name）
    files = current_fp.get("files") or {}
    cfg = current_fp.get("config") or {}

    def fget(k: str):
        x = files.get(k) or {}
        return {"sha256": x.get("sha256", ""), "size": x.get("size", 0)}

    return {
        "config": {"detail_level": cfg.get("detail_level", "")},
        "files": {
            "meta_adset": fget("meta_adset"),
            "meta_ads": fget("meta_ads"),
            "web_excel": fget("web_excel"),
        },
    }


def fp_short(current_fp: dict) -> str:
    dumped = json.dumps(fingerprint_key_for_version(current_fp), ensure_ascii=False, sort_keys=True)
    return sha256_str(dumped)[:8]


# =========================
# New path helpers (week-based)
# =========================
def week_meta_dir(week_id: str) -> Path:
    return HISTORY_ROOT / week_id / "meta"


def versions_root(week_id: str) -> Path:
    return week_meta_dir(week_id) / "versions"


def version_dir(week_id: str, fp_code: str) -> Path:
    return versions_root(week_id) / f"fp-{fp_code}"


def latest_ptr_path(week_id: str) -> Path:
    return week_meta_dir(week_id) / "latest.json"


def read_latest_ptr(week_id: str) -> Optional[dict]:
    return read_json_if_exists(latest_ptr_path(week_id))


def write_latest_ptr(week_id: str, fp_code: str) -> None:
    """latest.json 改存相對路徑（避免搬環境 / root 變更不穩）。"""
    rel = f"versions/fp-{fp_code}"
    write_json(
        latest_ptr_path(week_id),
        {
            "schema_version": "latest_ptr.v2",
            "updated_at": now_iso(),
            "week_id": week_id,
            "fp": fp_code,
            "rel_path": rel,
        },
    )


def write_week_info(week_id: str, date_range: str) -> None:
    write_json(
        week_meta_dir(week_id) / "week_info.json",
        {
            "schema_version": "week_info.v1",
            "updated_at": now_iso(),
            "week_id": week_id,
            "date_range": date_range,
        },
    )


def restore_from_version_dir(vdir: Path) -> None:
    """rerun 後從落盤 artifacts 還原 session_state。"""
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


# =========================
# pipeline_state + sidebar status
# =========================
def write_pipeline_state(
    vdir: Path,
    last_completed_step: str,
    mode: str,
    status: str = "ok",
    error: Optional[str] = None,
    details: Optional[List[str]] = None,
) -> None:
    """寫入 pipeline_state.json（events 追溯用）。
    - status="error" 時，會確保 details 至少有一條文字，方便你之後回溯。
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

    ev: Dict[str, Any] = {"at": now_iso(), "mode": mode, "step": last_completed_step, "status": status}
    if error:
        ev["error"] = error

    if details is not None:
        # 去掉空值，避免存入 [None]
        clean = [d for d in details if isinstance(d, str) and d.strip()]
        ev["details"] = clean
    elif status == "error":
        # ✅ 讓 details 一定有內容（可選但很實用）
        ev["details"] = [error] if error else ["(no details)"]

    state["events"].append(ev)
    write_json(p, state)


def artifacts_panel(vdir: Path) -> None:
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


# =========================
# Sidebar (互斥模式：用 radio，避免死鎖)
# =========================
st.sidebar.header("設定（MVP）")
detail_level = st.sidebar.selectbox("Detail Level", ["default", "adset+ads"], index=1, key="detail_level")
validate_schema = st.sidebar.checkbox(
    "Step B 後 Schema Validate（強制）",
    value=True,
    key="validate_schema",
    help="用 schemas/report_summary.v1.json 強制驗證 Step B 產物，避免口徑漂移。",
)

def safe_stamp() -> str:
    """filesystem-safe stamp for staging folders."""
    if TAIPEI_TZ:
        return datetime.now(TAIPEI_TZ).strftime("%Y%m%d_%H%M%S")
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def staging_version_dir(fp_code: str) -> Path:
    """A staging vdir to record early Step-B errors before week_id/vdir is resolved."""
    return HISTORY_ROOT / "_staging" / safe_stamp() / "meta" / "versions" / f"fp-{fp_code}"


def _cleanup_staging_on_success(stage_vdir: Path) -> None:
    """Delete only the single staging run folder (<stamp>) after Step B succeeds.

    Expected structure:
      history/_staging/<stamp>/meta/versions/fp-xxxxxxxx  <-- stage_vdir
    We delete:
      history/_staging/<stamp>
    """
    try:
        p = str(stage_vdir).replace("\\", "/")
        if "/_staging/" not in p:
            return

        stamp_dir = None
        for parent in stage_vdir.parents:
            if parent.parent and parent.parent.name == "_staging":
                stamp_dir = parent
                break

        if not stamp_dir:
            return
        if stamp_dir.name in ("", "_staging"):
            return

        shutil.rmtree(stamp_dir, ignore_errors=True)
    except Exception:
        pass

st.sidebar.divider()
st.sidebar.caption("版本模式（互斥）")

mode_choice = st.sidebar.radio(
    "Version Mode",
    options=[
        "Auto new version（mismatch 才新版本）",
        "Force re-run（覆蓋重跑，不新建版本）",
    ],
    index=0,
    key="version_mode_choice",
)
force_rerun = mode_choice.startswith("Force")
auto_new_version = mode_choice.startswith("Auto")

st.sidebar.divider()
status_ph = st.sidebar.empty()


def render_sidebar_status(week_id: Optional[str], vdir: Optional[Path]) -> None:
    with status_ph.container():
        st.subheader("流程狀態（逐步更新）")
        st.write("week_id:", week_id or "（未鎖定）")
        st.write("version_dir:", str(vdir) if vdir else "（未鎖定）")

        if not vdir:
            return

        def ok(name: str) -> bool:
            try:
                return (vdir / name).exists()
            except Exception:
                return False

        st.write(("✅ " if ok("report_summary.json") else "❌ ") + "B report_summary.json")
        st.write(("✅ " if ok("report_insights.json") else "❌ ") + "C report_insights.json")
        st.write(("✅ " if ok("meeting_draft.md") else "❌ ") + "D meeting_draft.md")
        st.write(("✅ " if ok("workflow_state_draft.json") else "❌ ") + "D workflow_state_draft.json")
        st.write(("✅ " if ok("consultant_notes.json") else "❌ ") + "E consultant_notes.json")
        st.write(("✅ " if ok("meeting.md") else "❌ ") + "F meeting.md")
        st.write(("✅ " if ok("workflow_state.json") else "❌ ") + "F workflow_state.json")

        ps = read_json_if_exists(vdir / "pipeline_state.json")
        if ps:
            st.caption(f"last_completed_step: {ps.get('last_completed_step')}｜mode: {ps.get('last_mode')}")


# =========================
# Session lock
# =========================
if "locked_week_id" not in st.session_state:
    st.session_state["locked_week_id"] = None
if "locked_fp" not in st.session_state:
    st.session_state["locked_fp"] = None
if "locked_vdir" not in st.session_state:
    st.session_state["locked_vdir"] = None


def reset_session_lock() -> None:
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


if st.sidebar.button("Reset（清除 session lock，不刪 history）", key="btn_reset"):
    reset_session_lock()
    st.rerun()


# =========================
# Step A｜Upload & Preview
# =========================
st.divider()
with st.expander("Step A｜上傳檔案 + 預覽（必做）", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        meta_adset_file = st.file_uploader("Meta Adset CSV（廣告組合層）", type=["csv"], key="uploader_meta_adset")
    with c2:
        meta_ads_file = st.file_uploader("Meta Ads CSV（廣告層）", type=["csv"], key="uploader_meta_ads")
    with c3:
        web_excel_file = st.file_uploader("官網 Excel（BVshop/後台匯出）", type=["xlsx", "xls"], key="uploader_web_excel")

    can_run = True
    missing: List[str] = []
    if meta_adset_file is None:
        missing.append("Meta Adset CSV")
    if meta_ads_file is None:
        missing.append("Meta Ads CSV")
    if web_excel_file is None:
        missing.append("官網 Excel")

    if missing:
        can_run = False
        st.warning("請先上傳缺少的檔案：" + "、".join(missing))
    else:
        try:
            adset_df = read_csv(meta_adset_file)
            ads_df = read_csv(meta_ads_file)
        except Exception as e:
            can_run = False
            st.error(f"讀取 Meta CSV 失敗：{e}")

        if can_run:
            try:
                xls = pd.ExcelFile(web_excel_file)
                sheet = xls.sheet_names[0]
                web_df = pd.read_excel(xls, sheet_name=sheet)
            except Exception as e:
                can_run = False
                st.error(f"讀取官網 Excel 失敗：{e}")

        if can_run:
            st.success("✅ 檔案讀取成功（可進入一鍵流程）")
            t1, t2, t3 = st.tabs(["Meta Adset 預覽", "Meta Ads 預覽", "官網 Excel 預覽"])
            with t1:
                preview_df(adset_df, "Meta Adset（廣告組合層）")
            with t2:
                preview_df(ads_df, "Meta Ads（廣告層）")
            with t3:
                preview_df(web_df, "官網資料（第一個工作表）")


# =========================
# Manual inputs（每週人工快照）
# =========================
with st.expander("Inputs 快照（每週人工填一次｜補 Meta 匯出缺欄位）", expanded=False):
    default_manual = st.session_state.get("manual_inputs") or {}
    colm1, colm2, colm3 = st.columns(3)
    with colm1:
        buying_type = st.selectbox(
            "Buying type",
            options=["", "AUCTION", "RESERVATION", "MIXED", "UNKNOWN"],
            index=(
                ["", "AUCTION", "RESERVATION", "MIXED", "UNKNOWN"].index(default_manual.get("buying_type", ""))
                if default_manual.get("buying_type", "") in ["", "AUCTION", "RESERVATION", "MIXED", "UNKNOWN"]
                else 0
            ),
            key="mi_buying_type",
        )
    with colm2:
        optimization_goal = st.text_input("Optimization goal", value=str(default_manual.get("optimization_goal", "")), key="mi_optimization_goal")
    with colm3:
        billing_event = st.text_input("Billing event", value=str(default_manual.get("billing_event", "")), key="mi_billing_event")

    weekly_changes = st.text_area("本週重大調整", value=str(default_manual.get("weekly_changes", "")), height=110, key="mi_weekly_changes")
    note_for_consultants = st.text_area("給顧問/主持人的備註", value=str(default_manual.get("note_for_consultants", "")), height=110, key="mi_note_for_consultants")

    st.session_state["manual_inputs"] = {
        "schema_version": "manual_inputs.v1",
        "updated_at": now_iso(),
        "buying_type": buying_type,
        "optimization_goal": optimization_goal,
        "billing_event": billing_event,
        "weekly_changes": weekly_changes,
        "note_for_consultants": note_for_consultants,
    }
    st.caption("會寫入 inputs.json，並在 meeting.md 的「策略快照」固定輸出。")


# =========================
# Fingerprint preview
# =========================
current_fp: Optional[dict] = None
fp_code: Optional[str] = None
if can_run:
    current_fp = compute_inputs_fingerprint(meta_adset_file, meta_ads_file, web_excel_file, detail_level)
    fp_code = fp_short(current_fp)

with st.expander("防呆｜Fingerprint（deterministic version code）", expanded=False):
    if current_fp:
        st.json(current_fp)
        st.caption(f"fp short (deterministic): {fp_code}")
    else:
        st.info("請先完成 Step A 上傳後才會產生 fingerprint。")


# =========================
# Auto prev_week (week_id only)
# =========================
def load_prev_week_context(curr_week_id: str) -> dict:
    prev = get_prev_week_id(curr_week_id)
    if not prev:
        return {"prev_week_id": None, "prev_meta": None}

    ptr = read_latest_ptr(prev)
    if not ptr or "fp" not in ptr:
        return {"prev_week_id": prev, "prev_meta": None}

    prev_vdir = version_dir(prev, ptr["fp"])
    prev_ws = read_json_if_exists(prev_vdir / "workflow_state.json")
    prev_rs = read_json_if_exists(prev_vdir / "report_summary.json")
    return {
        "prev_week_id": prev,
        "prev_meta": {
            "week_id": prev,
            "fp": ptr["fp"],
            "workflow_state": prev_ws,
            "report_summary": prev_rs,
        },
    }


# =========================
# Target dir selection (week-based) — 版本邏輯（以 fp_code 當真值）
# =========================
def ensure_week_meta_dirs(week_id: str) -> None:
    (week_meta_dir(week_id) / "legacy").mkdir(parents=True, exist_ok=True)
    versions_root(week_id).mkdir(parents=True, exist_ok=True)


def detect_mismatch_vs_latest(week_id: str, fp_code_: str) -> Tuple[bool, Optional[str]]:
    """mismatch 第一真值：latest_ptr.fp 是否等於 current fp_code。"""
    ptr = read_latest_ptr(week_id)
    if not ptr or "fp" not in ptr:
        return (False, None)
    latest_fp = ptr["fp"]
    return (latest_fp != fp_code_, latest_fp)


def choose_version_dir_for_run(report_summary: dict, fp_code_: str) -> Tuple[str, Path]:
    """
    回傳： (resolved_fp_code, vdir)

    ✅ 語意（可驗收）：
    - Force re-run：
        * 永遠覆蓋「本次 fp_code」對應資料夾（若不存在就建立）
        * 絕不覆蓋不同 fp 的 latest（避免資料夾名與 fingerprint 失配）
    - 非 Force：
        - 若本週尚無 latest：建立本 fp
        - 若 latest.fp != 本 fp：
            * auto_new_version=True -> 建本 fp
            * 否則停下（避免用錯資料）
        - 若 latest.fp == 本 fp：用本 fp（若資料夾不存在就建立）
    """
    week_id_raw = report_summary.get("week_id") or ""
    week_id = normalize_week_id(week_id_raw)
    if not week_id:
        raise RuntimeError(f"report_summary.week_id 不合法：{week_id_raw}（需 YYYY-Www）")

    ensure_week_meta_dirs(week_id)
    write_week_info(week_id, report_summary.get("date_range") or "")

    fp_vdir = version_dir(week_id, fp_code_)
    mismatch, latest_fp = detect_mismatch_vs_latest(week_id, fp_code_)

    if force_rerun:
        fp_vdir.mkdir(parents=True, exist_ok=True)
        return (fp_code_, fp_vdir)

    if latest_fp is None:
        fp_vdir.mkdir(parents=True, exist_ok=True)
        return (fp_code_, fp_vdir)

    if mismatch:
        if auto_new_version:
            fp_vdir.mkdir(parents=True, exist_ok=True)
            return (fp_code_, fp_vdir)
        raise RuntimeError("偵測到與本週 latest.fp 不一致，且未啟用 Auto new version / Force，已停止以避免用錯資料。")

    fp_vdir.mkdir(parents=True, exist_ok=True)
    return (fp_code_, fp_vdir)


def build_inputs_snapshot(
    report_summary: dict,
    current_fp_: dict,
    fp_code_: str,
    meta_adset_file_,
    meta_ads_file_,
    web_excel_file_,
    prev_ctx: dict,
) -> dict:
    return {
        "schema_version": "inputs_snapshot.v3",
        "created_at": now_iso(),
        "week_id": report_summary.get("week_id"),
        "date_range": report_summary.get("date_range"),
        "uploaded_files": {
            "meta_adset": getattr(meta_adset_file_, "name", ""),
            "meta_ads": getattr(meta_ads_file_, "name", ""),
            "web_excel": getattr(web_excel_file_, "name", ""),
        },
        "fingerprint": current_fp_,
        "fp_short": fp_code_,
        "manual_inputs": st.session_state.get("manual_inputs") or {},
        "prev_week": {"week_id": prev_ctx.get("prev_week_id")},
    }


def rs_with_context(rs: dict, current_fp_: dict, fp_code_: str, prev_ctx: dict) -> dict:
    enriched = dict(rs or {})
    enriched["_context"] = {
        "fingerprint": current_fp_,
        "fp_short": fp_code_,
        "manual_inputs": st.session_state.get("manual_inputs") or {},
        "prev_week": prev_ctx,
        "time": {"tz": "Asia/Taipei", "now": now_iso()},
    }
    return enriched


# =========================
# Steps
# =========================
def step_exists(vdir: Path, filename: str) -> bool:
    return (vdir / filename).exists()


def load_or_session(key: str, path: Path):
    if key in st.session_state:
        return st.session_state[key]
    obj = read_json_if_exists(path)
    if obj is not None:
        st.session_state[key] = obj
    return st.session_state.get(key)


def sync_manual_inputs_to_inputs_json(vdir: Path) -> None:
    p = vdir / "inputs.json"
    if not p.exists():
        return
    obj = read_json_if_exists(p) or {}
    obj["manual_inputs"] = st.session_state.get("manual_inputs") or {}
    obj["updated_at"] = now_iso()
    write_json(p, obj)


def run_step_b(mode_label: str) -> Tuple[str, str, Path, dict]:
    if not can_run:
        raise RuntimeError("請先完成 Step A 上傳與讀取成功。")
    if not current_fp or not fp_code:
        raise RuntimeError("缺少 fingerprint（請先完成 Step A）。")

    # staging vdir: record early failures (e.g., language-drift guard) before week_id is resolved
    stage_vdir = staging_version_dir(fp_code)
    stage_vdir.mkdir(parents=True, exist_ok=True)

    cleanup_ok = False
    try:
        try:
            with st.spinner(f"{mode_label}｜Step B：deterministic KPI -> report_summary.json..."):
                rs = build_report_summary(
                    meta_adset_file.getvalue(),
                    meta_ads_file.getvalue(),
                    web_excel_file.getvalue(),
                )
        except Exception as e:
            msg = str(e)
            step_name = "B(lang_drift_error)" if ("請用中文欄位匯出" in msg or "中文欄位" in msg) else "B(preflight_error)"
            write_pipeline_state(
                stage_vdir,
                step_name,
                mode_label,
                status="error",
                error=msg,
                details=[msg],
                extra={"staging_vdir": str(stage_vdir)},
            )
            raise

            # ✅ week_id 正規化（W 補零）
            rs_week_raw = rs.get("week_id")
            rs_week_norm = normalize_week_id(rs_week_raw or "")
            if not rs_week_norm:
                raise RuntimeError(f"report_summary.week_id 不合法：{rs_week_raw}（需 YYYY-Www）")
            rs["week_id"] = rs_week_norm

            week_id = rs["week_id"]
            prev_ctx = load_prev_week_context(week_id)

            # ✅ 先決定 vdir（讓 validate 失敗也能落盤到 pipeline_state）
            resolved_fp, vdir = choose_version_dir_for_run(rs, fp_code)
            vdir.mkdir(parents=True, exist_ok=True)

            # ✅ Step B 後強制 schema validate（避免口徑漂）+ 失敗寫入 pipeline_state events
            if st.session_state.get("validate_schema", True):
                try:
                    validate_report_summary(rs)
                except SchemaValidationError as e:
                    write_pipeline_state(
                        vdir,
                        "B(validate_error)",
                        mode_label,
                        status="error",
                        error=str(e),
                        details=e.details,
                    )
                    raise
                except Exception as e:
                    write_pipeline_state(
                        vdir,
                        "B(validate_error)",
                        mode_label,
                        status="error",
                        error=str(e),
                        details=[str(e)],
                    )
                    raise

            # inputs + report_summary
            inputs = build_inputs_snapshot(rs, current_fp, resolved_fp, meta_adset_file, meta_ads_file, web_excel_file, prev_ctx)
            write_json(vdir / "inputs.json", inputs)
            write_json(vdir / "report_summary.json", rs)

            # lock
            st.session_state["locked_week_id"] = week_id
            st.session_state["locked_fp"] = resolved_fp
            st.session_state["locked_vdir"] = str(vdir)
            st.session_state["report_summary"] = rs

            # 更新 latest 指標 -> 指向「本次 fp_code」（相對路徑存 latest.json）
            write_latest_ptr(week_id, resolved_fp)

            write_pipeline_state(vdir, "B", mode_label)
            render_sidebar_status(week_id, vdir)

        cleanup_ok = True
        return week_id, resolved_fp, vdir, prev_ctx
    finally:
        if cleanup_ok:
            _cleanup_staging_on_success(stage_vdir)

def run_step_c(mode_label: str, week_id: str, vdir: Path, prev_ctx: dict, resolved_fp: str) -> None:
    sync_manual_inputs_to_inputs_json(vdir)

    if (not force_rerun) and step_exists(vdir, "report_insights.json"):
        ri = load_or_session("report_insights", vdir / "report_insights.json")
        if ri:
            write_pipeline_state(vdir, "C1(skip)", mode_label)
            render_sidebar_status(week_id, vdir)
            return

    with st.spinner(f"{mode_label}｜Step C1：LLM 洞察 -> report_insights.json..."):
        rs = load_or_session("report_summary", vdir / "report_summary.json")
        if not rs:
            raise RuntimeError("缺少 report_summary（Step B 未成功）")
        insights = generate_report_insights(rs_with_context(rs, current_fp, resolved_fp, prev_ctx))  # type: ignore[arg-type]
        write_json(vdir / "report_insights.json", insights)
        st.session_state["report_insights"] = insights

    write_pipeline_state(vdir, "C1", mode_label)
    render_sidebar_status(week_id, vdir)


def run_step_d_draft(mode_label: str, week_id: str, vdir: Path, prev_ctx: dict, resolved_fp: str) -> None:
    sync_manual_inputs_to_inputs_json(vdir)

    if (not force_rerun) and step_exists(vdir, "meeting_draft.md") and step_exists(vdir, "workflow_state_draft.json"):
        wsd = read_json_if_exists(vdir / "workflow_state_draft.json")
        if wsd:
            st.session_state["workflow_state_draft"] = wsd
            mdd = read_text_if_exists(vdir / "meeting_draft.md")
            if mdd:
                st.session_state["meeting_md_draft"] = mdd
            write_pipeline_state(vdir, "D(draft)(skip)", mode_label)
            render_sidebar_status(week_id, vdir)
            return

    with st.spinner(f"{mode_label}｜Step D：Moderator draft -> meeting_draft/workflow_state_draft..."):
        rs = load_or_session("report_summary", vdir / "report_summary.json")
        ri = load_or_session("report_insights", vdir / "report_insights.json")
        if not rs or not ri:
            raise RuntimeError("缺少 report_summary/report_insights（Step B/C 未成功）")

        rs_ctx = rs_with_context(rs, current_fp, resolved_fp, prev_ctx)  # type: ignore[arg-type]
        ws = build_workflow_state(rs_ctx, ri)
        md = build_meeting_markdown(ws, rs_ctx, ri)

        write_text(vdir / "meeting_draft.md", md)
        write_json(vdir / "workflow_state_draft.json", ws)

        st.session_state["workflow_state_draft"] = ws
        st.session_state["meeting_md_draft"] = md

    write_pipeline_state(vdir, "D(draft)", mode_label)
    render_sidebar_status(week_id, vdir)


def run_step_e(mode_label: str, week_id: str, vdir: Path, prev_ctx: dict, resolved_fp: str) -> None:
    sync_manual_inputs_to_inputs_json(vdir)

    if (not force_rerun) and step_exists(vdir, "consultant_notes.json"):
        cn = read_json_if_exists(vdir / "consultant_notes.json")
        if cn:
            st.session_state["consultant_notes"] = cn
            write_pipeline_state(vdir, "E(skip)", mode_label)
            render_sidebar_status(week_id, vdir)
            return

    with st.spinner(f"{mode_label}｜Step E：三顧問 -> consultant_notes.json..."):
        rs = load_or_session("report_summary", vdir / "report_summary.json")
        ri = load_or_session("report_insights", vdir / "report_insights.json")
        if not rs or not ri:
            raise RuntimeError("缺少 report_summary/report_insights（Step B/C 未成功）")

        rs_ctx = rs_with_context(rs, current_fp, resolved_fp, prev_ctx)  # type: ignore[arg-type]
        cn = run_three_consultants(rs_ctx, ri)
        write_json(vdir / "consultant_notes.json", cn)
        st.session_state["consultant_notes"] = cn

    write_pipeline_state(vdir, "E", mode_label)
    render_sidebar_status(week_id, vdir)


def run_step_f_final(mode_label: str, week_id: str, vdir: Path, prev_ctx: dict, resolved_fp: str) -> None:
    sync_manual_inputs_to_inputs_json(vdir)

    if (not force_rerun) and step_exists(vdir, "meeting.md") and step_exists(vdir, "workflow_state.json"):
        ws = read_json_if_exists(vdir / "workflow_state.json")
        if ws:
            st.session_state["workflow_state"] = ws
            md = read_text_if_exists(vdir / "meeting.md")
            if md:
                st.session_state["meeting_md"] = md
            write_pipeline_state(vdir, "F(final)(skip)", mode_label)
            render_sidebar_status(week_id, vdir)
            return

    with st.spinner(f"{mode_label}｜Step F：Moderator final -> meeting/workflow_state..."):
        rs = load_or_session("report_summary", vdir / "report_summary.json")
        ri = load_or_session("report_insights", vdir / "report_insights.json")
        cn = load_or_session("consultant_notes", vdir / "consultant_notes.json")
        if not rs or not ri or not cn:
            raise RuntimeError("缺少 report_summary/report_insights/consultant_notes（Step B/C/E 未成功）")

        rs_ctx = rs_with_context(rs, current_fp, resolved_fp, prev_ctx)  # type: ignore[arg-type]
        ws = build_workflow_state(rs_ctx, ri, consultant_notes=cn)
        md = build_meeting_markdown(ws, rs_ctx, ri)
        write_artifacts(vdir, md, ws)

        st.session_state["workflow_state"] = ws
        st.session_state["meeting_md"] = md

    write_pipeline_state(vdir, "F(final)", mode_label)
    render_sidebar_status(week_id, vdir)


# =========================
# Legacy migration (non-destructive) — 原封不動保留
# =========================
LEGACY_RE = re.compile(r"^(?P<wk>[^_]+)_(?P<dr>.+?)(?:_fp-[0-9a-f]{8})?$")


def is_legacy_folder(name: str) -> bool:
    return bool(LEGACY_RE.match(name))


def migrate_one_legacy_dir(src: Path) -> Optional[dict]:
    rs = read_json_if_exists(src / "report_summary.json")
    if not rs:
        return None

    wk_norm = normalize_week_id(rs.get("week_id") or "")
    if not wk_norm:
        return None
    rs["week_id"] = wk_norm

    ensure_week_meta_dirs(wk_norm)

    legacy_dst = week_meta_dir(wk_norm) / "legacy" / src.name
    legacy_dst.mkdir(parents=True, exist_ok=True)

    inp = read_json_if_exists(src / "inputs.json") or {}
    saved_fp = inp.get("fingerprint")
    if isinstance(saved_fp, dict):
        code = fp_short(saved_fp)
    else:
        dumped = json.dumps(rs, ensure_ascii=False, sort_keys=True)
        code = sha256_str(dumped)[:8]

    vdst = version_dir(wk_norm, code)
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

    write_week_info(wk_norm, rs.get("date_range") or "")
    if not read_latest_ptr(wk_norm):
        write_latest_ptr(wk_norm, code)

    return {
        "src": str(src),
        "week_id": wk_norm,
        "fp": code,
        "version_dir": str(vdst),
        "legacy_dir": str(legacy_dst),
    }


with st.expander("遷移工具（不丟舊資料夾｜只複製）", expanded=False):
    st.caption(
        "掃描 history/ 下舊命名資料夾（如 2025-W49_2025-12-04_2025-12-09），"
        "複製到新結構的 legacy/ 與 versions/。不刪原資料夾。"
    )
    legacy_candidates = [p for p in HISTORY_ROOT.iterdir() if p.is_dir() and is_legacy_folder(p.name)]
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
                res = migrate_one_legacy_dir(src)
                if res:
                    mig_map["items"].append(res)
                    migrated += 1
                else:
                    skipped += 1

            mig_map["updated_at"] = now_iso()
            write_json(HISTORY_ROOT / "MIGRATION_MAP.json", mig_map)
            st.success(f"遷移完成：migrated={migrated}, skipped={skipped}")
            st.json(mig_map)


# initial sidebar status (locked or not)
locked_week = st.session_state.get("locked_week_id")
locked_vdir = st.session_state.get("locked_vdir")
render_sidebar_status(locked_week, Path(locked_vdir) if locked_vdir else None)


# =========================
# One-click buttons
# =========================
st.divider()
st.subheader("一鍵流程（兩顆按鈕）")

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    btn_quick = st.button("⚡ 一鍵快篩（B→C→D draft）", type="secondary", disabled=not can_run)
with col2:
    btn_final = st.button("🚀 一鍵最終（B→C→E→F final）", type="primary", disabled=not can_run)
with col3:
    st.write("prev_week 只靠 week_id 排序（YYYY-Www），不使用 date_range 推導。")

if btn_quick:
    mode = "oneclick_quick_BCD"
    try:
        week_id, resolved_fp, vdir, prev_ctx = run_step_b(mode)
        restore_from_version_dir(vdir)

        run_step_c(mode, week_id, vdir, prev_ctx, resolved_fp)
        restore_from_version_dir(vdir)

        run_step_d_draft(mode, week_id, vdir, prev_ctx, resolved_fp)
        restore_from_version_dir(vdir)

        st.success("✅ 一鍵快篩完成（B→C→D draft）")
        artifacts_panel(vdir)
    except Exception as e:
        st.error(f"一鍵快篩中斷：{e}")
        st.stop()

if btn_final:
    mode = "oneclick_final_BCEF"
    try:
        week_id, resolved_fp, vdir, prev_ctx = run_step_b(mode)
        restore_from_version_dir(vdir)

        run_step_c(mode, week_id, vdir, prev_ctx, resolved_fp)
        restore_from_version_dir(vdir)

        run_step_e(mode, week_id, vdir, prev_ctx, resolved_fp)
        restore_from_version_dir(vdir)

        run_step_f_final(mode, week_id, vdir, prev_ctx, resolved_fp)
        restore_from_version_dir(vdir)

        st.success("✅ 一鍵最終完成（B→C→E→F final）")
        artifacts_panel(vdir)
    except Exception as e:
        st.error(f"一鍵最終中斷：{e}")
        st.stop()


# =========================
# Quick view
# =========================
st.divider()
st.subheader("快速檢視（當前 session）")

if st.session_state.get("locked_week_id") and st.session_state.get("locked_vdir"):
    st.write("🔒 Locked week:", st.session_state["locked_week_id"])
    st.write("🔒 Locked version dir:", st.session_state["locked_vdir"])

    prev = get_prev_week_id(st.session_state["locked_week_id"])
    st.caption(f"Auto prev_week_id: {prev or '（找不到）'}")

colv1, colv2 = st.columns(2)
with colv1:
    st.markdown("### Draft（快篩）")
    if "meeting_md_draft" in st.session_state:
        st.text_area("meeting_draft.md（預覽）", st.session_state["meeting_md_draft"], height=220)
    if "workflow_state_draft" in st.session_state:
        st.json(st.session_state["workflow_state_draft"])

with colv2:
    st.markdown("### Final（最終）")
    if "meeting_md" in st.session_state:
        st.text_area("meeting.md（預覽）", st.session_state["meeting_md"], height=220)
    if "workflow_state" in st.session_state:
        st.json(st.session_state["workflow_state"])

st.info(
    "行為規則：\n"
    "1) 主鍵=week_id（YYYY-Www，W 自動補零）。\n"
    "2) 版本=fp-xxxxxxxx（只由檔案 sha/size + detail_level 決定）。\n"
    "3) Force re-run：永遠覆蓋『本次 fp』對應資料夾（若不存在就建立），不覆蓋其他 fp。\n"
    "4) Auto new version：只有 mismatch（latest.fp != 本次 fp）才新建版本。\n"
    "5) prev_week：只靠 week_id 排序找上一週，完全不靠 date_range 字串。\n"
    "6) latest.json 存相對路徑 rel_path=versions/fp-xxxx，避免搬環境不穩。\n"
    "7) 時間欄位固定用台北時間（Asia/Taipei）。"
)
