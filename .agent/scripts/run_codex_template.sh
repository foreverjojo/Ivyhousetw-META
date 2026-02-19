#!/usr/bin/env bash
# run_codex_template.sh v2 - 簡化版（VS Code 原生終端；無 tmux）
#
# 用途：
#   - 從 Plan 的 EXECUTION_BLOCK 解析 execution 欄位
#   - 若為 codex-cli，使用 `codex exec` 執行（stdin 為 plan 內容）
#   - 以 exit code 判斷成功/失敗，落盤 JSONL 到 `.agent/execution_log.jsonl`
#   - 失敗時自動觸發 L2 Rollback（僅限乾淨 worktree）
#
# 使用方式：
#   .agent/scripts/run_codex_template.sh doc/plans/Idx-NNN_plan.md

set -euo pipefail

PLAN_FILE="${1:-}"
LOG_FILE=".agent/execution_log.jsonl"
BACKUP_PATCH=".agent/.pre_execution_backup.patch"
mkdir -p .agent

# 生成唯一 run_id
RUN_ID="$(date +%s%N 2>/dev/null || echo "$(date +%s)000000000")"
START_TIME="$(date -Iseconds 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%S+00:00")"

# 預設值
EXECUTION_DECLARED=""
EXECUTION_EFFECTIVE=""
EXIT_CODE_VAL=""
STATUS=""
REASON=""

json_escape() {
  local s="${1:-}"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  printf '%s' "$s"
}

json_str_or_null() {
  if [[ -n "${1:-}" ]]; then
    printf '"%s"' "$(json_escape "$1")"
  else
    printf 'null'
  fi
}

json_num_or_null() {
  [[ -n "${1:-}" && "${1:-}" =~ ^[0-9]+$ ]] && printf '%s' "$1" || printf 'null'
}

log_jsonl() {
  local end_time
  end_time="$(date -Iseconds 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%S+00:00")"

  printf '{"schema_version":2,"plan":%s,"execution_declared":%s,"execution_effective":%s,"status":"%s","exit_code":%s,"reason":%s,"run_id":"%s","start":"%s","end":"%s"}\n' \
    "$(json_str_or_null "$PLAN_FILE")" \
    "$(json_str_or_null "$EXECUTION_DECLARED")" \
    "$(json_str_or_null "$EXECUTION_EFFECTIVE")" \
    "$STATUS" \
    "$(json_num_or_null "$EXIT_CODE_VAL")" \
    "$(json_str_or_null "$REASON")" \
    "$RUN_ID" \
    "$START_TIME" \
    "$end_time" >>"$LOG_FILE"
}

fail_and_exit() {
  STATUS="FAILED"
  REASON="$1"
  log_jsonl
  echo "❌ 執行失敗: $REASON" >&2
  exit 1
}

skip_and_exit() {
  STATUS="SKIPPED"
  REASON="$1"
  log_jsonl
  echo "⏭️  跳過執行: $REASON"
  exit 0
}

# 1. 參數驗證
if [[ -z "$PLAN_FILE" ]]; then
  PLAN_FILE="(missing)"
  fail_and_exit "missing_plan_arg"
fi
[[ ! -f "$PLAN_FILE" ]] && fail_and_exit "plan_file_not_found"
[[ ! -r "$PLAN_FILE" ]] && fail_and_exit "plan_file_unreadable"

# 2. 依賴檢查
command -v git >/dev/null 2>&1 || fail_and_exit "git_missing"
command -v codex >/dev/null 2>&1 || fail_and_exit "codex_cli_missing"

# 3. 解析 execution 欄位（從 EXECUTION_BLOCK 標記中）
EXECUTION_DECLARED="$(awk '
  /<!-- EXECUTION_BLOCK_START -->/ {in=1; next}
  /<!-- EXECUTION_BLOCK_END -->/ {in=0}
  in && /^execution:/ {sub(/^execution:[[:space:]]*/, ""); print; exit}
' "$PLAN_FILE" | xargs)"

[[ -z "$EXECUTION_DECLARED" ]] && skip_and_exit "missing_execution_field"
[[ "$EXECUTION_DECLARED" != "codex-cli" && "$EXECUTION_DECLARED" != "copilot" ]] && skip_and_exit "invalid_execution_field"
[[ "$EXECUTION_DECLARED" != "codex-cli" ]] && skip_and_exit "execution_tool_not_codex_cli"

# 4. L2 Rollback 前置條件：乾淨 worktree
if [[ -n "$(git status --porcelain 2>/dev/null || true)" ]]; then
  skip_and_exit "dirty_worktree"
fi

# 記錄執行前狀態（以防 codex 造成 commit 變更）
PRE_HEAD="$(git rev-parse HEAD 2>/dev/null || echo "")"
git diff >"$BACKUP_PATCH" 2>/dev/null || true

# 5. 執行 Codex CLI
echo "🚀 執行 Codex CLI: $PLAN_FILE"

CODEX_PROMPT="請以 stdin 內容作為本次 plan 指令執行；不要自行改寫 plan。"
set +e
cat "$PLAN_FILE" | codex exec "$CODEX_PROMPT"
EXIT_CODE_VAL=$?
set -e

# 6. 檢查執行結果
EXECUTION_EFFECTIVE="codex-cli"

if [[ "$EXIT_CODE_VAL" -ne 0 ]]; then
  echo "❌ Codex CLI 執行失敗 (exit code: $EXIT_CODE_VAL)"
  REASON="codex_nonzero"

  # L2 Rollback
  echo "🔄 觸發 L2 Rollback..."
  POST_HEAD="$(git rev-parse HEAD 2>/dev/null || echo "")"

  if [[ -n "$PRE_HEAD" && -n "$POST_HEAD" && "$POST_HEAD" != "$PRE_HEAD" ]]; then
    git reset --hard "$PRE_HEAD" 2>/dev/null || true
  fi

  git restore --worktree --staged -- . 2>/dev/null || true
  git ls-files --others --exclude-standard -z 2>/dev/null | \
    grep -zv '^\.agent/' | \
    xargs -0 rm -rf -- 2>/dev/null || true

  STATUS="FAILED"
  log_jsonl
  exit 1
fi

# 7. 執行成功
echo "✅ 執行成功"
STATUS="SUCCESS"
log_jsonl
