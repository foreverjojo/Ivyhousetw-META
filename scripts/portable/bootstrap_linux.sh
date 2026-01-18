#!/usr/bin/env bash
set -euo pipefail

OWNER="${OWNER:-foreverjojo}"
REPO="${REPO:-Ivyhousetw-META}"
BRANCH="${BRANCH:-main}"
DEST_ROOT="${DEST_ROOT:-$HOME/src}"
WITH_DOCKER="${WITH_DOCKER:-0}"
WITH_VSCODE="${WITH_VSCODE:-0}"
WITH_GHCR_PINNED="${WITH_GHCR_PINNED:-0}"

repo_path="$DEST_ROOT/$REPO"

ensure_dir() { mkdir -p "$1"; }

require_sudo() {
  if [[ "$(id -u)" -ne 0 ]] && ! command -v sudo >/dev/null 2>&1; then
    echo "[ERROR] sudo is required." >&2
    exit 1
  fi
}

apt_install_base() {
  require_sudo
  echo "Installing base tools (git/python/venv/pip/curl/unzip)..."
  sudo apt-get update -y
  sudo apt-get install -y git python3 python3-venv python3-pip curl ca-certificates unzip
}

apt_install_docker_optional() {
  [[ "$WITH_DOCKER" != "1" ]] && return
  require_sudo
  echo "Installing Docker (docker.io) via apt..."
  sudo apt-get install -y docker.io
  echo "[INFO] Starting Docker daemon..."
  sudo systemctl enable --now docker || true
  echo "[INFO] You may need to add your user to the docker group:"
  echo "       sudo usermod -aG docker $USER && newgrp docker"
  echo "[INFO] Quick check: docker version (may require re-login if group changed)"
  docker version >/dev/null 2>&1 || true
}

install_vscode_optional() {
  [[ "$WITH_VSCODE" != "1" ]] && return

  if command -v snap >/dev/null 2>&1; then
    require_sudo
    echo "Installing VS Code via snap..."
    sudo snap install code --classic
    return
  fi

  echo "[WARN] snap not available; skipping VS Code install. Install manually from https://code.visualstudio.com/" >&2
}

clone_or_update_repo() {
  ensure_dir "$DEST_ROOT"

  if command -v git >/dev/null 2>&1; then
    if [[ -d "$repo_path/.git" ]]; then
      echo "Updating repo: $repo_path"
      (cd "$repo_path" && git fetch --all && git checkout "$BRANCH" && git pull --ff-only)
      return
    fi

    echo "Cloning repo: $repo_path"
    git clone "https://github.com/$OWNER/$REPO.git" "$repo_path"
    return
  fi

  echo "Git not found; downloading zip."
  tmpzip="$(mktemp -t ${REPO}.XXXXXX).zip"
  curl -fsSL "https://github.com/$OWNER/$REPO/archive/refs/heads/$BRANCH.zip" -o "$tmpzip"
  rm -rf "$repo_path"
  unzip -q "$tmpzip" -d "$DEST_ROOT"
  rm -f "$tmpzip"
  mv "$DEST_ROOT/$REPO-$BRANCH" "$repo_path"
}

install_extensions() {
  if [[ -f "$repo_path/scripts/portable/install_extensions.sh" ]]; then
    bash "$repo_path/scripts/portable/install_extensions.sh" "$repo_path" || true
  fi
}

apt_install_base
apt_install_docker_optional
install_vscode_optional
clone_or_update_repo

if [[ "$WITH_GHCR_PINNED" == "1" && -f "$repo_path/scripts/portable/pin_devcontainer_image.py" ]]; then
  echo "Pinning Dev Container image (GHCR; best-effort digest)..."
  python3 "$repo_path/scripts/portable/pin_devcontainer_image.py" || true
else
  echo "[INFO] GHCR pinned devcontainer is opt-in. To enable:"
  echo "       WITH_GHCR_PINNED=1 $0"
fi
install_extensions

echo "Done. Next steps:"
echo "- Open the repo in VS Code and run: Dev Containers: Reopen in Container"
