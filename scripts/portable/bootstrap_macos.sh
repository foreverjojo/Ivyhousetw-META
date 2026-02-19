#!/usr/bin/env bash
set -euo pipefail

OWNER="${OWNER:-foreverjojo}"
REPO="${REPO:-Ivyhousetw-META}"
BRANCH="${BRANCH:-main}"
DEST_ROOT="${DEST_ROOT:-$HOME/src}"
SKIP_DOCKER="${SKIP_DOCKER:-0}"
WITH_GHCR_PINNED="${WITH_GHCR_PINNED:-0}"

repo_path="$DEST_ROOT/$REPO"

ensure_dir() { mkdir -p "$1"; }

install_brew_if_missing() {
  if command -v brew >/dev/null 2>&1; then
    return
  fi

  echo "Homebrew not found."
  echo "This script can install Homebrew from: https://brew.sh"
  read -r -p "Proceed to install Homebrew? (y/N) " ans
  if [[ "${ans}" != "y" && "${ans}" != "Y" ]]; then
    echo "Abort. Install Homebrew then re-run." >&2
    exit 1
  fi

  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  # shellcheck disable=SC2016
  if [[ -x "/opt/homebrew/bin/brew" ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x "/usr/local/bin/brew" ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
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
  ensure_dir "$DEST_ROOT"
  tmpzip="$(mktemp -t ${REPO}.XXXXXX).zip"
  curl -fsSL "https://github.com/$OWNER/$REPO/archive/refs/heads/$BRANCH.zip" -o "$tmpzip"
  rm -rf "$repo_path"
  unzip -q "$tmpzip" -d "$DEST_ROOT"
  rm -f "$tmpzip"
  mv "$DEST_ROOT/$REPO-$BRANCH" "$repo_path"
}

install_tools() {
  install_brew_if_missing

  echo "Installing tools via Homebrew..."
  brew update

  brew install git python@3.11
  brew install --cask visual-studio-code

  if [[ "$SKIP_DOCKER" != "1" ]]; then
    brew install --cask docker
    echo "[INFO] Docker Desktop installed. Please open Docker once to complete setup:"
    echo "       open -a Docker"
  fi
}

install_extensions() {
  if [[ -f "$repo_path/scripts/portable/install_extensions.sh" ]]; then
    bash "$repo_path/scripts/portable/install_extensions.sh" "$repo_path" || true
  fi
}

install_tools
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
echo "- Open VS Code: open -a 'Visual Studio Code' '$repo_path'"
echo "- Then: Dev Containers: Reopen in Container"
echo "- If 'code' CLI is missing: VS Code -> Cmd+Shift+P -> Shell Command: Install 'code' command in PATH"
