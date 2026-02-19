#!/usr/bin/env python3
"""檔案用途：在 Engineer 注入前做一鍵 preflight，檢查 Proposed API 與 SendText Bridge 健康度。"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _load_latest_proposed_api(debug_file: Path) -> dict[str, Any]:
    if not debug_file.exists():
        return {
            "ok": False,
            "reason": "monitor_debug.jsonl_not_found",
            "path": str(debug_file),
            "value": None,
            "ts": None,
        }

    lines = debug_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        if obj.get("type") != "proposed_api":
            continue

        value = bool(obj.get("onDidWriteTerminalData", False))
        return {
            "ok": value,
            "reason": "ok" if value else "proposed_api_false",
            "path": str(debug_file),
            "value": value,
            "ts": obj.get("ts"),
        }

    return {
        "ok": False,
        "reason": "no_proposed_api_event_found",
        "path": str(debug_file),
        "value": None,
        "ts": None,
    }


def _check_bridge_healthz(healthz_url: str, timeout_sec: float) -> dict[str, Any]:
    try:
        req = urllib.request.Request(healthz_url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            payload: dict[str, Any]
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = {"raw": body}

            status = str(payload.get("status", "")).lower()
            ok = status == "ok"
            return {
                "ok": ok,
                "reason": "ok" if ok else "unexpected_healthz_payload",
                "url": healthz_url,
                "http_status": resp.status,
                "payload": payload,
            }
    except urllib.error.URLError as exc:
        return {
            "ok": False,
            "reason": "bridge_unreachable",
            "url": healthz_url,
            "error": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "reason": "bridge_healthz_error",
            "url": healthz_url,
            "error": str(exc),
        }


def _check_bridge_token(token_file: Path) -> dict[str, Any]:
    if not token_file.exists():
        return {
            "ok": False,
            "reason": "token_file_not_found",
            "path": str(token_file),
        }

    token = token_file.read_text(encoding="utf-8", errors="ignore").strip()
    if not token:
        return {
            "ok": False,
            "reason": "token_file_empty",
            "path": str(token_file),
        }

    return {
        "ok": True,
        "reason": "ok",
        "path": str(token_file),
    }


def run_preflight(
    repo_root: Path,
    require_bridge: bool,
    healthz_url: str,
    timeout_sec: float,
) -> dict[str, Any]:
    monitor_debug = repo_root / ".service" / "terminal_capture" / "monitor_debug.jsonl"
    token_file = repo_root / ".service" / "sendtext_bridge" / "token"

    proposed = _load_latest_proposed_api(monitor_debug)
    bridge_healthz = _check_bridge_healthz(healthz_url, timeout_sec)
    bridge_token = _check_bridge_token(token_file)

    checks = {
        "proposed_api_true": proposed,
        "sendtext_bridge_healthz": bridge_healthz,
        "sendtext_bridge_token": bridge_token,
    }

    failures: list[str] = []
    warnings: list[str] = []

    if not proposed["ok"]:
        failures.append("proposed_api_true")

    if require_bridge:
        if not bridge_healthz["ok"]:
            failures.append("sendtext_bridge_healthz")
        if not bridge_token["ok"]:
            failures.append("sendtext_bridge_token")
    else:
        if not bridge_healthz["ok"]:
            warnings.append("sendtext_bridge_healthz")
        if not bridge_token["ok"]:
            warnings.append("sendtext_bridge_token")

    status = "pass" if not failures else "fail"

    return {
        "status": status,
        "require_bridge": require_bridge,
        "repo_root": str(repo_root),
        "checks": checks,
        "failures": failures,
        "warnings": warnings,
        "next_steps": [
            "若 proposed_api_true 失敗：請確認 Windows 端 argv.json 已啟用 proposed API，並完整重啟 VS Code。",
            "若 sendtext_bridge_healthz 失敗：請先啟動/重載 orchestrator extension 或檢查 bridge 服務。",
            "若 sendtext_bridge_token 失敗：請確認 .service/sendtext_bridge/token 已建立且非空。",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repo 根目錄（預設：目前目錄）",
    )
    parser.add_argument(
        "--require-bridge",
        action="store_true",
        help="要求 SendText Bridge 必須健康（healthz + token）。",
    )
    parser.add_argument(
        "--healthz-url",
        default="http://127.0.0.1:8765/healthz",
        help="SendText Bridge 健康檢查 URL。",
    )
    parser.add_argument(
        "--timeout-sec",
        type=float,
        default=2.0,
        help="Bridge 健康檢查 timeout（秒）。",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="輸出 JSON。",
    )
    args = parser.parse_args()

    result = run_preflight(
        repo_root=args.repo_root.resolve(),
        require_bridge=args.require_bridge,
        healthz_url=args.healthz_url,
        timeout_sec=args.timeout_sec,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Preflight status: {result['status']}")
        print(f"require_bridge: {result['require_bridge']}")
        for key, item in result["checks"].items():
            print(f"- {key}: {'OK' if item.get('ok') else 'FAIL'} ({item.get('reason')})")

        if result["warnings"]:
            print("Warnings:")
            for w in result["warnings"]:
                print(f"  - {w}")

        if result["failures"]:
            print("Failures:")
            for f in result["failures"]:
                print(f"  - {f}")

    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
