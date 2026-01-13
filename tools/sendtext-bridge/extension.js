const vscode = require('vscode');
const http = require('http');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const DEFAULT_PORT = 38765;
const DEFAULT_TERMINAL_NAME = 'Codex CLI';
const TOKEN_FILE_REL = path.join('.agent', 'state', 'sendtext_bridge_token');
const INFO_FILE_REL = path.join('.agent', 'state', 'sendtext_bridge_info.json');

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
    listeners: new Map(), // listener_id -> { patterns, callback }
    nextListenerId: 1,
  };

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
        wait: 'POST /wait { timeout?: number, checkInterval?: number }'
      }
    };
    fs.writeFileSync(infoPath, JSON.stringify(body, null, 2) + '\n', 'utf8');
  }

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
    const newTerm = vscode.window.createTerminal({ name: state.terminalName });
    setupTerminalListener(newTerm);
    return newTerm;
  }

  function setupTerminalListener(terminal) {
    // 監聽 terminal 輸出（透過 onDidWriteTerminalShellIntegration 需要 shell integration）
    // 使用 onDidChangeTerminalState 替代方案
    const disposable = vscode.window.onDidChangeTerminalState((e) => {
      if (e.terminal === terminal) {
        checkTerminalOutput();
      }
    });
    context.subscriptions.push(disposable);
  }

  function checkTerminalOutput() {
    // 檢查是否有 listener 需要通知
    // 由於 VS Code API 無法直接讀取 terminal 輸出，我們改用輪詢 git status
    state.listeners.forEach((listener) => {
      listener.callback();
    });
  }

  function addOutputListener(patterns, callback) {
    const id = state.nextListenerId++;
    state.listeners.set(id, { patterns, callback });
    return id;
  }

  function removeOutputListener(id) {
    state.listeners.delete(id);
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

        if (req.url === '/wait' && req.method === 'POST') {
          const raw = await readBody(req);
          let payload;
          try {
            payload = raw ? JSON.parse(raw) : {};
          } catch {
            return json(res, 400, { ok: false, error: 'invalid json' });
          }

          const timeout = typeof payload.timeout === 'number' ? payload.timeout : 300000; // 預設 5 分鐘
          const checkInterval = typeof payload.checkInterval === 'number' ? payload.checkInterval : 2000; // 預設 2 秒

          const startTime = Date.now();
          let completed = false;

          // 輪詢 git status 檢查變更
          const checkCompletion = async () => {
            const root = workspaceRoot();
            if (!root) return false;

            try {
              const { exec } = require('child_process');
              const { promisify } = require('util');
              const execAsync = promisify(exec);

              const { stdout } = await execAsync('git status --porcelain', { cwd: root });
              return stdout.trim().length > 0; // 有變更即表示完成
            } catch {
              return false;
            }
          };

          while (!completed && (Date.now() - startTime) < timeout) {
            completed = await checkCompletion();
            if (!completed) {
              await new Promise((resolve) => setTimeout(resolve, checkInterval));
            }
          }

          if (completed) {
            return json(res, 200, { ok: true, completed: true, elapsed: Date.now() - startTime });
          } else {
            return json(res, 408, { ok: false, completed: false, error: 'timeout', elapsed: Date.now() - startTime });
          }
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
