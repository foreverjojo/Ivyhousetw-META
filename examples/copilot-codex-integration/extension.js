const vscode = require('vscode');

/**
 * Activate the demo extension.
 * Commands:
 * - example.sendToCodex : send a QA prompt to 'codex.runQA'
 * - codex.runQA         : simulates Codex processing and replies via a provided command id
 * - example.receiveQAResult : receives QA result (simulates caller handling)
 */
function activate(context) {
  // Codex command: receives payload { prompt, replyCommand }
  const codexCmd = vscode.commands.registerCommand('codex.runQA', async (payload) => {
    const prompt = (payload && payload.prompt) || '<no prompt>';
    vscode.window.showInformationMessage(`Codex: received QA request: ${prompt}`);

    // Simulate async QA processing
    setTimeout(async () => {
      const result = {
        success: true,
        summary: `QA result for: ${prompt}`,
        timestamp: new Date().toISOString()
      };

          if (payload && payload.replyCommand) {
            try {
              await vscode.commands.executeCommand(payload.replyCommand, result);
              vscode.window.showInformationMessage('Codex: sent QA result back to caller.');
            } catch (err) {
              vscode.window.showErrorMessage('Codex: failed to send QA result - ' + String(err));
            }
          } else {
            vscode.window.showInformationMessage('Codex: no replyCommand provided.');
          }
    }, 1000);
  });

  // Caller receives QA results here
  const receiveCmd = vscode.commands.registerCommand('example.receiveQAResult', (result) => {
    vscode.window.showInformationMessage(`Caller: received QA result: ${JSON.stringify(result)}`);
    // Additional processing could be done here
  });

  // Forwarder: ask for a target command id and optional JSON payload, then execute it
  const forwardCmd = vscode.commands.registerCommand('example.forwardToCommand', async () => {
    const target = await vscode.window.showInputBox({ prompt: 'Target command id to call (e.g., codex.runQA)' });
    if (!target) {
      vscode.window.showInformationMessage('No target command id entered.');
      return;
    }

    const payloadStr = await vscode.window.showInputBox({ prompt: 'JSON payload to send (or leave empty for {})' });
    let payload = {};
    if (payloadStr) {
      try {
        payload = JSON.parse(payloadStr);
      } catch (e) {
        vscode.window.showErrorMessage('Invalid JSON payload');
        return;
      }
    }

    // Ask whether caller should receive a reply if none provided
    if (!payload.replyCommand) {
      const wantReply = await vscode.window.showQuickPick(['Yes', 'No'], { placeHolder: 'Do you want this caller to receive a reply via command?' });
      if (wantReply === 'Yes') payload.replyCommand = 'example.receiveQAResult';
    }

    try {
      const available = await vscode.commands.getCommands(true);
      if (!available.includes(target)) {
        vscode.window.showWarningMessage(`Command ${target} not found among registered commands.`);
      }
      await vscode.commands.executeCommand(target, payload);
      vscode.window.showInformationMessage(`Forwarded to ${target}`);
    } catch (err) {
      vscode.window.showErrorMessage('Forward failed: ' + String(err));
    }
  });

  // Example command to send QA to Codex (prompts user for input)
  const sendCmd = vscode.commands.registerCommand('example.sendToCodex', async () => {
    const prompt = await vscode.window.showInputBox({ prompt: 'Enter QA prompt to send to Codex' });
    if (!prompt) {
      vscode.window.showInformationMessage('No prompt entered.');
      return;
    }

    const payload = { prompt, replyCommand: 'example.receiveQAResult' };
    try {
      await vscode.commands.executeCommand('codex.runQA', payload);
      vscode.window.showInformationMessage('Sent QA request to Codex.');
    } catch (err) {
      vscode.window.showErrorMessage('Failed to send QA to Codex: ' + String(err));
    }
  });

  // One-shot command: invoke codex.runQA with a single prompt and receive result
  const runOnceCmd = vscode.commands.registerCommand('example.runCodexOnce', async () => {
    const prompt = await vscode.window.showInputBox({ prompt: 'One-shot QA prompt for codex.runQA', value: 'One-shot QA: summarize this example' });
    if (!prompt) {
      vscode.window.showInformationMessage('No prompt entered.');
      return;
    }

    const payload = { prompt, replyCommand: 'example.receiveQAResult' };
    try {
      await vscode.commands.executeCommand('codex.runQA', payload);
      vscode.window.showInformationMessage('Triggered codex.runQA (one-shot).');
    } catch (err) {
      vscode.window.showErrorMessage('Failed to trigger codex.runQA: ' + String(err));
    }
  });

  // Run an external Codex CLI: prompt for command name, prompt text, and whether to pass via stdin
  const runCliCmd = vscode.commands.registerCommand('example.runCodexCLI', async () => {
    const cli = await vscode.window.showInputBox({ prompt: 'External CLI command to run', value: 'codex' });
    if (!cli) return vscode.window.showInformationMessage('No CLI command entered.');

    const prompt = await vscode.window.showInputBox({ prompt: 'Prompt to send to CLI', value: 'Please summarize this example' });
    if (typeof prompt === 'undefined') return;

    const viaStdin = await vscode.window.showQuickPick(['stdin', 'arg'], { placeHolder: 'Send prompt via stdin or as an argument?' });
    if (!viaStdin) return;

    const cp = require('child_process');
    try {
      if (viaStdin === 'stdin') {
        const child = cp.spawn(cli, [], { shell: true });
        let out = '';
        let errOut = '';
        child.stdout.on('data', d => out += d.toString());
        child.stderr.on('data', d => errOut += d.toString());
        child.on('close', async (code) => {
          if (code === 0) {
            const result = { success: true, summary: out.trim(), timestamp: new Date().toISOString() };
            await vscode.commands.executeCommand('example.receiveQAResult', result);
          } else {
            vscode.window.showErrorMessage(`CLI exited ${code}: ${errOut}`);
          }
        });
        child.stdin.write(prompt);
        child.stdin.end();
      } else {
        const exec = require('child_process').exec;
        exec(`${cli} ${JSON.stringify(prompt)}`, (error, stdout, stderr) => {
          if (error) {
            vscode.window.showErrorMessage('CLI error: ' + String(stderr || error.message));
            return;
          }
          const result = { success: true, summary: stdout.trim(), timestamp: new Date().toISOString() };
          vscode.commands.executeCommand('example.receiveQAResult', result);
        });
      }
    } catch (err) {
      vscode.window.showErrorMessage('Failed to run CLI: ' + String(err));
    }
  });

  context.subscriptions.push(runCliCmd);

  context.subscriptions.push(codexCmd, receiveCmd, sendCmd, forwardCmd, runOnceCmd);
}

function deactivate() {}

module.exports = { activate, deactivate };
