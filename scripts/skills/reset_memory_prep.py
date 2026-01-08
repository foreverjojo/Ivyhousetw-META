"""
記憶重置準備技能 (Memory Reset Prep Skill)

目的：在清除 Agent 記憶前，自動生成完整的交接文件。
功能：備份 task.md、互動式更新任務狀態、同步 walkthrough、生成 handover

使用方式：
  python -m scripts.skills.reset_memory_prep
  from scripts.skills.reset_memory_prep import run_reset_memory_prep
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


def _get_project_root() -> Path:
    """取得專案根目錄，支援環境變數覆寫"""
    env_root = os.environ.get("PROJECT_ROOT")
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parent.parent.parent


PROJECT_ROOT = _get_project_root()
TASK_PATTERN = re.compile(r"^(\s*)-\s*\[([ x/])\]\s*(.+)$", re.MULTILINE)


@dataclass
class TaskItem:
    """單一任務項目"""
    indent: str
    status: str  # ' '=未開始, 'x'=完成, '/'=進行中
    text: str
    line_number: int = 0

    @property
    def is_completed(self) -> bool:
        return self.status == "x"

    @property
    def is_in_progress(self) -> bool:
        return self.status == "/"

    def to_markdown(self) -> str:
        return f"{self.indent}- [{self.status}] {self.text}"


@dataclass
class TaskSummary:
    """任務統計摘要"""
    completed: int = 0
    in_progress: int = 0
    pending: int = 0

    @property
    def total(self) -> int:
        return self.completed + self.in_progress + self.pending


@dataclass
class PrepResult:
    """準備結果"""
    success: bool = False
    backup_path: Optional[Path] = None
    tasks_updated: int = 0
    walkthrough_updated: int = 0
    handover_path: Optional[Path] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 檔案與解析工具
# ---------------------------------------------------------------------------

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_read_file(path: Path) -> Tuple[Optional[str], Optional[str]]:
    """安全讀取檔案，回傳 (內容, 錯誤訊息)"""
    if not path.exists():
        return None, f"檔案不存在：{path.name}"
    try:
        return path.read_text(encoding="utf-8"), None
    except Exception as e:
        return None, f"讀取 {path.name} 失敗：{str(e)}"


def safe_write_file(path: Path, content: str) -> Tuple[bool, Optional[str]]:
    """
    安全寫入檔案 (Atomic Write)
    
    使用 temp 檔 + fsync + rename 機制確保檔案完整性：
    1. 先寫入 .tmp 暫存檔
    2. fsync 確保資料落盤
    3. atomic rename 覆蓋原檔
    
    回傳 (成功與否, 錯誤訊息)
    """
    import tempfile
    
    fd = None
    tmp_file = None
    
    try:
        ensure_dir(path.parent)
        
        # Step 1: 建立暫存檔 (同目錄以確保同一檔案系統)
        fd, tmp_path = tempfile.mkstemp(
            suffix=".tmp",
            prefix=f".{path.stem}_",
            dir=path.parent
        )
        tmp_file = Path(tmp_path)
        
        # Step 2: 寫入內容並 fsync
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                fd = None  # os.fdopen 接管 fd，不需再手動關閉
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            # 若 os.fdopen 失敗，手動關閉 fd
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            raise
        
        # Step 3: Atomic rename (覆蓋原檔)
        tmp_file.replace(path)
        return True, None
        
    except Exception as e:
        # 清理暫存檔 (容錯)
        if tmp_file is not None:
            try:
                tmp_file.unlink(missing_ok=True)
            except OSError:
                pass
        return False, f"寫入 {path.name} 失敗：{str(e)}"


def create_backup(source: Path, backup_dir: Path) -> Optional[Path]:
    if not source.exists():
        return None
    ensure_dir(backup_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{source.name}.{timestamp}.bak"
    try:
        shutil.copy2(source, backup_path)
        return backup_path
    except Exception:
        return None


def parse_tasks(content: str) -> List[TaskItem]:
    tasks: List[TaskItem] = []
    lines = content.split("\n")
    for i, line in enumerate(lines):
        match = TASK_PATTERN.match(line)
        if match:
            indent, status, text = match.groups()
            tasks.append(TaskItem(indent, status, text.strip(), i))
    return tasks


def get_task_summary(tasks: List[TaskItem]) -> TaskSummary:
    summary = TaskSummary()
    for task in tasks:
        if task.is_completed:
            summary.completed += 1
        elif task.is_in_progress:
            summary.in_progress += 1
        else:
            summary.pending += 1
    return summary


def update_task_in_content(content: str, task: TaskItem, new_status: str) -> str:
    lines = content.split("\n")
    if 0 <= task.line_number < len(lines):
        lines[task.line_number] = f"{task.indent}- [{new_status}] {task.text}"
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 互動功能
# ---------------------------------------------------------------------------

def prompt_user(message: str, options: List[str], default: int = 1) -> int:
    print(f"\n{message}")
    for i, opt in enumerate(options, 1):
        marker = " *" if i == default else ""
        print(f"  ({i}) {opt}{marker}")
    while True:
        try:
            inp = input(f"請選擇 [1-{len(options)}，預設 {default}]: ").strip()
            if not inp:
                return default
            choice = int(inp)
            if 1 <= choice <= len(options):
                return choice
        except ValueError:
            pass
        print(f"  無效輸入，請輸入 1-{len(options)} 的數字")


def prompt_yes_no(message: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        inp = input(f"{message} [{hint}]: ").strip().lower()
        if not inp:
            return default
        if inp in ("y", "yes", "是"):
            return True
        if inp in ("n", "no", "否"):
            return False
        print("  請輸入 y 或 n")


# ---------------------------------------------------------------------------
# 核心功能
# ---------------------------------------------------------------------------

def interactive_update_tasks(content: str) -> Tuple[str, int]:
    """互動式更新進行中的任務"""
    tasks = parse_tasks(content)
    in_progress = [t for t in tasks if t.is_in_progress]

    if not in_progress:
        print("\n📋 沒有進行中的任務需要確認。")
        return content, 0

    print(f"\n📋 發現 {len(in_progress)} 個進行中的任務：")
    print("-" * 50)

    updated_count = 0
    updated_content = content

    for task in in_progress:
        print(f"\n  任務：{task.text}")
        choice = prompt_user("  目前狀態？", ["完成 [x]", "保持進行中 [/]", "跳過"], default=2)

        if choice == 1:
            updated_content = update_task_in_content(updated_content, task, "x")
            task.status = "x"
            updated_count += 1
            print("  → 已標記為完成 ✓")
        elif choice == 2:
            print("  → 保持進行中")
        else:
            print("  → 跳過")

    return updated_content, updated_count


def interactive_update_walkthrough(
    task_content: str, walkthrough_content: Optional[str]
) -> Tuple[str, int]:
    """互動式更新 walkthrough.md"""
    tasks = parse_tasks(task_content)
    completed = [t for t in tasks if t.is_completed]

    if not completed:
        print("\n📝 沒有已完成的任務可加入 walkthrough。")
        return walkthrough_content or "", 0

    recent = completed[-5:]
    print(f"\n📝 最近完成的 {len(recent)} 個任務：")
    print("-" * 50)
    for i, task in enumerate(recent, 1):
        print(f"  {i}. {task.text}")

    if not prompt_yes_no("\n是否要將這些任務加入 walkthrough.md？", default=False):
        print("  → 跳過更新 walkthrough")
        return walkthrough_content or "", 0

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entries = "\n".join(f"- {t.text}" for t in recent)
    new_section = f"\n### {timestamp}\n{new_entries}\n"

    if walkthrough_content and "## Recent Updates" in walkthrough_content:
        parts = walkthrough_content.split("## Recent Updates", 1)
        updated = parts[0] + "## Recent Updates\n" + new_section
        if len(parts) > 1:
            updated += parts[1].lstrip("\n")
    elif walkthrough_content:
        updated = walkthrough_content.rstrip() + "\n\n## Recent Updates\n" + new_section
    else:
        updated = f"# Walkthrough\n\n專案開發歷程記錄。\n\n## Recent Updates\n{new_section}"

    print(f"  → 已加入 {len(recent)} 個項目到 walkthrough")
    return updated, len(recent)


def generate_handover(task_content: Optional[str], walkthrough_content: Optional[str]) -> str:
    """生成交接文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if task_content:
        tasks = parse_tasks(task_content)
        summary = get_task_summary(tasks)
        pending_tasks = [t for t in tasks if not t.is_completed]
    else:
        summary = TaskSummary()
        pending_tasks = []

    next_steps = "\n".join(f"- [ ] {t.text}" for t in pending_tasks) if pending_tasks else "- 所有任務已完成"

    known_issues = "None"
    if task_content:
        issues = [f"- {ln.strip()}" for ln in task_content.split("\n")
                  if any(kw in ln.upper() for kw in ["ISSUE", "BUG", "FIXME", "問題"])]
        if issues:
            known_issues = "\n".join(issues)

    return f"""# Handover Document

> 此文件由 Memory Reset Prep Skill 自動生成

## Generated At
{timestamp}

## Current Status

| 狀態 | 數量 |
|------|------|
| ✅ 完成 | {summary.completed} 項 |
| 🔄 進行中 | {summary.in_progress} 項 |
| ⏳ 未開始 | {summary.pending} 項 |
| **總計** | **{summary.total} 項** |

## Next Steps

{next_steps}

## Known Issues

{known_issues}

## Notes

- 交接前請確認所有重要變更已 commit
- 若有未完成的任務，請在新對話開始時提供此文件
"""


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_reset_memory_prep(
    project_root: Optional[Path] = None, interactive: bool = True
) -> PrepResult:
    """執行記憶重置準備"""
    result = PrepResult()
    root = project_root or PROJECT_ROOT
    agent_dir = root / ".agent"
    backup_dir = agent_dir / "backup"
    task_file = agent_dir / "task.md"
    walkthrough_file = agent_dir / "walkthrough.md"
    handover_file = agent_dir / "handover.md.resolved"

    print("=" * 60)
    print("🔄 記憶重置準備程序")
    print("=" * 60)
    print(f"專案目錄：{root}")

    ensure_dir(agent_dir)
    ensure_dir(backup_dir)

    # Step 1: 備份
    print("\n[Step 1/4] 備份 task.md...")
    if task_file.exists():
        backup_path = create_backup(task_file, backup_dir)
        if backup_path:
            result.backup_path = backup_path
            print(f"  ✓ 已備份至：{backup_path.name}")
        else:
            result.warnings.append("無法建立 task.md 備份")
            print("  ⚠ 備份失敗，繼續執行...")
    else:
        print("  ⚠ task.md 不存在，將建立新檔案")
        initial = "# Task List\n\n專案任務追蹤。\n\n## Current Sprint\n\n- [ ] 初始化任務清單\n"
        success, write_err = safe_write_file(task_file, initial)
        if not success:
            result.errors.append(f"無法建立 task.md：{write_err}")
            print(f"  ❌ 建立失敗，中止執行")
            return result
        result.warnings.append("task.md 不存在，已建立初始檔案")

    task_content, task_err = safe_read_file(task_file)
    if task_err:
        result.warnings.append(task_err)
    task_content = task_content or ""
    
    walkthrough_content, wt_err = safe_read_file(walkthrough_file)
    if wt_err and walkthrough_file.exists():  # 不存在不算錯誤
        result.warnings.append(wt_err)

    # Step 2: 更新 task.md
    print("\n[Step 2/4] 檢查進行中的任務...")
    if interactive:
        task_content, tasks_updated = interactive_update_tasks(task_content)
        result.tasks_updated = tasks_updated
        if tasks_updated > 0:
            success, write_err = safe_write_file(task_file, task_content)
            if success:
                print(f"  ✓ task.md 已更新（{tasks_updated} 項變更）")
            else:
                result.errors.append(f"無法寫入 task.md：{write_err}")
    else:
        print("  → 非互動模式，跳過任務確認")

    # Step 3: 更新 walkthrough.md
    print("\n[Step 3/4] 同步 walkthrough.md...")
    if interactive:
        walkthrough_content, wt_updated = interactive_update_walkthrough(task_content, walkthrough_content)
        result.walkthrough_updated = wt_updated
        if wt_updated > 0:
            success, write_err = safe_write_file(walkthrough_file, walkthrough_content)
            if success:
                print(f"  ✓ walkthrough.md 已更新（{wt_updated} 項新增）")
            else:
                result.errors.append(f"無法寫入 walkthrough.md：{write_err}")
    else:
        print("  → 非互動模式，跳過 walkthrough 更新")

    # Step 4: 生成 handover
    print("\n[Step 4/4] 生成交接文件...")
    handover_content = generate_handover(task_content, walkthrough_content)
    success, write_err = safe_write_file(handover_file, handover_content)
    if success:
        result.handover_path = handover_file
        print(f"  ✓ 已生成：{handover_file.name}")
    else:
        result.errors.append(f"無法生成 handover.md.resolved：{write_err}")

    # 結果
    print("\n" + "=" * 60)
    if not result.errors:
        result.success = True
        print("✅ 交接準備完成！您現在可以安全地清除 Agent 記憶。")
        print(f"\n📄 交接文件位置：{handover_file}")
    else:
        print("❌ 準備過程發生錯誤：")
        for err in result.errors:
            print(f"  - {err}")

    if result.warnings:
        print("\n⚠ 警告：")
        for warn in result.warnings:
            print(f"  - {warn}")

    print("=" * 60)
    return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="記憶重置準備 - 生成交接文件")
    parser.add_argument("--project-root", type=Path, default=None, help="專案根目錄")
    parser.add_argument("--non-interactive", action="store_true", help="非互動模式")
    args = parser.parse_args()

    result = run_reset_memory_prep(project_root=args.project_root, interactive=not args.non_interactive)
    exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
