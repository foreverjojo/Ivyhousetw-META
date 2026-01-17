#!/usr/bin/env python3
"""
Pin Dev Container image for full-fidelity restore (GHCR).

用途：
  - 將 `.devcontainer/devcontainer.json` 切換為 GHCR image 模式，並盡量 pin 到當前 git commit。
  - 只修改工作區檔案（不做 git commit），適合由 portable bootstrap 在新電腦自動呼叫。

策略：
  - 若可取得 git SHA → 使用 tag `devcontainer-<sha>`
  - 若無 git（zip 下載）→ fallback `devcontainer-main`
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
    image = f"{IMAGE_REPO}:{tag}"

    if TARGET.exists() and not BACKUP_BUILD.exists():
        try:
            BACKUP_BUILD.write_text(TARGET.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            pass

    obj = load_json(TEMPLATE)
    obj["image"] = image
    obj.pop("build", None)

    save_json(TARGET, obj)

    print(f"[OK] Pinned devcontainer image: {image}")
    if sha:
        print(f"[OK] Git SHA: {sha}")
    else:
        print("[WARN] Git SHA unavailable (zip download?). Using devcontainer-main tag.")
    print(f"[INFO] Backup (build-mode) saved at: {BACKUP_BUILD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

