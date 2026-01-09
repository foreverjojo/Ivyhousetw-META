#!/usr/bin/env python3
"""
State Gate 驗證腳本

功能：
1. 驗證 Commit Message 格式（feat(Idx-NNN): ...）
2. 檢查 Index 是否存在於 implementation_plan_index.md
3. 驗證任務鎖一致性
4. 豁免規則：chore:, docs:, style:, ci:, build:, revert:

基於五條鐵律中的 State Gate 原則
"""

import re
import sys
from pathlib import Path


INDEX_FILE = Path("doc/Implementation_Plan_index.md")
LOCK_FILE = Path(".agent/active_task.lock")

# Commit message 豁免前綴（不需要 Index）
EXEMPT_PREFIXES = [
    "chore:",
    "docs:",
    "style:",
    "ci:",
    "build:",
    "revert:",
]


def is_exempt_commit(message):
    """檢查是否為豁免的 commit 類型"""
    for prefix in EXEMPT_PREFIXES:
        if message.startswith(prefix):
            return True
    return False


def extract_index(commit_message):
    """從 commit message 中提取 Index"""
    # 匹配格式：<type>(Idx-NNN): <description>
    pattern = r'\(Idx-(\d+)\):'
    match = re.search(pattern, commit_message)

    if match:
        return f"Idx-{match.group(1)}"
    return None


def check_index_exists(index):
    """檢查 Index 是否存在於 implementation_plan_index.md"""
    if not INDEX_FILE.exists():
        print(f"❌ 錯誤: {INDEX_FILE} 不存在")
        return False

    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # 檢查是否包含 Index（例如：| Idx-001 |）
    if f"| {index} |" in content or f"|{index}|" in content:
        return True

    return False


def check_lock_consistency(index):
    """檢查任務鎖一致性"""
    if not LOCK_FILE.exists():
        print("⚠️  警告: 沒有活動的任務鎖")
        print("   建議先執行: python scripts/check_active_task.py acquire <index>")
        return None  # 警告但不阻擋

    import json
    try:
        with open(LOCK_FILE, 'r', encoding='utf-8') as f:
            lock_data = json.load(f)

        if lock_data['index'] != index:
            print(f"❌ 錯誤: 任務鎖不一致")
            print(f"   Commit Index: {index}")
            print(f"   鎖定 Index: {lock_data['index']}")
            return False

        return True

    except (json.JSONDecodeError, KeyError):
        print("⚠️  警告: 任務鎖檔案格式錯誤")
        return None


def validate_commit_message(message):
    """驗證 commit message"""
    print(f"🔍 驗證 Commit Message: {message[:80]}...")
    print()

    # 檢查豁免
    if is_exempt_commit(message):
        print(f"✅ 豁免類型，跳過 Index 檢查")
        print(f"   類型: {message.split(':')[0]}")
        return True

    # 提取 Index
    index = extract_index(message)
    if not index:
        print("❌ 錯誤: Commit message 格式錯誤")
        print()
        print("正確格式：")
        print("  <type>(Idx-NNN): <description>")
        print()
        print("範例：")
        print("  feat(Idx-001): 實作新功能")
        print("  fix(Idx-002): 修復 bug")
        print()
        print("或使用豁免前綴：")
        for prefix in EXEMPT_PREFIXES:
            print(f"  {prefix} <description>")
        return False

    print(f"✅ Index 格式正確: {index}")

    # 檢查 Index 存在性
    if not check_index_exists(index):
        print(f"❌ 錯誤: {index} 不存在於 {INDEX_FILE}")
        print()
        print("請先在 implementation_plan_index.md 中註冊此 Index")
        return False

    print(f"✅ Index 存在於 {INDEX_FILE.name}")

    # 檢查鎖一致性
    lock_check = check_lock_consistency(index)
    if lock_check is False:
        return False
    elif lock_check is True:
        print(f"✅ 任務鎖一致")
    # lock_check is None：警告但不阻擋

    print()
    print("🎉 State Gate 驗證通過！")
    return True


def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("用法:")
        print('  python scripts/validate_state_gate.py "feat(Idx-001): 描述"')
        print()
        print("或在 commit-msg hook 中使用（傳入 commit message 檔案路徑）：")
        print("  python scripts/validate_state_gate.py .git/COMMIT_EDITMSG")
        sys.exit(1)

    arg = sys.argv[1]
    commit_message = arg
    msg_path = Path(arg)
    if msg_path.exists() and msg_path.is_file():
        commit_message = msg_path.read_text(encoding="utf-8", errors="replace").strip()

    if validate_commit_message(commit_message):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
