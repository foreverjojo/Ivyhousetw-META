#!/usr/bin/env python3
"""
Pin Dev Container image for full-fidelity restore (GHCR).

用途：
  - 將 `.devcontainer/devcontainer.json` 切換為 GHCR image 模式，並盡量 pin 到當前 git commit。
  - 只修改工作區檔案（不做 git commit），適合由 portable bootstrap 在新電腦自動呼叫。

策略：
    - 若可取得 git SHA → 使用 tag `devcontainer-<sha>` 並嘗試解析成 digest pin（@sha256:...）
    - 若無 git（zip 下載）→ fallback `devcontainer-main`
    - 若無法解析 digest（未登入 GHCR / image 尚未 build / Docker 未就緒）→ 仍使用 tag pin
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
import base64
from pathlib import Path
from typing import Any, Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
DEVCONTAINER_DIR = REPO_ROOT / ".devcontainer"
TARGET = DEVCONTAINER_DIR / "devcontainer.json"
TEMPLATE = DEVCONTAINER_DIR / "devcontainer.ghcr.json"
BACKUP_BUILD = DEVCONTAINER_DIR / "devcontainer.build.json"

IMAGE_REPO = "ghcr.io/foreverjojo/ivyhousetw-meta-devcontainer"


def resolve_digest_via_ghcr(image_repo: str, tag: str) -> Optional[str]:
    """Resolve manifest digest from GHCR using GHCR_TOKEN (PAT), best-effort.

    This avoids requiring Docker/buildx on the target machine.

    Env:
      - GHCR_TOKEN: GitHub PAT with read:packages
      - GHCR_USERNAME (optional): username for Basic auth; defaults to org/owner name
    """

    pat = os.getenv("GHCR_TOKEN")
    if not pat:
        return None

    # image_repo: ghcr.io/<owner>/<image>
    parts = image_repo.split("/")
    if len(parts) < 3 or parts[0] != "ghcr.io":
        return None

    owner = parts[1]
    image = "/".join(parts[2:])
    repo = f"{owner}/{image}"

    username = os.getenv("GHCR_USERNAME") or os.getenv("GITHUB_ACTOR") or owner

    # Exchange PAT for registry bearer token
    scope = f"repository:{repo}:pull"
    token_url = f"https://ghcr.io/token?scope={scope}"
    basic = base64.b64encode(f"{username}:{pat}".encode()).decode()
    req = urllib.request.Request(token_url)
    req.add_header("Authorization", f"Basic {basic}")

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.load(r)
            reg_token = payload.get("token")
    except Exception:
        return None

    if not reg_token:
        return None

    manifest_url = f"https://ghcr.io/v2/{repo}/manifests/{tag}"
    req = urllib.request.Request(manifest_url)
    req.add_header("Authorization", f"Bearer {reg_token}")
    req.add_header(
        "Accept",
        ", ".join(
            [
                "application/vnd.oci.image.index.v1+json",
                "application/vnd.docker.distribution.manifest.list.v2+json",
                "application/vnd.oci.image.manifest.v1+json",
                "application/vnd.docker.distribution.manifest.v2+json",
            ]
        ),
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            digest = r.headers.get("Docker-Content-Digest")
    except Exception:
        return None

    if isinstance(digest, str) and digest.startswith("sha256:") and len(digest) > 20:
        return digest
    return None


def resolve_digest(image_ref: str) -> Optional[str]:
    """Best-effort resolve manifest digest for an image ref.

    Requires Docker CLI; for private GHCR images, user must `docker login ghcr.io`.
    """

    # Prefer buildx imagetools (registry-aware)
    try:
        out = subprocess.check_output(
            ["docker", "buildx", "imagetools", "inspect", image_ref],
            cwd=str(REPO_ROOT),
            text=True,
            stderr=subprocess.STDOUT,
        )
        for line in out.splitlines():
            line = line.strip()
            if line.lower().startswith("digest:"):
                digest = line.split(":", 1)[1].strip()
                if digest.startswith("sha256:") and len(digest) > 20:
                    return digest
    except Exception:
        pass

    # Fallback: docker manifest inspect (often works, but digest may be absent)
    try:
        out = subprocess.check_output(
            ["docker", "manifest", "inspect", image_ref],
            cwd=str(REPO_ROOT),
            text=True,
            stderr=subprocess.STDOUT,
        )
        import re

        m = re.search(r"sha256:[a-f0-9]{64}", out)
        if m:
            return m.group(0)
    except Exception:
        pass

    return None


def git_sha() -> Optional[str]:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True).strip()
        if out and len(out) >= 7:
            return out
    except Exception:
        return None
    return None


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj: Dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    if not TEMPLATE.exists():
        print(f"[ERROR] Missing template: {TEMPLATE}", file=sys.stderr)
        return 2

    sha = git_sha()
    tag = f"devcontainer-{sha}" if sha else "devcontainer-main"
    tag_ref = f"{IMAGE_REPO}:{tag}"

    pinned_ref = None
    try:
        # Quick docker readiness check
        subprocess.check_output(["docker", "version"], cwd=str(REPO_ROOT), stderr=subprocess.STDOUT)
        digest = resolve_digest(tag_ref)
        if digest:
            pinned_ref = f"{IMAGE_REPO}@{digest}"
    except Exception:
        pinned_ref = None

    if not pinned_ref:
        # Registry-based digest resolution (no Docker required)
        digest = resolve_digest_via_ghcr(IMAGE_REPO, tag)
        if digest:
            pinned_ref = f"{IMAGE_REPO}@{digest}"

    if TARGET.exists() and not BACKUP_BUILD.exists():
        try:
            BACKUP_BUILD.write_text(TARGET.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            pass

    obj = load_json(TEMPLATE)
    obj["image"] = pinned_ref or tag_ref
    obj.pop("build", None)

    save_json(TARGET, obj)

    print(f"[OK] Pinned devcontainer image: {obj['image']}")
    if sha:
        print(f"[OK] Git SHA: {sha}")
    else:
        print("[WARN] Git SHA unavailable (zip download?). Using devcontainer-main tag.")
    if not pinned_ref:
        print("[WARN] Digest pin unavailable; using tag pin.")
        print("       Tips: ensure image exists (CI built).")
        print("       - Option A: set GHCR_TOKEN (PAT with read:packages) then re-run.")
        print("       - Option B: run `docker login ghcr.io` (and ensure docker/buildx ready) then re-run.")
    print(f"[INFO] Backup (build-mode) saved at: {BACKUP_BUILD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
