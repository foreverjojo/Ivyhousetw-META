#!/usr/bin/env python3
"""
驗證計畫到期檢查工具

對應 P1 改進：PASS WITH RISK 的驗證計畫追蹤

功能：
1. 從 Implementation_Plan_index.md 讀取待驗證項目
2. 檢查是否有到期或即將到期的驗證計畫
3. 輸出提醒訊息

使用方式：
    # 檢查驗證計畫
    python scripts/check_verification_due.py

    # 只顯示逾期項目
    python scripts/check_verification_due.py --overdue-only

    # 作為每日提醒（CI 中使用）
    python scripts/check_verification_due.py --ci
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

# === 設定 ===
INDEX_FILE = Path("doc/Implementation_Plan_index.md")
TECH_DEBT_FILE = Path("doc/tech_debt.md")


class VerificationItem(NamedTuple):
    """待驗證項目"""

    index: str
    title: str
    qa_result: str
    verification_plan: str
    due_date: str
    status: str


def parse_date(date_str: str) -> datetime | None:
    """解析日期字串"""
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def parse_index_for_verifications() -> list[VerificationItem]:
    """
    從 Implementation_Plan_index.md 解析待驗證項目

    尋找含有「驗證」「待驗證」「PASS WITH RISK」的行
    """
    if not INDEX_FILE.exists():
        return []

    content = INDEX_FILE.read_text(encoding="utf-8")
    items = []

    # 尋找表格行
    for line in content.split("\n"):
        if "|" not in line:
            continue

        # 檢查是否包含 PASS WITH RISK 或待驗證
        if "PASS WITH RISK" not in line.upper() and "待驗證" not in line:
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 5:
            continue

        # 嘗試解析
        idx = None
        title = None
        qa_result = None
        verification_plan = ""
        due_date = ""
        status = "⏳ 待驗證"

        for _i, part in enumerate(parts):
            if re.match(r"Idx-\d{3}", part):
                idx = part
            elif "PASS WITH RISK" in part.upper():
                qa_result = "PASS WITH RISK"
            elif re.match(r"\d{4}-\d{2}-\d{2}", part):
                due_date = re.search(r"\d{4}-\d{2}-\d{2}", part).group()
            elif "驗證" in part or "監控" in part:
                verification_plan = part

        # 需要 title，通常在 index 後面
        if idx:
            for i, part in enumerate(parts):
                if idx in part and i + 1 < len(parts):
                    title = parts[i + 1]
                    break

        if idx and (qa_result or "待驗證" in line):
            items.append(
                VerificationItem(
                    index=idx,
                    title=title or "",
                    qa_result=qa_result or "PASS WITH RISK",
                    verification_plan=verification_plan,
                    due_date=due_date,
                    status=status,
                )
            )

    return items


def check_due_verifications(
    items: list[VerificationItem],
    warn_days: int = 3,
) -> tuple[list[tuple[VerificationItem, int]], list[tuple[VerificationItem, int]]]:
    """
    檢查到期的驗證計畫

    Returns:
        (逾期項目列表, 即將到期項目列表)
        每個項目是 (VerificationItem, 天數差)
    """
    today = datetime.today()
    overdue = []
    due_soon = []

    for item in items:
        if not item.due_date:
            continue

        due = parse_date(item.due_date)
        if not due:
            continue

        days_diff = (due - today).days

        if days_diff < 0:
            overdue.append((item, abs(days_diff)))
        elif days_diff <= warn_days:
            due_soon.append((item, days_diff))

    return overdue, due_soon


def print_results(
    overdue: list[tuple[VerificationItem, int]],
    due_soon: list[tuple[VerificationItem, int]],
    ci_mode: bool = False,
) -> None:
    """輸出結果"""
    if overdue:
        print("\n🔴 逾期的驗證計畫：")
        print("=" * 60)
        for item, days in overdue:
            print(f"   {item.index}: {item.title}")
            print(f"   └─ 逾期 {days} 天（原定：{item.due_date}）")
            if item.verification_plan:
                print(f"   └─ 驗證計畫：{item.verification_plan}")
            print()

    if due_soon:
        print("\n⚠️  即將到期的驗證計畫：")
        print("=" * 60)
        for item, days in due_soon:
            print(f"   {item.index}: {item.title}")
            if days == 0:
                print("   └─ 今天到期！")
            else:
                print(f"   └─ {days} 天後到期（{item.due_date}）")
            if item.verification_plan:
                print(f"   └─ 驗證計畫：{item.verification_plan}")
            print()

    if not overdue and not due_soon:
        print("✅ 沒有到期或即將到期的驗證計畫")

    # CI 模式輸出
    if ci_mode:
        if overdue:
            print("\n::warning::有逾期的驗證計畫需要處理")
        if due_soon:
            print("\n::notice::有即將到期的驗證計畫")


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="驗證計畫到期檢查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  檢查所有驗證計畫：
    python scripts/check_verification_due.py

  只顯示逾期項目：
    python scripts/check_verification_due.py --overdue-only

  作為 CI 提醒：
    python scripts/check_verification_due.py --ci
        """,
    )

    parser.add_argument(
        "--overdue-only",
        action="store_true",
        help="只顯示逾期項目",
    )
    parser.add_argument(
        "--warn-days",
        type=int,
        default=3,
        help="提前警告天數（預設 3 天）",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI 模式（輸出 GitHub Actions 格式的警告）",
    )

    args = parser.parse_args()

    # 解析待驗證項目
    items = parse_index_for_verifications()

    if not items:
        print("ℹ️  沒有找到待驗證項目")
        print("   （提示：在 Implementation_Plan_index.md 中標記 PASS WITH RISK 的項目）")
        return 0

    print(f"📋 找到 {len(items)} 個待驗證項目")

    # 檢查到期狀態
    overdue, due_soon = check_due_verifications(items, args.warn_days)

    if args.overdue_only:
        print_results(overdue, [], args.ci)
    else:
        print_results(overdue, due_soon, args.ci)

    # 返回值：有逾期則返回 1
    return 1 if overdue else 0


if __name__ == "__main__":
    sys.exit(main())
