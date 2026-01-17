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
elif [[ -x "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" ]]; then
  code_cmd="/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
fi

if [[ -z "$code_cmd" ]]; then
  echo "[WARN] VS Code command not found; skipping extension installation." >&2
  echo "       - Install VS Code from https://code.visualstudio.com/" >&2
  echo "       - Open VS Code once, then re-run this script." >&2
  exit 0
fi

mapfile -t exts < <(python3 - <<'PY'
import json, sys
p = sys.argv[1]
try:
    with open(p, 'r', encoding='utf-8') as f:
        obj = json.load(f)
    recommendations = obj.get('recommendations', [])
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
for ext in "${exts[@]}"; do
  echo "- Installing $ext"
  "$code_cmd" --install-extension "$ext"
done

echo "Done."
