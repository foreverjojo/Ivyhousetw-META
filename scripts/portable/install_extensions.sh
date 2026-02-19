#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
EXT_JSON="$REPO_ROOT/.vscode/extensions.json"

if [[ ! -f "$EXT_JSON" ]]; then
  echo "[ERROR] extensions.json file not found at $EXT_JSON" >&2
  exit 1
fi

code_cmd=""
if command -v code >/dev/null 2>&1; then
  code_cmd="code"
elif command -v code-insiders >/dev/null 2>&1; then
  code_cmd="code-insiders"
elif [[ -x "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" ]]; then
  code_cmd="/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
elif [[ -x "/Applications/Visual Studio Code - Insiders.app/Contents/Resources/app/bin/code-insiders" ]]; then
  code_cmd="/Applications/Visual Studio Code - Insiders.app/Contents/Resources/app/bin/code-insiders"
fi

if [[ -z "$code_cmd" ]]; then
  echo "[WARN] VS Code command not found; skipping extension installation." >&2
  echo "       - Install VS Code from https://code.visualstudio.com/" >&2
  echo "       - Open VS Code once, then re-run this script." >&2
  exit 0
fi

mapfile -t exts < <(python3 - <<'PY'
import json
import sys

p = sys.argv[1]
try:
    with open(p, "r", encoding="utf-8") as f:
        obj = json.load(f)
    recommendations = obj.get("recommendations", [])
    if not isinstance(recommendations, list):
        print("[ERROR] 'recommendations' is not a list.")
        sys.exit(1)
    for e in recommendations:
        if e and isinstance(e, str):
            print(e)
except (json.JSONDecodeError, FileNotFoundError) as e:
    print(f"[ERROR] Failed to parse {p}: {e}")
    sys.exit(1)
PY
"$EXT_JSON")

if [[ ${#exts[@]} -eq 0 ]]; then
  echo "[WARN] No extensions to install. Please check $EXT_JSON." >&2
  exit 0
fi

echo "Installing VS Code extensions from $EXT_JSON"

resolve_local_extension_dir() {
  local ext_id="$1"
  case "$ext_id" in
    ivyhouse-local.ivyhouse-terminal-injector)
      echo "$REPO_ROOT/tools/vscode_terminal_injector"
      ;;
    ivyhouse-local.ivyhouse-terminal-monitor)
      echo "$REPO_ROOT/tools/vscode_terminal_monitor"
      ;;
    ivyhouse-local.ivyhouse-terminal-orchestrator)
      echo "$REPO_ROOT/tools/vscode_terminal_orchestrator"
      ;;
    *)
      echo ""
      ;;
  esac
}

install_local_extension() {
  local ext_id="$1"
  local ext_dir="$2"

  if [[ ! -d "$ext_dir" ]]; then
    echo "  [WARN] Local extension source not found: $ext_dir"
    return 1
  fi
  if ! command -v npm >/dev/null 2>&1; then
    echo "  [WARN] npm not found; cannot package local extension: $ext_id"
    return 1
  fi

  echo "  [LOCAL] Packaging $ext_id from $ext_dir"
  (
    cd "$ext_dir"
    npm -s exec --yes @vscode/vsce package -- --allow-missing-repository --skip-license >/dev/null
  ) || {
    echo "  [WARN] Failed to package local extension: $ext_id"
    return 1
  }

  local vsix_path
  vsix_path="$(ls -t "$ext_dir"/*.vsix 2>/dev/null | head -n1 || true)"
  if [[ -z "$vsix_path" ]]; then
    echo "  [WARN] VSIX not found after packaging: $ext_id"
    return 1
  fi

  "$code_cmd" --install-extension "$vsix_path" --force >/dev/null || {
    echo "  [WARN] Failed to install local VSIX: $vsix_path"
    return 1
  }

  return 0
}

failed=0
for ext in "${exts[@]}"; do
  echo "- Installing $ext"
  local_dir="$(resolve_local_extension_dir "$ext")"
  if [[ -n "$local_dir" ]]; then
    install_local_extension "$ext" "$local_dir" || failed=$((failed + 1))
    continue
  fi

  "$code_cmd" --install-extension "$ext" >/dev/null || {
    echo "  [WARN] Failed: $ext"
    failed=$((failed + 1))
  }
done

if [[ "$failed" -gt 0 ]]; then
  echo "[WARN] Completed with $failed failures."
fi

echo "Done."
