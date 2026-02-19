#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VSCODE_SERVER_EXT_DIR="$HOME/.vscode-server/extensions"

get_extension_version() {
  local ext_dir="$1"
  python3 - "$ext_dir" <<'PY'
import json
import pathlib
import sys

ext_dir = pathlib.Path(sys.argv[1])
pkg = ext_dir / "package.json"
if not pkg.exists():
    print("")
    raise SystemExit(0)

try:
    data = json.loads(pkg.read_text(encoding="utf-8"))
    print(str(data.get("version", "")).strip())
except Exception:
    print("")
PY
}

install_local_extension_symlink() {
  local ext_id="$1"
  local ext_src="$2"

  if [[ ! -d "$ext_src" ]]; then
    echo "[WARN] extension source not found, skip: $ext_src" >&2
    return 0
  fi

  local version
  version="$(get_extension_version "$ext_src")"
  if [[ -z "$version" ]]; then
    echo "[WARN] failed to read version from: $ext_src/package.json" >&2
    return 0
  fi

  local dest_name="${ext_id}-${version}"
  local dest="$VSCODE_SERVER_EXT_DIR/$dest_name"

  find "$VSCODE_SERVER_EXT_DIR" -maxdepth 1 -mindepth 1 \( -type l -o -type d \) -name "${ext_id}-*" -exec rm -rf {} +
  ln -s "$ext_src" "$dest"

  echo "Installed local extension symlink:"
  echo "  $dest -> $ext_src"
}

mkdir -p "$VSCODE_SERVER_EXT_DIR"

install_local_extension_symlink \
  "ivyhouse-local.ivyhouse-terminal-injector" \
  "$REPO_ROOT/tools/vscode_terminal_injector"

install_local_extension_symlink \
  "ivyhouse-local.ivyhouse-terminal-monitor" \
  "$REPO_ROOT/tools/vscode_terminal_monitor"

install_local_extension_symlink \
  "ivyhouse-local.ivyhouse-terminal-orchestrator" \
  "$REPO_ROOT/tools/vscode_terminal_orchestrator"

echo
echo "Next step: in VS Code run 'Developer: Reload Window' to activate extensions."
