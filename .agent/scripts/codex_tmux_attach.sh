#!/bin/bash
set -euo pipefail

SESSION="${1:-codex-session}"
STATE_FILE=".agent/state/codex_last_resume_id"

if ! command -v tmux >/dev/null 2>&1; then
  echo "❌ tmux not found" >&2
  exit 1
fi

# Create session if missing
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux new-session -d -s "$SESSION" -n codex
fi

# Best-effort: if codex already running in the main pane, don't start another.
PANE_PID="$(tmux display-message -p -t "$SESSION" '#{pane_pid}')"
if ! pgrep -P "$PANE_PID" -f '/usr/bin/codex' >/dev/null 2>&1; then
  # Clean any partially typed input then start codex (resume if we have an id).
  tmux send-keys -t "$SESSION" C-c C-c C-u
  if [ -f "$STATE_FILE" ]; then
    RESUME_ID="$(cat "$STATE_FILE" | tr -d '\r\n' || true)"
  else
    RESUME_ID=""
  fi

  if [ -n "$RESUME_ID" ]; then
    tmux send-keys -t "$SESSION" "codex resume $RESUME_ID" C-m
  else
    tmux send-keys -t "$SESSION" "codex" C-m
  fi
fi

# Attach or switch into the session
if [ -n "${TMUX:-}" ]; then
  tmux switch-client -t "$SESSION"
else
  tmux attach -t "$SESSION"
fi
