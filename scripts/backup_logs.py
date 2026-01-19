#!/usr/bin/env python3
"""
Log 備份工具

對應 P2 改進：災難恢復（Disaster Recovery）

功能：
1. 將 doc/logs/ 中的 Log 檔案打包成 zip
2. 可選：上傳到 Google Drive（需配置）
3. 清理過期的備份

使用方式：
    # 建立本地備份
    python scripts/backup_logs.py

    # 指定輸出目錄
    python scripts/backup_logs.py --output-dir backups/

    # 清理 30 天前的備份
    python scripts/backup_logs.py --cleanup --days 30

    # 列出現有備份
    python scripts/backup_logs.py --list
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

# === 設定 ===
LOGS_DIR = Path("doc/logs")
DEFAULT_BACKUP_DIR = Path("backups/logs")
BACKUP_PREFIX = "logs_backup_"


def create_backup(
    output_dir: Path = DEFAULT_BACKUP_DIR,
    include_empty: bool = False,
) -> Path | None:
    """
    建立 Log 備份

    Args:
        output_dir: 備份輸出目錄
        include_empty: 是否包含空的 Log 目錄

    Returns:
        備份檔案路徑，若無檔案則返回 None
    """
    if not LOGS_DIR.exists():
        print(f"❌ Log 目錄不存在：{LOGS_DIR}")
        return None

    # 收集要備份的檔案
    log_files = list(LOGS_DIR.glob("Idx-*_log.md"))
    log_files = [f for f in log_files if "template" not in f.name.lower()]

    if not log_files and not include_empty:
        print("ℹ️  沒有找到 Log 檔案，跳過備份")
        return None

    # 建立輸出目錄
    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成備份檔名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"{BACKUP_PREFIX}{timestamp}.zip"
    zip_path = output_dir / zip_name

    # 建立 zip 檔案
    with ZipFile(zip_path, "w") as zf:
        for log_file in log_files:
            zf.write(log_file, log_file.name)
            print(f"   📄 {log_file.name}")

        # 加入備份資訊
        info = f"""Backup Information
==================
Created: {datetime.now().isoformat()}
Files: {len(log_files)}
Source: {LOGS_DIR.absolute()}
"""
        zf.writestr("_backup_info.txt", info)

    print(f"\n✅ 備份完成：{zip_path}")
    print(f"   檔案數：{len(log_files)}")
    print(f"   大小：{zip_path.stat().st_size / 1024:.1f} KB")

    return zip_path


def list_backups(backup_dir: Path = DEFAULT_BACKUP_DIR) -> list[Path]:
    """列出現有備份"""
    if not backup_dir.exists():
        print(f"ℹ️  備份目錄不存在：{backup_dir}")
        return []

    backups = sorted(backup_dir.glob(f"{BACKUP_PREFIX}*.zip"), reverse=True)

    if not backups:
        print("ℹ️  沒有找到備份檔案")
        return []

    print(f"📋 現有備份（{len(backups)} 個）\n")
    print(f"{'檔名':<40} {'大小':>10} {'建立時間':<20}")
    print("-" * 70)

    for backup in backups:
        size = backup.stat().st_size / 1024
        # 從檔名解析時間
        try:
            ts = backup.stem.replace(BACKUP_PREFIX, "")
            dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            time_str = "Unknown"

        print(f"{backup.name:<40} {size:>8.1f} KB {time_str:<20}")

    return backups


def cleanup_old_backups(
    backup_dir: Path = DEFAULT_BACKUP_DIR,
    days: int = 30,
    dry_run: bool = False,
) -> int:
    """
    清理過期備份

    Args:
        backup_dir: 備份目錄
        days: 保留天數
        dry_run: 只顯示不刪除

    Returns:
        刪除的檔案數
    """
    if not backup_dir.exists():
        print(f"ℹ️  備份目錄不存在：{backup_dir}")
        return 0

    backups = list(backup_dir.glob(f"{BACKUP_PREFIX}*.zip"))
    cutoff = datetime.now() - timedelta(days=days)
    deleted = 0

    print(f"🧹 清理 {days} 天前的備份（截止：{cutoff.strftime('%Y-%m-%d')}）\n")

    for backup in backups:
        try:
            ts = backup.stem.replace(BACKUP_PREFIX, "")
            dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
        except ValueError:
            continue

        if dt < cutoff:
            if dry_run:
                print(f"   [DRY RUN] 會刪除：{backup.name}")
            else:
                backup.unlink()
                print(f"   🗑️  已刪除：{backup.name}")
            deleted += 1

    if deleted == 0:
        print("ℹ️  沒有過期的備份")
    else:
        action = "將會刪除" if dry_run else "已刪除"
        print(f"\n{action} {deleted} 個備份")

    return deleted


def restore_backup(
    backup_path: Path,
    target_dir: Path = LOGS_DIR,
    overwrite: bool = False,
) -> bool:
    """
    從備份還原 Log

    Args:
        backup_path: 備份檔案路徑
        target_dir: 還原目標目錄
        overwrite: 是否覆蓋現有檔案

    Returns:
        是否成功
    """
    if not backup_path.exists():
        print(f"❌ 備份檔案不存在：{backup_path}")
        return False

    target_dir.mkdir(parents=True, exist_ok=True)

    with ZipFile(backup_path, "r") as zf:
        for name in zf.namelist():
            if name.startswith("_"):  # 跳過資訊檔案
                continue

            target_file = target_dir / name
            if target_file.exists() and not overwrite:
                print(f"   ⚠️  跳過（已存在）：{name}")
                continue

            zf.extract(name, target_dir)
            print(f"   📄 還原：{name}")

    print(f"\n✅ 還原完成：{target_dir}")
    return True


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="Log 備份工具（災難恢復）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  建立備份：
    python scripts/backup_logs.py

  列出備份：
    python scripts/backup_logs.py --list

  清理過期備份：
    python scripts/backup_logs.py --cleanup --days 30

  還原備份：
    python scripts/backup_logs.py --restore backups/logs/logs_backup_20260110.zip
        """,
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help=f"備份輸出目錄（預設：{DEFAULT_BACKUP_DIR}）",
    )
    parser.add_argument(
        "--include-empty",
        action="store_true",
        help="即使沒有任何 Log 檔案也建立備份（只包含 _backup_info.txt）",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="列出現有備份",
    )
    parser.add_argument(
        "--cleanup",
        "-c",
        action="store_true",
        help="清理過期備份",
    )
    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=30,
        help="保留天數（預設 30）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只顯示不執行（用於清理）",
    )
    parser.add_argument(
        "--restore",
        "-r",
        type=Path,
        help="從備份還原",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="還原時覆蓋現有檔案",
    )

    args = parser.parse_args()

    if args.list:
        list_backups(args.output_dir)
        return 0

    if args.cleanup:
        cleanup_old_backups(args.output_dir, args.days, args.dry_run)
        return 0

    if args.restore:
        success = restore_backup(args.restore, LOGS_DIR, args.overwrite)
        return 0 if success else 1

    # 預設：建立備份
    result = create_backup(args.output_dir, include_empty=args.include_empty)
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
