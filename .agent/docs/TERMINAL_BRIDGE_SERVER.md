# Terminal Bridge Server

Standalone HTTP server for monitoring terminal operations and git status changes. Provides automated completion detection for Codex CLI workflows.

## Overview

This Python-based HTTP server provides terminal automation helpers (tmux control) and git-status based completion detection for Codex CLI workflows.

**Status**: ✅ Production Ready (v0.1.0-standalone)

---

## Features

- **Send Commands to Terminal**: `/send` and `/enter` endpoints control Codex CLI via tmux
- **Git Status Monitoring**: Detect when Codex CLI completes work by tracking git changes
- **Automated Completion Detection**: `/wait` endpoint blocks until git status stabilizes
- **Capture Changes**: `/capture` endpoint returns current git status
- **Token Authentication**: Secure Bearer token authentication
- **Daemon Mode**: Run as background process with PID management

---

## Quick Start

### 1. Start the Server

```bash
.agent/scripts/start_terminal_bridge.sh
```

Output:
```
🚀 Starting Terminal Bridge Server...
✅ Terminal Bridge Server started successfully
   PID: 19060
   Port: 38765
   Log: .agent/state/terminal_bridge.log

📡 Available endpoints:
   GET  /health  - Health check
   POST /send    - Send text to terminal
   POST /enter   - Send Enter key to terminal
   GET  /capture - Get git status changes
   POST /wait    - Wait for git status to stabilize

🔑 Token file: .agent/state/terminal_bridge_token
```

### 2. Monitor Completion (Optional)

Run your Codex CLI work as usual (manually or via `.agent/scripts/run_codex_template.sh`). If you want an external “completion signal”, call `/wait` to watch git status changes until they stabilize.

```bash
TOKEN=$(cat .agent/state/terminal_bridge_token)
curl -sS -X POST http://127.0.0.1:38765/wait \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"timeout":300000,"checkInterval":2000}'
```

### 3. Stop the Server

```bash
.agent/scripts/stop_terminal_bridge.sh
```

---

## API Reference

### Base URL
```
http://127.0.0.1:38765
```

### Authentication

All endpoints (except `/health`) require Bearer token authentication:

```bash
TOKEN=$(cat .agent/state/terminal_bridge_token)
curl -H "Authorization: Bearer ${TOKEN}" http://127.0.0.1:38765/capture
```

### Endpoints

#### `GET /health`
Health check endpoint (no authentication required).

**Response**:
```json
{
  "ok": true,
  "status": "running",
  "version": "0.1.0"
}
```

---

#### `POST /send`
Send text to Codex CLI terminal (via tmux).

**Headers**:
- `Authorization: Bearer <token>`
- `Content-Type: application/json`

**Request Body**:
```json
{
  "text": "/status",
  "execute": false  // If true, sends Enter key after text
}
```

**Response**:
```json
{
  "ok": true,
  "sent": "/status",
  "executed": false
}
```

**Example**:
```bash
TOKEN=$(cat .agent/state/terminal_bridge_token)

# Send text without executing
curl -X POST http://127.0.0.1:38765/send \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"text":"/status","execute":false}' | jq .

# Send text and execute (press Enter)
curl -X POST http://127.0.0.1:38765/send \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"text":"/status","execute":true}' | jq .
```

**How It Works**:
- Uses `tmux send-keys` to send text to terminal
- Default terminal: `codex-session:0` (configurable via `TERMINAL_NAME` env var)
- If `execute: false`, sends text in literal mode (no special key interpretation)
- If `execute: true`, sends text followed by Enter key

---

#### `POST /enter`
Send Enter key to Codex CLI terminal.

**Headers**:
- `Authorization: Bearer <token>`

**Response**:
```json
{
  "ok": true
}
```

**Example**:
```bash
TOKEN=$(cat .agent/state/terminal_bridge_token)
curl -X POST http://127.0.0.1:38765/enter \
  -H "Authorization: Bearer ${TOKEN}" | jq .
```

---

#### `GET /capture`
Get current git status changes.

**Headers**:
- `Authorization: Bearer <token>`

**Response**:
```json
{
  "ok": true,
  "lines": [
    "M file1.js",
    "?? new_file.py"
  ],
  "totalLines": 2,
  "timestamp": 1768355245.22
}
```

**Example**:
```bash
TOKEN=$(cat .agent/state/terminal_bridge_token)
curl -H "Authorization: Bearer ${TOKEN}" \
  http://127.0.0.1:38765/capture | jq .
```

---

#### `POST /wait`
Wait for git status to stabilize (automated completion detection).

**Headers**:
- `Authorization: Bearer <token>`
- `Content-Type: application/json`

**Request Body**:
```json
{
  "timeout": 300000,        // Max wait time in ms (default: 5 minutes)
  "checkInterval": 2000     // Check frequency in ms (default: 2 seconds)
}
```

**Success Response (200)**:
```json
{
  "ok": true,
  "completed": true,
  "elapsed": 45230,           // Actual elapsed time in ms
  "detectedChanges": true,    // Whether any changes were detected
  "finalStatus": {
    "timestamp": 1768355242.12,
    "changes": ["M file.js"],
    "count": 1
  }
}
```

**Timeout Response (408)**:
```json
{
  "ok": false,
  "completed": false,
  "elapsed": 300000,
  "reason": "timeout",
  "lastStatus": { ... }
}
```

**Example**:
```bash
TOKEN=$(cat .agent/state/terminal_bridge_token)
curl -X POST http://127.0.0.1:38765/wait \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"timeout":60000,"checkInterval":2000}' | jq .
```

**How It Works**:
1. Gets initial git status
2. Waits for `checkInterval` milliseconds
3. Checks git status again
4. If status unchanged for `checkInterval` duration → returns completed
5. If status changed → resets timer and repeats
6. Returns timeout error if `timeout` exceeded

---

## File Structure

```
.agent/
├── scripts/
│   ├── terminal_bridge_server.py      # Main server implementation
│   ├── start_terminal_bridge.sh       # Start server daemon
│   ├── stop_terminal_bridge.sh        # Stop server daemon
│   ├── test_terminal_bridge.sh        # Integration tests
└── state/
    ├── terminal_bridge_token          # Authentication token
    ├── terminal_bridge_info.json      # Server configuration
    ├── terminal_bridge.pid            # Process ID (when running)
    └── terminal_bridge.log            # Server logs
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TERMINAL_BRIDGE_PORT` | `38765` | HTTP server port |
| `WORKSPACE_ROOT` | `$(pwd)` | Git repository root |
| `TERMINAL_NAME` | `codex-session:0` | Tmux session/window for terminal commands |

**Example**:
```bash
export TERMINAL_BRIDGE_PORT=9000
export TERMINAL_NAME="my-session:1"
.agent/scripts/start_terminal_bridge.sh
```

---

## Comparison with VS Code Extension

| Feature | VS Code Extension | Standalone Server |
|---------|------------------|-------------------|
| Send commands to terminal | ✅ | ✅ (via tmux) |
| Terminal output capture | ✅ Real terminal output | ⚠️ Git status only |
| Git status monitoring | ✅ | ✅ |
| `/send` endpoint | ✅ | ✅ |
| `/enter` endpoint | ✅ | ✅ |
| `/wait` endpoint | ✅ | ✅ |
| `/capture` endpoint | ✅ | ✅ (limited) |
| Requires VS Code | ✅ | ❌ |
| Requires tmux | ❌ | ✅ |
| Activation issues | ⚠️ Known issues | ✅ Always works |
| Setup complexity | Medium | Low |

**Recommendation**: Use standalone server until VS Code extension activation issues are resolved.

---

## Troubleshooting

### Server Won't Start

**Check if port is already in use**:
```bash
lsof -i :38765
```

**View server logs**:
```bash
tail -f .agent/state/terminal_bridge.log
```

**Ensure git repository**:
```bash
git status  # Should not error
```

### Authentication Errors

**Verify token file exists**:
```bash
cat .agent/state/terminal_bridge_token
```

**Re-generate token**:
```bash
rm .agent/state/terminal_bridge_token
.agent/scripts/stop_terminal_bridge.sh
.agent/scripts/start_terminal_bridge.sh
```

### /wait Endpoint Times Out

**Reduce timeout and check interval**:
```bash
curl -X POST http://127.0.0.1:38765/wait \
  -H "Authorization: Bearer $(cat .agent/state/terminal_bridge_token)" \
  -H "Content-Type: application/json" \
  -d '{"timeout":30000,"checkInterval":1000}'
```

**Check git status manually**:
```bash
git status --short
```

If git status shows ongoing changes, `/wait` will keep checking until stable.

---

## Testing

Run integration tests:
```bash
.agent/scripts/test_terminal_bridge.sh
```

Expected output:
```
✅ All tests passed!

📊 Summary:
   - Health check: OK
   - Capture endpoint: OK
   - Wait endpoint: OK (527ms)
   - Authentication: OK
```

---

## Implementation Details

### Completion Detection Algorithm

The `/wait` endpoint uses a **stability-based** algorithm:

1. Take initial git status snapshot
2. Wait for `checkInterval` milliseconds
3. Take new snapshot
4. Compare snapshots:
   - **If different**: Reset stability timer, repeat from step 2
   - **If same**: Check if stable for ≥ `checkInterval` duration
     - **Yes**: Return completed
     - **No**: Wait more, repeat from step 2
5. If total elapsed time > `timeout`: Return timeout error

**Example Timeline**:
```
t=0s     Initial snapshot: 5 files changed
t=2s     New snapshot: 7 files changed (RESET timer)
t=4s     New snapshot: 7 files changed (stable for 2s)
         → Return completed (elapsed: 4000ms)
```

### Security

- **Token Generation**: Cryptographically secure random tokens (256-bit)
- **Token Storage**: File permissions set to `0600` (owner read/write only)
- **Token Validation**: Constant-time comparison to prevent timing attacks
- **CORS Headers**: Allow all origins (localhost only, no external access)

---

## Future Enhancements

- [ ] Real terminal output capture via tmux integration
- [ ] WebSocket support for real-time git status streaming
- [ ] Configurable stability duration (currently fixed at `checkInterval`)
- [ ] Multiple workspace support
- [ ] Metrics and performance logging

---

## License

Part of Ivyhousetw META project - Internal use only.

---

## Support

**Issues**: Create an issue in the project repository
**Logs**: `.agent/state/terminal_bridge.log`
**Status**: Check with `curl http://127.0.0.1:38765/health`
