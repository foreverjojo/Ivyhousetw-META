#!/bin/bash
# Codex CLI Execution Wrapper Script
#
# This script wraps Codex CLI execution with Terminal Manager integration
# and L2 Rollback support.
#
# Usage:
#   ./run_codex_template.sh <plan_file>

set -e

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1" >&2
}

log_step() {
    echo -e "${BLUE}▶${NC} $1"
}

# Check if plan file is provided
if [ -z "$1" ]; then
    log_error "Usage: $0 <plan_file>"
    exit 1
fi

PLAN_FILE="$1"

if [ ! -f "$PLAN_FILE" ]; then
    log_error "Plan file not found: $PLAN_FILE"
    exit 1
fi

log_step "Reading plan file: $PLAN_FILE"

# Extract execution tool from plan
EXECUTION_TOOL=$(grep -E "^\*\*execution\*\*:" "$PLAN_FILE" | sed 's/\*\*execution\*\*://g' | sed 's/\[//g' | sed 's/\]//g' | tr -d ' ' || echo "")

if [ -z "$EXECUTION_TOOL" ]; then
    log_warn "No execution tool specified in plan, defaulting to 'copilot'"
    EXECUTION_TOOL="copilot"
fi

log_info "Execution tool: $EXECUTION_TOOL"

# If not Codex CLI, exit early
if [[ "$EXECUTION_TOOL" != "codex-cli" ]]; then
    log_info "Non Codex CLI execution, skipping Terminal management"
    echo ""
    echo "📋 Next steps:"
    echo "  1. Execute the plan using GitHub Copilot"
    echo "  2. Run QA checks after completion"
    exit 0
fi

log_step "Codex CLI execution detected, managing Terminal session..."

# Check Codex CLI login status
log_step "檢查 Codex CLI 登入狀態..."

# Try to check if codex is logged in by running a simple command
if ! codex --version &>/dev/null; then
    log_warn "Codex CLI 未安裝或無法執行"
    exit 1
fi

# Check if user is logged in (this will fail if not logged in)
# We use 'codex whoami' or similar command to verify
if ! codex config get user.email &>/dev/null 2>&1; then
    log_warn "Codex CLI 未登入，正在啟動登入流程..."
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔐 請執行以下命令進行 Codex CLI 登入："
    echo ""
    echo "   codex"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Attempt automatic login
    log_step "正在啟動 Codex CLI 登入..."
    codex

    # Verify login succeeded
    if ! codex config get user.email &>/dev/null 2>&1; then
        log_error "Codex CLI 登入失敗，請手動執行 'codex' 命令完成登入"
        exit 1
    fi

    log_info "✅ Codex CLI 登入成功"
fi

log_info "✅ Codex CLI 已登入，繼續執行..."

# Get or create terminal session
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERMINAL_MANAGER="$SCRIPT_DIR/terminal_manager.py"

if [ ! -f "$TERMINAL_MANAGER" ]; then
    log_error "Terminal Manager not found: $TERMINAL_MANAGER"
    exit 1
fi

# Get terminal session
TERMINAL_ID=$(python3 "$TERMINAL_MANAGER" get-terminal 2>&1 | tail -1)

if [ $? -ne 0 ]; then
    log_error "Failed to get terminal session"
    exit 1
fi

log_info "Using Terminal: $TERMINAL_ID"

# Backup current state for L2 rollback
log_step "Creating backup point for L2 rollback..."
BACKUP_BRANCH="backup-$(date +%Y%m%d-%H%M%S)"
git stash push -m "Pre-execution backup for $PLAN_FILE" --include-untracked || true

# Extract plan index for logging
PLAN_INDEX=$(basename "$PLAN_FILE" | sed 's/_plan.md//g')

log_step "Sending Codex CLI command to Terminal..."

# Build Codex CLI command
CODEX_COMMAND="codex --plan $PLAN_FILE"

# Send command to terminal
python3 "$TERMINAL_MANAGER" send-command "$TERMINAL_ID" "$CODEX_COMMAND"

if [ $? -ne 0 ]; then
    log_error "Failed to send command to terminal"
    exit 1
fi

log_info "Command sent successfully"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📌 Codex CLI is now executing in Terminal: $TERMINAL_ID"
echo ""
echo "📋 Next steps:"
echo "  1. Monitor execution in the Terminal"
echo "  2. If execution succeeds, proceed to QA (Step 4)"
echo "  3. If execution fails, L2 Rollback will be triggered"
echo ""
echo "🔄 Rollback options:"
echo "  L2 (Script): git stash pop  # Restore backup"
echo "  L3 (Copilot): Ask Copilot for git reset suggestion"
echo "  L4 (User): git reset --hard <commit>"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Note: Actual execution monitoring and L2 rollback trigger
# should be implemented based on Codex CLI exit code or error detection
# This is a simplified version for demonstration

# Wait for user confirmation or implement automatic monitoring
read -p "Press Enter after Codex execution completes to continue..."

# Check if execution succeeded (simplified check)
echo ""
read -p "Did Codex execution succeed? (y/n): " SUCCESS

if [[ "$SUCCESS" != "y" && "$SUCCESS" != "Y" ]]; then
    log_warn "Execution failed, triggering L2 Rollback..."

    # L2 Rollback: Restore from stash
    if git stash list | grep -q "Pre-execution backup"; then
        git stash pop
        log_info "L2 Rollback completed - changes restored from backup"
    else
        log_warn "No backup found in stash"
    fi

    log_error "Task execution failed, rolled back to previous state"
    exit 1
else
    log_info "Execution succeeded, proceeding to QA"

    # Clear the backup stash
    git stash drop 2>/dev/null || true

    echo ""
    echo "✅ Ready for QA (Step 4)"
    echo "   Remember: QA tool must be different from Executor (Cross-QA rule)"
    echo "   Executor: Codex CLI → QA: GitHub Copilot"
fi

exit 0
