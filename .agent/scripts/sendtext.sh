#!/bin/bash
set -euo pipefail

PORT="${SENDTEXT_BRIDGE_PORT:-38765}"
TOKEN_FILE="${SENDTEXT_BRIDGE_TOKEN_FILE:-.agent/state/sendtext_bridge_token}"

usage() {
  cat >&2 <<'EOF'
Usage:
  .agent/scripts/sendtext.sh text <string> [--execute]
  .agent/scripts/sendtext.sh enter

Environment:
  SENDTEXT_BRIDGE_PORT (default: 38765)
  SENDTEXT_BRIDGE_TOKEN (optional; overrides token file)
  SENDTEXT_BRIDGE_TOKEN_FILE (default: .agent/state/sendtext_bridge_token)
EOF
}

if [ "$#" -lt 1 ]; then
  usage
  exit 2
fi

CMD="$1"; shift

TOKEN="${SENDTEXT_BRIDGE_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  if [ ! -f "$TOKEN_FILE" ]; then
    echo "❌ token file not found: $TOKEN_FILE" >&2
    echo "Install/enable the SendText Bridge VS Code extension first." >&2
    exit 1
  fi
  TOKEN="$(cat "$TOKEN_FILE" | tr -d '\r\n')"
fi

case "$CMD" in
  text)
    if [ "$#" -lt 1 ]; then
      usage
      exit 2
    fi
    TEXT="$1"; shift
    EXECUTE=false
    if [ "${1:-}" = "--execute" ]; then
      EXECUTE=true
    fi
    # 先送文字（不執行）
    curl -sS -X POST "http://127.0.0.1:${PORT}/send" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"text\":$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$TEXT"),\"execute\":false}"
    # 若需要執行，稍微延遲後再送 Enter（避免 terminal 來不及接收）
    if [ "$EXECUTE" = "true" ]; then
      sleep 0.3
      curl -sS -X POST "http://127.0.0.1:${PORT}/enter" \
        -H "Authorization: Bearer ${TOKEN}"
    fi
    ;;
  enter)
    curl -sS -X POST "http://127.0.0.1:${PORT}/enter" \
      -H "Authorization: Bearer ${TOKEN}"
    ;;
  *)
    usage
    exit 2
    ;;
esac
