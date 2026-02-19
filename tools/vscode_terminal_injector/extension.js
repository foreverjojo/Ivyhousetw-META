/* eslint-disable no-console */
const vscode = require("vscode");

const STATE_KEYS = {
  startedCodex: "ivyhouseTerminalInjector.startedCodex",
  startedOpenCode: "ivyhouseTerminalInjector.startedOpenCode",
};

function getConfig() {
  const cfg = vscode.workspace.getConfiguration("ivyhouseTerminalInjector");
  const legacyDelayMs = cfg.get("codexSubmitDelayMs", 350);
  return {
    autoStart: cfg.get("autoStart", true),
    codexCommand: cfg.get("codexCommand", "codex"),
    opencodeCommand: cfg.get("opencodeCommand", "opencode"),
    codexTerminalName: cfg.get("codexTerminalName", "Codex CLI"),
    opencodeTerminalName: cfg.get("opencodeTerminalName", "OpenCode CLI"),
    submitDelayMs: cfg.get("submitDelayMs", legacyDelayMs),
  };
}

function findTerminalByName(name) {
  return vscode.window.terminals.find((terminal) => terminal.name === name);
}

function getOrCreateTerminal(name) {
  const existing = findTerminalByName(name);
  if (existing) return existing;
  return vscode.window.createTerminal({ name });
}

function disposeTerminalByName(name) {
  const terminal = findTerminalByName(name);
  if (!terminal) return false;
  try {
    terminal.dispose();
    return true;
  } catch {
    return false;
  }
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, Math.max(0, Number(ms) || 0)));
}

async function waitForMonitorReady(maxWaitMs = 5000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < Math.max(0, Number(maxWaitMs) || 0)) {
    try {
      const ok = await vscode.commands.executeCommand("ivyhouseTerminalMonitor.ping");
      if (ok) return true;
    } catch {
      // ignore
    }
    await delay(200);
  }
  return false;
}

async function focusTerminal(terminal) {
  try {
    if (vscode.window.activeTerminal?.name !== terminal.name) {
      terminal.show(false);
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
  } catch {
    // ignore
  }
}

async function startTerminalIfNeeded(context, terminal, stateKey, command, force = false) {
  const hasStateKey = typeof stateKey === "string" && stateKey.trim() !== "";
  const alreadyStarted = hasStateKey ? context.workspaceState.get(stateKey, false) : false;

  try {
    terminal.show(true);
  } catch {
    // ignore
  }

  if (alreadyStarted && !force) {
    return true;
  }

  try {
    terminal.sendText(String(command || ""), true);
  } catch {
    return false;
  }

  if (hasStateKey) {
    await context.workspaceState.update(stateKey, true);
  }

  return true;
}

function parseSendArgs(args) {
  if (typeof args === "string") {
    return { text: args, submit: true };
  }

  if (args && typeof args === "object") {
    return {
      text: typeof args.text === "string" ? args.text : "",
      submit: typeof args.submit === "boolean" ? args.submit : true,
    };
  }

  return { text: "", submit: true };
}

async function sendToTerminal(terminal, text, submit, submitDelayMs = 40) {
  const payload = String(text || "");

  // NOTE: workbench.action.terminal.sendSequence targets the active terminal.
  // Ensure the intended terminal is active before sending the Enter sequence.
  await focusTerminal(terminal);

  if (!submit) {
    terminal.sendText(payload, false);
    return;
  }

  terminal.sendText(payload, false);
  await new Promise((resolve) => setTimeout(resolve, Math.max(0, Number(submitDelayMs) || 0)));

  // Primary: write CR directly to the target terminal input stream.
  // This does not depend on the terminal being active/focused.
  terminal.sendText("\r", false);

  // Best-effort extra: if the terminal is active, also send a key sequence.
  // Some TUIs behave differently for pasted text vs. key events.
  try {
    await focusTerminal(terminal);
    if (vscode.window.activeTerminal?.name === terminal.name) {
      await vscode.commands.executeCommand("workbench.action.terminal.sendSequence", {
        text: "\r",
      });
    }
  } catch {
    // ignore
  }
}

async function sendLiteralToTerminal(terminalName, args) {
  const terminal = findTerminalByName(terminalName);
  if (!terminal) {
    throw new Error(`Terminal '${terminalName}' not found. Start it first.`);
  }

  const payload = parseSendArgs(args);
  const text = String(payload.text || "");
  if (!text.trim()) {
    throw new Error("Text to send is empty.");
  }

  const cfg = getConfig();
  await sendToTerminal(terminal, text, payload.submit, cfg.submitDelayMs);
}

async function promptAndSend(terminalName) {
  const text = await vscode.window.showInputBox({
    title: `Send text to ${terminalName}`,
    prompt: "Text will be sent via Injector sendText",
    placeHolder: "e.g. /status",
  });

  if (typeof text !== "string" || text.trim() === "") return;
  await sendLiteralToTerminal(terminalName, { text, submit: true });
}

async function startAll(context) {
  const cfg = getConfig();

  await waitForMonitorReady();

  const codexExisting = findTerminalByName(cfg.codexTerminalName);
  const codexTerminal = codexExisting || getOrCreateTerminal(cfg.codexTerminalName);
  await startTerminalIfNeeded(
    context,
    codexTerminal,
    STATE_KEYS.startedCodex,
    cfg.codexCommand,
    !codexExisting,
  );

  const opencodeExisting = findTerminalByName(cfg.opencodeTerminalName);
  const opencodeTerminal = opencodeExisting || getOrCreateTerminal(cfg.opencodeTerminalName);
  await startTerminalIfNeeded(
    context,
    opencodeTerminal,
    STATE_KEYS.startedOpenCode,
    cfg.opencodeCommand,
    !opencodeExisting,
  );
}

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalInjector.startCodex", async () => {
      const cfg = getConfig();
      await waitForMonitorReady();
      const terminal = getOrCreateTerminal(cfg.codexTerminalName);
      await startTerminalIfNeeded(context, terminal, STATE_KEYS.startedCodex, cfg.codexCommand, true);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalInjector.pressEnterCodex", async () => {
      const cfg = getConfig();
      const terminal = findTerminalByName(cfg.codexTerminalName);
      if (!terminal) {
        vscode.window.showErrorMessage(
          `Terminal '${cfg.codexTerminalName}' not found. Start it first via Injector: Start Codex Terminal.`,
        );
        return;
      }
      terminal.sendText("\r", false);
      try {
        await focusTerminal(terminal);
        if (vscode.window.activeTerminal?.name === terminal.name) {
          await vscode.commands.executeCommand("workbench.action.terminal.sendSequence", {
            text: "\r",
          });
        }
      } catch {
        // ignore
      }
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalInjector.restartCodex", async () => {
      const cfg = getConfig();
      await waitForMonitorReady();
      disposeTerminalByName(cfg.codexTerminalName);
      await context.workspaceState.update(STATE_KEYS.startedCodex, false);
      const terminal = getOrCreateTerminal(cfg.codexTerminalName);
      await startTerminalIfNeeded(context, terminal, STATE_KEYS.startedCodex, cfg.codexCommand, true);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalInjector.restartOpenCode", async () => {
      const cfg = getConfig();
      await waitForMonitorReady();
      disposeTerminalByName(cfg.opencodeTerminalName);
      await context.workspaceState.update(STATE_KEYS.startedOpenCode, false);
      const terminal = getOrCreateTerminal(cfg.opencodeTerminalName);
      await startTerminalIfNeeded(
        context,
        terminal,
        STATE_KEYS.startedOpenCode,
        cfg.opencodeCommand,
        true,
      );
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalInjector.startOpenCode", async () => {
      const cfg = getConfig();
      await waitForMonitorReady();
      const terminal = getOrCreateTerminal(cfg.opencodeTerminalName);
      await startTerminalIfNeeded(
        context,
        terminal,
        STATE_KEYS.startedOpenCode,
        cfg.opencodeCommand,
        true,
      );
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalInjector.startAll", async () => {
      await startAll(context);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalInjector.sendToCodex", async () => {
      const cfg = getConfig();
      await promptAndSend(cfg.codexTerminalName);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalInjector.sendToOpenCode", async () => {
      const cfg = getConfig();
      await promptAndSend(cfg.opencodeTerminalName);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalInjector.sendLiteralToCodex", async (args) => {
      const cfg = getConfig();
      await sendLiteralToTerminal(cfg.codexTerminalName, args);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalInjector.sendLiteralToOpenCode", async (args) => {
      const cfg = getConfig();
      await sendLiteralToTerminal(cfg.opencodeTerminalName, args);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalInjector.resetSessionState", async () => {
      await context.workspaceState.update(STATE_KEYS.startedCodex, false);
      await context.workspaceState.update(STATE_KEYS.startedOpenCode, false);
      vscode.window.showInformationMessage("IvyHouse Terminal Injector session state reset.");
    }),
  );

  const cfg = getConfig();
  if (cfg.autoStart) {
    startAll(context).catch((err) => {
      console.error(err);
      vscode.window.showErrorMessage("IvyHouse Terminal Injector autoStart failed.");
    });
  }
}

function deactivate() {
  // noop
}

module.exports = {
  activate,
  deactivate,
};
