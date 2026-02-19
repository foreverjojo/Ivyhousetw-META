#!/usr/bin/env python3
"""
Git 分支管理腳本

功能：
- create <index>: 建立任務分支（task/Idx-NNN）
- merge <index>: 合併分支到 main
- abort <index>: 中止任務並刪除分支

基於五條鐵律中的 Parallel Isolation 和 Execution Mode Recording 原則
"""

import subprocess
import sys


def run_command(cmd, check=True):
    """執行 shell 指令"""
    try:
        result = subprocess.run(
            cmd, shell=True, check=check, capture_output=True, text=True, encoding="utf-8"
        )
        return result.stdout.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stderr.strip(), e.returncode


def get_current_branch():
    """取得當前分支名稱"""
    output, code = run_command("git rev-parse --abbrev-ref HEAD", check=False)
    if code == 0:
        return output
    return None


def branch_exists(branch_name):
    """檢查分支是否存在"""
    output, code = run_command(f"git rev-parse --verify {branch_name}", check=False)
    return code == 0


def has_uncommitted_changes():
    """檢查是否有未提交的變更"""
    output, code = run_command("git status --porcelain", check=False)
    return len(output) > 0


def create_branch(index):
    """建立任務分支"""
    branch_name = f"task/{index}"

    # 檢查是否在 main 分支
    current_branch = get_current_branch()
    if current_branch != "main":
        print(f"⚠️  警告: 當前分支是 {current_branch}，不是 main")
        response = input("是否繼續？(yes/no): ")
        if response.lower() != "yes":
            print("❌ 取消操作")
            return False

    # 檢查分支是否已存在
    if branch_exists(branch_name):
        print(f"❌ 錯誤: 分支 {branch_name} 已存在")
        print("   請先刪除舊分支或使用 checkout：")
        print(f"   git checkout {branch_name}")
        return False

    # 檢查未提交變更
    if has_uncommitted_changes():
        print("❌ 錯誤: 有未提交的變更")
        print("   請先 commit 或 stash 變更")
        return False

    # 建立並切換分支
    print(f"🌿 建立分支: {branch_name}")
    output, code = run_command(f"git checkout -b {branch_name}")

    if code == 0:
        print(f"✅ 成功建立並切換到分支: {branch_name}")
        print()
        print("下一步：")
        print("  1. 執行任務開發")
        print(f"  2. git commit -m 'feat({index}): 描述'")
        print(f"  3. QA 審查後執行: python scripts/task_branch.py merge {index}")
        return True
    else:
        print(f"❌ 錯誤: {output}")
        return False


def merge_branch(index):
    """合併分支到 main"""
    branch_name = f"task/{index}"

    # 檢查分支是否存在
    if not branch_exists(branch_name):
        print(f"❌ 錯誤: 分支 {branch_name} 不存在")
        return False

    # 檢查當前分支
    current_branch = get_current_branch()
    if current_branch != branch_name:
        print(f"⚠️  當前分支是 {current_branch}")
        print(f"   切換到 {branch_name}...")
        run_command(f"git checkout {branch_name}")

    # 檢查未提交變更
    if has_uncommitted_changes():
        print("❌ 錯誤: 有未提交的變更")
        print("   請先 commit 變更")
        return False

    # 確認 QA 通過
    print("⚠️  請確認：")
    print("   1. QA 審查已通過")
    print("   2. 所有測試都通過")
    print("   3. 準備合併到 main")
    print()
    response = input("確定繼續？(yes/no): ")

    if response.lower() != "yes":
        print("❌ 取消操作")
        return False

    # 切換到 main
    print("🔄 切換到 main 分支...")
    output, code = run_command("git checkout main")
    if code != 0:
        print(f"❌ 錯誤: {output}")
        return False

    # 合併分支
    print(f"🔀 合併 {branch_name} 到 main...")
    output, code = run_command(f"git merge {branch_name} --no-ff", check=False)

    if code != 0:
        print(f"❌ 合併失敗: {output}")
        print()
        print("請手動解決衝突後執行：")
        print("  git merge --continue")
        return False

    print(f"✅ 成功合併 {branch_name} 到 main")

    # 詢問是否刪除分支
    response = input(f"\n是否刪除分支 {branch_name}？(yes/no): ")
    if response.lower() == "yes":
        run_command(f"git branch -d {branch_name}")
        print(f"✅ 已刪除分支 {branch_name}")

    print()
    print("下一步：")
    print(f"  1. python scripts/check_active_task.py release {index}")
    print("  2. 更新 doc/Implementation_Plan_index.md（狀態改為 COMPLETED）")
    print(f"  3. 完成 Log: doc/logs/{index}_log.md")

    return True


def abort_branch(index):
    """中止任務並刪除分支"""
    branch_name = f"task/{index}"

    # 檢查分支是否存在
    if not branch_exists(branch_name):
        print(f"❌ 錯誤: 分支 {branch_name} 不存在")
        return False

    # 確認操作
    print("⚠️  警告: 此操作將：")
    print(f"   1. 刪除分支 {branch_name}")
    print("   2. 丟棄該分支上的所有變更")
    print("   3. 無法恢復")
    print()
    response = input("確定要中止任務？(yes/no): ")

    if response.lower() != "yes":
        print("❌ 取消操作")
        return False

    # 切換到 main
    current_branch = get_current_branch()
    if current_branch == branch_name:
        print("🔄 切換到 main 分支...")
        output, code = run_command("git checkout main")
        if code != 0:
            print(f"❌ 錯誤: {output}")
            return False

    # 強制刪除分支
    print(f"🗑️  刪除分支 {branch_name}...")
    output, code = run_command(f"git branch -D {branch_name}")

    if code == 0:
        print(f"✅ 已刪除分支 {branch_name}")
        print()
        print("下一步：")
        print(f"  1. python scripts/check_active_task.py release {index}")
        print("  2. 更新 doc/Implementation_Plan_index.md（狀態改為 ABORTED）")
        print("  3. 記錄 Log 並說明中止原因")
        return True
    else:
        print(f"❌ 錯誤: {output}")
        return False


def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python scripts/task_branch.py create <index>")
        print("  python scripts/task_branch.py merge <index>")
        print("  python scripts/task_branch.py abort <index>")
        print()
        print("範例:")
        print("  python scripts/task_branch.py create Idx-001")
        print("  python scripts/task_branch.py merge Idx-001")
        print("  python scripts/task_branch.py abort Idx-001")
        sys.exit(1)

    command = sys.argv[1]

    if len(sys.argv) < 3:
        print("❌ 錯誤: 請提供 Index (例如: Idx-001)")
        sys.exit(1)

    index = sys.argv[2]

    # 驗證 Index 格式
    if not index.startswith("Idx-"):
        print("❌ 錯誤: Index 格式錯誤（應為 Idx-NNN）")
        sys.exit(1)

    if command == "create":
        success = create_branch(index)
    elif command == "merge":
        success = merge_branch(index)
    elif command == "abort":
        success = abort_branch(index)
    else:
        print(f"❌ 未知指令: {command}")
        print("\n有效指令: create, merge, abort")
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
