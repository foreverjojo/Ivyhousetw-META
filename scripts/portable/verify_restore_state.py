#!/usr/bin/env python3
"""
一鍵恢復狀態檢查器（不修改系統）

用途：
  - 在「新電腦」或「恢復後」快速檢查 repo 是否具備可重現的一鍵恢復條件
  - 專注於 repo 內可驗證的部分（Dev Container / workspace / extensions 清單）

使用方式：
  python scripts/portable/verify_restore_state.py
  python scripts/portable/verify_restore_state.py --json
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[2]


def run_extensions_check() -> Dict[str, Any]:
    script = REPO_ROOT / "scripts" / "portable" / "check_extensions_consistency.py"
    if not script.exists():
        return {"status": "error", "summary": "缺少 extensions 一致性檢查腳本", "path": str(script)}

    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    return {
        "status": "pass" if proc.returncode == 0 else "fail",
        "exit_code": proc.returncode,
        "stdout_tail": "\n".join((proc.stdout or "").splitlines()[-10:]),
        "stderr_tail": "\n".join((proc.stderr or "").splitlines()[-10:]),
    }


def check_file(path: Path) -> Dict[str, Any]:
    return {"path": str(path.relative_to(REPO_ROOT)), "exists": path.exists()}


def main(argv: List[str]) -> int:
    as_json = "--json" in argv
    strict = "--strict" in argv

    required_files = [
        REPO_ROOT / "uv.lock",
        REPO_ROOT / ".devcontainer" / "Dockerfile",
        REPO_ROOT / ".devcontainer" / "devcontainer.json",
        REPO_ROOT / ".vscode" / "extensions.json",
        REPO_ROOT / ".vscode" / "settings.json",
        REPO_ROOT / ".idx" / "dev.nix",
        REPO_ROOT / "scripts" / "portable" / "bootstrap_windows.ps1",
        REPO_ROOT / "scripts" / "portable" / "bootstrap.sh",
        REPO_ROOT / "scripts" / "portable" / "check_extensions_consistency.py",
        REPO_ROOT / "scripts" / "portable" / "pin_devcontainer_image.py",
    ]

    optional_files = [
        # Full-fidelity restore (GHCR pinned image) uses this as template
        REPO_ROOT / ".devcontainer" / "devcontainer.ghcr.json",
    ]

    file_checks = [check_file(p) for p in (required_files + optional_files)]
    missing = [c for c in file_checks if not c["exists"]]

    extensions_check = run_extensions_check()

    devcontainer_mode = "unknown"
    devcontainer_image = None
    devcontainer_is_digest = False
    try:
        dc = json.loads((REPO_ROOT / ".devcontainer" / "devcontainer.json").read_text(encoding="utf-8"))
        if "image" in dc:
            devcontainer_mode = "image"
            devcontainer_image = dc.get("image")
            if isinstance(devcontainer_image, str) and "@sha256:" in devcontainer_image:
                devcontainer_is_digest = True
        elif "build" in dc:
            devcontainer_mode = "build"
        else:
            devcontainer_mode = "unknown"
    except Exception:
        devcontainer_mode = "unknown"

    status = "pass"
    problems: List[str] = []
    warnings: List[str] = []
    missing_required = [c for c in missing if (REPO_ROOT / c["path"]) in required_files]
    missing_optional = [c for c in missing if (REPO_ROOT / c["path"]) in optional_files]

    if missing_required:
        status = "fail"
        problems.append(f"缺少必要檔案：{len(missing_required)} 個")
    if extensions_check.get("status") != "pass":
        status = "fail"
        problems.append("extensions 清單不一致（devcontainer / .vscode / idx）")

    if devcontainer_mode != "image":
        msg = "devcontainer.json 目前不是 image 模式（GHCR pinned）；無法保證容器層完全一致"
        if strict:
            status = "fail"
            problems.append(msg)
        else:
            warnings.append(msg)
    elif not devcontainer_is_digest:
        warnings.append("devcontainer.json 為 image 模式但未 pin digest（@sha256）；仍可能因 tag 漂移而不完全一致")
    if missing_optional:
        warnings.append("缺少 GHCR template（.devcontainer/devcontainer.ghcr.json）；將無法自動切換到 pinned image")

    result = {
        "status": status,
        "repo_root": str(REPO_ROOT),
        "problems": problems,
        "warnings": warnings,
        "files": file_checks,
        "devcontainer": {
            "mode": devcontainer_mode,
            "image": devcontainer_image,
            "digest_pinned": devcontainer_is_digest,
        },
        "extensions_consistency": extensions_check,
        "next_steps": [
            "若 extensions 不一致：執行 python scripts/portable/check_extensions_consistency.py --verbose",
            "若 uv.lock 不存在：請先在原機器產生並 commit uv.lock，再於新機器 pull",
            "若要 full-fidelity（容器層一致）：執行 python scripts/portable/pin_devcontainer_image.py（會盡量 pin digest），再 Reopen in Container",
            "新機器建議：VS Code -> Dev Containers: Reopen in Container",
        ],
    }

    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=== Restore State Check ===")
        print(f"Repo: {REPO_ROOT}")
        print(f"Status: {status}")
        if problems:
            for p in problems:
                print(f"- {p}")
        if missing:
            print("\nMissing files:")
            for c in missing_required:
                print(f"- {c['path']}")
            if missing_optional:
                print("\nOptional (recommended) missing files:")
                for c in missing_optional:
                    print(f"- {c['path']}")
        print("\nExtensions consistency:")
        print(extensions_check.get("stdout_tail", "").strip())

    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
