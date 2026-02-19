#!/usr/bin/env python3
"""同步本 repo 的 dev-team workflow/skills 到 template repo（不含 portable）

用途：
- 把本 repo 已落地的 `.agent/` 工作流與 skills 強化，快速回推到 template repo。
- 僅同步 allowlist 內的路徑（避免把 logs/plans/runtime 檔案帶過去）。

安全設計：
- 預設 dry-run（不寫入）。
- 需要明確加 `--apply` 才會覆寫/寫入檔案。

使用方式：
    python scripts/template/sync_agent_workflow_to_template.py --template-root /path/to/agent-workflow-template
    python scripts/template/sync_agent_workflow_to_template.py --template-root ../agent-workflow-template --apply

    # （選用）也同步 VS Code 周邊（local extension / 安裝腳本 / .vscode 設定 / client）
    python scripts/template/sync_agent_workflow_to_template.py --template-root ../agent-workflow-template --include-peripherals
    python scripts/template/sync_agent_workflow_to_template.py --template-root ../agent-workflow-template --include-peripherals --apply

注意：
- 此腳本不會做 git commit。
- 此腳本不會同步任何 `scripts/portable/**`（一鍵復原/自檢模組）。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_files(base: Path) -> list[Path]:
    return [p for p in base.rglob("*") if p.is_file()]


def _is_ignored(path: Path) -> bool:
    name = path.name
    if name in {".DS_Store"}:
        return True
    if name.endswith(".pyc"):
        return True
    if "__pycache__" in path.parts:
        return True
    return False


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--template-root",
        required=True,
        help="template repo 根目錄（agent-workflow-template 的工作目錄路徑）",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="實際寫入/覆寫檔案（預設為 dry-run）",
    )
    parser.add_argument(
        "--include-peripherals",
        action="store_true",
        help=(
            "同步 VS Code 周邊（tools/vscode_terminal_injector、tools/vscode_terminal_monitor、"
            "tools/vscode_terminal_orchestrator、scripts/vscode/、"
            "scripts/sendtext_bridge_client.py、.vscode/）。預設不包含。"
        ),
    )
    args = parser.parse_args(argv)

    template_root = Path(os.path.expanduser(args.template_root)).resolve()
    if not template_root.exists():
        print(f"ERROR: template_root 不存在：{template_root}")
        return 2

    # allowlist：只同步這些路徑（不含 portable）
    allow_dirs = [
        REPO_ROOT / ".agent" / "workflows",
        REPO_ROOT / ".agent" / "roles",
        REPO_ROOT / ".agent" / "skills",
        REPO_ROOT / ".agent" / "VScode_system",
        REPO_ROOT / ".agent" / "templates",
    ]
    allow_files = [
        REPO_ROOT / ".agent" / "scripts" / "setup_workflow.sh",
        REPO_ROOT / ".agent" / "scripts" / "run_codex_template.sh",
    ]

    if args.include_peripherals:
        allow_dirs.extend(
            [
                REPO_ROOT / ".vscode",
                REPO_ROOT / "tools" / "vscode_terminal_injector",
                REPO_ROOT / "tools" / "vscode_terminal_monitor",
                REPO_ROOT / "tools" / "vscode_terminal_orchestrator",
                REPO_ROOT / "scripts" / "vscode",
            ]
        )
        allow_files.extend([REPO_ROOT / "scripts" / "sendtext_bridge_client.py"])

    src_files: list[Path] = []
    for d in allow_dirs:
        if d.exists():
            src_files.extend([p for p in _iter_files(d) if not _is_ignored(p)])
    for f in allow_files:
        if f.exists() and f.is_file() and not _is_ignored(f):
            src_files.append(f)

    # 以 repo root 的相對路徑，寫到 template root 同一路徑
    planned = []
    for src in sorted(set(src_files)):
        rel = src.relative_to(REPO_ROOT)
        dst = template_root / rel
        action = "add" if not dst.exists() else "update"
        same = False
        if dst.exists() and dst.is_file():
            try:
                same = _sha256(src) == _sha256(dst)
            except Exception:
                same = False
        planned.append({"action": action, "same": same, "src": src, "dst": dst, "rel": rel})

    to_write = [p for p in planned if not p["same"]]

    print("=== Sync .agent workflow/skills to template (no portable) ===")
    print(f"Source repo:   {REPO_ROOT}")
    print(f"Template repo: {template_root}")
    print(f"Total files (scanned): {len(planned)}")
    print(f"Files to write:        {len(to_write)}")

    if not to_write:
        print("✅ 已同步（內容一致），無需更新")
        return 0

    # 顯示前幾個差異，避免輸出過長
    preview = to_write[:20]
    for item in preview:
        print(f"- {item['action']}: {item['rel']}")
    if len(to_write) > len(preview):
        print(f"  ...（省略 {len(to_write) - len(preview)} 個）")

    if not args.apply:
        print("\n（dry-run）未寫入任何檔案。若要套用，請加上 --apply")
        return 0

    for item in to_write:
        _copy_file(item["src"], item["dst"])

    print("\n✅ 已套用同步（請到 template repo 內自行檢查、跑測試、再 commit/PR）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
