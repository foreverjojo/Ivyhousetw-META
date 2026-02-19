#!/usr/bin/env python3
"""SendText Bridge Python client (localhost-only helper).

This client talks to the local VS Code extension "IvyHouse Terminal Orchestrator"
SendText Bridge HTTP server.

Token source (priority):
1) CLI flag: --token
2) Environment variable: IVY_SENDTEXT_BRIDGE_TOKEN
3) Token file: .service/sendtext_bridge/token

Examples:
  python scripts/sendtext_bridge_client.py healthz
  python scripts/sendtext_bridge_client.py send --terminal-kind codex --text "hi" --submit
  python scripts/sendtext_bridge_client.py workflow-start --plan-id Idx-025 --scope workflow
  python scripts/sendtext_bridge_client.py workflow-status
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_TOKEN_FILE_REL = ".service/sendtext_bridge/token"


@dataclass(frozen=True)
class BridgeConfig:
    host: str
    port: int
    token: str | None


def _read_token_file(path: Path) -> str | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    except OSError:
        return None
    return raw or None


def _load_token(token_arg: str | None, token_file_rel: str) -> str | None:
    if token_arg:
        return token_arg

    env_token = os.environ.get("IVY_SENDTEXT_BRIDGE_TOKEN")
    if env_token:
        return env_token.strip() or None

    token_file_abs = (REPO_ROOT / token_file_rel).resolve()
    return _read_token_file(token_file_abs)


def _build_cfg(args: argparse.Namespace) -> BridgeConfig:
    host = str(args.host or DEFAULT_HOST)
    port = int(args.port or DEFAULT_PORT)
    token = _load_token(args.token, args.token_file)
    return BridgeConfig(host=host, port=port, token=token)


def _request_json(
    cfg: BridgeConfig,
    method: str,
    path: str,
    body: dict[str, Any] | None,
    require_token: bool,
) -> tuple[int, dict[str, Any]]:
    url = f"http://{cfg.host}:{cfg.port}{path}"

    if require_token and not cfg.token:
        raise RuntimeError(
            "missing_token: set --token, env IVY_SENDTEXT_BRIDGE_TOKEN, or .service/sendtext_bridge/token"
        )

    data: bytes | None
    headers = {
        "Accept": "application/json",
        "User-Agent": "ivyhouse-sendtext-bridge-client/0.1",
    }

    if body is None:
        data = None
    else:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    if cfg.token:
        headers["Authorization"] = f"Bearer {cfg.token}"

    req = urllib.request.Request(url=url, method=method, data=data, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"raw": raw}
            return int(resp.status), payload
    except urllib.error.HTTPError as e:
        raw = None
        try:
            raw = e.read().decode("utf-8")
        except Exception:
            raw = None

        payload: dict[str, Any]
        if raw:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"error": "http_error", "status": e.code, "raw": raw}
        else:
            payload = {"error": "http_error", "status": e.code}
        return int(e.code), payload
    except urllib.error.URLError as e:
        raise RuntimeError(f"connection_error: {e}") from e


def _print_result(status: int, payload: dict[str, Any]) -> int:
    out = {"http_status": status, "response": payload}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if 200 <= status < 300 else 2


def cmd_healthz(args: argparse.Namespace) -> int:
    cfg = _build_cfg(args)
    status, payload = _request_json(cfg, "GET", "/healthz", None, require_token=False)
    return _print_result(status, payload)


def cmd_send(args: argparse.Namespace) -> int:
    cfg = _build_cfg(args)
    body = {
        "terminalKind": args.terminal_kind,
        "text": args.text,
        "submit": bool(args.submit),
        "mode": args.mode,
    }
    status, payload = _request_json(cfg, "POST", "/send", body, require_token=True)
    return _print_result(status, payload)


def cmd_workflow_start(args: argparse.Namespace) -> int:
    cfg = _build_cfg(args)
    body = {"planId": args.plan_id, "scope": args.scope}
    status, payload = _request_json(cfg, "POST", "/workflow/start", body, require_token=True)
    return _print_result(status, payload)


def cmd_workflow_status(args: argparse.Namespace) -> int:
    cfg = _build_cfg(args)
    status, payload = _request_json(cfg, "GET", "/workflow/status", None, require_token=True)
    return _print_result(status, payload)


def _add_common_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--host", default=DEFAULT_HOST, help=f"bridge host (default: {DEFAULT_HOST})")
    p.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help=f"bridge port (default: {DEFAULT_PORT})"
    )
    p.add_argument("--token", default=None, help="bearer token (overrides env/file)")
    p.add_argument(
        "--token-file",
        default=DEFAULT_TOKEN_FILE_REL,
        help=f"repo-relative token file (default: {DEFAULT_TOKEN_FILE_REL})",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SendText Bridge Python client")
    sub = parser.add_subparsers(dest="command", required=True)

    p_healthz = sub.add_parser("healthz", help="GET /healthz")
    _add_common_flags(p_healthz)
    p_healthz.set_defaults(func=cmd_healthz)

    p_send = sub.add_parser("send", help="POST /send")
    _add_common_flags(p_send)
    p_send.add_argument("--terminal-kind", required=True, choices=["codex", "opencode"])
    p_send.add_argument("--text", required=True)
    p_send.add_argument("--submit", action="store_true")
    p_send.add_argument("--mode", default="single", choices=["single", "chunked"])
    p_send.set_defaults(func=cmd_send)

    p_wf_start = sub.add_parser("workflow-start", help="POST /workflow/start")
    _add_common_flags(p_wf_start)
    p_wf_start.add_argument("--plan-id", required=True, help="e.g. Idx-025")
    p_wf_start.add_argument("--scope", required=True, choices=["workflow", "project"])
    p_wf_start.set_defaults(func=cmd_workflow_start)

    p_wf_status = sub.add_parser("workflow-status", help="GET /workflow/status")
    _add_common_flags(p_wf_status)
    p_wf_status.set_defaults(func=cmd_workflow_status)

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except RuntimeError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
