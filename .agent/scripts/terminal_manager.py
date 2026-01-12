#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Terminal 會話管理器 - 用於 Codex CLI 執行

用途：
    確保所有 Codex CLI 命令都發送到同一個 Terminal 會話中，
    避免為每個任務創建新的 Terminal，提高執行效率與一致性。

使用方式：
    python terminal_manager.py get-terminal
    python terminal_manager.py send-command <terminal_id> <command>
    python terminal_manager.py close-terminal <terminal_id>

Terminal Manager for Codex CLI Execution

Ensures all Codex CLI commands are sent to the same terminal session,
avoiding the creation of new terminals for each task execution.
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

# State file location
STATE_FILE = Path(__file__).parent.parent / ".terminal_session.json"


class TerminalManager:
    """Manage persistent terminal sessions for Codex CLI"""

    def __init__(self):
        self.state_file = STATE_FILE

    def load_state(self) -> Optional[Dict]:
        """Load terminal state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Failed to load state: {e}", file=sys.stderr)
                return None
        return None

    def save_state(self, terminal_id: str, session_name: str = "codex-session"):
        """Save terminal state to file"""
        state = {
            'terminal_id': terminal_id,
            'session_name': session_name,
            'created_at': datetime.now().isoformat(),
            'last_used': datetime.now().isoformat(),
            'command_count': 1
        }

        # Create directory if it doesn't exist
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def update_last_used(self):
        """Update the last_used timestamp"""
        state = self.load_state()
        if state:
            state['last_used'] = datetime.now().isoformat()
            state['command_count'] = state.get('command_count', 0) + 1

            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

    def get_or_create_terminal(self) -> str:
        """Get existing terminal or create a new one using tmux"""
        state = self.load_state()

        if state:
            session_name = state.get('session_name', 'codex-session')

            # Check if tmux session still exists
            result = subprocess.run(
                ['tmux', 'has-session', '-t', session_name],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"✓ Using existing terminal: {session_name}")
                self.update_last_used()
                return session_name
            else:
                print(f"⚠️  Previous session '{session_name}' not found, creating new one")

        # Create new tmux session
        session_name = "codex-session"
        result = subprocess.run(
            ['tmux', 'new-session', '-d', '-s', session_name],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"✓ Created new terminal session: {session_name}")
            self.save_state(session_name, session_name)
            return session_name
        else:
            print(f"❌ Failed to create tmux session: {result.stderr}", file=sys.stderr)
            sys.exit(1)

    def send_command(self, terminal_id: str, command: str):
        """Send command to the specified terminal"""
        try:
            # Send command to tmux session
            result = subprocess.run(
                ['tmux', 'send-keys', '-t', terminal_id, command, 'C-m'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"✓ Command sent to terminal '{terminal_id}'")
                self.update_last_used()
            else:
                print(f"❌ Failed to send command: {result.stderr}", file=sys.stderr)
                sys.exit(1)

        except Exception as e:
            print(f"❌ Error sending command: {e}", file=sys.stderr)
            sys.exit(1)

    def close_terminal(self, terminal_id: str):
        """Close the terminal and clean up state"""
        try:
            # Kill tmux session
            result = subprocess.run(
                ['tmux', 'kill-session', '-t', terminal_id],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"✓ Terminal '{terminal_id}' closed")
            else:
                print(f"⚠️  Failed to close terminal: {result.stderr}", file=sys.stderr)

            # Remove state file
            if self.state_file.exists():
                self.state_file.unlink()
                print(f"✓ State file cleaned up")

        except Exception as e:
            print(f"❌ Error closing terminal: {e}", file=sys.stderr)
            sys.exit(1)

    def get_terminal_info(self):
        """Get current terminal session information"""
        state = self.load_state()
        if state:
            print(json.dumps(state, indent=2, ensure_ascii=False))
        else:
            print("No active terminal session")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python terminal_manager.py get-terminal")
        print("  python terminal_manager.py send-command <terminal_id> <command>")
        print("  python terminal_manager.py close-terminal <terminal_id>")
        print("  python terminal_manager.py info")
        sys.exit(1)

    manager = TerminalManager()
    command = sys.argv[1]

    if command == "get-terminal":
        terminal_id = manager.get_or_create_terminal()
        print(terminal_id)

    elif command == "send-command":
        if len(sys.argv) < 4:
            print("Usage: python terminal_manager.py send-command <terminal_id> <command>")
            sys.exit(1)
        terminal_id = sys.argv[2]
        cmd = ' '.join(sys.argv[3:])
        manager.send_command(terminal_id, cmd)

    elif command == "close-terminal":
        if len(sys.argv) < 3:
            print("Usage: python terminal_manager.py close-terminal <terminal_id>")
            sys.exit(1)
        terminal_id = sys.argv[2]
        manager.close_terminal(terminal_id)

    elif command == "info":
        manager.get_terminal_info()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
