# -*- coding: utf-8 -*-
"""
.agent/skills/skill_converter.py
=====================================
用途：技能轉換流水線模組
職責：
  - 驗證使用者批准狀態
  - 為下載的技能腳本加入繁體中文 Header
  - 適配代碼為專案規範格式
  - 自動更新 __init__.py 與 SKILL.md
=====================================

使用方式：
    由 github_explorer.py 內部調用，不建議直接執行

安全機制：
    ⚠️ 必須通過 --confirm 參數才能執行任何轉換操作
"""

import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple


# =========================
# 常數設定
# =========================
SKILLS_DIR = Path(__file__).parent
INIT_FILE = SKILLS_DIR / "__init__.py"
SKILL_MD_FILE = SKILLS_DIR / "SKILL.md"

# 標準 Header 模板
HEADER_TEMPLATE = '''# -*- coding: utf-8 -*-
"""
{file_path}
=====================================
用途：{description}
來源：{source_repo}
下載日期：{download_date}
=====================================

⚠️ 此技能由 GitHub Explorer 自動下載並轉換
原始來源：https://github.com/{source_repo}
"""

'''


# =========================
# 批准驗證
# =========================
def validate_approval(user_confirmed: bool) -> Dict[str, Any]:
    """
    驗證使用者是否已確認批准下載
    
    ⚠️ 這是安全機制的核心，禁止跳過
    
    參數:
        user_confirmed: 使用者是否已確認 (--confirm 參數)
    
    回傳:
        驗證結果的 JSON 物件
    """
    if not user_confirmed:
        return {
            "status": "blocked",
            "approved": False,
            "message": "⛔ 安全機制：必須先執行 preview 並加上 --confirm 參數確認下載",
            "action_required": "請使用：python github_explorer.py download <repo> <file> --confirm"
        }
    
    return {
        "status": "success",
        "approved": True,
        "message": "✅ 使用者已確認批准"
    }


# =========================
# 中文 Header 處理
# =========================
def has_chinese_header(content: str) -> bool:
    """
    檢查檔案是否已有中文註釋 Header
    
    參數:
        content: 檔案內容
    
    回傳:
        是否有中文 Header
    """
    # 檢查前 10 行是否包含中文
    lines = content.split("\n")[:10]
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
    
    for line in lines:
        if chinese_pattern.search(line):
            return True
    return False


def add_chinese_header(
    content: str,
    skill_name: str,
    source_repo: str,
    description: Optional[str] = None
) -> Tuple[str, bool]:
    """
    為技能腳本加入繁體中文 Header
    
    參數:
        content: 原始檔案內容
        skill_name: 技能名稱
        source_repo: 來源 Repo (owner/repo)
        description: 技能描述 (若無則自動提取)
    
    回傳:
        (轉換後內容, 是否有變更)
    """
    # 若已有中文 Header，不重複加入
    if has_chinese_header(content):
        return content, False
    
    # 自動提取 description
    if not description:
        # 嘗試從 docstring 提取
        docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if docstring_match:
            first_line = docstring_match.group(1).strip().split("\n")[0]
            description = first_line[:50] if first_line else f"來自 {source_repo} 的技能"
        else:
            description = f"來自 {source_repo} 的技能"
    
    # 移除原有的 encoding 宣告 (避免重複)
    content = re.sub(r'^# -\*- coding: utf-8 -\*-\s*\n?', '', content)
    
    # 生成 Header
    header = HEADER_TEMPLATE.format(
        file_path=f".agent/skills/{skill_name}.py",
        description=description,
        source_repo=source_repo,
        download_date=datetime.now().strftime("%Y-%m-%d")
    )
    
    return header + content, True


# =========================
# 代碼適配
# =========================
def adapt_to_project_convention(content: str) -> Tuple[str, list]:
    """
    將代碼適配為專案規範格式
    
    參數:
        content: 原始檔案內容
    
    回傳:
        (轉換後內容, 變更清單)
    """
    changes = []
    
    # 1. 移除可能的 hardcoded 路徑
    hardcoded_patterns = [
        (r'/home/\w+/', '/path/to/'),
        (r'C:\\\\Users\\\\[^\\\\]+\\\\', 'C:\\\\Users\\\\user\\\\'),
        (r"C:/Users/[^/]+/", 'C:/Users/user/'),
    ]
    
    for pattern, replacement in hardcoded_patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            changes.append(f"移除 hardcoded 路徑模式: {pattern}")
    
    # 2. 確保有 ensure_ascii=False 於 json.dumps
    if 'json.dumps' in content and 'ensure_ascii' not in content:
        # 這是一個警告，不自動修改
        changes.append("⚠️ 建議：json.dumps 應加入 ensure_ascii=False 以支援中文")
    
    # 3. 檢查是否有 API Key 相關的 hardcode (僅警告)
    api_key_patterns = [
        r'sk-[a-zA-Z0-9]{20,}',
        r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
    ]
    
    for pattern in api_key_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            changes.append("🚨 警告：偵測到可能的 API Key，請手動檢查")
    
    return content, changes


# =========================
# 自動更新 __init__.py
# =========================
def update_init_py(skill_name: str) -> Dict[str, Any]:
    """
    更新 __init__.py 的 AVAILABLE_SKILLS 清單
    
    參數:
        skill_name: 要加入的技能名稱
    
    回傳:
        更新結果的 JSON 物件
    """
    if not INIT_FILE.exists():
        return {
            "status": "error",
            "message": f"找不到 {INIT_FILE}"
        }
    
    try:
        content = INIT_FILE.read_text(encoding="utf-8")
        
        # 檢查是否已存在
        if f'"{skill_name}"' in content or f"'{skill_name}'" in content:
            return {
                "status": "skipped",
                "message": f"技能 {skill_name} 已存在於 AVAILABLE_SKILLS"
            }
        
        # 找到 AVAILABLE_SKILLS 清單並加入新技能
        pattern = r'(AVAILABLE_SKILLS\s*=\s*\[)'
        if not re.search(pattern, content):
            return {
                "status": "error",
                "message": "找不到 AVAILABLE_SKILLS 清單"
            }
        
        # 找到清單的結尾 ] 並在前面插入新技能
        # 使用更簡單的方式：找到最後一個已有的技能並在其後加入
        lines = content.split("\n")
        new_lines = []
        added = False
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            # 找到 AVAILABLE_SKILLS 區塊中的最後一個項目
            if not added and 'AVAILABLE_SKILLS' in content:
                if '"github_explorer"' in line or "'github_explorer'" in line:
                    # 在 github_explorer 後面加入新技能
                    indent = len(line) - len(line.lstrip())
                    new_lines.append(f'{" " * indent}"{skill_name}",')
                    added = True
        
        if not added:
            # 備用方案：直接在 ] 前加入
            content = re.sub(
                r'(\s*"github_explorer",?\s*)\]',
                f'\\1    "{skill_name}",\n]',
                content
            )
            INIT_FILE.write_text(content, encoding="utf-8")
        else:
            INIT_FILE.write_text("\n".join(new_lines), encoding="utf-8")
        
        return {
            "status": "success",
            "message": f"✅ 已將 {skill_name} 加入 AVAILABLE_SKILLS"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"更新 __init__.py 失敗：{str(e)}"
        }


# =========================
# 自動更新 SKILL.md
# =========================
def update_skill_md(
    skill_name: str,
    description: str,
    usage: str,
    source_repo: str
) -> Dict[str, Any]:
    """
    更新 SKILL.md 技能文件
    
    參數:
        skill_name: 技能名稱
        description: 技能描述
        usage: 使用方式
        source_repo: 來源 Repo
    
    回傳:
        更新結果的 JSON 物件
    """
    if not SKILL_MD_FILE.exists():
        return {
            "status": "error",
            "message": f"找不到 {SKILL_MD_FILE}"
        }
    
    try:
        content = SKILL_MD_FILE.read_text(encoding="utf-8")
        
        # 檢查是否已存在
        if f"`{skill_name}`" in content:
            return {
                "status": "skipped",
                "message": f"技能 {skill_name} 已存在於 SKILL.md"
            }
        
        # 1. 在「可用技能一覽」表格新增一行
        table_pattern = r'(\| `github_explorer` \|[^\n]+\n)'
        table_row = f'| `{skill_name}` | {description} | `python .agent/skills/{skill_name}.py` |\n'
        
        if re.search(table_pattern, content):
            content = re.sub(table_pattern, f'\\1{table_row}', content)
        
        # 2. 在「技能詳細說明」區塊新增文件 (在 github_explorer 之後)
        detail_section = f'''
### {len([m for m in re.finditer(r'### \d+\.', content)]) + 1}. {skill_name}.py (外部技能)

**功能**：{description}

**來源**：[{source_repo}](https://github.com/{source_repo})

**調用方式**：
```bash
{usage}
```

**下載日期**：{datetime.now().strftime("%Y-%m-%d")}

'''
        
        # 找到「未來技能」區塊並在其前面插入
        future_pattern = r'(---\s*\n\s*## 🚧 未來技能)'
        if re.search(future_pattern, content):
            content = re.sub(future_pattern, f'{detail_section}\\1', content)
        
        SKILL_MD_FILE.write_text(content, encoding="utf-8")
        
        return {
            "status": "success",
            "message": f"✅ 已將 {skill_name} 加入 SKILL.md"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"更新 SKILL.md 失敗：{str(e)}"
        }


# =========================
# 完整轉換流程
# =========================
def convert_skill(
    file_path: str,
    skill_name: str,
    source_repo: str,
    description: Optional[str] = None,
    user_confirmed: bool = False
) -> Dict[str, Any]:
    """
    執行完整的技能轉換流程
    
    ⚠️ 安全機制：必須 user_confirmed=True 才會執行
    
    參數:
        file_path: 已下載的技能檔案路徑
        skill_name: 技能名稱
        source_repo: 來源 Repo
        description: 技能描述
        user_confirmed: 使用者是否已確認
    
    回傳:
        轉換結果的 JSON 物件
    """
    # 1. 驗證批准狀態
    approval = validate_approval(user_confirmed)
    if not approval.get("approved"):
        return approval
    
    # 2. 讀取檔案
    path = Path(file_path)
    if not path.exists():
        return {
            "status": "error",
            "message": f"檔案不存在：{file_path}"
        }
    
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "status": "error",
            "message": f"讀取檔案失敗：{str(e)}"
        }
    
    results = {
        "status": "success",
        "skill_name": skill_name,
        "source_repo": source_repo,
        "steps": []
    }
    
    # 3. 加入中文 Header (僅 .py 檔案)
    if path.suffix == ".py":
        content, header_added = add_chinese_header(
            content, skill_name, source_repo, description
        )
        if header_added:
            results["steps"].append("✅ 已加入繁體中文 Header")
        else:
            results["steps"].append("ℹ️ 已有中文 Header，跳過")
        
        # 4. 代碼適配
        content, changes = adapt_to_project_convention(content)
        if changes:
            results["steps"].extend(changes)
        
        # 5. 寫回檔案
        path.write_text(content, encoding="utf-8")
        results["steps"].append(f"✅ 已更新 {path.name}")
    
    # 6. 更新 __init__.py
    init_result = update_init_py(skill_name)
    results["steps"].append(init_result.get("message", "更新 __init__.py"))
    
    # 7. 更新 SKILL.md
    usage = f"python .agent/skills/{skill_name}.py"
    md_result = update_skill_md(
        skill_name,
        description or f"來自 {source_repo} 的技能",
        usage,
        source_repo
    )
    results["steps"].append(md_result.get("message", "更新 SKILL.md"))
    
    results["message"] = f"✅ 技能 {skill_name} 轉換完成"
    return results


# =========================
# 主程式 (測試用)
# =========================
def main():
    """主程式入口 (僅供測試)"""
    print(json.dumps({
        "status": "info",
        "message": "此模組由 github_explorer.py 內部調用",
        "available_functions": [
            "validate_approval",
            "add_chinese_header",
            "adapt_to_project_convention",
            "update_init_py",
            "update_skill_md",
            "convert_skill"
        ]
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
