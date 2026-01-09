# -*- coding: utf-8 -*-
"""
.agent/skills/code_reviewer.py
=====================================
用途：代碼品質審查工具
職責：靜態分析 Python 檔案，檢查 API Key 洩漏、檔案長度、中文註釋等
=====================================

使用方式：
    python .agent/skills/code_reviewer.py <file_path>

輸出：
    JSON 格式報告，包含 pass/fail 狀態與問題列表
"""

import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any


# 敏感金鑰的正規表達式模式
API_KEY_PATTERNS = [
    r"sk-[a-zA-Z0-9]{20,}",           # OpenAI / OpenRouter 格式
    r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]",  # api_key = "xxx"
    r"ANTHROPIC_API_KEY\s*=\s*['\"][^'\"]+['\"]",
    r"GOOGLE_API_KEY\s*=\s*['\"][^'\"]+['\"]",
    r"secret[_-]?key\s*=\s*['\"][^'\"]+['\"]",
]

# 常數設定
MAX_FILE_LINES = 500
MIN_CHINESE_LINES = 5


def check_api_key_leak(content: str, lines: List[str]) -> List[Dict[str, Any]]:
    """檢查是否有 API Key 洩漏"""
    issues = []
    for pattern in API_KEY_PATTERNS:
        for i, line in enumerate(lines, start=1):
            # 跳過註釋行
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if re.search(pattern, line, re.IGNORECASE):
                issues.append({
                    "type": "api_key_leak",
                    "line": i,
                    "message": f"偵測到可能的 API Key 洩漏：{stripped[:50]}..."
                })
    return issues


def check_file_length(lines: List[str]) -> List[Dict[str, Any]]:
    """檢查檔案行數是否超過限制"""
    issues = []
    line_count = len(lines)
    if line_count > MAX_FILE_LINES:
        issues.append({
            "type": "file_too_long",
            "line": line_count,
            "message": f"檔案共 {line_count} 行，超過 {MAX_FILE_LINES} 行限制，建議拆分模組"
        })
    return issues


def check_chinese_comments(lines: List[str]) -> List[Dict[str, Any]]:
    """檢查前幾行是否包含中文註釋"""
    issues = []
    has_chinese = False
    check_range = min(len(lines), MIN_CHINESE_LINES)

    chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
    for line in lines[:check_range]:
        if chinese_pattern.search(line):
            has_chinese = True
            break

    if not has_chinese:
        issues.append({
            "type": "missing_chinese_comment",
            "line": 1,
            "message": f"前 {check_range} 行未發現中文註釋，請在檔案開頭加入繁體中文用途說明"
        })
    return issues


def review_file(file_path: str) -> Dict[str, Any]:
    """執行完整的代碼審查"""
    path = Path(file_path)

    # 檢查檔案是否存在
    if not path.exists():
        return {
            "status": "error",
            "file": file_path,
            "message": f"檔案不存在：{file_path}",
            "issues": []
        }

    # 讀取檔案內容
    try:
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
    except Exception as e:
        return {
            "status": "error",
            "file": file_path,
            "message": f"讀取檔案失敗：{str(e)}",
            "issues": []
        }

    # 收集所有問題
    all_issues = []
    all_issues.extend(check_api_key_leak(content, lines))
    all_issues.extend(check_file_length(lines))
    all_issues.extend(check_chinese_comments(lines))

    # 判定結果
    has_critical = any(i["type"] == "api_key_leak" for i in all_issues)
    status = "fail" if has_critical else ("warning" if all_issues else "pass")

    return {
        "status": status,
        "file": file_path,
        "line_count": len(lines),
        "issues": all_issues,
        "summary": {
            "api_key_leak": sum(1 for i in all_issues if i["type"] == "api_key_leak"),
            "file_too_long": sum(1 for i in all_issues if i["type"] == "file_too_long"),
            "missing_chinese_comment": sum(1 for i in all_issues if i["type"] == "missing_chinese_comment"),
        }
    }


def main():
    """主程式入口"""
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "error",
            "message": "使用方式：python code_reviewer.py <file_path>"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    file_path = sys.argv[1]
    result = review_file(file_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 根據狀態設定退出碼
    if result["status"] == "fail":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
