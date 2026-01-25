#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EXT_SRC="$REPO_ROOT/tools/vscode_terminal_orchestrator"

# VS Code Server extensions dir (Dev Container)
VSCODE_SERVER_EXT_DIR="$HOME/.vscode-server/extensions"

if [[ ! -d "$EXT_SRC" ]]; then
  echo "ERROR: extension source not found: $EXT_SRC" >&2
  exit 1
fi

mkdir -p "$VSCODE_SERVER_EXT_DIR"

NAME="ivyhouse-local.ivyhouse-terminal-orchestrator-0.0.1"
DEST="$VSCODE_SERVER_EXT_DIR/$NAME"

# Use symlink so updates in repo take effect immediately.
if [[ -L "$DEST" || -d "$DEST" ]]; then
  rm -rf "$DEST"
fi

ln -s "$EXT_SRC" "$DEST"

echo "Installed local extension symlink:"
echo "  $DEST -> $EXT_SRC"
echo
echo "Next step: in VS Code run 'Developer: Reload Window' to activate it."
