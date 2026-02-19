/* eslint-disable no-console */
const fs = require("fs");
const path = require("path");
const vscode = require("vscode");

let terminalDataWriteEventAvailable = false;
let capturePromiseResolve;

const shellReadState = {
  attachedExecutionIdByTerminal: new Map(),
  lastAttachedTerminalName: "",
};

let captureState = {
  active: false,
  terminalName: "",
  lastFile: "",
  startedAtMs: 0,
  lastDataAtMs: 0,
  bytesWritten: 0,
  stopTimer: undefined,
};

function getConfig() {
  const cfg = vscode.workspace.getConfiguration("ivyhouseTerminalMonitor");
  return {
    codexCommand: cfg.get("codexCommand", "codex"),
    codexTerminalName: cfg.get("codexTerminalName", "Codex CLI"),
    alwaysCaptureCodex: cfg.get("alwaysCaptureCodex", true),
    opencodeCommand: cfg.get("opencodeCommand", "opencode"),
    opencodeTerminalName: cfg.get("opencodeTerminalName", "OpenCode CLI"),
    alwaysCaptureOpenCode: cfg.get("alwaysCaptureOpenCode", true),
    captureMaxSeconds: cfg.get("captureMaxSeconds", 10),
    captureSilenceMs: cfg.get("captureSilenceMs", 800),
    captureMaxBytes: cfg.get("captureMaxBytes", 65536),
    captureDir: cfg.get("captureDir", ".service/terminal_capture"),
  };
}

function getWorkspaceRootFsPath() {
  return vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath;
}

function resolveCapturePaths(cfg) {
  const root = getWorkspaceRootFsPath();
  if (!root) return undefined;
  const dir = path.join(root, cfg.captureDir);
  return {
    dir,
    lastFile: path.join(dir, "codex_last.txt"),
    lastFileDisplay: path.join(cfg.captureDir, "codex_last.txt"),
    liveFile: path.join(dir, "codex_live.txt"),
    liveFileDisplay: path.join(cfg.captureDir, "codex_live.txt"),
    opencodeLiveFile: path.join(dir, "opencode_live.txt"),
    opencodeLiveFileDisplay: path.join(cfg.captureDir, "opencode_live.txt"),
    debugFile: path.join(dir, "monitor_debug.jsonl"),
    debugFileDisplay: path.join(cfg.captureDir, "monitor_debug.jsonl"),
  };
}

function appendDebugEvent(cfg, event) {
  const paths = resolveCapturePaths(cfg);
  if (!paths) return;
  try {
    fs.mkdirSync(paths.dir, { recursive: true });
    const payload = {
      ts: new Date().toISOString(),
      ...event,
    };
    fs.appendFileSync(paths.debugFile, `${JSON.stringify(payload)}\n`, "utf8");
  } catch {
    // ignore
  }
}

function getLiveCaptureTarget(cfg, paths, terminalName) {
  if (!paths || !terminalName) return undefined;

  if (terminalName === cfg.codexTerminalName && cfg.alwaysCaptureCodex) {
    return {
      filePath: paths.liveFile,
      fileDisplay: paths.liveFileDisplay,
    };
  }

  if (terminalName === cfg.opencodeTerminalName && cfg.alwaysCaptureOpenCode) {
    return {
      filePath: paths.opencodeLiveFile,
      fileDisplay: paths.opencodeLiveFileDisplay,
    };
  }

  return undefined;
}

function appendRollingFile(filePath, buf, maxBytes) {
  fs.appendFileSync(filePath, buf);
  if (maxBytes <= 0) return;
  try {
    const st = fs.statSync(filePath);
    if (st.size <= maxBytes) return;
    const data = fs.readFileSync(filePath);
    const keepFrom = Math.max(0, data.length - maxBytes);
    fs.writeFileSync(filePath, data.subarray(keepFrom));
  } catch {
    // ignore
  }
}

function appendLiveCapture(cfg, terminal, data) {
  const paths = resolveCapturePaths(cfg);
  if (!paths) return;
  const target = getLiveCaptureTarget(cfg, paths, terminal?.name);
  if (!target) return;
  try {
    fs.mkdirSync(paths.dir, { recursive: true });
    const buf = Buffer.from(String(data), "utf8");
    const maxBytes = Math.max(0, Number(cfg.captureMaxBytes) || 0);
    appendRollingFile(target.filePath, buf, maxBytes);
  } catch {
    // ignore
  }
}

function findTerminalByName(name) {
  return vscode.window.terminals.find((terminal) => terminal.name === name);
}

function stripAnsi(s) {
  return String(s || "")
    .replace(/\x1b\[[0-9;?]*[ -/]*[@-~]/g, "")
    .replace(/\x1b\][^\x07]*(\x07|\x1b\\)/g, "")
    .replace(/\x1b\([^)]/g, "");
}

function readLastCaptureRaw(cfg) {
  const paths = resolveCapturePaths(cfg);
  if (!paths || !fs.existsSync(paths.lastFile)) return "";
  try {
    return fs.readFileSync(paths.lastFile, "utf8");
  } catch {
    return "";
  }
}

function analyzeCodexStatusCapture(raw) {
  const text = stripAnsi(String(raw || "")).replace(/\r/g, "\n");

  const hasStatusEcho = /(^|\n)\s*(›\s*)?\/status\b/i.test(text) || text.includes("/status");
  const hasContextLeft = /context left/i.test(text);
  const hasCodexSignal = /OpenAI Codex/i.test(text) || /\bTip:/i.test(text);
  const hasPastedOverlay = /\[Pasted Content\s+\d+\s+chars\]/i.test(text);

  const ok = hasStatusEcho && (hasContextLeft || hasCodexSignal) && !hasPastedOverlay;

  return {
    ok,
    hasStatusEcho,
    hasContextLeft,
    hasCodexSignal,
    hasPastedOverlay,
  };
}

function stopCapture(reason) {
  if (!captureState.active) return;
  captureState.active = false;
  if (captureState.stopTimer) {
    clearInterval(captureState.stopTimer);
  }
  captureState.stopTimer = undefined;
  if (typeof capturePromiseResolve === "function") {
    capturePromiseResolve(reason);
    capturePromiseResolve = undefined;
  }
}

function startCapture(cfg, terminalName) {
  const paths = resolveCapturePaths(cfg);
  if (!paths) {
    vscode.window.showErrorMessage("Workspace folder not found; cannot write capture file.");
    return undefined;
  }

  fs.mkdirSync(paths.dir, { recursive: true });
  fs.writeFileSync(paths.lastFile, "", "utf8");

  captureState = {
    active: true,
    terminalName,
    lastFile: paths.lastFile,
    startedAtMs: Date.now(),
    lastDataAtMs: Date.now(),
    bytesWritten: 0,
    stopTimer: undefined,
  };

  const maxMs = Math.max(0, Number(cfg.captureMaxSeconds) || 0) * 1000;
  const silenceMs = Math.max(0, Number(cfg.captureSilenceMs) || 0);
  captureState.stopTimer = setInterval(() => {
    if (!captureState.active) return;
    const now = Date.now();
    if (maxMs > 0 && now - captureState.startedAtMs >= maxMs) {
      stopCapture("timeout");
      return;
    }
    if (silenceMs > 0 && now - captureState.lastDataAtMs >= silenceMs) {
      stopCapture("silent");
    }
  }, 100);

  const capturePromise = new Promise((resolve) => {
    capturePromiseResolve = resolve;
  });

  return {
    captureFile: paths.lastFileDisplay,
    capturePromise,
  };
}

function appendCapture(cfg, terminal, data) {
  if (!captureState.active) return;
  if (!captureState.lastFile || !captureState.terminalName) return;
  if (terminal.name !== captureState.terminalName) return;

  const buf = Buffer.from(String(data), "utf8");
  const maxBytes = Math.max(0, Number(cfg.captureMaxBytes) || 0);

  if (maxBytes > 0 && captureState.bytesWritten + buf.length > maxBytes) {
    const remaining = maxBytes - captureState.bytesWritten;
    if (remaining > 0) {
      fs.appendFileSync(captureState.lastFile, buf.subarray(0, remaining));
      captureState.bytesWritten += remaining;
    }
    stopCapture("size limit");
    return;
  }

  fs.appendFileSync(captureState.lastFile, buf);
  captureState.bytesWritten += buf.length;
  captureState.lastDataAtMs = Date.now();
}

async function sendViaInjector(text) {
  await vscode.commands.executeCommand("ivyhouseTerminalInjector.sendLiteralToCodex", {
    text,
    submit: true,
  });
}

function formatDiagnostics(cfg) {
  const paths = resolveCapturePaths(cfg);
  const attachedTerminals = Array.from(shellReadState.attachedExecutionIdByTerminal.keys());
  const lines = [
    "IvyHouse Terminal Monitor diagnostics",
    `VS Code version: ${vscode.version}`,
    `Proposed API onDidWriteTerminalData available: ${terminalDataWriteEventAvailable}`,
    `captureDir: ${cfg.captureDir}`,
    `capture file: ${paths ? paths.lastFileDisplay : "<n/a>"}`,
    `shell read attached terminals: ${attachedTerminals.length ? attachedTerminals.join(", ") : "<none>"}`,
  ];
  return lines.join("\n");
}

function ensureCaptureSourceReady(cfg) {
  if (terminalDataWriteEventAvailable) return true;
  const hasShellRead = shellReadState.attachedExecutionIdByTerminal.has(cfg.codexTerminalName);
  return hasShellRead;
}

async function captureWithCommand(text) {
  const cfg = getConfig();
  const terminal = findTerminalByName(cfg.codexTerminalName);
  if (!terminal) {
    vscode.window.showErrorMessage(
      `Terminal '${cfg.codexTerminalName}' not found. Start it first via Injector extension.`,
    );
    return { ok: false, error: "terminal_not_found" };
  }

  const captureResult = startCapture(cfg, cfg.codexTerminalName);
  if (!captureResult) return { ok: false, error: "capture_start_failed" };

  if (!ensureCaptureSourceReady(cfg)) {
    stopCapture("no capture source");
    vscode.window.showErrorMessage(
      "目前無法擷取輸出：Proposed API 不可用，且尚未掛上 shell integration fallback。",
    );
    return {
      ok: false,
      error: "no_capture_source",
      captureFile: captureResult.captureFile,
    };
  }

  await sendViaInjector(text);
  const stopReason = await captureResult.capturePromise;
  const rawCapture = readLastCaptureRaw(cfg);

  return {
    ok: true,
    captureFile: captureResult.captureFile,
    stopReason,
    rawCapture,
  };
}

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalMonitor.ping", () => {
      const cfg = getConfig();
      appendDebugEvent(cfg, {
        type: "ping",
        vscodeVersion: vscode.version,
        hasWorkspaceFolder: Boolean(getWorkspaceRootFsPath()),
      });
      return true;
    }),
  );

  try {
    const cfg = getConfig();
    appendDebugEvent(cfg, {
      type: "activate",
      vscodeVersion: vscode.version,
    });
  } catch {
    // ignore
  }

  try {
    if (vscode.window.onDidWriteTerminalData) {
      terminalDataWriteEventAvailable = true;
      context.subscriptions.push(
        vscode.window.onDidWriteTerminalData((e) => {
          const cfg = getConfig();
          appendLiveCapture(cfg, e.terminal, e.data);
          appendCapture(cfg, e.terminal, e.data);
        }),
      );
    }
  } catch (err) {
    console.error(err);
    terminalDataWriteEventAvailable = false;
  }

  try {
    const cfg = getConfig();
    appendDebugEvent(cfg, {
      type: "proposed_api",
      onDidWriteTerminalData: terminalDataWriteEventAvailable,
    });
  } catch {
    // ignore
  }

  try {
    if (vscode.window.onDidStartTerminalShellExecution) {
      context.subscriptions.push(
        vscode.window.onDidStartTerminalShellExecution((e) => {
          try {
            const cfg = getConfig();
            const terminalName = e?.terminal?.name;
            if (!terminalName) return;

            const isCodexTerminal = terminalName === cfg.codexTerminalName;
            const isOpenCodeTerminal = terminalName === cfg.opencodeTerminalName;
            if (!isCodexTerminal && !isOpenCodeTerminal) return;

            const cmdValue = e.execution?.commandLine?.value;
            const cmdLine = typeof cmdValue === "string" ? cmdValue : "";

            if (typeof e.execution?.read !== "function") {
              appendDebugEvent(cfg, {
                type: "shell_execution_start",
                terminalName,
                commandLine: cmdLine,
                hasRead: false,
              });
              return;
            }

            appendDebugEvent(cfg, {
              type: "shell_execution_start",
              terminalName,
              commandLine: cmdLine,
              hasRead: true,
            });

            const currentId = shellReadState.attachedExecutionIdByTerminal.get(terminalName) || 0;
            const execId = currentId + 1;
            shellReadState.attachedExecutionIdByTerminal.set(terminalName, execId);
            shellReadState.lastAttachedTerminalName = terminalName;

            let sawData = false;

            (async () => {
              try {
                const stream = e.execution.read();
                for await (const data of stream) {
                  if (shellReadState.attachedExecutionIdByTerminal.get(terminalName) !== execId) {
                    break;
                  }
                  const cfgNow = getConfig();
                  if (!sawData) {
                    sawData = true;
                    let bytes = 0;
                    try {
                      if (Buffer.isBuffer(data)) {
                        bytes = data.length;
                      } else if (data instanceof Uint8Array) {
                        bytes = data.byteLength;
                      } else {
                        bytes = Buffer.byteLength(String(data), "utf8");
                      }
                    } catch {
                      bytes = 0;
                    }
                    appendDebugEvent(cfgNow, {
                      type: "shell_execution_first_data",
                      terminalName,
                      execId,
                      bytes,
                    });
                  }
                  appendLiveCapture(cfgNow, e.terminal, data);
                  appendCapture(cfgNow, e.terminal, data);
                }
              } catch (err) {
                console.error(err);
                appendDebugEvent(getConfig(), {
                  type: "shell_execution_error",
                  terminalName,
                  execId,
                  error: String(err || ""),
                });
              } finally {
                appendDebugEvent(getConfig(), {
                  type: "shell_execution_end",
                  terminalName,
                  execId,
                  sawData,
                });
              }
            })();
          } catch (err) {
            console.error(err);
          }
        }),
      );
    }
  } catch (err) {
    console.error(err);
  }

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalMonitor.captureCodexOutput", async () => {
      const text = await vscode.window.showInputBox({
        title: "Capture output from Codex CLI",
        prompt: "Command will be sent through Injector extension and output will be captured.",
        value: "/status",
      });
      if (typeof text !== "string" || text.trim() === "") return;
      await captureWithCommand(text);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalMonitor.autoCaptureCodexStatus", async () => {
      await captureWithCommand("/status");
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand(
      "ivyhouseTerminalMonitor.restartAndCaptureCodexStatus",
      async () => {
        await vscode.commands.executeCommand("ivyhouseTerminalInjector.restartCodex");
        await new Promise((resolve) => setTimeout(resolve, 5000));
        await captureWithCommand("/status");
      },
    ),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand(
      "ivyhouseTerminalMonitor.verifyCodexStatusInjection",
      async () => {
        await vscode.commands.executeCommand("ivyhouseTerminalInjector.restartCodex");
        await new Promise((resolve) => setTimeout(resolve, 5000));

        const capture = await captureWithCommand("/status");
        if (!capture || !capture.ok) {
          vscode.window.showErrorMessage(
            `Codex /status 自動驗證失敗：${capture?.error || "unknown_error"}`,
          );
          return;
        }

        const analysis = analyzeCodexStatusCapture(capture.rawCapture || "");
        const summary = [
          `status=${analysis.hasStatusEcho ? "Y" : "N"}`,
          `context=${analysis.hasContextLeft ? "Y" : "N"}`,
          `codexSignal=${analysis.hasCodexSignal ? "Y" : "N"}`,
          `overlay=${analysis.hasPastedOverlay ? "Y" : "N"}`,
          `stop=${capture.stopReason || "unknown"}`,
        ].join(" | ");

        if (analysis.ok) {
          vscode.window.showInformationMessage(
            `✅ Codex /status 自動驗證通過 (${summary})`,
          );
          return;
        }

        const choice = await vscode.window.showWarningMessage(
          `⚠️ Codex /status 自動驗證未通過 (${summary})`,
          "Open Last Capture",
        );

        if (choice === "Open Last Capture") {
          await vscode.commands.executeCommand("ivyhouseTerminalMonitor.openLastCodexCapture");
        }
      },
    ),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalMonitor.openLastCodexCapture", async () => {
      const cfg = getConfig();
      const paths = resolveCapturePaths(cfg);
      if (!paths) {
        vscode.window.showErrorMessage("Workspace folder not found; cannot open capture file.");
        return;
      }
      fs.mkdirSync(paths.dir, { recursive: true });
      if (!fs.existsSync(paths.lastFile)) {
        fs.writeFileSync(paths.lastFile, "", "utf8");
      }
      const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(paths.lastFile));
      await vscode.window.showTextDocument(doc, { preview: false });
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalMonitor.clearCodexCapture", async () => {
      const cfg = getConfig();
      const paths = resolveCapturePaths(cfg);
      if (!paths) {
        vscode.window.showErrorMessage("Workspace folder not found; cannot clear capture file.");
        return;
      }
      fs.mkdirSync(paths.dir, { recursive: true });
      fs.writeFileSync(paths.lastFile, "", "utf8");
      vscode.window.showInformationMessage(`Cleared ${paths.lastFileDisplay}`);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalMonitor.codexCaptureDiagnostics", async () => {
      const cfg = getConfig();
      const diag = formatDiagnostics(cfg);
      console.log(diag);
      vscode.window.showInformationMessage("Diagnostics printed to extension host console.");
    }),
  );
}

function deactivate() {
  stopCapture("deactivate");
}

module.exports = {
  activate,
  deactivate,
};
