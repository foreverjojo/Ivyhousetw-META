"""
檔案用途：媒體素材掃描工具
職責：
  - 掃描 `attached_assets/` 目錄下的圖片/影片檔案
  - 提供「最多 N 張圖片」的選取邏輯，供視覺顧問分析使用
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from core.config import MEDIA_ASSETS_DIR


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov"}


@dataclass(frozen=True)
class MediaScanResult:
    images: List[Path]
    videos: List[Path]


def _iter_files(root: Path, *, recursive: bool) -> Iterable[Path]:
    if recursive:
        yield from root.rglob("*")
    else:
        yield from root.glob("*")


def scan_media_assets(
    media_dir: Optional[Path] = None, *, recursive: bool = True
) -> MediaScanResult:
    """
    掃描素材目錄，回傳圖片與影片清單（以副檔名判斷）。
    """
    root = media_dir or MEDIA_ASSETS_DIR
    if not root.exists():
        return MediaScanResult(images=[], videos=[])

    images: List[Path] = []
    videos: List[Path] = []

    for path in _iter_files(root, recursive=recursive):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in IMAGE_SUFFIXES:
            images.append(path)
        elif suffix in VIDEO_SUFFIXES:
            videos.append(path)

    return MediaScanResult(images=images, videos=videos)


def get_top_images(images: List[Path], n: int = 6) -> List[Path]:
    """
    取得最多 N 張圖片（以檔案修改時間由新到舊排序）。
    """
    if n <= 0:
        return []

    def _mtime(p: Path) -> float:
        try:
            return p.stat().st_mtime
        except Exception:
            return 0.0

    images_sorted = sorted(images, key=_mtime, reverse=True)
    return images_sorted[:n]
