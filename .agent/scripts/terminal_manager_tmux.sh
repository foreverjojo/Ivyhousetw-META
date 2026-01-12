#!/bin/bash
# -*- coding: utf-8 -*-
#
# Terminal 會話管理器 - tmux 版本
#
# 用途：
#   使用 tmux 確保所有 Codex CLI 命令都發送到同一個 tmux 會話中，
#   避免為每個任務創建新的 Terminal，提供持久化的執行環境。
#
# 使用方式：
#   ./terminal_manager_tmux.sh get-or-create
#   ./terminal_manager_tmux.sh send-command <session_name> <command>
#   ./terminal_manager_tmux.sh close <session_name>
#   ./terminal_manager_tmux.sh info
#
# Terminal Manager for Codex CLI Execution (tmux version)
# Ensures all Codex CLI commands are sent to the same tmux session.

set -e

SESSION_NAME="codex-session"
STATE_FILE=".agent/.terminal_session.json"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠️${NC}  $1" >&2
}

log_error() {
    echo -e "${RED}❌${NC} $1" >&2
}

# Check if tmux is installed
check_tmux() {
    if ! command -v tmux &> /dev/null; then
        log_error "tmux is not installed. Please install it first:"
        echo "  Debian/Ubuntu: sudo apt-get install tmux"
        echo "  macOS: brew install tmux"
        exit 1
    fi
}

# Get or create tmux session
get_or_create_session() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        log_info "Using existing terminal session: $SESSION_NAME"
        update_state
    else
        log_warn "Creating new terminal session: $SESSION_NAME"
        tmux new-session -d -s "$SESSION_NAME"
        save_state
    fi
    echo "$SESSION_NAME"
}

# Save state to JSON file
save_state() {
    local timestamp=$(date -Iseconds)
    mkdir -p "$(dirname "$STATE_FILE")"

    cat > "$STATE_FILE" <<EOF
{
  "terminal_id": "$SESSION_NAME",
  "session_name": "$SESSION_NAME",
  "created_at": "$timestamp",
  "last_used": "$timestamp",
  "command_count": 1
}
EOF
    log_info "State saved to $STATE_FILE"
}

# Update last_used timestamp
update_state() {
    if [ -f "$STATE_FILE" ]; then
        local timestamp=$(date -Iseconds)
        local count=$(jq -r '.command_count // 0' "$STATE_FILE")
        count=$((count + 1))

        jq --arg ts "$timestamp" --arg cnt "$count" \
           '.last_used = $ts | .command_count = ($cnt | tonumber)' \
           "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
    fi
}

# Send command to tmux session
send_command() {
    local session=$1
    local cmd=$2

    if [ -z "$cmd" ]; then
        log_error "No command provided"
        exit 1
    fi

    if ! tmux has-session -t "$session" 2>/dev/null; then
        log_error "Session '$session' does not exist"
        exit 1
    fi

    tmux send-keys -t "$session" "$cmd" C-m
    log_info "Command sent to terminal '$session'"
    update_state
}

# Close tmux session
close_session() {
    local session=$1

    if tmux has-session -t "$session" 2>/dev/null; then
        tmux kill-session -t "$session"
        log_info "Terminal '$session' closed"
    else
        log_warn "Session '$session' does not exist"
    fi

    if [ -f "$STATE_FILE" ]; then
        rm "$STATE_FILE"
        log_info "State file cleaned up"
    fi
}

# Show session info
show_info() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
    else
        echo "No active terminal session"
    fi
}

# Main command dispatcher
main() {
    check_tmux

    case "${1:-}" in
        get-or-create)
            get_or_create_session
            ;;
        send-command)
            if [ -z "${2:-}" ] || [ -z "${3:-}" ]; then
                log_error "Usage: $0 send-command <session_name> <command>"
                exit 1
            fi
            send_command "$2" "${@:3}"
            ;;
        close)
            if [ -z "${2:-}" ]; then
                log_error "Usage: $0 close <session_name>"
                exit 1
            fi
            close_session "$2"
            ;;
        info)
            show_info
            ;;
        *)
            echo "Usage: $0 {get-or-create|send-command|close|info}"
            echo ""
            echo "Commands:"
            echo "  get-or-create              Get existing or create new terminal session"
            echo "  send-command <session> <cmd>   Send command to terminal session"
            echo "  close <session>            Close terminal session"
            echo "  info                       Show current session information"
            exit 1
            ;;
    esac
}

main "$@"
