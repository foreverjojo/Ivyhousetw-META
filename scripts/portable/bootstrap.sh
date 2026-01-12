#!/usr/bin/env bash
set -euo pipefail

# Cross-platform entrypoint for macOS/Linux.
# - macOS -> bootstrap_macos.sh
# - Linux -> bootstrap_linux.sh

here="$(cd "$(dirname "$0")" && pwd)"

os="$(uname -s || true)"
case "$os" in
  Darwin)
    exec bash "$here/bootstrap_macos.sh" "$@"
    ;;
  Linux)
    exec bash "$here/bootstrap_linux.sh" "$@"
    ;;
  *)
    echo "[ERROR] Unsupported OS: $os" >&2
    echo "Windows: run scripts/portable/bootstrap_windows.ps1" >&2
    exit 1
    ;;
esac
