"""
檔案用途：Headless Debug Pipeline（不經 Streamlit UI 的完整試跑）
職責：
  - 從本機資料夾讀取 Meta 報表（adset/ad）與官網銷售報表（xlsx）
  - 依序執行 Step B→C→E→F，產出與 UI 相同的 artifacts（report_summary/report_insights/consultant_notes/workflow_state/meeting）
  - 在 Terminal 印出可觀測資訊（每步驟耗時、顧問回傳錯誤/JSON 解析狀態）
注意事項：
  - 需要先設定 OPENAI_API_KEY（或 OPENROUTER_API_KEY）才能跑 Step C/E/F
  - 建議用專案 venv 執行：`.\\.venv\\Scripts\\python.exe scripts\\debug_pipeline.py --input-dir examples\\meta`
"""

from __future__ import annotations

import argparse
import io
import sys
import time
from dataclasses import dataclass
from pathlib import Path

"""
執行提示：
- 本檔案位於 scripts/ 之下，直接 `python scripts/debug_pipeline.py` 時，
  Python 預設 sys.path[0] 會是 scripts/，導致 `import scripts.xxx` 找不到。
  因此我們在此將專案根目錄加入 sys.path，確保 headless 模式可用。
"""

# 確保可從專案根目錄 import（避免 ModuleNotFoundError: scripts）
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# 注意：這些 imports 刻意放在 sys.path 調整之後（避免 ModuleNotFoundError）
from scripts.consultants import generate_consultant_notes  # noqa: E402
from scripts.kpi_calc import build_report_summary  # noqa: E402
from scripts.llm_insights import generate_report_insights  # noqa: E402
from utils import (  # noqa: E402
    compute_inputs_fingerprint,
    ensure_week_meta_dirs,
    fp_short,
    version_dir,
    write_json,
    write_text,
)


def _try_load_env() -> None:
    """
    嘗試載入 ifp.env/.env 與 Secret Manager（若專案有啟用）。
    注意：若缺少依賴（例如 python-dotenv）或模組不存在，會安靜略過。
    """
    try:
        from core.env_loader import load_environment_variables

        load_environment_variables()
    except Exception:
        return


@dataclass(frozen=True)
class InputFiles:
    meta_adset: Path
    meta_ads: Path
    web_excel: Path


def _now_stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _read_bytes(p: Path) -> bytes:
    return p.read_bytes()


def _discover_input_files(input_dir: Path) -> InputFiles:
    """
    依檔名習慣自動找：
      - meta_adset: 含 'adset' 的 csv
      - meta_ads: 含 'ad' 但不含 'adset' 的 csv
      - web_excel: xlsx（允許中文檔名）
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"找不到資料夾：{input_dir}")

    csvs = sorted([p for p in input_dir.glob("*.csv") if p.is_file()])
    xlsxs = sorted([p for p in input_dir.glob("*.xlsx") if p.is_file()])

    if not csvs:
        raise FileNotFoundError(f"在 {input_dir} 找不到任何 .csv")
    if not xlsxs:
        raise FileNotFoundError(f"在 {input_dir} 找不到任何 .xlsx")

    def norm(s: str) -> str:
        return s.lower().replace(" ", "").replace("-", "_")

    adset = None
    ads = None
    for p in csvs:
        name = norm(p.name)
        if "adset" in name or "ad_set" in name:
            adset = adset or p
        elif "meta_ad_" in name or (("ad" in name or "ads" in name) and "adset" not in name):
            ads = ads or p

    # fallback：若判斷不出，採「較短視為 adset」的保守策略
    if adset is None or ads is None:
        if len(csvs) >= 2:
            a, b = sorted(csvs, key=lambda x: x.stat().st_size)[:2]
            adset = adset or a
            ads = ads or b
        else:
            raise FileNotFoundError("需要至少 2 個 csv（meta adset + meta ad）")

    web = xlsxs[0]
    return InputFiles(meta_adset=adset, meta_ads=ads, web_excel=web)


def _mk_debug_history_root() -> Path:
    """
    debug run 輸出根目錄：history/_debug_runs/<timestamp>
    其下仍維持 week/meta/versions/fp-xxxx 的結構，方便複用 renderer/檢視器。
    """
    root = Path("history") / "_debug_runs" / _now_stamp()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_inputs_json(vdir: Path, fp_code: str, files: InputFiles) -> None:
    write_json(
        vdir / "inputs.json",
        {
            "platform": "Meta",
            "fp_code": fp_code,
            "files": {
                "meta_adset": files.meta_adset.name,
                "meta_ad": files.meta_ads.name,
                "web_excel": files.web_excel.name,
            },
            "manual_inputs": {
                "schema_version": "manual_inputs.v1",
                "updated_at": "",
                "buying_type": "",
                "optimization_goal": "",
                "billing_event": "",
                "weekly_changes": "",
                "note_for_consultants": "",
            },
        },
    )


def _print_step(title: str) -> None:
    print(f"\n=== {title} ===", flush=True)


def _summarize_consultants(cn: dict) -> None:
    for key in ["consultant_A", "consultant_B", "consultant_C"]:
        c = cn.get(key)
        if isinstance(c, dict) and c.get("error"):
            print(f"- {key}: ERROR: {c.get('error')}")
        elif isinstance(c, dict):
            # 嘗試找 1~2 個可讀欄位，避免滿版輸出
            summary = None
            for k in [
                "summary",
                "executive_summary",
                "creative_performance_analysis",
                "next_steps",
                "opportunities",
            ]:
                if k in c:
                    summary = c.get(k)
                    break
            if isinstance(summary, list) and summary:
                print(f"- {key}: OK: {str(summary[0])[:160]}")
            elif isinstance(summary, dict):
                print(f"- {key}: OK: {list(summary.keys())[:6]}")
            else:
                print(f"- {key}: OK")
        else:
            print(f"- {key}: (missing)")


def run_debug_pipeline(
    *,
    input_dir: Path,
    detail_level: str,
    model_insights: str | None,
    model_a: str | None,
    model_b: str | None,
    model_c: str | None,
    model_moderator: str | None,
) -> tuple[Path, str]:
    files = _discover_input_files(input_dir)
    print("Input files:")
    print(f"- meta_adset: {files.meta_adset}")
    print(f"- meta_ads:   {files.meta_ads}")
    print(f"- web_excel:  {files.web_excel}")

    meta_adset_b = _read_bytes(files.meta_adset)
    meta_ads_b = _read_bytes(files.meta_ads)
    web_excel_b = _read_bytes(files.web_excel)

    # 計算 fingerprint（對齊 UI 的版本機制）
    fp = compute_inputs_fingerprint(
        io.BytesIO(meta_adset_b), io.BytesIO(meta_ads_b), io.BytesIO(web_excel_b), detail_level
    )
    fp_code = fp_short(fp)

    debug_root = _mk_debug_history_root()

    _print_step("Step B：KPI 計算")
    t0 = time.time()
    report_summary = build_report_summary(meta_adset_b, meta_ads_b, web_excel_b)
    t1 = time.time()
    print(
        f"week_id={report_summary.get('week_id')} date_range={report_summary.get('date_range')} ({t1 - t0:.1f}s)"
    )

    week_id = str(report_summary.get("week_id") or "").strip()
    if not week_id:
        raise RuntimeError("Step B 未取得 week_id（請檢查 Meta CSV 的日期欄位）")

    ensure_week_meta_dirs(week_id, debug_root)
    vdir = version_dir(week_id, fp_code, debug_root)
    vdir.mkdir(parents=True, exist_ok=True)

    _write_inputs_json(vdir, fp_code, files)
    write_json(vdir / "report_summary.json", report_summary)

    _print_step("Step C：LLM 洞察")
    t0 = time.time()
    if model_insights:
        report_insights = generate_report_insights(
            report_summary, model=model_insights, version_fp=vdir.name
        )
    else:
        report_insights = generate_report_insights(report_summary, version_fp=vdir.name)

    # generate_report_insights 可能回傳 (out, usage)（當 return_usage=True 時）；這裡強制只取 out
    if isinstance(report_insights, tuple):
        report_insights = report_insights[0]
    t1 = time.time()
    write_json(vdir / "report_insights.json", report_insights)
    print(f"insights_version={report_insights.get('insights_version')} ({t1 - t0:.1f}s)")
    if isinstance(report_insights, dict) and report_insights.get("error"):
        print(f"[WARN] Step C JSON 解析失敗：{report_insights.get('error')}")

    _print_step("Step E：三顧問")

    def cb(role: str, model: str) -> None:
        print(f"[{role}] start model={model}", flush=True)

    t0 = time.time()
    consultant_notes = generate_consultant_notes(
        report_summary,
        report_insights,
        model_a=model_a,
        model_b=model_b,
        model_c=model_c,
        status_callback=cb,
        version_fp=vdir.name,
    )
    t1 = time.time()
    write_json(vdir / "consultant_notes.json", consultant_notes)
    print(f"consultants_version={consultant_notes.get('consultants_version')} ({t1 - t0:.1f}s)")
    _summarize_consultants(consultant_notes)

    _print_step("Step F：Moderator（workflow_state + meeting.md）")
    try:
        from scripts.moderator import build_workflow_state
        from scripts.moderator_meeting import build_meeting_markdown
    except ModuleNotFoundError as e:
        raise RuntimeError(
            f"匯入 scripts.moderator 失敗：{e}\n"
            "這通常代表你沒有使用專案 venv 或依賴未安裝（例如 jsonschema）。\n"
            "請先執行：pip install -r requirements.txt（或用 venv python 執行本腳本）。"
        ) from e

    t0 = time.time()
    ws = build_workflow_state(
        report_summary,
        report_insights,
        consultant_notes=consultant_notes,
        model=model_moderator,
        step="F",
        version_fp=vdir.name,
    )
    md = build_meeting_markdown(ws, report_summary, report_insights)
    t1 = time.time()

    write_json(vdir / "workflow_state.json", ws)
    write_text(vdir / "meeting.md", md)
    print(f"workflow_state.schema_version={ws.get('schema_version')} ({t1 - t0:.1f}s)")

    # 額外輸出 quick pointers
    print("\nArtifacts:")
    for name in [
        "inputs.json",
        "report_summary.json",
        "report_insights.json",
        "consultant_notes.json",
        "workflow_state.json",
        "meeting.md",
    ]:
        print(f"- {vdir / name}")

    return vdir, week_id


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        prog="debug_pipeline",
        description="Headless Debug Pipeline：從資料夾讀檔，跑 B→C→E→F 產出完整報告 artifacts。",
    )
    p.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="輸入資料夾（包含 meta_adset.csv、meta_ad.csv、官網銷售報表.xlsx）",
    )
    p.add_argument(
        "--detail-level",
        type=str,
        default="default",
        help="輸入指紋 detail_level（預設 default；只影響 fingerprint）",
    )
    p.add_argument(
        "--model-insights", type=str, default=None, help="覆寫 MODEL_INSIGHTS（例：openai/gpt-5.2）"
    )
    p.add_argument("--model-a", type=str, default=None, help="覆寫 MODEL_CONSULTANT_A")
    p.add_argument("--model-b", type=str, default=None, help="覆寫 MODEL_CONSULTANT_B")
    p.add_argument("--model-c", type=str, default=None, help="覆寫 MODEL_CONSULTANT_C")
    p.add_argument("--model-moderator", type=str, default=None, help="覆寫 MODEL_MODERATOR")

    args = p.parse_args(argv)

    try:
        _try_load_env()
        run_debug_pipeline(
            input_dir=args.input_dir,
            detail_level=args.detail_level,
            model_insights=args.model_insights,
            model_a=args.model_a,
            model_b=args.model_b,
            model_c=args.model_c,
            model_moderator=args.model_moderator,
        )
        return 0
    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
