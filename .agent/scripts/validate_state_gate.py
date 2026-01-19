#!/usr/bin/env python3
"""
State Gate 驗證腳本

功能：
1. 驗證 Commit Message 格式（feat(Idx-NNN): ...）
2. 檢查 Index 是否存在於 Implementation_Plan_index.md
3. 驗證任務鎖一致性
4. 豁免規則：chore:, docs:, style:, ci:, build:, revert:

基於五條鐵律中的 State Gate 原則
"""

import re
import subprocess
import sys
from pathlib import Path

# Index 檔案會根據變更路徑自動選擇
PROJECT_INDEX_FILE = Path("doc/Implementation_Plan_index.md")
WORKFLOW_INDEX_FILE = Path(".agent/Workflow_Plan_index.md")
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


def detect_index_file():
    """
    根據 git staged 變更自動判斷要驗證哪一份 Index

    規則：
    - 若變更包含 .agent/** 路徑 → 驗證 .agent/Workflow_Plan_index.md
    - 否則 → 驗證 doc/Implementation_Plan_index.md

    Returns:
        Path: 要驗證的 Index 檔案路徑
    """
    try:
        # 取得 staged 變更的檔案清單
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            # 無法取得 git 狀態，預設使用專案 Index
            print("⚠️  警告: 無法取得 git staged 檔案清單，使用預設 Index")
            return PROJECT_INDEX_FILE

        changed_files = result.stdout.strip().split("\n")
        changed_files = [f for f in changed_files if f]  # 過濾空行

        # 檢查是否有 .agent/ 開頭的檔案
        has_agent_changes = any(f.startswith(".agent/") for f in changed_files)

        if has_agent_changes:
            print("🔀 偵測到 .agent/ 變更，使用 Workflow Index")
            return WORKFLOW_INDEX_FILE
        else:
            print("🔀 偵測到專案檔案變更，使用 Project Index")
            return PROJECT_INDEX_FILE

    except Exception as e:
        print(f"⚠️  警告: 偵測變更檔案時發生錯誤: {e}")
        print("   使用預設 Project Index")
        return PROJECT_INDEX_FILE


def is_exempt_commit(message):
    """檢查是否為豁免的 commit 類型"""
    for prefix in EXEMPT_PREFIXES:
        if message.startswith(prefix):
            return True
    return False


def extract_index(commit_message):
    """從 commit message 中提取 Index"""
    # 匹配格式：<type>(Idx-NNN): <description>
    pattern = r"\(Idx-(\d+)\):"
    match = re.search(pattern, commit_message)

    if match:
        return f"Idx-{match.group(1)}"
    return None


def check_index_exists(index, index_file):
    """檢查 Index 是否存在於指定的 Index 檔案中"""
    if not index_file.exists():
        print(f"❌ 錯誤: {index_file} 不存在")
        return False

    with open(index_file, encoding="utf-8") as f:
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
        with open(LOCK_FILE, encoding="utf-8") as f:
            lock_data = json.load(f)

        if lock_data["index"] != index:
            print("❌ 錯誤: 任務鎖不一致")
            print(f"   Commit Index: {index}")
            print(f"   鎖定 Index: {lock_data['index']}")
            return False

        return True

    except (json.JSONDecodeError, KeyError):
        print("⚠️  警告: 任務鎖檔案格式錯誤")
        return None


def validate_commit_message(message, index_file):
    """驗證 commit message"""
    print(f"🔍 驗證 Commit Message: {message[:80]}...")
    print()

    # 檢查豁免
    if is_exempt_commit(message):
        print("✅ 豁免類型，跳過 Index 檢查")
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
    if not check_index_exists(index, index_file):
        print(f"❌ 錯誤: {index} 不存在於 {index_file}")
        print()
        print(f"請先在 {index_file} 中註冊此 Index")
        return False

    print(f"✅ Index 存在於 {index_file.name}")

    # 檢查鎖一致性
    lock_check = check_lock_consistency(index)
    if lock_check is False:
        return False
    elif lock_check is True:
        print("✅ 任務鎖一致")
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

    # 自動偵測要使用的 Index 檔案
    index_file = detect_index_file()
    print(f"📋 使用 Index: {index_file}")
    print()

    arg = sys.argv[1]
    commit_message = arg
    msg_path = Path(arg)
    if msg_path.exists() and msg_path.is_file():
        commit_message = msg_path.read_text(encoding="utf-8", errors="replace").strip()

    if validate_commit_message(commit_message, index_file):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
