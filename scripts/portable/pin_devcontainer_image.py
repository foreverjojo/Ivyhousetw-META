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
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
DEVCONTAINER_DIR = REPO_ROOT / ".devcontainer"
TARGET = DEVCONTAINER_DIR / "devcontainer.json"
TEMPLATE = DEVCONTAINER_DIR / "devcontainer.ghcr.json"
BACKUP_BUILD = DEVCONTAINER_DIR / "devcontainer.build.json"

IMAGE_REPO = "ghcr.io/foreverjojo/ivyhousetw-meta-devcontainer"


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
        print("       Tips: ensure image exists (CI built), run `docker login ghcr.io`, then re-run.")
    print(f"[INFO] Backup (build-mode) saved at: {BACKUP_BUILD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
