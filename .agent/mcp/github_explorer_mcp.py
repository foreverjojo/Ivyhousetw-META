# -*- coding: utf-8 -*-
"""
.agent/mcp/github_explorer_mcp.py
=================================
用途：將 github_explorer 封裝為 MCP Server
職責：暴露 search、preview、download、list、rollback 五個 Tool 給 MCP Client
通訊方式：stdio (標準輸入輸出)

啟動方式：
    python .agent/mcp/github_explorer_mcp.py

註冊到 Codex CLI：
    codex mcp add ivy-github-explorer -- python .agent/mcp/github_explorer_mcp.py

注意事項：
    - 使用 FastMCP 高階 API 以確保正確的協議初始化
    - 所有匯入必須靜默進行，避免污染 stdout/stderr
"""

import sys
import json
import os
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

# 載入環境變數（使用 python-dotenv）
try:
    from dotenv import load_dotenv
    # 定義 ifp.env 的路徑（相對於此腳本位於 .agent/mcp/）
    ENV_PATH = Path(__file__).resolve().parent.parent.parent / "ifp.env"
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
except ImportError:
    pass  # 若缺少 dotenv 則跳過

# 將 skills 目錄加入 Python Path（使用 resolve() 確保絕對路徑）
SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
sys.path.insert(0, str(SKILLS_DIR))

# 抑制匯入時可能產生的任何輸出（MCP 使用 stdio，任何非協議輸出都會破壞 handshake）
_import_buffer = StringIO()

# 匯入現有的 github_explorer 功能
try:
    with redirect_stdout(_import_buffer), redirect_stderr(_import_buffer):
        from github_explorer import (
            search_github_skills,
            preview_skill,
            download_skill,
            list_local_skills,
            rollback_skill,
        )
except ImportError as e:
    sys.stderr.write(f"錯誤：無法匯入 github_explorer: {e}\n")
    sys.exit(1)

# 嘗試匯入 FastMCP（高階 API，更穩定）
try:
    with redirect_stdout(_import_buffer), redirect_stderr(_import_buffer):
        from mcp.server.fastmcp import FastMCP
except ImportError:
    sys.stderr.write("錯誤：MCP SDK 未安裝。請執行：pip install mcp[cli]\n")
    sys.exit(1)


# =========================
# 使用 FastMCP 建立 Server
# =========================

mcp = FastMCP("ivy-github-explorer")


@mcp.tool()
def github_skill_search(keyword: str) -> str:
    """
    在 GitHub 搜尋含有 SKILL.md 的技能庫。

    Args:
        keyword: 搜尋關鍵字（如 'crewai', 'langchain'）

    Returns:
        JSON 格式的搜尋結果
    """
    result = search_github_skills(keyword)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def github_skill_preview(repo: str, skill_path: str = "SKILL.md") -> str:
    """
    預覽指定 GitHub Repo 的 SKILL.md 內容（唯讀，不會下載）

    Args:
        repo: Repo 的 full_name (如 'owner/repo') 或完整 URL
        skill_path: SKILL.md 在 Repo 中的路徑（預設為 'SKILL.md'）

    Returns:
        JSON 格式的預覽結果
    """
    result = preview_skill(repo, skill_path)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def github_skill_download(repo: str, file_path: str, confirm: bool = False) -> str:
    """
    下載指定的技能檔案（需通過白名單檢查與安全掃描）

    Args:
        repo: Repo 的 full_name (如 'owner/repo')
        file_path: 要下載的檔案路徑
        confirm: 是否確認下載（必須為 true 才會執行）

    Returns:
        JSON 格式的下載結果
    """
    result = download_skill(repo, file_path, user_confirmed=confirm)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def github_skill_list() -> str:
    """
    列出本地已安裝的所有技能

    Returns:
        JSON 格式的技能清單
    """
    result = list_local_skills()
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def github_skill_rollback(skill_name: str) -> str:
    """
    回滾（移除）已安裝的技能

    Args:
        skill_name: 要移除的技能名稱（不含 .py 後綴）

    Returns:
        JSON 格式的回滾結果
    """
    result = rollback_skill(skill_name)
    return json.dumps(result, ensure_ascii=False, indent=2)


# =========================
# 主程式
# =========================

if __name__ == "__main__":
    # 使用 FastMCP 的 run() 方法啟動 stdio server
    mcp.run()
