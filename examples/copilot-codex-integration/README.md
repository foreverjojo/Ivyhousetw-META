# Copilot ↔ Codex Command Integration Example

This is a minimal demo VS Code extension showing how one extension can send a QA request to another extension (here simulated as `codex.runQA`) and receive the QA result back via a command.

How it works:
- `example.sendToCodex` asks the user for a prompt and calls `vscode.commands.executeCommand('codex.runQA', { prompt, replyCommand })`.
- `codex.runQA` simulates processing and then calls `vscode.commands.executeCommand(replyCommand, result)` to send the result back.

Usage:
1. Open this workspace in VS Code.
2. Run the `Developer: Load Extension` flow or package/install this extension.
3. Run the command palette entry: `Example: Send QA to Codex` and enter a prompt.
4. Observe notifications showing the flow and the returned QA result.

Notes:
- In a real integration, `codex.runQA` would be provided by the Codex extension and `example.sendToCodex` by your caller extension (e.g., Cline or Copilot). The pattern is the same: use `vscode.commands.executeCommand` for call/response.
- Authentication and entitlement steps (login prompts) must be handled according to each extension's requirements.
