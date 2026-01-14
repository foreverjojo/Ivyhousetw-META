#!/usr/bin/env bash
# Integration test for Terminal Bridge Server
# Tests /wait endpoint behavior with actual git changes

set -euo pipefail

echo "🧪 Terminal Bridge Server Integration Test"
echo "==========================================="
echo ""

# Configuration
PORT="${TERMINAL_BRIDGE_PORT:-38765}"
TOKEN_FILE=".agent/state/terminal_bridge_token"
TEST_FILE=".agent/state/test_$(date +%s).tmp"

# Load token
if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "❌ Token file not found: $TOKEN_FILE"
  echo "   Please start the server first: .agent/scripts/start_terminal_bridge.sh"
  exit 1
fi

TOKEN=$(cat "$TOKEN_FILE")

# Test 1: Health check
echo "Test 1: Health Check"
echo "--------------------"
HEALTH_RESPONSE=$(curl -sS http://127.0.0.1:${PORT}/health)
echo "Response: $HEALTH_RESPONSE"

if echo "$HEALTH_RESPONSE" | jq -e '.ok == true' > /dev/null; then
  echo "✅ PASS: Health check successful"
else
  echo "❌ FAIL: Health check failed"
  exit 1
fi
echo ""

# Test 2: Capture endpoint (git status)
echo "Test 2: Capture Endpoint (Git Status)"
echo "--------------------------------------"
CAPTURE_RESPONSE=$(curl -sS http://127.0.0.1:${PORT}/capture \
  -H "Authorization: Bearer ${TOKEN}")
echo "Response (first 5 lines):"
echo "$CAPTURE_RESPONSE" | jq '.lines[:5]'

if echo "$CAPTURE_RESPONSE" | jq -e '.ok == true' > /dev/null; then
  echo "✅ PASS: Capture endpoint working"
else
  echo "❌ FAIL: Capture endpoint failed"
  exit 1
fi
echo ""

# Test 3: Wait endpoint - should complete immediately if no changes
echo "Test 3: Wait Endpoint (Stable State)"
echo "-------------------------------------"
echo "Creating a test file to make git status dirty..."
echo "test content" > "$TEST_FILE"

echo "Waiting for git status to stabilize (10 second timeout, 1 second interval)..."
START_TIME=$(date +%s)

WAIT_RESPONSE=$(curl -sS -X POST http://127.0.0.1:${PORT}/wait \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"timeout":10000,"checkInterval":1000}')

END_TIME=$(date +%s)
ACTUAL_ELAPSED=$((END_TIME - START_TIME))

echo "Response:"
echo "$WAIT_RESPONSE" | jq '.'

COMPLETED=$(echo "$WAIT_RESPONSE" | jq -r '.completed')
DETECTED_CHANGES=$(echo "$WAIT_RESPONSE" | jq -r '.detectedChanges')
ELAPSED=$(echo "$WAIT_RESPONSE" | jq -r '.elapsed')

if [[ "$COMPLETED" == "true" ]]; then
  echo "✅ PASS: Wait completed successfully"
  echo "   Elapsed: ${ELAPSED}ms (actual: ${ACTUAL_ELAPSED}s)"
  echo "   Detected changes: $DETECTED_CHANGES"
else
  echo "❌ FAIL: Wait did not complete"
  exit 1
fi
echo ""

# Test 4: Authentication failure
echo "Test 4: Authentication"
echo "----------------------"
echo "Testing with invalid token..."
AUTH_FAIL_RESPONSE=$(curl -sS -w "\nHTTP_CODE:%{http_code}" http://127.0.0.1:${PORT}/capture \
  -H "Authorization: Bearer invalid_token_123")

HTTP_CODE=$(echo "$AUTH_FAIL_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
RESPONSE_BODY=$(echo "$AUTH_FAIL_RESPONSE" | grep -v "HTTP_CODE:")

if [[ "$HTTP_CODE" == "401" ]]; then
  echo "✅ PASS: Authentication properly rejected invalid token (401)"
else
  echo "❌ FAIL: Expected 401, got $HTTP_CODE"
  exit 1
fi
echo ""

# Cleanup
echo "🧹 Cleaning up test file..."
rm -f "$TEST_FILE"

echo ""
echo "=========================================="
echo "✅ All tests passed!"
echo "=========================================="
echo ""
echo "📊 Summary:"
echo "   - Health check: OK"
echo "   - Capture endpoint: OK"  
echo "   - Wait endpoint: OK (${ELAPSED}ms)"
echo "   - Authentication: OK"
