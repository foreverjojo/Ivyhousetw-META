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
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_extensions_check() -> dict[str, Any]:
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


def check_file(path: Path) -> dict[str, Any]:
    return {"path": str(path.relative_to(REPO_ROOT)), "exists": path.exists()}


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    strict = "--strict" in argv

    required_files = [
        REPO_ROOT / "uv.lock",
        REPO_ROOT / ".devcontainer" / "Dockerfile",
        REPO_ROOT / ".devcontainer" / "devcontainer.json",
        REPO_ROOT / "scripts" / "vscode" / "install_terminal_orchestrator.sh",
        REPO_ROOT / "tools" / "vscode_terminal_orchestrator" / "package.json",
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
    post_create_command = None
    post_create_installs_dev = False
    post_create_installs_local_extension = False
    ghcr_template_post_create_command = None
    ghcr_template_installs_dev = False
    ghcr_template_installs_local_extension = False
    ghcr_template_exists = False
    ghcr_template_image = None
    ghcr_template_is_digest = False
    try:
        dc = json.loads(
            (REPO_ROOT / ".devcontainer" / "devcontainer.json").read_text(encoding="utf-8")
        )
        post_create_command = dc.get("postCreateCommand")
        if isinstance(post_create_command, str):
            post_create_installs_dev = (
                "uv sync" in post_create_command
                and "--extra dev" in post_create_command
                or "requirements-dev.txt" in post_create_command
            )
            post_create_installs_local_extension = (
                "scripts/vscode/install_terminal_orchestrator.sh" in post_create_command
            )
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

    ghcr_template_path = REPO_ROOT / ".devcontainer" / "devcontainer.ghcr.json"
    if ghcr_template_path.exists():
        ghcr_template_exists = True
        try:
            gh = json.loads(ghcr_template_path.read_text(encoding="utf-8"))
            ghcr_template_image = gh.get("image")
            ghcr_template_post_create_command = gh.get("postCreateCommand")
            if isinstance(ghcr_template_post_create_command, str):
                ghcr_template_installs_dev = (
                    "uv sync" in ghcr_template_post_create_command
                    and "--extra dev" in ghcr_template_post_create_command
                    or "requirements-dev.txt" in ghcr_template_post_create_command
                )
                ghcr_template_installs_local_extension = (
                    "scripts/vscode/install_terminal_orchestrator.sh"
                    in ghcr_template_post_create_command
                )
            if isinstance(ghcr_template_image, str) and "@sha256:" in ghcr_template_image:
                ghcr_template_is_digest = True
        except Exception:
            ghcr_template_image = None
            ghcr_template_is_digest = False

    status = "pass"
    problems: list[str] = []
    warnings: list[str] = []
    missing_required = [c for c in missing if (REPO_ROOT / c["path"]) in required_files]
    missing_optional = [c for c in missing if (REPO_ROOT / c["path"]) in optional_files]

    if missing_required:
        status = "fail"
        problems.append(f"缺少必要檔案：{len(missing_required)} 個")
    if extensions_check.get("status") != "pass":
        status = "fail"
        problems.append("extensions 清單不一致（devcontainer / .vscode / idx）")

    if not post_create_installs_dev:
        msg = "devcontainer.json 的 postCreateCommand 未明確安裝 dev 依賴（pytest/ruff）；新機器可能無法直接跑 ruff/pytest"
        if strict:
            status = "fail"
            problems.append(msg)
        else:
            warnings.append(msg)

    if not post_create_installs_local_extension:
        msg = "devcontainer.json 的 postCreateCommand 未自動安裝 local terminal orchestrator extension；開發體驗可能與現況不一致"
        if strict:
            status = "fail"
            problems.append(msg)
        else:
            warnings.append(msg)

    if ghcr_template_exists and not ghcr_template_installs_dev:
        msg = "devcontainer.ghcr.json 的 postCreateCommand 未明確安裝 dev 依賴（pytest/ruff）；full-fidelity restore 後可能無法直接跑 ruff/pytest"
        if strict:
            status = "fail"
            problems.append(msg)
        else:
            warnings.append(msg)

    if ghcr_template_exists and not ghcr_template_installs_local_extension:
        msg = "devcontainer.ghcr.json 的 postCreateCommand 未自動安裝 local terminal orchestrator extension；full-fidelity restore 後開發體驗可能不一致"
        if strict:
            status = "fail"
            problems.append(msg)
        else:
            warnings.append(msg)

    full_fidelity_ready = bool(ghcr_template_exists and ghcr_template_is_digest) or bool(
        devcontainer_mode == "image" and devcontainer_is_digest
    )

    if devcontainer_mode != "image":
        msg = "devcontainer.json 目前不是 image 模式（GHCR pinned）；容器層完全一致需切換到 pinned image"
        if strict and not full_fidelity_ready:
            status = "fail"
            problems.append(msg)
        else:
            warnings.append(msg)
    elif not devcontainer_is_digest:
        msg = "devcontainer.json 為 image 模式但未 pin digest（@sha256）；仍可能因 tag 漂移而不完全一致"
        if strict:
            status = "fail"
            problems.append(msg)
        else:
            warnings.append(msg)

    if missing_optional:
        warnings.append(
            "缺少 GHCR template（.devcontainer/devcontainer.ghcr.json）；將無法自動切換到 pinned image"
        )
    elif ghcr_template_exists and not ghcr_template_is_digest:
        msg = "GHCR template 存在但未 pin digest（@sha256）；full-fidelity 仍可能因 tag 漂移而不完全一致"
        if strict:
            status = "fail"
            problems.append(msg)
        else:
            warnings.append(msg)

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
            "postCreateCommand": post_create_command,
            "postCreate": {
                "installs_dev": post_create_installs_dev,
                "installs_local_extension": post_create_installs_local_extension,
            },
        },
        "ghcr_template": {
            "exists": ghcr_template_exists,
            "image": ghcr_template_image,
            "digest_pinned": ghcr_template_is_digest,
            "full_fidelity_ready": full_fidelity_ready,
            "postCreateCommand": ghcr_template_post_create_command,
            "postCreate": {
                "installs_dev": ghcr_template_installs_dev,
                "installs_local_extension": ghcr_template_installs_local_extension,
            },
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
