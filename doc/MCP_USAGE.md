# MCP (Model Context Protocol) 使用指南

## 概述

本專案已整合 MCP 協議，讓 AI 代理（如 Codex CLI）能夠**自動發現並調用**本地工具。

## 已註冊的 MCP Server

### ivy-github-explorer

**功能**：GitHub 技能搜尋與管理工具

| Tool 名稱 | 說明 |
|-----------|------|
| `github_skill_search` | 在 GitHub 搜尋含有 SKILL.md 的技能庫 |
| `github_skill_preview` | 預覽指定 Repo 的 SKILL.md 內容 |
| `github_skill_download` | 下載技能（需白名單 + 安全掃描） |
| `github_skill_list` | 列出本地已安裝的技能 |
| `github_skill_rollback` | 回滾已安裝的技能 |

## 管理指令

```bash
# 列出所有 MCP Server
codex mcp list

# 移除 MCP Server
codex mcp remove ivy-github-explorer

# 重新註冊
codex mcp add ivy-github-explorer -- .\.venv\Scripts\python.exe .agent\mcp\github_explorer_mcp.py
```

## 開發新的 MCP Server

1. 在 `.agent/mcp/` 建立新的 Python 檔案
2. 使用 MCP SDK (`pip install mcp[cli]`) 定義 Server 與 Tools
3. 透過 `codex mcp add` 註冊

範例請參考：`.agent/mcp/github_explorer_mcp.py`

## 安全機制

- 所有下載操作仍需通過 `.agent/skills/skill_whitelist.json` 白名單檢查
- 下載後自動執行 `code_reviewer.py` 安全掃描
- 所有操作記錄於 `.agent/skills/audit.log`
