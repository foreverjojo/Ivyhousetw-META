#!/usr/bin/env bash
# 自動化執行 Plan → 等待完成 → 執行 QA
set -euo pipefail

PLAN_FILE="${1:-}"
if [[ -z "$PLAN_FILE" ]]; then
  echo "Usage: $0 <plan_file.md>" >&2
  exit 1
fi

if [[ ! -f "$PLAN_FILE" ]]; then
  echo "❌ Plan 檔案不存在: $PLAN_FILE" >&2
  exit 1
fi

echo "🚀 開始執行 Plan: $PLAN_FILE"

# 1. 讀取 Plan 內容並發送給 Codex CLI
PLAN_CONTENT=$(cat "$PLAN_FILE")
PROMPT="請依照以下 Plan 執行，不要自行改寫內容：

$PLAN_CONTENT"

echo "📤 發送 Plan 到 Codex CLI..."
.agent/scripts/sendtext.sh text "$PROMPT" --execute

# 2. 等待 Codex CLI 完成（監測 git status 變更）
echo "⏳ 等待 Codex CLI 執行完成（最多 5 分鐘）..."

PORT="${SENDTEXT_BRIDGE_PORT:-38765}"
TOKEN=$(cat .agent/state/sendtext_bridge_token 2>/dev/null || echo "")

if [[ -z "$TOKEN" ]]; then
  echo "❌ Token 檔案不存在" >&2
  exit 1
fi

# 呼叫 /wait 端點（timeout: 5 分鐘，checkInterval: 2 秒）
WAIT_RESPONSE=$(curl -sS -X POST "http://127.0.0.1:${PORT}/wait" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"timeout":300000,"checkInterval":2000}')

COMPLETED=$(echo "$WAIT_RESPONSE" | jq -r '.completed // false')

if [[ "$COMPLETED" != "true" ]]; then
  echo "❌ Codex CLI 執行逾時或失敗"
  echo "$WAIT_RESPONSE" | jq .
  exit 1
fi

ELAPSED=$(echo "$WAIT_RESPONSE" | jq -r '.elapsed // 0')
echo "✅ Codex CLI 執行完成（耗時: $((ELAPSED / 1000)) 秒）"

# 3. 自動執行 QA
echo ""
echo "🔍 開始執行 QA..."

# 讀取 Plan 的 index
PLAN_INDEX=$(basename "$PLAN_FILE" | sed 's/_plan.md//')

# 建立 QA prompt
QA_PROMPT="請依照 .agent/roles/qa.md 審查 $PLAN_INDEX 的執行結果。

檢查項目：
- [ ] 無 Hard-code API Key
- [ ] 有中文檔案註釋
- [ ] 符合 ivy_house_rules.md
- [ ] 邏輯正確
- [ ] Cross-QA 規則已遵守

請給出完整 QA 報告，並在最後給出明確判定：✅ PASS / ⚠️ PASS WITH RISK / ❌ FAIL

檔案變更：
\`\`\`
$(git status --short)
\`\`\`
"

# 這裡應該由 GitHub Copilot 執行 QA（Cross-QA 規則）
# 但在腳本中我們只能提示使用者
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 請在 GitHub Copilot Chat 中執行以下 QA："
echo ""
echo "$QA_PROMPT"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 提示：由於 Executor 是 Codex CLI，QA 必須由 GitHub Copilot 執行（Cross-QA 規則）"
