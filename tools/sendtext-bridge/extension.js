const vscode = require('vscode');
const http = require('http');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

const DEFAULT_PORT = 38765;
const DEFAULT_TERMINAL_NAME = 'Codex CLI';
const TOKEN_FILE_REL = path.join('.agent', 'state', 'sendtext_bridge_token');
const INFO_FILE_REL = path.join('.agent', 'state', 'sendtext_bridge_info.json');
const MAX_BUFFER_LINES = 1000;

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  /** @type {http.Server | null} */
  let server = null;

  const state = {
    port: getConfiguredPort(),
    token: '',
    terminalName: getConfiguredTerminalName(),
  };

  // Terminal output buffer (v0.1.0)
  const outputBuffer = [];

  function workspaceRoot() {
    const folders = vscode.workspace.workspaceFolders;
    if (folders && folders.length > 0) return folders[0].uri.fsPath;
    return null;
  }

  function ensureAgentStateDir(root) {
    const dir = path.join(root, '.agent', 'state');
    fs.mkdirSync(dir, { recursive: true });
  }

  function loadOrCreateToken(root) {
    const envToken = process.env.SENDTEXT_BRIDGE_TOKEN;
    if (envToken && envToken.trim()) return envToken.trim();

    const tokenPath = path.join(root, TOKEN_FILE_REL);

    try {
      if (fs.existsSync(tokenPath)) {
        const existing = fs.readFileSync(tokenPath, 'utf8').trim();
        if (existing) return existing;
      }
    } catch {
      // ignore
    }

    const token = crypto.randomBytes(24).toString('hex');
    fs.writeFileSync(tokenPath, token + '\n', 'utf8');
    return token;
  }

  function writeInfoFile(root) {
    const infoPath = path.join(root, INFO_FILE_REL);
    const body = {
      port: state.port,
      terminalName: state.terminalName,
      tokenFile: TOKEN_FILE_REL,
      tokenEnv: 'SENDTEXT_BRIDGE_TOKEN',
      terminalNameEnv: 'SENDTEXT_BRIDGE_TERMINAL_NAME',
      endpoints: {
        health: 'GET /health',
        send: 'POST /send { text, execute?: boolean }',
        enter: 'POST /enter',
        capture: 'GET /capture?lines=N',
        wait: 'POST /wait { timeout?, checkInterval? }'
      }
    };
    fs.writeFileSync(infoPath, JSON.stringify(body, null, 2) + '\n', 'utf8');
  }

  // Strip ANSI escape codes (v0.1.0)
  function stripAnsi(str) {
    return str.replace(/\x1b\[[0-9;]*m/g, '');
  }

  // Check git status for changes (v0.1.0)
  function checkGitStatus() {
    return new Promise((resolve) => {
      const cwd = workspaceRoot();
      if (!cwd) return resolve(false);

      exec('git status --porcelain', { cwd }, (err, stdout) => {
        if (err) return resolve(false);
        resolve(stdout.trim().length > 0);
      });
    });
  }

  // Sleep helper (v0.1.0)
  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Terminal output listener (v0.1.0)
  context.subscriptions.push(
    vscode.window.onDidWriteTerminalData(event => {
      if (event.terminal.name === state.terminalName) {
        const lines = event.data.split(/\r?\n/).map(line => stripAnsi(line));
        outputBuffer.push(...lines);

        // Keep buffer size limited (circular buffer)
        if (outputBuffer.length > MAX_BUFFER_LINES) {
          outputBuffer.splice(0, outputBuffer.length - MAX_BUFFER_LINES);
        }
      }
    })
  );

  function authOk(req) {
    const header = req.headers['authorization'];
    if (!header) return false;
    const m = /^Bearer\s+(.+)$/.exec(String(header));
    if (!m) return false;
    return m[1] === state.token;
  }

  function json(res, code, obj) {
    res.writeHead(code, { 'content-type': 'application/json' });
    res.end(JSON.stringify(obj));
  }

  function readBody(req) {
    return new Promise((resolve, reject) => {
      let data = '';
      req.on('data', (chunk) => {
        data += chunk;
        if (data.length > 1024 * 1024) {
          reject(new Error('body too large'));
          try { req.destroy(); } catch {}
        }
      });
      req.on('end', () => resolve(data));
      req.on('error', reject);
    });
  }

  function getOrCreateTerminal() {
    const existing = vscode.window.terminals.find((t) => t.name === state.terminalName);
    if (existing) return existing;
    return vscode.window.createTerminal({ name: state.terminalName });
  }

  async function startServer() {
    const root = workspaceRoot();
    if (!root) {
      vscode.window.showWarningMessage('SendText Bridge: no workspace folder; not starting.');
      return;
    }

    ensureAgentStateDir(root);
    state.token = loadOrCreateToken(root);
    writeInfoFile(root);

    if (server) {
      await new Promise((resolve) => server.close(() => resolve()));
      server = null;
    }

    server = http.createServer(async (req, res) => {
      try {
        if (req.url === '/health' && req.method === 'GET') {
          return json(res, 200, { ok: true });
        }

        if (!authOk(req)) {
          return json(res, 401, { ok: false, error: 'unauthorized' });
        }

        if (req.url === '/send' && req.method === 'POST') {
          const raw = await readBody(req);
          let payload;
          try {
            payload = raw ? JSON.parse(raw) : {};
          } catch {
            return json(res, 400, { ok: false, error: 'invalid json' });
          }

          const text = typeof payload.text === 'string' ? payload.text : '';
          const execute = payload.execute === true;

          const term = getOrCreateTerminal();
          term.show(true);
          term.sendText(text, execute);

          return json(res, 200, { ok: true, execute });
        }

        if (req.url === '/enter' && req.method === 'POST') {
          const term = getOrCreateTerminal();
          term.show(true);
          term.sendText('', true);
          return json(res, 200, { ok: true });
        }

        // NEW: /capture endpoint (v0.1.0)
        if (req.url.startsWith('/capture') && req.method === 'GET') {
          const url = new URL(req.url, `http://localhost:${state.port}`);
          const lines = parseInt(url.searchParams.get('lines') || '100', 10);

          const captured = outputBuffer.slice(-Math.min(lines, outputBuffer.length));

          return json(res, 200, {
            ok: true,
            lines: captured,
            totalLines: captured.length,
            bufferSize: outputBuffer.length
          });
        }

        // NEW: /wait endpoint (v0.1.0)
        if (req.url === '/wait' && req.method === 'POST') {
          const raw = await readBody(req);
          let payload;
          try {
            payload = raw ? JSON.parse(raw) : {};
          } catch {
            return json(res, 400, { ok: false, error: 'invalid json' });
          }

          const timeout = payload.timeout || 300000; // default 5 min
          const checkInterval = payload.checkInterval || 2000; // default 2s
          const startTime = Date.now();

          // Polling loop
          while (Date.now() - startTime < timeout) {
            const hasChanges = await checkGitStatus();

            if (hasChanges) {
              return json(res, 200, {
                ok: true,
                completed: true,
                elapsed: Date.now() - startTime,
                detectedChanges: true
              });
            }

            await sleep(checkInterval);
          }

          // Timeout
          return json(res, 200, {
            ok: true,
            completed: false,
            elapsed: Date.now() - startTime,
            reason: 'timeout'
          });
        }

        return json(res, 404, { ok: false, error: 'not found' });
      } catch (e) {
        return json(res, 500, { ok: false, error: String(e && e.message ? e.message : e) });
      }
    });

    await new Promise((resolve, reject) => {
      server.on('error', reject);
      server.listen(state.port, '127.0.0.1', () => resolve());
    });

    vscode.window.showInformationMessage(`SendText Bridge: listening on 127.0.0.1:${state.port}`);
  }

  context.subscriptions.push(
    vscode.commands.registerCommand('sendtextBridge.showInfo', async () => {
      const root = workspaceRoot();
      if (!root) {
        vscode.window.showWarningMessage('SendText Bridge: no workspace folder.');
        return;
      }
      vscode.window.showInformationMessage(
        'SendText Bridge: see .agent/state/sendtext_bridge_info.json and .agent/state/sendtext_bridge_token'
      );
    }),
    vscode.commands.registerCommand('sendtextBridge.restart', async () => {
      await startServer();
    })
  );

  startServer().catch((e) => {
    vscode.window.showErrorMessage(`SendText Bridge failed to start: ${String(e && e.message ? e.message : e)}`);
  });
}

function getConfiguredPort() {
  const envPort = process.env.SENDTEXT_BRIDGE_PORT;
  if (envPort && /^\d+$/.test(envPort)) return Number(envPort);
  return DEFAULT_PORT;
}

function getConfiguredTerminalName() {
  const envName = process.env.SENDTEXT_BRIDGE_TERMINAL_NAME;
  if (envName && envName.trim()) return envName.trim();
  return DEFAULT_TERMINAL_NAME;
}

function deactivate() {}

module.exports = { activate, deactivate };
