/* eslint-disable no-console */
const vscode = require("vscode");

const STATE_KEYS = {
  startedCodex: "ivyhouseTerminalOrchestrator.startedCodex",
  startedOpenCode: "ivyhouseTerminalOrchestrator.startedOpenCode",
};

function getConfig() {
  const cfg = vscode.workspace.getConfiguration("ivyhouseTerminalOrchestrator");
  return {
    autoStart: cfg.get("autoStart", true),
    codexCommand: cfg.get("codexCommand", "codex"),
    opencodeCommand: cfg.get("opencodeCommand", "opencode --port 35103"),
    codexTerminalName: cfg.get("codexTerminalName", "Codex CLI"),
    opencodeTerminalName: cfg.get("opencodeTerminalName", "OpenCode CLI"),
  };
}

function findTerminalByName(name) {
  return vscode.window.terminals.find((t) => t.name === name);
}

function getOrCreateTerminal(name) {
  const existing = findTerminalByName(name);
  if (existing) return existing;
  return vscode.window.createTerminal({ name });
}

async function startTerminalIfNeeded(context, terminal, stateKey, command) {
  const alreadyStarted = context.workspaceState.get(stateKey, false);
  terminal.show(true);

  if (alreadyStarted) {
    return;
  }

  // Start via sendText (requirement: only sendText into these terminals)
  terminal.sendText(command, true);
  await context.workspaceState.update(stateKey, true);
}

async function promptAndSend(terminalName) {
  const terminal = findTerminalByName(terminalName);
  if (!terminal) {
    vscode.window.showErrorMessage(`Terminal '${terminalName}' not found. Start it first.`);
    return;
  }

  const text = await vscode.window.showInputBox({
    title: `Send text to ${terminalName}`,
    prompt: "Text will be sent via terminal.sendText()",
    placeHolder: "e.g. help",
  });

  if (typeof text !== "string" || text.trim() === "") return;

  terminal.show(true);
  terminal.sendText(text, true);
}

async function startAll(context) {
  const cfg = getConfig();

  const codexTerminal = getOrCreateTerminal(cfg.codexTerminalName);
  await startTerminalIfNeeded(context, codexTerminal, STATE_KEYS.startedCodex, cfg.codexCommand);

  const opencodeTerminal = getOrCreateTerminal(cfg.opencodeTerminalName);
  await startTerminalIfNeeded(
    context,
    opencodeTerminal,
    STATE_KEYS.startedOpenCode,
    cfg.opencodeCommand,
  );
}

function activate(context) {
  const cfg = getConfig();

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalOrchestrator.startCodex", async () => {
      const c = getConfig();
      const t = getOrCreateTerminal(c.codexTerminalName);
      await startTerminalIfNeeded(context, t, STATE_KEYS.startedCodex, c.codexCommand);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalOrchestrator.startOpenCode", async () => {
      const c = getConfig();
      const t = getOrCreateTerminal(c.opencodeTerminalName);
      await startTerminalIfNeeded(context, t, STATE_KEYS.startedOpenCode, c.opencodeCommand);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalOrchestrator.startAll", async () => {
      await startAll(context);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalOrchestrator.sendToCodex", async () => {
      const c = getConfig();
      await promptAndSend(c.codexTerminalName);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalOrchestrator.sendToOpenCode", async () => {
      const c = getConfig();
      await promptAndSend(c.opencodeTerminalName);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalOrchestrator.resetSessionState", async () => {
      await context.workspaceState.update(STATE_KEYS.startedCodex, false);
      await context.workspaceState.update(STATE_KEYS.startedOpenCode, false);
      vscode.window.showInformationMessage("IvyHouse Terminal Orchestrator session state reset.");
    }),
  );

  if (cfg.autoStart) {
    // Fire-and-forget; we intentionally don't block activation.
    startAll(context).catch((e) => {
      console.error(e);
      vscode.window.showErrorMessage("IvyHouse Terminal Orchestrator autoStart failed. See console.");
    });
  }
}

function deactivate() {}

module.exports = {
  activate,
  deactivate,
};
