#!/bin/bash
# -*- coding: utf-8 -*-
#
# Codex CLI 互動模式輸入助手（tmux）
#
# 用途：
#   將一段文字（或檔案內容）可靠地送入指定的 tmux session。
#   避免 send-keys 在遇到大量內容、特殊字元、或 quoting 時不穩定。
#
# 使用方式：
#   .agent/scripts/codex_tmux_send.sh codex-session --text "請開始 QA..."
#   .agent/scripts/codex_tmux_send.sh codex-session --file /path/to/prompt.txt
#   .agent/scripts/codex_tmux_send.sh codex-session --file prompt.txt --no-enter
#

set -euo pipefail

SESSION="${1:-}"
shift || true

if [ -z "$SESSION" ]; then
  echo "Usage: $0 <tmux-session> (--text <text> | --file <file>) [--no-enter]" >&2
  exit 1
fi

if ! command -v tmux >/dev/null 2>&1; then
  echo "❌ tmux 未安裝，請先安裝 tmux" >&2
  exit 1
fi

if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "❌ tmux session 不存在: $SESSION" >&2
  exit 1
fi

MODE=""
TEXT=""
FILE=""
SEND_ENTER=1

while [ "$#" -gt 0 ]; do
  case "$1" in
    --text)
      MODE="text"
      shift
      TEXT="${1:-}"
      ;;
    --file)
      MODE="file"
      shift
      FILE="${1:-}"
      ;;
    --no-enter)
      SEND_ENTER=0
      ;;
    -h|--help)
      echo "Usage: $0 <tmux-session> (--text <text> | --file <file>) [--no-enter]"
      exit 0
      ;;
    *)
      echo "❌ Unknown arg: $1" >&2
      exit 1
      ;;
  esac
  shift || true
done

if [ -z "$MODE" ]; then
  echo "❌ 必須指定 --text 或 --file" >&2
  exit 1
fi

BUF_NAME="codex-input"

if [ "$MODE" = "file" ]; then
  if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
    echo "❌ 檔案不存在: $FILE" >&2
    exit 1
  fi
  tmux load-buffer -b "$BUF_NAME" "$FILE"
else
  # 避免把內容當作 shell 參數展開，使用 printf 走 stdin。
  printf "%s" "$TEXT" | tmux load-buffer -b "$BUF_NAME" -
fi

# 用 paste-buffer 可避免特殊字元/大量內容造成 send-keys 不穩定
tmux paste-buffer -t "$SESSION" -b "$BUF_NAME"

if [ "$SEND_ENTER" = "1" ]; then
  tmux send-keys -t "$SESSION" C-m
fi

exit 0
