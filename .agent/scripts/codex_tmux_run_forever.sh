#!/bin/bash
set -euo pipefail

SESSION="${1:-codex-session}"
WINDOW_INDEX="${2:-0}"
PANE_INDEX="${3:-0}"

if ! command -v tmux >/dev/null 2>&1; then
  echo "❌ tmux not found" >&2
  exit 1
fi

if ! command -v script >/dev/null 2>&1; then
  echo "❌ util-linux 'script' not found" >&2
  exit 1
fi

# Ensure session exists
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux new-session -d -s "$SESSION" -n codex
fi

TARGET="$SESSION:$WINDOW_INDEX.$PANE_INDEX"

# Respawn the target pane with a loop that keeps Codex running.
# Using `script` gives Codex a proper pseudo-tty even when detached.
CMD=$(cat <<'EOF'
set -euo pipefail
while true; do
  script -q -c "codex" /dev/null
  code=$?
  echo "[codex_tmux_run_forever] codex exited code=$code at $(date -Is)" >&2
  sleep 1
done
EOF
)

tmux respawn-pane -t "$TARGET" -k "bash -lc $(printf '%q' "$CMD")"

echo "✅ Codex is now supervised in tmux session '$SESSION' (pane $WINDOW_INDEX.$PANE_INDEX)."
echo "Attach with: tmux attach -t $SESSION"
