#!/usr/bin/env bash
# Start Terminal Bridge Server as a daemon
# Usage: ./start_terminal_bridge.sh [port]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$WORKSPACE_ROOT/.agent/state"
PID_FILE="$STATE_DIR/terminal_bridge.pid"
SERVER_SCRIPT="$SCRIPT_DIR/terminal_bridge_server.py"

PORT="${1:-${TERMINAL_BRIDGE_PORT:-38765}}"

# Check if already running
if [[ -f "$PID_FILE" ]]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "⚠️  Terminal Bridge Server already running (PID: $OLD_PID)"
    echo "   Use ./stop_terminal_bridge.sh to stop it first"
    exit 0
  else
    echo "🧹 Cleaning up stale PID file"
    rm -f "$PID_FILE"
  fi
fi

# Ensure state directory exists
mkdir -p "$STATE_DIR"

# Start server in background
echo "🚀 Starting Terminal Bridge Server..."
export TERMINAL_BRIDGE_PORT="$PORT"
export WORKSPACE_ROOT="$WORKSPACE_ROOT"

nohup python3 "$SERVER_SCRIPT" > "$STATE_DIR/terminal_bridge.log" 2>&1 &
SERVER_PID=$!

# Save PID
echo "$SERVER_PID" > "$PID_FILE"

# Wait for server to start
sleep 2

# Check if server is running
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "❌ Failed to start server"
  echo "📋 Log output:"
  tail -20 "$STATE_DIR/terminal_bridge.log"
  rm -f "$PID_FILE"
  exit 1
fi

# Test health endpoint
if curl -s http://127.0.0.1:${PORT}/health > /dev/null 2>&1; then
  echo "✅ Terminal Bridge Server started successfully"
  echo "   PID: $SERVER_PID"
  echo "   Port: $PORT"
  echo "   Log: $STATE_DIR/terminal_bridge.log"
  echo ""
  echo "📡 Available endpoints:"
  echo "   GET  /health  - Health check"
  echo "   GET  /capture - Get git status changes"
  echo "   POST /wait    - Wait for git status to stabilize"
  echo ""
  echo "🔑 Token file: $STATE_DIR/terminal_bridge_token"
else
  echo "❌ Server started but not responding to health checks"
  echo "📋 Log output:"
  tail -20 "$STATE_DIR/terminal_bridge.log"
  kill "$SERVER_PID" 2>/dev/null || true
  rm -f "$PID_FILE"
  exit 1
fi
