---
description: Automatically manages persistent terminal sessions for various CLI tools (Codex, Claude, etc.)
triggers:
  - codex cli
  - claude cli
  - open terminal
  - persistent session
---

# ♾️ Persistent Terminal Skill (Generic)

此技能用於確保與任何 CLI 工具 (Codex, Claude, etc.) 的互動永遠發生在對應的 named PowerShell Session 中。

## ⚠️ 技術限制說明
Antigravity 的 `run_command` 預設開啟的終端機名稱通常是 "Task - <TaskName>" 或 "Terminal"，無法直接指定名稱。
因此，本技能依賴 **CommandId 追蹤** 與 **進程識別**。

## 🛠️ 執行邏輯 (Python Implementation Logic)

```python
# 模擬的全域狀態追蹤 (Agent Memory)
active_sessions = {
    "codex": None,  # CommandId
    "claude": None
}

def ensure_persistent_session(tool_name: str, context):
    """
    Ensures a specific named terminal is running and returns its CommandId.
    Args:
        tool_name (str): The name of the tool/session (e.g., 'codex', 'claude').
    """
    global active_sessions
    
    # 1. Memory Check: Do we already have a CommandId for this tool?
    cached_id = active_sessions.get(tool_name)
    if cached_id and context.is_command_running(cached_id):
        return cached_id
    
    # 2. Heuristic Check: Scan active terminals for running command line
    # (If agent restarted and lost memory, look for prompt or process)
    active_cmds = context.get_running_commands()
    for cmd in active_cmds:
        if tool_name in cmd.command_line:
            active_sessions[tool_name] = cmd.id
            return cmd.id

    # 3. Start New Session
    command_id = context.run_command(
        CommandLine=tool_name, 
        WaitMsBeforeAsync=5000
    )
    
    # Update Memory
    active_sessions[tool_name] = command_id
    return command_id
```

## 📋 使用守則

1. **優先查表**：Agent 應維護一份 `Tool Name -> CommandId` 的對照表。
2. **重啟復原**：若 Agent 重啟失憶，則列出所有背景指令，看哪一個指令列包含 "codex"。
3. **無法改名**：接受終端機名稱無法更改的事實，改以 `CommandId` 作為唯一識別證。
