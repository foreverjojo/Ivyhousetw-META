#!/usr/bin/env bash
# Service manager: start/stop/status/restart/tail/list for long-running dev services
# Prefers tmux sessions (if available) and falls back to nohup + pidfile.

set -euo pipefail
IFS=$'\n\t'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_DIR="$REPO_ROOT/.service"
PIDS_DIR="$SERVICE_DIR/pids"
LOGS_DIR="$SERVICE_DIR/logs"
SESS_DIR="$SERVICE_DIR/sessions"

mkdir -p "$PIDS_DIR" "$LOGS_DIR" "$SESS_DIR"

TMUX_CMD="$(command -v tmux || true)"
USE_TMUX=false
if [[ -n "$TMUX_CMD" ]]; then
  USE_TMUX=true
fi

# default commands for known services
service_cmd() {
  local svc="$1"
  case "$svc" in
    opencode)
      echo "opencode --port 35103"
      ;;
    codex)
      echo "codex"
      ;;
    *)
      echo ""  # empty: caller must pass --cmd
      ;;
  esac
}

pidfile() { echo "$PIDS_DIR/$1.pid"; }
logfile() { echo "$LOGS_DIR/$1.log"; }
session_file() { echo "$SESS_DIR/$1.session"; }

echo_err() { printf "%s\n" "$*" >&2; }

is_running_pid() {
  local pid=$1
  if [[ -z "$pid" ]]; then return 1; fi
  if kill -0 "$pid" >/dev/null 2>&1; then return 0; else return 1; fi
}

tmux_session_exists() {
  local s="$1"
  if ! $USE_TMUX; then return 1; fi
  $TMUX_CMD has-session -t "$s" >/dev/null 2>&1
}

start_with_tmux() {
  local svc="$1" cmd="$2" session="svc_$svc" log
  log="$(logfile "$svc")"
  if tmux_session_exists "$session"; then
    echo "tmux session '$session' already exists (service may be running)."
    return 0
  fi
  echo "Starting '$svc' in tmux session '$session'..."
  # Launch command in tmux; tee to logfile so we keep output
  $TMUX_CMD new-session -d -s "$session" "bash -lc 'set -euo pipefail; exec $cmd 2>&1 | tee -a \"$log\"'"
  sleep 0.2
  if tmux_session_exists "$session"; then
    echo "$session" > "$(session_file "$svc")"
    echo "Started $svc (tmux session: $session). Log: $log"
    return 0
  else
    echo_err "Failed to start tmux session for $svc"
    return 1
  fi
}

start_with_nohup() {
  local svc="$1" cmd="$2" pidf="$(pidfile "$svc")" log
  log="$(logfile "$svc")"
  if [[ -f "$pidf" ]] && is_running_pid "$(cat "$pidf")"; then
    echo "$svc already running (pid: $(cat "$pidf"))."; return 0
  fi
  echo "Starting '$svc' with nohup (background)..."
  nohup bash -lc "set -euo pipefail; exec $cmd" >> "$log" 2>&1 &
  local pid=$!
  echo "$pid" > "$pidf"
  sleep 0.1
  if is_running_pid "$pid"; then
    echo "$svc started (pid: $pid). Log: $log"
    return 0
  else
    echo_err "Failed to start $svc (pid $pid not running)"; return 1
  fi
}

start_service() {
  local svc="$1" cmd_arg="$2"
  local cmd
  if [[ -n "$cmd_arg" ]]; then
    cmd="$cmd_arg"
  else
    cmd="$(service_cmd "$svc")"
  fi
  if [[ -z "$cmd" ]]; then
    echo_err "No command provided for service '$svc'. Use --cmd '<command>' or add mapping in script."; return 2
  fi

  if $USE_TMUX; then
    start_with_tmux "$svc" "$cmd"
  else
    start_with_nohup "$svc" "$cmd"
  fi
}

stop_service() {
  local svc="$1" session="svc_$svc" pidf="$(pidfile "$svc")" sessf="$(session_file "$svc")"
  if $USE_TMUX && tmux_session_exists "$session"; then
    echo "Stopping tmux session '$session'..."
    $TMUX_CMD kill-session -t "$session" >/dev/null 2>&1 || true
    rm -f "$sessf"
    echo "$svc stopped (tmux session killed)."
    return 0
  fi

  if [[ -f "$pidf" ]]; then
    local pid="$(cat "$pidf")"
    if is_running_pid "$pid"; then
      echo "Stopping $svc (pid: $pid)..."
      kill "$pid" >/dev/null 2>&1 || true
      sleep 0.5
      if is_running_pid "$pid"; then
        echo "PID still running; sending SIGKILL..."
        kill -9 "$pid" >/dev/null 2>&1 || true
      fi
      rm -f "$pidf"
      echo "$svc stopped."
      return 0
    else
      echo "Stale pidfile found but process not running. Removing pidfile."; rm -f "$pidf"; return 0
    fi
  fi

  echo "$svc is not running."; return 1
}

status_service() {
  local svc="$1" session="svc_$svc" pidf="$(pidfile "$svc")" log
  log="$(logfile "$svc")"
  if $USE_TMUX && tmux_session_exists "$session"; then
    echo "$svc is running in tmux session: $session"
    echo "Log: $log"
    return 0
  fi
  if [[ -f "$pidf" ]]; then
    local pid="$(cat "$pidf")"
    if is_running_pid "$pid"; then
      echo "$svc running (pid: $pid). Log: $log"
      return 0
    else
      echo "$svc pidfile exists but process not running (stale)."; return 2
    fi
  fi
  echo "$svc is not running."; return 1
}

tail_service() {
  local svc="$1" log
  log="$(logfile "$svc")"
  if [[ -f "$log" ]]; then
    tail -n 200 -f "$log"
  else
    echo "No log yet for $svc (expected at: $log)"; return 1
  fi
}

list_services() {
  echo "Known sessions (tmux) and pidfiles:"
  if $USE_TMUX; then
    $TMUX_CMD list-sessions -F '#S' 2>/dev/null | grep '^svc_' || true
  fi
  ls -1 "$PIDS_DIR" 2>/dev/null || true
}

attach_service() {
  local svc="$1" session="svc_$svc"
  if $USE_TMUX && tmux_session_exists "$session"; then
    echo "Attaching to tmux session $session (use Ctrl-b d to detach)";
    exec $TMUX_CMD attach -t "$session"
  else
    echo "Attach not available (no tmux session for $svc). Use tail to follow log."; return 1
  fi
}

print_help() {
  cat <<'EOF'
Usage: scripts/service_manager.sh <command> <service> [--cmd '<command>']
Commands:
  start <service> [--cmd '<command>']   Start service (tmux preferred, fallback nohup)
  stop <service>                        Stop service
  status <service>                      Show status
  restart <service> [--cmd '<command>'] Restart service
  tail <service>                        Tail service log
  attach <service>                      Attach to tmux session (if tmux available)
  list                                  List known sessions/pids
  help                                  Show this message
Examples:
  scripts/service_manager.sh start opencode
  scripts/service_manager.sh start codex --cmd 'codex'
  scripts/service_manager.sh status opencode
EOF
}

# ---- main arg parsing ----
if [[ $# -lt 1 ]]; then print_help; exit 2; fi
cmd="$1"; shift || true
svc=""; custom_cmd=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cmd)
      shift; custom_cmd="$1"; shift || true;;
    --cmd=*) custom_cmd="${1#--cmd=}"; shift;;
    -h|--help) print_help; exit 0;;
    *) if [[ -z "$svc" ]]; then svc="$1"; else echo_err "Unknown arg: $1"; exit 2; fi; shift;;
  esac
done

case "$cmd" in
  start)
    if [[ -z "$svc" ]]; then echo_err "service required"; print_help; exit 2; fi
    start_service "$svc" "$custom_cmd";;
  stop)
    if [[ -z "$svc" ]]; then echo_err "service required"; print_help; exit 2; fi
    stop_service "$svc";;
  restart)
    if [[ -z "$svc" ]]; then echo_err "service required"; print_help; exit 2; fi
    stop_service "$svc" || true
    start_service "$svc" "$custom_cmd";;
  status)
    if [[ -z "$svc" ]]; then echo_err "service required"; print_help; exit 2; fi
    status_service "$svc";;
  tail)
    if [[ -z "$svc" ]]; then echo_err "service required"; print_help; exit 2; fi
    tail_service "$svc";;
  attach)
    if [[ -z "$svc" ]]; then echo_err "service required"; print_help; exit 2; fi
    attach_service "$svc";;
  list)
    list_services;;
  *) print_help; exit 2;;
esac
