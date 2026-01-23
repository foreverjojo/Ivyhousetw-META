#!/usr/bin/env python3
"""一鍵自檢入口（不修改系統）

用途：
- 新電腦 / 新環境 / Dev Container 恢復後，用「一行指令」驗證 repo 可工作：
  1) restore readiness（verify_restore_state）
  2) ruff lint + format check
  3) pytest（tests/）

使用方式：
  python scripts/portable/self_check.py --strict
  python scripts/portable/self_check.py --strict --json

可選：
  python scripts/portable/self_check.py --skip-tests

Exit code：
- 0: 全部通過
- 1: 有檢查失敗
- 2: 執行時錯誤（例外/參數/非預期狀況）
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def _tail(text: str, max_lines: int = 40) -> str:
    lines = (text or "").splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[-max_lines:])


def _run(cmd: list[str]) -> dict[str, Any]:
    started = time.monotonic()
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    duration_ms = int((time.monotonic() - started) * 1000)
    return {
        "command": cmd,
        "exit_code": proc.returncode,
        "duration_ms": duration_ms,
        "stdout_tail": _tail(proc.stdout or ""),
        "stderr_tail": _tail(proc.stderr or ""),
    }


def _is_module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _print_install_hint() -> None:
    print("\n💡 安裝開發/測試依賴（擇一）：")
    print("- pip：pip install -r requirements.txt -r requirements-dev.txt")
    print("- uv ：uv sync --extra dev  （若 repo 已提供 uv.lock）")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict", action="store_true", help="使用 strict 模式（restore 檢查更嚴格）"
    )
    parser.add_argument("--json", action="store_true", help="輸出 JSON 結果")
    parser.add_argument("--skip-restore", action="store_true", help="跳過 restore readiness 檢查")
    parser.add_argument("--skip-lint", action="store_true", help="跳過 ruff lint")
    parser.add_argument("--skip-format", action="store_true", help="跳過 ruff format --check")
    parser.add_argument("--skip-tests", action="store_true", help="跳過 pytest")
    args = parser.parse_args(argv)

    steps: list[dict[str, Any]] = []

    try:
        # 1) Restore readiness
        if not args.skip_restore:
            cmd = [
                sys.executable,
                str(REPO_ROOT / "scripts" / "portable" / "verify_restore_state.py"),
            ]
            if args.strict:
                cmd.append("--strict")
            r = _run(cmd)
            r.update(
                {"name": "restore_readiness", "status": "pass" if r["exit_code"] == 0 else "fail"}
            )
            steps.append(r)

        # 2) Ruff checks
        need_ruff = not args.skip_lint or not args.skip_format
        if need_ruff and not _is_module_available("ruff"):
            steps.append(
                {
                    "name": "ruff_available",
                    "status": "fail",
                    "exit_code": 1,
                    "command": [sys.executable, "-m", "ruff"],
                    "stdout_tail": "",
                    "stderr_tail": "找不到 ruff（dev dependencies 未安裝）",
                    "duration_ms": 0,
                }
            )

        if not args.skip_lint and _is_module_available("ruff"):
            cmd = [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "core",
                "utils",
                "scripts",
                "tests",
                "main.py",
                "--target-version=py311",
            ]
            r = _run(cmd)
            r.update({"name": "ruff_check", "status": "pass" if r["exit_code"] == 0 else "fail"})
            steps.append(r)

        if not args.skip_format and _is_module_available("ruff"):
            cmd = [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                "core",
                "utils",
                "scripts",
                "tests",
                "main.py",
            ]
            r = _run(cmd)
            r.update(
                {"name": "ruff_format_check", "status": "pass" if r["exit_code"] == 0 else "fail"}
            )
            steps.append(r)

        # 3) Pytest
        if not args.skip_tests and not _is_module_available("pytest"):
            steps.append(
                {
                    "name": "pytest_available",
                    "status": "fail",
                    "exit_code": 1,
                    "command": [sys.executable, "-m", "pytest"],
                    "stdout_tail": "",
                    "stderr_tail": "找不到 pytest（dev dependencies 未安裝）",
                    "duration_ms": 0,
                }
            )

        if not args.skip_tests and _is_module_available("pytest"):
            cmd = [sys.executable, "-m", "pytest", "tests", "-q"]
            r = _run(cmd)
            r.update({"name": "pytest", "status": "pass" if r["exit_code"] == 0 else "fail"})
            steps.append(r)

        overall_status = "pass" if all(s.get("status") == "pass" for s in steps) else "fail"

        result = {
            "status": overall_status,
            "repo_root": str(REPO_ROOT),
            "strict": bool(args.strict),
            "skips": {
                "restore": bool(args.skip_restore),
                "lint": bool(args.skip_lint),
                "format": bool(args.skip_format),
                "tests": bool(args.skip_tests),
            },
            "steps": steps,
        }

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("=== One-click Self Check ===")
            print(f"Repo: {REPO_ROOT}")
            print(f"Status: {overall_status}")
            for s in steps:
                name = s.get("name")
                status = s.get("status")
                ms = s.get("duration_ms")
                print(f"- {name}: {status} ({ms}ms)")
                if status != "pass":
                    err = (s.get("stderr_tail") or s.get("stdout_tail") or "").strip()
                    if err:
                        print(_tail(err, max_lines=10))

            if overall_status != "pass":
                _print_install_hint()

        return 0 if overall_status == "pass" else 1

    except Exception as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "status": "error",
                        "repo_root": str(REPO_ROOT),
                        "error": str(exc),
                        "steps": steps,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print("❌ 自檢執行時發生非預期錯誤")
            print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
