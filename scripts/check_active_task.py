#!/usr/bin/env python3
"""
任務鎖管理工具

功能：
- acquire <index>: 取得任務鎖（預設 TTL 24h）
- release <index>: 釋放任務鎖
- status: 查看當前鎖狀態
- force-release: 強制釋放過期鎖

基於五條鐵律中的 Parallel Isolation 原則
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

LOCK_FILE = Path(".agent/active_task.lock")
DEFAULT_TTL_HOURS = 24


def load_lock():
    """載入任務鎖"""
    if not LOCK_FILE.exists():
        return None

    try:
        with open(LOCK_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def save_lock(lock_data):
    """儲存任務鎖"""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        json.dump(lock_data, f, indent=2, ensure_ascii=False)


def is_expired(lock_data):
    """檢查鎖是否過期"""
    if not lock_data:
        return True

    started_at = datetime.fromisoformat(lock_data["started_at"])
    ttl_hours = lock_data.get("ttl_hours", DEFAULT_TTL_HOURS)
    expiry = started_at + timedelta(hours=ttl_hours)

    return datetime.now() > expiry


def acquire_lock(index):
    """取得任務鎖"""
    lock = load_lock()

    # 檢查是否已有鎖
    if lock and not is_expired(lock):
        print(f"❌ 錯誤: 任務 {lock['index']} 正在進行中")
        print(f"   開始時間: {lock['started_at']}")
        print(f"   TTL: {lock.get('ttl_hours', DEFAULT_TTL_HOURS)} 小時")
        print("\n   請先釋放鎖或等待過期後使用 force-release")
        return False

    # 建立新鎖
    new_lock = {
        "index": index,
        "started_at": datetime.now().isoformat(),
        "ttl_hours": DEFAULT_TTL_HOURS,
        "status": "IN_PROGRESS",
    }

    save_lock(new_lock)
    print(f"✅ 成功取得任務鎖: {index}")
    print(f"   TTL: {DEFAULT_TTL_HOURS} 小時")
    print(f"   過期時間: {(datetime.now() + timedelta(hours=DEFAULT_TTL_HOURS)).isoformat()}")
    return True


def release_lock(index):
    """釋放任務鎖"""
    lock = load_lock()

    if not lock:
        print("❌ 錯誤: 沒有活動的任務鎖")
        return False

    if lock["index"] != index:
        print(f"❌ 錯誤: 當前鎖是 {lock['index']}，不是 {index}")
        return False

    LOCK_FILE.unlink()
    print(f"✅ 成功釋放任務鎖: {index}")
    return True


def force_release():
    """強制釋放鎖（通常用於過期鎖）"""
    lock = load_lock()

    if not lock:
        print("ℹ️  沒有活動的任務鎖")
        return True

    if is_expired(lock):
        LOCK_FILE.unlink()
        print(f"✅ 強制釋放過期鎖: {lock['index']}")
        print(f"   原開始時間: {lock['started_at']}")
        return True
    else:
        print("⚠️  警告: 鎖尚未過期")
        print(f"   任務: {lock['index']}")
        print(f"   開始時間: {lock['started_at']}")

        response = input("\n確定要強制釋放？(yes/no): ")
        if response.lower() == "yes":
            LOCK_FILE.unlink()
            print(f"✅ 已強制釋放鎖: {lock['index']}")
            return True
        else:
            print("❌ 取消操作")
            return False


def show_status():
    """顯示當前鎖狀態"""
    lock = load_lock()

    if not lock:
        print("✅ 沒有活動的任務鎖")
        return

    expired = is_expired(lock)

    print("📋 當前任務鎖狀態:")
    print(f"   Index: {lock['index']}")
    print(f"   狀態: {lock['status']}")
    print(f"   開始時間: {lock['started_at']}")
    print(f"   TTL: {lock.get('ttl_hours', DEFAULT_TTL_HOURS)} 小時")

    if expired:
        print("   ⚠️  狀態: 已過期")
        print("\n   建議執行: python scripts/check_active_task.py force-release")
    else:
        started_at = datetime.fromisoformat(lock["started_at"])
        ttl_hours = lock.get("ttl_hours", DEFAULT_TTL_HOURS)
        expiry = started_at + timedelta(hours=ttl_hours)
        remaining = expiry - datetime.now()

        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)

        print(f"   過期時間: {expiry.isoformat()}")
        print(f"   剩餘時間: {hours} 小時 {minutes} 分鐘")


def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python scripts/check_active_task.py acquire <index>")
        print("  python scripts/check_active_task.py release <index>")
        print("  python scripts/check_active_task.py status")
        print("  python scripts/check_active_task.py force-release")
        sys.exit(1)

    command = sys.argv[1]

    if command == "acquire":
        if len(sys.argv) < 3:
            print("❌ 錯誤: 請提供 Index (例如: Idx-001)")
            sys.exit(1)
        index = sys.argv[2]
        success = acquire_lock(index)
        sys.exit(0 if success else 1)

    elif command == "release":
        if len(sys.argv) < 3:
            print("❌ 錯誤: 請提供 Index (例如: Idx-001)")
            sys.exit(1)
        index = sys.argv[2]
        success = release_lock(index)
        sys.exit(0 if success else 1)

    elif command == "status":
        show_status()
        sys.exit(0)

    elif command == "force-release":
        success = force_release()
        sys.exit(0 if success else 1)

    else:
        print(f"❌ 未知指令: {command}")
        print("\n有效指令: acquire, release, status, force-release")
        sys.exit(1)


if __name__ == "__main__":
    main()
