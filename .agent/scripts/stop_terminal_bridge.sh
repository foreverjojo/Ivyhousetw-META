#!/usr/bin/env bash
# Stop Terminal Bridge Server daemon
# Usage: ./stop_terminal_bridge.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$WORKSPACE_ROOT/.agent/state"
PID_FILE="$STATE_DIR/terminal_bridge.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "⚠️  Terminal Bridge Server is not running (no PID file found)"
  exit 0
fi

PID=$(cat "$PID_FILE")

if ! kill -0 "$PID" 2>/dev/null; then
  echo "⚠️  Process $PID is not running (stale PID file)"
  rm -f "$PID_FILE"
  exit 0
fi

echo "⏹️  Stopping Terminal Bridge Server (PID: $PID)..."
kill "$PID"

# Wait for process to terminate
for i in {1..10}; do
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "✅ Server stopped successfully"
    rm -f "$PID_FILE"
    exit 0
  fi
  sleep 0.5
done

# Force kill if still running
echo "⚠️  Process did not stop gracefully, forcing..."
kill -9 "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
echo "✅ Server stopped (forced)"
