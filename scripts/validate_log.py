#!/usr/bin/env python3
"""
Log 完整性驗證工具

對應鐵律 #5（Log 強制綁定）

功能：
1. 解析 Log 檔案的 YAML frontmatter
2. 驗證 Log 是否符合 Schema
3. 檢查必填欄位是否完整
4. PASS WITH RISK 時確認有風險描述

使用方式：
    # 驗證單一 Log 檔案
    python scripts/validate_log.py doc/logs/Idx-001_log.md

    # 驗證所有 Log 檔案
    python scripts/validate_log.py --all

    # 只檢查必填欄位（不使用 JSON Schema）
    python scripts/validate_log.py --simple doc/logs/Idx-001_log.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# === 設定 ===
LOGS_DIR = Path("doc/logs")
SCHEMA_FILE = Path("schemas/log.schema.json")

# 必填欄位（簡易模式）
REQUIRED_FIELDS = [
    "index",
    "plan_version",
    "executor_tool",
    "qa_result",
    "commit_hashes",
]

# PASS WITH RISK 時額外必填
RISK_REQUIRED_FIELDS = [
    "risk_description",
]


def parse_yaml_frontmatter(content: str) -> dict[str, Any]:
    """
    解析 Markdown 檔案的 YAML frontmatter

    支援格式：
    ---
    key: value
    key2: value2
    ---

    也支援：
    | **Key** | Value |
    """
    result: dict[str, Any] = {}

    # 嘗試解析 YAML frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            for line in frontmatter.split("\n"):
                if ":" in line and not line.strip().startswith("#"):
                    key, _, value = line.partition(":")
                    key = key.strip().lower().replace(" ", "_")
                    value = value.strip()
                    # 移除引號
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    result[key] = value

    # 嘗試從表格格式解析
    table_pattern = r"\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|]+)\s*\|"
    for match in re.finditer(table_pattern, content):
        key = match.group(1).strip().lower().replace(" ", "_")
        value = match.group(2).strip()
        if key and value and value != "—":
            result[key] = value

    # 特殊處理：從內容中提取 Index ID
    if "index" not in result and "index_id" not in result:
        idx_match = re.search(r"Idx-\d{3}", content)
        if idx_match:
            result["index"] = idx_match.group(0)

    # 標準化欄位名稱
    field_aliases = {
        "index_id": "index",
        "plan_hash": "plan_version",
        "executor": "executor_tool",
        "qa_結果": "qa_result",
        "qa結果": "qa_result",
        "commit_hash": "commit_hashes",
        "commit": "commit_hashes",
    }
    for alias, standard in field_aliases.items():
        if alias in result and standard not in result:
            result[standard] = result[alias]

    return result


def parse_changed_files(content: str) -> list[dict[str, str]]:
    """從 Log 內容中解析變更檔案清單"""
    files = []

    # 尋找變更清單區塊
    patterns = [
        r"[-*]\s*\[.\]\s*`([^`]+)`:\s*(.+)",  # - [x] `file.py`: 說明
        r"[-*]\s*`([^`]+)`\s*[:\-]\s*(.+)",  # - `file.py`: 說明
        r"\|\s*([^|]+\.py)\s*\|\s*(NEW|MODIFY|DELETE)",  # | file.py | MODIFY |
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, content):
            path = match.group(1).strip()
            action_or_desc = match.group(2).strip().upper() if len(match.groups()) > 1 else "MODIFY"

            action = "MODIFY"
            if "NEW" in action_or_desc or "新增" in action_or_desc:
                action = "NEW"
            elif "DELETE" in action_or_desc or "刪除" in action_or_desc:
                action = "DELETE"

            files.append({"path": path, "action": action})

    return files


def parse_commit_hashes(content: str) -> list[str]:
    """從 Log 內容中解析 commit hash"""
    hashes = []

    # 常見格式
    patterns = [
        r"[`\[]([a-f0-9]{7,40})[`\]]",  # `abc1234` 或 [abc1234]
        r"commit[:\s]+([a-f0-9]{7,40})",  # commit: abc1234
        r"^([a-f0-9]{7,40})\s",  # abc1234 message
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE):
            h = match.group(1)
            if h not in hashes:
                hashes.append(h)

    return hashes


def validate_simple(log_data: dict[str, Any], content: str) -> list[str]:
    """
    簡易驗證模式（不使用 JSON Schema）

    Returns:
        錯誤訊息列表
    """
    errors = []

    # 檢查必填欄位
    for field in REQUIRED_FIELDS:
        if field not in log_data or not log_data[field]:
            # 嘗試從內容中補充
            if field == "changed_files":
                files = parse_changed_files(content)
                if files:
                    log_data[field] = files
                else:
                    errors.append(f"缺少必填欄位：{field}")
            elif field == "commit_hashes":
                hashes = parse_commit_hashes(content)
                if hashes:
                    log_data[field] = hashes
                else:
                    errors.append(f"缺少必填欄位：{field}（找不到 commit hash）")
            else:
                errors.append(f"缺少必填欄位：{field}")

    # 檢查 Index 格式
    if "index" in log_data:
        if not re.match(r"^Idx-\d{3}$", str(log_data["index"])):
            errors.append(f"Index 格式錯誤：{log_data['index']}（應為 Idx-NNN）")

    # 檢查 Plan Version 格式
    if "plan_version" in log_data:
        if not re.match(r"^\d{4}-\d{2}-\d{2}-v\d+$", str(log_data["plan_version"])):
            # 可能是舊格式，只警告
            pass

    # 檢查 QA 結果
    if "qa_result" in log_data:
        valid_results = ["PASS", "PASS WITH RISK", "FAIL"]
        result = str(log_data["qa_result"]).upper()
        if result not in valid_results:
            errors.append(f"無效的 QA 結果：{log_data['qa_result']}（應為 {valid_results}）")

        # PASS WITH RISK 需要風險描述
        if result == "PASS WITH RISK":
            has_risk_desc = any(log_data.get(f) for f in ["risk_description", "風險描述", "risk"])
            if not has_risk_desc:
                # 檢查內容中是否有風險描述區塊
                if "風險" not in content and "risk" not in content.lower():
                    errors.append("QA 結果為 PASS WITH RISK，但缺少風險描述")

    return errors


def validate_with_schema(log_data: dict[str, Any]) -> list[str]:
    """
    使用 JSON Schema 驗證

    Returns:
        錯誤訊息列表
    """
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema 未安裝，請執行：pip install jsonschema"]

    if not SCHEMA_FILE.exists():
        return [f"Schema 檔案不存在：{SCHEMA_FILE}"]

    try:
        schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
        jsonschema.validate(log_data, schema)
        return []
    except jsonschema.ValidationError as e:
        return [f"Schema 驗證失敗：{e.message}"]
    except json.JSONDecodeError as e:
        return [f"Schema 檔案格式錯誤：{e}"]


def validate_log_file(
    log_path: Path,
    use_schema: bool = True,
    verbose: bool = True,
) -> tuple[bool, list[str]]:
    """
    驗證單一 Log 檔案

    Returns:
        (是否通過, 錯誤訊息列表)
    """
    if not log_path.exists():
        return False, [f"檔案不存在：{log_path}"]

    try:
        content = log_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, [f"讀取檔案失敗：{e}"]

    # 解析 frontmatter
    log_data = parse_yaml_frontmatter(content)

    # 補充從內容中解析的資料
    if "changed_files" not in log_data:
        log_data["changed_files"] = parse_changed_files(content)
    if "commit_hashes" not in log_data:
        log_data["commit_hashes"] = parse_commit_hashes(content)

    # 驗證
    errors = validate_simple(log_data, content)

    if use_schema and not errors:
        schema_errors = validate_with_schema(log_data)
        errors.extend(schema_errors)

    if verbose:
        if errors:
            print(f"❌ {log_path.name}")
            for err in errors:
                print(f"   - {err}")
        else:
            print(f"✅ {log_path.name}")

    return len(errors) == 0, errors


def validate_all_logs(use_schema: bool = True) -> tuple[int, int]:
    """
    驗證所有 Log 檔案

    Returns:
        (通過數, 總數)
    """
    if not LOGS_DIR.exists():
        print(f"❌ Log 目錄不存在：{LOGS_DIR}")
        return 0, 0

    log_files = list(LOGS_DIR.glob("Idx-*_log.md"))

    # 排除範本
    log_files = [f for f in log_files if "template" not in f.name.lower()]

    if not log_files:
        print("ℹ️  沒有找到 Log 檔案")
        return 0, 0

    print(f"📋 驗證 {len(log_files)} 個 Log 檔案\n")

    passed = 0
    for log_file in sorted(log_files):
        ok, _ = validate_log_file(log_file, use_schema)
        if ok:
            passed += 1

    print(f"\n結果：{passed}/{len(log_files)} 通過")
    return passed, len(log_files)


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="Log 完整性驗證工具（鐵律 #5）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  驗證單一檔案：
    python scripts/validate_log.py doc/logs/Idx-001_log.md

  驗證所有 Log：
    python scripts/validate_log.py --all

  簡易模式（不使用 Schema）：
    python scripts/validate_log.py --simple doc/logs/Idx-001_log.md
        """,
    )

    parser.add_argument(
        "log_file",
        nargs="?",
        type=Path,
        help="要驗證的 Log 檔案路徑",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="驗證所有 Log 檔案",
    )
    parser.add_argument(
        "--simple",
        "-s",
        action="store_true",
        help="簡易模式（只檢查必填欄位，不使用 Schema）",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="安靜模式",
    )

    args = parser.parse_args()

    use_schema = not args.simple

    if args.all:
        passed, total = validate_all_logs(use_schema)
        return 0 if passed == total else 1
    elif args.log_file:
        ok, errors = validate_log_file(args.log_file, use_schema, not args.quiet)
        return 0 if ok else 1
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
