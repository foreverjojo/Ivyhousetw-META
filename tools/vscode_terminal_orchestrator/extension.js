/* eslint-disable no-console */
const vscode = require("vscode");
const fs = require("fs");
const path = require("path");
const childProcess = require("child_process");
const crypto = require("crypto");

const STATE_KEYS = {
  startedCodex: "ivyhouseTerminalOrchestrator.startedCodex",
  startedOpenCode: "ivyhouseTerminalOrchestrator.startedOpenCode",
};

function getConfig() {
  const cfg = vscode.workspace.getConfiguration("ivyhouseTerminalOrchestrator");
  return {
    autoStart: cfg.get("autoStart", true),
    codexCommand: cfg.get("codexCommand", "codex"),
    opencodeCommand: cfg.get("opencodeCommand", "opencode"),
    codexTerminalName: cfg.get("codexTerminalName", "Codex CLI"),
    opencodeTerminalName: cfg.get("opencodeTerminalName", "OpenCode CLI"),
    captureMaxSeconds: cfg.get("captureMaxSeconds", 10),
    captureSilenceMs: cfg.get("captureSilenceMs", 800),
    captureMaxBytes: cfg.get("captureMaxBytes", 65536),
    captureDir: cfg.get("captureDir", ".service/terminal_capture"),
    workflowPollIntervalMs: cfg.get("workflowPollIntervalMs", 5000),
    workflowMaxRounds: cfg.get("workflowMaxRounds", 10),
    workflowTimeoutMs: cfg.get("workflowTimeoutMs", 1800000),
    workflowTailLines: cfg.get("workflowTailLines", 200),
    workflowReadyTimeoutMs: cfg.get("workflowReadyTimeoutMs", 60000),
    workflowReadyPollIntervalMs: cfg.get("workflowReadyPollIntervalMs", 300),
    workflowSendRetryCount: cfg.get("workflowSendRetryCount", 3),
    workflowSendAckTimeoutMs: cfg.get("workflowSendAckTimeoutMs", 3000),
    workflowSendRetryDelayMs: cfg.get("workflowSendRetryDelayMs", 1200),
    workflowPrimeEnterCount: cfg.get("workflowPrimeEnterCount", 2),
    workflowPromptClearCaptureOnPass: cfg.get("workflowPromptClearCaptureOnPass", true),
  };
}

function getWorkspaceRootFsPath() {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) return undefined;
  return folders[0].uri.fsPath;
}

function resolveCapturePaths(cfg) {
  const root = getWorkspaceRootFsPath();
  if (!root) return undefined;
  const dir = path.join(root, cfg.captureDir);
  const lastFile = path.join(dir, "codex_last.txt");
  const lastFileDisplay = path.join(cfg.captureDir, "codex_last.txt");
  return { dir, lastFile, lastFileDisplay };
}

function findTerminalByName(name) {
  return vscode.window.terminals.find((t) => t.name === name);
}

function getOrCreateTerminal(name) {
  const existing = findTerminalByName(name);
  if (existing) return existing;
  return vscode.window.createTerminal({ name });
}

function sleepMs(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForTerminalToClose(name, timeoutMs = 3000) {
  const startedAt = Date.now();
  if (!findTerminalByName(name)) return true;

  return await new Promise((resolve) => {
    let disposed = false;
    let closeSub;
    try {
      closeSub = vscode.window.onDidCloseTerminal((t) => {
        if (t?.name !== name) return;
        if (!findTerminalByName(name)) {
          disposed = true;
          try {
            closeSub?.dispose();
          } catch {
            // ignore
          }
          resolve(true);
        }
      });
    } catch {
      // If onDidCloseTerminal is unavailable, fall back to polling.
      closeSub = undefined;
    }

    const timer = setInterval(() => {
      const gone = !findTerminalByName(name);
      const timedOut = Date.now() - startedAt >= timeoutMs;
      if (gone || timedOut) {
        clearInterval(timer);
        try {
          closeSub?.dispose();
        } catch {
          // ignore
        }
        resolve(gone || disposed);
      }
    }, 100);
  });
}

function disposeTerminalByName(name) {
  const t = findTerminalByName(name);
  if (t) {
    try {
      t.dispose();
    } catch {
      // ignore
    }
    return true;
  }
  return false;
}

let captureState = {
  active: false,
  terminalName: undefined,
  lastFile: undefined,
  lastFileDisplay: undefined,
  bytesWritten: 0,
  startedAtMs: 0,
  lastDataAtMs: 0,
  stopTimer: undefined,
};

let terminalDataWriteEventAvailable = false;
let outputChannel;

// Fallback path when proposed terminal data event isn't available.
// We attach to the shell execution stream for the long-running `codex` process.
const shellReadState = {
  attachedTerminalName: undefined,
  attachedExecutionId: 0,
};

// Capture Promise resolution
let capturePromiseResolve = undefined;

const WORKFLOW_MARKERS = {
  engineerDone: "[ENGINEER_DONE]",
  fixDone: "[FIX_DONE]",
  qaDone: "[QA_DONE]",
  qaPass: "QA_RESULT=PASS",
  qaFail: "QA_RESULT=FAIL",
};

const WORKFLOW_MARKER_NAMES = {
  engineerDone: "ENGINEER_DONE",
  fixDone: "FIX_DONE",
  qaDone: "QA_DONE",
};

const WORKFLOW_PHASE = {
  idle: "IDLE",
  waitEngineerDone: "WAIT_ENGINEER_DONE",
  waitQaDone: "WAIT_QA_DONE",
  waitFixDone: "WAIT_FIX_DONE",
  done: "DONE",
};

let workflowLoopState = {
  active: false,
  phase: WORKFLOW_PHASE.idle,
  captureMode: "none", // script | terminalData | none
  startedAtMs: 0,
  round: 0,
  taskDescription: "",
  engineerTerminalName: undefined,
  qaTerminalName: undefined,
  engineerTerminal: undefined,
  qaTerminal: undefined,
  // In script mode, we write raw transcripts to *_raw.log (noisy/large), and keep compact tail logs
  // in engineer_*.log / qa_*.log for human viewing + summaries.
  engineerRawLogAbs: undefined,
  qaRawLogAbs: undefined,
  engineerLogAbs: undefined,
  engineerLogDisplay: undefined,
  qaLogAbs: undefined,
  qaLogDisplay: undefined,
  eventLogAbs: undefined,
  eventLogDisplay: undefined,
  engineerOffset: 0,
  qaOffset: 0,
  engineerMarkerBuf: "",
  qaMarkerBuf: "",
  // When we send a prompt, transcript logs will include our input (including marker strings).
  // To avoid false-positive marker detection, we temporarily pause detection and then
  // fast-forward offsets once the prompt echo has been written.
  engineerPauseUntilMs: 0,
  qaPauseUntilMs: 0,
  pollIntervalMs: 5000,
  maxRounds: 10,
  timeoutMs: 1800000,
  timer: undefined,
  tickBusy: false,
};

function normalizeInstruction(text) {
  // Many interactive CLIs treat multi-line input specially (may not submit on Enter).
  // For reliability, collapse to a single line.
  return String(text || "")
    .replace(/\r?\n+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function safeGetFileSize(filePath) {
  try {
    return Number(fs.statSync(filePath).size) || 0;
  } catch {
    return 0;
  }
}

function bashSingleQuote(s) {
  // Safely wrap any string for bash single-quoted contexts.
  return `'${String(s).replace(/'/g, `'"'"'`)}'`;
}

function stripAnsi(s) {
  // Minimal ANSI stripper for marker detection.
  // Covers CSI + a few common ESC sequences.
  return String(s)
    .replace(/\x1b\[[0-9;]*[A-Za-z]/g, "")
    .replace(/\x1b\][^\x07]*(\x07|\x1b\\)/g, "")
    .replace(/\x1b\([^)]/g, "");
}

function hasMarkerLine(buf, markerName) {
  // Require the bracketed marker to appear as a standalone line.
  // This prevents false positives when prompts are echoed by the CLI.
  const m = String(markerName || "");
  if (!m) return false;
  const re = new RegExp(`(^|\\n)\\[${m.replace(/[-/\\^$*+?.()|[\\]{}]/g, "\\$&")}\\](\\r?\\n|$)`, "m");
  return re.test(String(buf || ""));
}

function getQaResult(buf) {
  // Accept both strict and spaced variants: QA_RESULT=PASS, QA_RESULT = PASS
  const s = String(buf || "");
  if (/(^|\n)QA_RESULT\s*=\s*PASS(\r?\n|$)/m.test(s)) return "PASS";
  if (/(^|\n)QA_RESULT\s*=\s*FAIL(\r?\n|$)/m.test(s)) return "FAIL";
  return undefined;
}

function isScriptAvailable() {
  try {
    const r = childProcess.spawnSync("bash", ["-lc", "command -v script"], {
      encoding: "utf8",
    });
    return r.status === 0 && String(r.stdout || "").trim() !== "";
  } catch {
    return false;
  }
}

function resolveWorkflowLogPaths(cfg) {
  const root = getWorkspaceRootFsPath();
  if (!root) return undefined;

  const dirAbs = path.join(root, cfg.captureDir);
  const ts = new Date()
    .toISOString()
    .replace(/[-:.TZ]/g, "")
    .slice(0, 14);
  const engineerFile = `engineer_${ts}.log`;
  const qaFile = `qa_${ts}.log`;
  const engineerRawFile = `engineer_${ts}_raw.log`;
  const qaRawFile = `qa_${ts}_raw.log`;
  const eventFile = `workflow_${ts}_events.jsonl`;

  return {
    dirAbs,
    engineerLogAbs: path.join(dirAbs, engineerFile),
    qaLogAbs: path.join(dirAbs, qaFile),
    engineerRawLogAbs: path.join(dirAbs, engineerRawFile),
    qaRawLogAbs: path.join(dirAbs, qaRawFile),
    engineerLogDisplay: path.join(cfg.captureDir, engineerFile),
    qaLogDisplay: path.join(cfg.captureDir, qaFile),
    engineerRawLogDisplay: path.join(cfg.captureDir, engineerRawFile),
    qaRawLogDisplay: path.join(cfg.captureDir, qaRawFile),
    eventLogAbs: path.join(dirAbs, eventFile),
    eventLogDisplay: path.join(cfg.captureDir, eventFile),
  };
}

function sha256Hex(s) {
  try {
    return crypto.createHash("sha256").update(String(s || ""), "utf8").digest("hex");
  } catch {
    return "";
  }
}

function appendWorkflowEvent(evt) {
  try {
    if (!workflowLoopState.active) return;
    if (!workflowLoopState.eventLogAbs) return;
    const payload = {
      ts: new Date().toISOString(),
      phase: workflowLoopState.phase,
      round: workflowLoopState.round,
      ...evt,
    };
    fs.appendFileSync(workflowLoopState.eventLogAbs, JSON.stringify(payload) + "\n", "utf8");
  } catch {
    // ignore
  }
}

function detectWorkflowTerminalKind(cfg, terminalName) {
  if (terminalName === cfg.opencodeTerminalName) return "opencode";
  if (terminalName === cfg.codexTerminalName) return "codex";
  return "unknown";
}

function getWorkflowRawLogAbsForTerminal(terminalName) {
  if (!workflowLoopState.active) return undefined;
  if (terminalName === workflowLoopState.engineerTerminalName) return workflowLoopState.engineerRawLogAbs;
  if (terminalName === workflowLoopState.qaTerminalName) return workflowLoopState.qaRawLogAbs;
  return undefined;
}

function isTerminalReadyFromTail(kind, cleanedTail) {
  const s = String(cleanedTail || "");
  if (!s) return false;
  if (kind === "opencode") {
    // Observed in captured transcript:
    // - "Ask anything..."
    // - "ctrl+p commands"
    return /Ask anything\.{3}/i.test(s) || /ctrl\+p commands/i.test(s);
  }
  if (kind === "codex") {
    // Observed in captured transcript:
    // - "OpenAI Codex (v...)"
    // - "Tip:" and "context left"
    return /OpenAI Codex/i.test(s) || /\bTip:\b/i.test(s) || /context left/i.test(s);
  }
  // Fallback: any non-empty tail after startup.
  return s.trim().length > 0;
}

async function waitForWorkflowTerminalReady(cfg, terminalName, rawLogAbs) {
  const kind = detectWorkflowTerminalKind(cfg, terminalName);
  const timeoutMs = Math.max(1000, Number(cfg.workflowReadyTimeoutMs) || 60000);
  const pollMs = Math.max(100, Number(cfg.workflowReadyPollIntervalMs) || 300);

  const startedAt = Date.now();
  appendWorkflowEvent({ action: "ready_wait_start", terminalName, kind, timeoutMs, pollMs });

  while (workflowLoopState.active) {
    const elapsed = Date.now() - startedAt;
    if (elapsed >= timeoutMs) {
      appendWorkflowEvent({ action: "ready_wait_timeout", terminalName, kind, elapsedMs: elapsed });
      return false;
    }

    const tail = cleanForTail(tailFile(rawLogAbs, 256 * 1024));
    if (isTerminalReadyFromTail(kind, tail)) {
      appendWorkflowEvent({ action: "ready_ok", terminalName, kind, elapsedMs: elapsed });
      return true;
    }

    await sleepMs(pollMs);
  }

  return false;
}

function getTailFingerprint(rawLogAbs) {
  const tail = cleanForTail(tailFile(rawLogAbs, 64 * 1024));
  // Fingerprint the tail to detect meaningful changes without storing full content.
  const compact = tail
    .split(/\n/)
    .map((l) => String(l || "").trim())
    .filter(Boolean)
    .slice(-30)
    .join("\n");
  return sha256Hex(compact);
}

async function workflowSendInstructionWithRetry(cfg, terminalName, text) {
  const rawLogAbs = getWorkflowRawLogAbsForTerminal(terminalName);
  const kind = detectWorkflowTerminalKind(cfg, terminalName);
  const retryCount = Math.max(0, Number(cfg.workflowSendRetryCount) || 0);
  const ackTimeoutMs = Math.max(500, Number(cfg.workflowSendAckTimeoutMs) || 3000);
  const retryDelayMs = Math.max(0, Number(cfg.workflowSendRetryDelayMs) || 1200);
  const primeEnterCount = Math.max(0, Number(cfg.workflowPrimeEnterCount) || 0);
  const effectivePrimeEnterCount = kind === "opencode" ? primeEnterCount : 0;

  const payload = normalizeInstruction(text);
  const payloadHash = sha256Hex(payload);
  const payloadLen = payload.length;

  if (!rawLogAbs) {
    appendWorkflowEvent({ action: "send_failed", terminalName, kind, reason: "missing raw log" });
    return false;
  }

  const readyOk = await waitForWorkflowTerminalReady(cfg, terminalName, rawLogAbs);
  if (!readyOk) {
    logLine(`[workflow] terminal not ready: ${terminalName} (${kind})`);
    stopWorkflowLoop(`terminal not ready: ${terminalName}`);
    return false;
  }

  for (let attempt = 1; attempt <= retryCount + 1; attempt += 1) {
    const sizeBefore = safeGetFileSize(rawLogAbs);
    const fpBefore = getTailFingerprint(rawLogAbs);

    appendWorkflowEvent({
      action: "send_attempt",
      terminalName,
      kind,
      attempt,
      payloadLen,
      payloadSha256: payloadHash,
      rawLogSizeBefore: sizeBefore,
    });

    // Prime input focus by sending a few blank lines first.
    for (let i = 0; i < effectivePrimeEnterCount; i += 1) {
      try {
        const t = findTerminalByName(terminalName);
        t?.sendText("", true);
      } catch {
        // ignore
      }
    }

    const ok = workflowSendInstruction(terminalName, payload + (attempt > 1 ? "（若你已開始處理請忽略此重送）" : ""));
    if (!ok) {
      appendWorkflowEvent({ action: "send_error", terminalName, kind, attempt });
      return false;
    }

    // Weak ACK: wait for transcript to change (size or tail fingerprint).
    const ackStartedAt = Date.now();
    while (workflowLoopState.active) {
      const ackElapsed = Date.now() - ackStartedAt;
      if (ackElapsed >= ackTimeoutMs) break;

      const sizeNow = safeGetFileSize(rawLogAbs);
      const fpNow = getTailFingerprint(rawLogAbs);
      if (sizeNow > sizeBefore || fpNow !== fpBefore) {
        appendWorkflowEvent({
          action: "send_ack",
          terminalName,
          kind,
          attempt,
          ackElapsedMs: ackElapsed,
          rawLogSizeAfter: sizeNow,
        });
        return true;
      }

      await sleepMs(200);
    }

    appendWorkflowEvent({ action: "send_no_ack", terminalName, kind, attempt, ackTimeoutMs });
    if (attempt <= retryCount && retryDelayMs > 0) {
      await sleepMs(retryDelayMs);
    }
  }

  logLine(`[workflow] send appears stuck (no ack): ${terminalName}`);
  stopWorkflowLoop(`send appears stuck (no ack): ${terminalName}`);
  return false;
}

function cleanForTail(text) {
  // Remove ANSI + non-printable control chars; normalize CR to LF.
  const noAnsi = stripAnsi(text);
  return String(noAnsi)
    .replace(/\r/g, "\n")
    .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, "")
    .replace(/\n{3,}/g, "\n\n");
}

function updateTailLogFromRaw(rawPath, tailPath, tailLines) {
  try {
    const lines = Math.max(1, Number(tailLines) || 200);
    const rawTail = tailFile(rawPath, 512 * 1024);
    const cleaned = cleanForTail(rawTail);
    const out = cleaned
      .split(/\n/)
      .slice(-lines)
      .join("\n")
      .trimEnd();
    fs.writeFileSync(tailPath, out + "\n", "utf8");
  } catch (err) {
    // best-effort
    logLine(`[workflow] failed to update tail log: ${String(err || "")}`);
  }
}

function getStartCommandForTerminal(cfg, terminalName) {
  if (terminalName === cfg.codexTerminalName) return cfg.codexCommand;
  if (terminalName === cfg.opencodeTerminalName) return cfg.opencodeCommand;
  return undefined;
}

function getStateKeyForTerminal(cfg, terminalName) {
  if (terminalName === cfg.codexTerminalName) return STATE_KEYS.startedCodex;
  if (terminalName === cfg.opencodeTerminalName) return STATE_KEYS.startedOpenCode;
  return undefined;
}

function appendWorkflowCapture(cfg, terminal, data) {
  if (!workflowLoopState.active) return;
  if (workflowLoopState.captureMode !== "terminalData") return;

  try {
    const terminalName = terminal?.name;
    const buf = Buffer.from(String(data), "utf8");

    if (terminalName === workflowLoopState.engineerTerminalName && workflowLoopState.engineerRawLogAbs) {
      fs.appendFileSync(workflowLoopState.engineerRawLogAbs, buf);
    }
    if (terminalName === workflowLoopState.qaTerminalName && workflowLoopState.qaRawLogAbs) {
      fs.appendFileSync(workflowLoopState.qaRawLogAbs, buf);
    }
  } catch (err) {
    console.error(err);
  }
}

function readNewLogChunk(filePath, startOffset) {
  try {
    const st = fs.statSync(filePath);
    const size = Number(st.size) || 0;
    const offset = Math.max(0, Number(startOffset) || 0);
    if (size <= offset) return { nextOffset: offset, text: "" };

    const fd = fs.openSync(filePath, "r");
    try {
      const toRead = size - offset;
      const buf = Buffer.allocUnsafe(toRead);
      const bytesRead = fs.readSync(fd, buf, 0, toRead, offset);
      const text = buf.subarray(0, bytesRead).toString("utf8");
      return { nextOffset: offset + bytesRead, text };
    } finally {
      fs.closeSync(fd);
    }
  } catch (err) {
    // File may not exist yet.
    if (err && err.code === "ENOENT") {
      return { nextOffset: Math.max(0, Number(startOffset) || 0), text: "" };
    }
    console.error(err);
    return { nextOffset: Math.max(0, Number(startOffset) || 0), text: "" };
  }
}

function tailFile(filePath, maxBytes = 65536) {
  try {
    const st = fs.statSync(filePath);
    const size = Number(st.size) || 0;
    const bytes = Math.max(0, Math.min(size, Number(maxBytes) || 0));
    const start = Math.max(0, size - bytes);
    const fd = fs.openSync(filePath, "r");
    try {
      const buf = Buffer.allocUnsafe(bytes);
      const bytesRead = fs.readSync(fd, buf, 0, bytes, start);
      return buf.subarray(0, bytesRead).toString("utf8");
    } finally {
      fs.closeSync(fd);
    }
  } catch {
    return "";
  }
}

function isValidIdxName(s) {
  return /^Idx-\d{3}$/i.test(String(s || "").trim());
}

function normalizeIdxName(s) {
  const m = /^Idx-(\d{3})$/i.exec(String(s || "").trim());
  if (!m) return undefined;
  return `Idx-${m[1]}`;
}

function resolveIdxLogAbs(idxName) {
  const root = getWorkspaceRootFsPath();
  if (!root) return undefined;
  const safe = normalizeIdxName(idxName);
  if (!safe) return undefined;
  return path.join(root, ".agent", "logs", `${safe}_log.md`);
}

function resolveTerminalCaptureDirAbs(cfg) {
  const root = getWorkspaceRootFsPath();
  if (!root) return undefined;
  return path.join(root, cfg.captureDir);
}

function findLatestCaptureFileAbs(dirAbs, nameRe) {
  try {
    const entries = fs
      .readdirSync(dirAbs, { withFileTypes: true })
      .filter((e) => e.isFile() && nameRe.test(e.name))
      .map((e) => e.name)
      .sort();
    if (entries.length === 0) return undefined;
    return path.join(dirAbs, entries[entries.length - 1]);
  } catch {
    return undefined;
  }
}

function detectQaPassEvidenceFromCaptureDir(cfg) {
  const dirAbs = resolveTerminalCaptureDirAbs(cfg);
  if (!dirAbs) return { ok: false, reason: "workspace root not found" };
  const qaRawAbs = findLatestCaptureFileAbs(dirAbs, /^qa_\d{14}_raw\.log$/);
  if (!qaRawAbs) return { ok: false, reason: "no qa raw log found" };

  const tail = tailFile(qaRawAbs, 200000);
  const cleaned = stripAnsi(tail).replace(/\r/g, "\n");
  const hasDone = hasMarkerLine(cleaned, WORKFLOW_MARKER_NAMES.qaDone);
  const qaResult = getQaResult(cleaned);

  if (!hasDone || qaResult !== "PASS") {
    return {
      ok: false,
      reason: `qa evidence not PASS (hasDone=${hasDone}, qaResult=${qaResult || "<none>"})`,
    };
  }

  return { ok: true, reason: "qa evidence PASS" };
}

function clearDirectoryContents(dirAbs) {
  let removed = 0;
  const entries = fs.readdirSync(dirAbs, { withFileTypes: true });
  for (const e of entries) {
    const target = path.join(dirAbs, e.name);
    fs.rmSync(target, { recursive: true, force: true });
    removed += 1;
  }
  return removed;
}

async function offerClearCaptureOnQaPass(cfg) {
  try {
    const idx = workflowLoopState?.idxName;
    if (!idx) {
      logLine("[workflow] no idx associated with this run; skipping auto clear prompt");
      return;
    }

    const logAbs = resolveIdxLogAbs(idx);
    if (!logAbs || !fs.existsSync(logAbs)) {
      logLine(`[workflow] QA PASS detected but log not found: .agent/logs/${idx}_log.md; skipping auto prompt`);
      await vscode.window.showInformationMessage(
        `QA PASS 偵測到，但 log 檔 .agent/logs/${idx}_log.md 尚未建立；不會自動提示是否清除 capture。你可以稍後手動執行 'IvyHouse: Clear .service/terminal_capture (after QA PASS + log)'。`,
      );
      return;
    }

    appendWorkflowEvent({ action: "cleanup_prompt_shown", idx });

    const qaEvidence = detectQaPassEvidenceFromCaptureDir(cfg);
    if (!qaEvidence.ok) {
      const choice = await vscode.window.showWarningMessage(
        `找不到 QA PASS 證據（${qaEvidence.reason}）。若你已人工確認 PASS，可選擇繼續清空；或先開啟 log 檔。`,
        { modal: true },
        "取消",
        "開啟 log 檔",
        "我已確認 PASS，仍要清空",
      );
      if (!choice) return;
      if (choice === "開啟 log 檔") {
        const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(logAbs));
        await vscode.window.showTextDocument(doc, { preview: false });
        return;
      }
      if (choice !== "我已確認 PASS，仍要清空") return;
      // user forced clear
    } else {
      const choice = await vscode.window.showWarningMessage(
        `已偵測到 QA PASS，且 log 檔 .agent/logs/${idx}_log.md 已存在。是否清空 ${cfg.captureDir}？`,
        { modal: true },
        "清空",
        "略過",
      );
      if (choice !== "清空") {
        appendWorkflowEvent({ action: "cleanup_skipped_user", idx });
        return;
      }
    }

    const captureDirAbs = resolveTerminalCaptureDirAbs(cfg);
    if (!captureDirAbs) {
      vscode.window.showErrorMessage("Workspace folder not found; cannot resolve capture dir.");
      return;
    }

    fs.mkdirSync(captureDirAbs, { recursive: true });
    const entries = fs.readdirSync(captureDirAbs, { withFileTypes: true });
    const count = entries.length;
    const confirm = await vscode.window.showWarningMessage(
      `確認要清空 ${cfg.captureDir} 內所有檔案/子資料夾嗎？（log 已確認存在）\n將刪除 ${count} 項。`,
      { modal: true },
      "清空",
      "取消",
    );
    if (confirm !== "清空") {
      appendWorkflowEvent({ action: "cleanup_cancelled", idx });
      return;
    }

    const removed = clearDirectoryContents(captureDirAbs);
    appendWorkflowEvent({ action: "cleanup_done", idx, removed });
    logLine(
      `[cleanup] cleared captureDir=${cfg.captureDir} removed=${removed} idx=${idx} qaEvidence=${qaEvidence.ok}`,
    );
    getOutputChannel().show(true);
    vscode.window.showInformationMessage(`已清空 ${cfg.captureDir}（移除 ${removed} 項）。`);
  } catch (err) {
    console.error(err);
  }
}

function stopWorkflowLoop(reason) {
  if (!workflowLoopState.active) {
    vscode.window.showInformationMessage("Workflow loop is not running.");
    return;
  }

  appendWorkflowEvent({ action: "workflow_stop", reason: reason || "stopped" });

  workflowLoopState.active = false;
  workflowLoopState.phase = WORKFLOW_PHASE.idle;
  workflowLoopState.captureMode = "none";
  if (workflowLoopState.timer) {
    clearInterval(workflowLoopState.timer);
  }
  workflowLoopState.timer = undefined;
  logLine(`[workflow] stopped: ${reason || "stopped"}`);
  vscode.window.showInformationMessage(`Workflow loop stopped${reason ? `: ${reason}` : ""}.`);
}

function formatWorkflowStatus() {
  if (!workflowLoopState.active) {
    return "Workflow loop: not running";
  }
  const elapsedMs = Date.now() - (workflowLoopState.startedAtMs || Date.now());
  return [
    `Workflow loop: RUNNING`,
    `phase: ${workflowLoopState.phase}`,
    `round: ${workflowLoopState.round}/${workflowLoopState.maxRounds}`,
    `elapsed: ${Math.round(elapsedMs / 1000)}s (timeout: ${Math.round(workflowLoopState.timeoutMs / 1000)}s)`,
    `captureMode: ${workflowLoopState.captureMode}`,
    `engineer terminal: ${workflowLoopState.engineerTerminalName || "<n/a>"}`,
    `qa terminal: ${workflowLoopState.qaTerminalName || "<n/a>"}`,
    `idx: ${workflowLoopState.idxName || "<n/a>"}`,
    `engineer log: ${workflowLoopState.engineerLogDisplay || "<n/a>"}`,
    `qa log: ${workflowLoopState.qaLogDisplay || "<n/a>"}`,
    `events log: ${workflowLoopState.eventLogDisplay || "<n/a>"}`,
  ].join("\n");
}

function workflowSendInstruction(terminalName, text) {
  let t;
  if (
    workflowLoopState.active &&
    terminalName === workflowLoopState.engineerTerminalName &&
    workflowLoopState.engineerTerminal
  ) {
    t = workflowLoopState.engineerTerminal;
  } else if (
    workflowLoopState.active &&
    terminalName === workflowLoopState.qaTerminalName &&
    workflowLoopState.qaTerminal
  ) {
    t = workflowLoopState.qaTerminal;
  } else {
    t = findTerminalByName(terminalName);
  }

  if (!t) {
    logLine(`[workflow] terminal not found: ${terminalName}`);
    stopWorkflowLoop(`terminal not found: ${terminalName}`);
    return false;
  }

  const payload = normalizeInstruction(text);

  try {
    t.show(true);
  } catch (err) {
    logLine(`[workflow] show() failed: ${String(err || "")}`);
  }

  try {
    // Send the instruction and then send an additional blank line.
    // This helps CLIs that require a second Enter to submit after paste.
    t.sendText(payload, true);
    t.sendText("", true);
    return true;
  } catch (err) {
    const msg = String(err || "");
    logLine(`[workflow] sendText failed (terminal may be disposed): ${msg}`);
    stopWorkflowLoop(`sendText failed: ${terminalName}`);
    return false;
  }
}

function buildEngineerPrompt(taskDescription) {
  // IMPORTANT: do NOT include the literal bracketed marker in the prompt.
  // Many CLIs echo the prompt; if the marker appears in the prompt, we'd false-trigger.
  return (
    "你是 Engineer（負責實作）。請遵守 repo 規範：不要在此終端執行 git 指令（git/pytest/ruff 請用 Project terminal）。" +
    ` 任務：${taskDescription}。` +
    " 請勿自行做 QA；只要完成實作即可。" +
    " 完成時請在『最後一行』單獨輸出：左中括號 + ENGINEER_DONE + 右中括號。" +
    "（提醒：除了最後一行以外，請不要提到/輸出 ENGINEER_DONE 或任何 marker 文字，以免誤判。）"
  );
}

function sanitizeSummaryForPrompt(summary) {
  // Summaries are injected into prompts that may be echoed into transcripts.
  // Remove any marker-like standalone lines to avoid false-positive detection.
  const lines = String(summary || "").replace(/\r/g, "\n").split("\n");
  const kept = lines.filter((line) => {
    const t = String(line || "").trim();
    if (!t) return true;
    if (t === WORKFLOW_MARKERS.engineerDone) return false;
    if (t === WORKFLOW_MARKERS.fixDone) return false;
    if (t === WORKFLOW_MARKERS.qaDone) return false;
    if (/^QA_RESULT\s*=\s*(PASS|FAIL)\s*$/i.test(t)) return false;
    return true;
  });
  return kept.join("\n").trimEnd();
}

function buildQaPrompt(round, taskDescription, engineerSummary) {
  return (
    `你是 QA（第 ${round} 輪）。請審查 Engineer 的變更是否符合 plan/whitelist 與 repo 規範。\n` +
    "完成時請輸出兩段標記（請各自獨立成行）：\n" +
    "1) 左中括號 + QA_DONE + 右中括號\n" +
    "2) QA_RESULT + 等號 + PASS 或 FAIL（等號前後不可有空白）\n\n" +
    `任務背景：${taskDescription}\n\n` +
    "Engineer 輸出摘要（供你審查判斷）：\n" +
    (engineerSummary ? engineerSummary : "(no engineer output captured)")
  );
}

function buildFixPrompt(round, qaSummary) {
  return (
    `QA 第 ${round} 輪結果為 FAIL，請依以下 QA 摘要修正：\n\n` +
    qaSummary +
    "\n\n修正完成時請在『最後一行』單獨輸出：左中括號 + FIX_DONE + 右中括號。" +
    "（提醒：除了最後一行以外，請不要提到/輸出 FIX_DONE 或任何 marker 文字，以免誤判。）"
  );
}

async function workflowTick(cfg) {
  if (!workflowLoopState.active) return;
  if (workflowLoopState.tickBusy) return;
  workflowLoopState.tickBusy = true;

  try {

  const now = Date.now();
  const elapsed = now - workflowLoopState.startedAtMs;
  if (workflowLoopState.timeoutMs > 0 && elapsed >= workflowLoopState.timeoutMs) {
    stopWorkflowLoop("timeout");
    return;
  }

  if (
    workflowLoopState.phase === WORKFLOW_PHASE.waitEngineerDone ||
    workflowLoopState.phase === WORKFLOW_PHASE.waitFixDone
  ) {
    // Avoid reading echoed prompts (which may contain marker strings).
    if (workflowLoopState.engineerPauseUntilMs && now < workflowLoopState.engineerPauseUntilMs) {
      return;
    }
    if (!workflowLoopState.engineerRawLogAbs || !workflowLoopState.engineerLogAbs) return;

    // Keep a compact tail view for humans (and for summaries).
    updateTailLogFromRaw(
      workflowLoopState.engineerRawLogAbs,
      workflowLoopState.engineerLogAbs,
      cfg.workflowTailLines,
    );

    const { nextOffset, text } = readNewLogChunk(
      workflowLoopState.engineerRawLogAbs,
      workflowLoopState.engineerOffset,
    );
    workflowLoopState.engineerOffset = nextOffset;
    if (text) {
      const cleaned = stripAnsi(text).replace(/\r/g, "\n");
      workflowLoopState.engineerMarkerBuf = (workflowLoopState.engineerMarkerBuf + cleaned).slice(-20000);

      if (
        workflowLoopState.phase === WORKFLOW_PHASE.waitEngineerDone &&
        hasMarkerLine(workflowLoopState.engineerMarkerBuf, WORKFLOW_MARKER_NAMES.engineerDone)
      ) {
        logLine("[workflow] detected ENGINEER_DONE");
        const engineerSummary = fs.existsSync(workflowLoopState.engineerLogAbs)
          ? fs.readFileSync(workflowLoopState.engineerLogAbs, "utf8")
          : "";

        workflowLoopState.phase = WORKFLOW_PHASE.waitQaDone;
        workflowLoopState.qaPauseUntilMs = Date.now() + 600;
        await workflowSendInstructionWithRetry(
          cfg,
          workflowLoopState.qaTerminalName,
          buildQaPrompt(
            workflowLoopState.round,
            workflowLoopState.taskDescription,
            sanitizeSummaryForPrompt(engineerSummary),
          ),
        );
        // Fast-forward QA offset after prompt echo is likely written.
        if (workflowLoopState.qaRawLogAbs) {
          workflowLoopState.qaOffset = safeGetFileSize(workflowLoopState.qaRawLogAbs);
          workflowLoopState.qaMarkerBuf = "";
        }
        return;
      }

      if (
        workflowLoopState.phase === WORKFLOW_PHASE.waitFixDone &&
        hasMarkerLine(workflowLoopState.engineerMarkerBuf, WORKFLOW_MARKER_NAMES.fixDone)
      ) {
        logLine("[workflow] detected FIX_DONE");
        workflowLoopState.round += 1;
        if (workflowLoopState.round > workflowLoopState.maxRounds) {
          stopWorkflowLoop("max rounds exceeded");
          return;
        }

        const engineerSummary = fs.existsSync(workflowLoopState.engineerLogAbs)
          ? fs.readFileSync(workflowLoopState.engineerLogAbs, "utf8")
          : "";

        workflowLoopState.phase = WORKFLOW_PHASE.waitQaDone;
        workflowLoopState.qaPauseUntilMs = Date.now() + 600;
        await workflowSendInstructionWithRetry(
          cfg,
          workflowLoopState.qaTerminalName,
          buildQaPrompt(
            workflowLoopState.round,
            workflowLoopState.taskDescription,
            sanitizeSummaryForPrompt(engineerSummary),
          ),
        );

        if (workflowLoopState.qaRawLogAbs) {
          workflowLoopState.qaOffset = safeGetFileSize(workflowLoopState.qaRawLogAbs);
          workflowLoopState.qaMarkerBuf = "";
        }
      }
    }
    return;
  }

  if (workflowLoopState.phase === WORKFLOW_PHASE.waitQaDone) {
    if (workflowLoopState.qaPauseUntilMs && now < workflowLoopState.qaPauseUntilMs) {
      return;
    }
    if (!workflowLoopState.qaRawLogAbs || !workflowLoopState.qaLogAbs) return;

    // Keep a compact tail view for humans.
    updateTailLogFromRaw(workflowLoopState.qaRawLogAbs, workflowLoopState.qaLogAbs, cfg.workflowTailLines);

    const { nextOffset, text } = readNewLogChunk(
      workflowLoopState.qaRawLogAbs,
      workflowLoopState.qaOffset,
    );
    workflowLoopState.qaOffset = nextOffset;
    if (!text) return;

    const cleaned = stripAnsi(text).replace(/\r/g, "\n");
    workflowLoopState.qaMarkerBuf = (workflowLoopState.qaMarkerBuf + cleaned).slice(-40000);

    const hasDone = hasMarkerLine(workflowLoopState.qaMarkerBuf, WORKFLOW_MARKER_NAMES.qaDone);
    const qaResult = getQaResult(workflowLoopState.qaMarkerBuf);
    if (!hasDone || !qaResult) return;

    if (qaResult === "PASS") {
      logLine("[workflow] detected QA PASS");
      appendWorkflowEvent({ action: "qa_pass_detected" });
      // If configured, offer to clear terminal capture when PASS detected and log exists.
      if (cfg.workflowPromptClearCaptureOnPass) {
        try {
          await offerClearCaptureOnQaPass(cfg);
        } catch (err) {
          console.error(err);
        }
      }
      workflowLoopState.phase = WORKFLOW_PHASE.done;
      stopWorkflowLoop("PASS");
      return;
    }

    logLine("[workflow] detected QA FAIL");

    if (workflowLoopState.round >= workflowLoopState.maxRounds) {
      stopWorkflowLoop("FAIL (max rounds reached)");
      return;
    }

    const qaSummary = fs.existsSync(workflowLoopState.qaLogAbs)
      ? fs.readFileSync(workflowLoopState.qaLogAbs, "utf8")
      : "";

    workflowLoopState.phase = WORKFLOW_PHASE.waitFixDone;
    workflowLoopState.engineerPauseUntilMs = Date.now() + 600;
    await workflowSendInstructionWithRetry(
      cfg,
      workflowLoopState.engineerTerminalName,
      buildFixPrompt(workflowLoopState.round, qaSummary || "(no QA output captured)"),
    );

    if (workflowLoopState.engineerRawLogAbs) {
      workflowLoopState.engineerOffset = safeGetFileSize(workflowLoopState.engineerRawLogAbs);
      workflowLoopState.engineerMarkerBuf = "";
    }
  }
  } finally {
    workflowLoopState.tickBusy = false;
  }
}

async function startWorkflowLoop(context) {
  try {
  if (workflowLoopState.active) {
    vscode.window.showWarningMessage("Workflow loop is already running.");
    return;
  }

  const cfg = getConfig();

  const terminalOptions = [
    {
      label: cfg.opencodeTerminalName,
      description: "OpenCode CLI",
    },
    {
      label: cfg.codexTerminalName,
      description: "Codex CLI",
    },
  ];

  const engineerPick = await vscode.window.showQuickPick(terminalOptions, {
    title: "Select Engineer terminal",
    placeHolder: "Engineer 負責實作（預設 OpenCode CLI）",
  });
  if (!engineerPick) return;

  const qaPick = await vscode.window.showQuickPick(
    terminalOptions.filter((o) => o.label !== engineerPick.label),
    {
      title: "Select QA terminal",
      placeHolder: "QA 負責審查（預設 Codex CLI）",
    },
  );
  if (!qaPick) return;

  const taskDescription = await vscode.window.showInputBox({
    title: "Workflow Loop task description",
    prompt: "This text will be sent to Engineer/QA via terminal.sendText().",
    placeHolder: "例如：請完成 Idx-023 workflow loop 並更新相關文件",
  });
  if (typeof taskDescription !== "string" || taskDescription.trim() === "") return;

  // Optional: link this run to an Idx (e.g., Idx-024) so that when QA PASSES we can
  // automatically prompt whether to clear `.service/terminal_capture` (only if the
  // corresponding .agent/logs/<Idx-XXX>_log.md exists).
  const idxInput = await vscode.window.showInputBox({
    title: "Optional: Associated Idx (e.g., Idx-024)",
    prompt:
      "輸入 Idx-XXX 可讓此工作在 QA PASS 且 log 檔存在時自動提示是否清空 `.service/terminal_capture`（可留空）。",
    placeHolder: "Idx-024",
  });
  let normalizedIdx;
  if (typeof idxInput === "string" && idxInput.trim() !== "") {
    normalizedIdx = normalizeIdxName(idxInput);
    if (!normalizedIdx) {
      vscode.window.showWarningMessage("Idx 格式不正確，將忽略此欄位（請輸入 Idx-XXX，例如 Idx-024）。");
      normalizedIdx = undefined;
    }
  }

  const paths = resolveWorkflowLogPaths(cfg);
  if (!paths) {
    vscode.window.showErrorMessage("Workspace folder not found; cannot create workflow logs.");
    return;
  }

  fs.mkdirSync(paths.dirAbs, { recursive: true });
  fs.writeFileSync(paths.engineerLogAbs, "", "utf8");
  fs.writeFileSync(paths.qaLogAbs, "", "utf8");
  fs.writeFileSync(paths.engineerRawLogAbs, "", "utf8");
  fs.writeFileSync(paths.qaRawLogAbs, "", "utf8");
  fs.writeFileSync(paths.eventLogAbs, "", "utf8");

  const scriptOk = isScriptAvailable();
  let captureMode = "none";
  if (scriptOk) {
    captureMode = "script";
  } else if (terminalDataWriteEventAvailable) {
    captureMode = "terminalData";
  }

  if (captureMode === "none") {
    vscode.window.showErrorMessage(
      "Workflow loop 無法啟動：找不到 `script`（落檔用），且 VS Code Proposed API terminalDataWriteEvent 未啟用。\n\n" +
        "請先安裝 util-linux（提供 script），或用 `--enable-proposed-api ivyhouse-local.ivyhouse-terminal-orchestrator` 啟動 VS Code。",
    );
    return;
  }

  workflowLoopState = {
    active: true,
    phase: WORKFLOW_PHASE.waitEngineerDone,
    captureMode,
    startedAtMs: Date.now(),
    round: 1,
    taskDescription: taskDescription.trim(),
    idxName: normalizedIdx,
    engineerTerminalName: engineerPick.label,
    qaTerminalName: qaPick.label,
    engineerTerminal: undefined,
    qaTerminal: undefined,
    engineerRawLogAbs: paths.engineerRawLogAbs,
    qaRawLogAbs: paths.qaRawLogAbs,
    engineerLogAbs: paths.engineerLogAbs,
    engineerLogDisplay: paths.engineerLogDisplay,
    qaLogAbs: paths.qaLogAbs,
    qaLogDisplay: paths.qaLogDisplay,
    eventLogAbs: paths.eventLogAbs,
    eventLogDisplay: paths.eventLogDisplay,
    engineerOffset: 0,
    qaOffset: 0,
    engineerMarkerBuf: "",
    qaMarkerBuf: "",
    pollIntervalMs: Math.max(200, Number(cfg.workflowPollIntervalMs) || 5000),
    maxRounds: Math.max(1, Number(cfg.workflowMaxRounds) || 10),
    timeoutMs: Math.max(1000, Number(cfg.workflowTimeoutMs) || 1800000),
    timer: undefined,
    tickBusy: false,
  };

  appendWorkflowEvent({
    action: "workflow_start",
    captureMode,
    engineerTerminalName: workflowLoopState.engineerTerminalName,
    qaTerminalName: workflowLoopState.qaTerminalName,
    engineerRawLog: paths.engineerRawLogDisplay,
    qaRawLog: paths.qaRawLogDisplay,
    idxName: workflowLoopState.idxName,
  });

  // Start / restart terminals to ensure clean session.
  for (const terminalName of [engineerPick.label, qaPick.label]) {
    const stateKey = getStateKeyForTerminal(cfg, terminalName);
    if (stateKey) {
      await context.workspaceState.update(stateKey, false);
    }
    disposeTerminalByName(terminalName);
    // Avoid a race where we create a new terminal with the same name while VS Code
    // is still finalizing disposal of the previous one.
    await waitForTerminalToClose(terminalName, 3000);
  }

  const engineerStart = getStartCommandForTerminal(cfg, engineerPick.label);
  const qaStart = getStartCommandForTerminal(cfg, qaPick.label);
  if (!engineerStart || !qaStart) {
    stopWorkflowLoop("invalid terminal selection");
    vscode.window.showErrorMessage("Unsupported terminal selection; expected Codex/OpenCode terminals.");
    return;
  }

  const engineerTerm = getOrCreateTerminal(engineerPick.label);
  const qaTerm = getOrCreateTerminal(qaPick.label);
  workflowLoopState.engineerTerminal = engineerTerm;
  workflowLoopState.qaTerminal = qaTerm;

  if (captureMode === "script") {
    const engineerCmd =
      `script -q -f -c ${bashSingleQuote(engineerStart)} ` +
      bashSingleQuote(workflowLoopState.engineerRawLogAbs);
    const qaCmd =
      `script -q -f -c ${bashSingleQuote(qaStart)} ` + bashSingleQuote(workflowLoopState.qaRawLogAbs);

    const engineerKey = getStateKeyForTerminal(cfg, engineerPick.label);
    const qaKey = getStateKeyForTerminal(cfg, qaPick.label);

    const ok1 = await startTerminalIfNeeded(context, engineerTerm, engineerKey, engineerCmd, true);
    const ok2 = await startTerminalIfNeeded(context, qaTerm, qaKey, qaCmd, true);
    if (!ok1 || !ok2) {
      stopWorkflowLoop("failed to start terminals (script mode)");
      return;
    }
  } else {
    // terminalData mode: start normally; output will be captured by onDidWriteTerminalData.
    const engineerKey = getStateKeyForTerminal(cfg, engineerPick.label);
    const qaKey = getStateKeyForTerminal(cfg, qaPick.label);
    const ok1 = await startTerminalIfNeeded(context, engineerTerm, engineerKey, engineerStart, true);
    const ok2 = await startTerminalIfNeeded(context, qaTerm, qaKey, qaStart, true);
    if (!ok1 || !ok2) {
      stopWorkflowLoop("failed to start terminals (terminalData mode)");
      return;
    }
  }

  vscode.window.showInformationMessage(
    `Workflow loop started. Logs: ${workflowLoopState.engineerLogDisplay}, ${workflowLoopState.qaLogDisplay} (events: ${workflowLoopState.eventLogDisplay})`,
  );

  // Avoid false-positive marker detection from transcript echo of our own prompt.
  workflowLoopState.engineerPauseUntilMs = Date.now() + 600;
  const firstSendOk = await workflowSendInstructionWithRetry(
    cfg,
    workflowLoopState.engineerTerminalName,
    buildEngineerPrompt(workflowLoopState.taskDescription),
  );

  if (!firstSendOk || !workflowLoopState.active) {
    return;
  }

  if (workflowLoopState.engineerRawLogAbs) {
    workflowLoopState.engineerOffset = safeGetFileSize(workflowLoopState.engineerRawLogAbs);
    workflowLoopState.engineerMarkerBuf = "";
  }

  // Start poller.
  workflowLoopState.timer = setInterval(() => {
    workflowTick(getConfig()).catch((err) => {
      console.error(err);
    });
  }, workflowLoopState.pollIntervalMs);
  } catch (err) {
    const msg = String(err || "");
    logLine(`[workflow] start failed: ${msg}`);
    // Ensure we don't leave a half-running state.
    try {
      stopWorkflowLoop("start failed");
    } catch {
      // ignore
    }
    vscode.window.showErrorMessage(`Workflow loop start failed: ${msg}`);
  }
}

function getOutputChannel() {
  if (!outputChannel) {
    outputChannel = vscode.window.createOutputChannel("IvyHouse Terminal Orchestrator");
  }
  return outputChannel;
}

function logLine(line) {
  try {
    const ch = getOutputChannel();
    ch.appendLine(String(line));
  } catch {
    // ignore
  }
}

function formatDiagnostics(cfg) {
  const root = getWorkspaceRootFsPath();
  const paths = resolveCapturePaths(cfg);
  const codexTerminal = findTerminalByName(cfg.codexTerminalName);
  return [
    `VS Code: ${vscode.version}`,
    `Proposed API onDidWriteTerminalData available: ${terminalDataWriteEventAvailable}`,
    `workspace root: ${root || "<none>"}`,
    `captureDir (setting): ${cfg.captureDir}`,
    `capture paths resolved: ${paths ? "yes" : "no"}`,
    paths ? `capture dir: ${paths.dir}` : "capture dir: <n/a>",
    paths ? `capture file: ${paths.lastFile}` : "capture file: <n/a>",
    `Codex terminal exists: ${Boolean(codexTerminal)}`,
    codexTerminal ? `Codex terminal name: ${codexTerminal.name}` : "Codex terminal name: <n/a>",
  ].join("\n");
}

function stopCapture(reason) {
  if (!captureState.active) return;
  captureState.active = false;
  if (captureState.stopTimer) {
    clearInterval(captureState.stopTimer);
  }
  captureState.stopTimer = undefined;
  vscode.window.showInformationMessage(
    `Codex capture stopped${reason ? `: ${reason}` : ""}. Output saved to ${captureState.lastFileDisplay}`,
  );
}

function stopCaptureWithPromise(reason) {
  stopCapture(reason);
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
    lastFileDisplay: paths.lastFileDisplay,
    bytesWritten: 0,
    startedAtMs: Date.now(),
    lastDataAtMs: Date.now(),
    stopTimer: undefined,
  };

  const maxMs = Math.max(0, Number(cfg.captureMaxSeconds) || 0) * 1000;
  const silenceMs = Math.max(0, Number(cfg.captureSilenceMs) || 0);

  captureState.stopTimer = setInterval(() => {
    if (!captureState.active) return;
    const now = Date.now();
    if (maxMs > 0 && now - captureState.startedAtMs >= maxMs) {
      stopCaptureWithPromise("timeout");
      return;
    }
    if (silenceMs > 0 && now - captureState.lastDataAtMs >= silenceMs) {
      stopCaptureWithPromise("silent");
    }
  }, 200);

  // Return promise that resolves when capture completes
  const capturePromise = new Promise((resolve) => {
    capturePromiseResolve = resolve;
  });

  return { captureFile: paths.lastFileDisplay, capturePromise };
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
    stopCaptureWithPromise("size limit");
    return;
  }

  fs.appendFileSync(captureState.lastFile, buf);
  captureState.bytesWritten += buf.length;
  captureState.lastDataAtMs = Date.now();
}

async function startTerminalIfNeeded(context, terminal, stateKey, command, force = false) {
  const hasKey = typeof stateKey === "string" && stateKey.trim() !== "";
  const alreadyStarted = hasKey ? context.workspaceState.get(stateKey, false) : false;
  try {
    terminal.show(true);
  } catch (err) {
    logLine(`[terminal] show() failed: ${String(err || "")}`);
  }

  if (alreadyStarted && !force) {
    return true;
  }

  // Start via sendText (requirement: only sendText into these terminals)
  try {
    terminal.sendText(command, true);
  } catch (err) {
    const msg = String(err || "");
    logLine(`[terminal] sendText() failed (terminal may be disposed): ${msg}`);
    return false;
  }
  if (hasKey) {
    await context.workspaceState.update(stateKey, true);
  }

  return true;
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

  // Important: workspaceState persists across Reload Window, but terminals do not.
  // If we create a new terminal (no existing terminal by name), we MUST re-send
  // the start command even if workspaceState says it was "started" previously.
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
  const cfg = getConfig();

  try {
    if (vscode.window.onDidWriteTerminalData) {
      terminalDataWriteEventAvailable = true;
      context.subscriptions.push(
        vscode.window.onDidWriteTerminalData((e) => {
          try {
            const c = getConfig();
            appendCapture(c, e.terminal, e.data);
            appendWorkflowCapture(c, e.terminal, e.data);
          } catch (err) {
            console.error(err);
          }
        }),
      );
    }
  } catch (err) {
    terminalDataWriteEventAvailable = false;
    console.error(err);
  }

  logLine("[activate] IvyHouse Terminal Orchestrator activated");
  logLine(`[activate] VS Code version: ${vscode.version}`);
  logLine(
    `[activate] Proposed API onDidWriteTerminalData available: ${terminalDataWriteEventAvailable}`,
  );

  // Stable fallback: shell integration stream.
  // This only works if we attach right when `codex` is started from the shell.
  try {
    if (vscode.window.onDidStartTerminalShellExecution) {
      context.subscriptions.push(
        vscode.window.onDidStartTerminalShellExecution((e) => {
          try {
            const c = getConfig();
            const codexTerminalName = c.codexTerminalName;
            if (!e || !e.terminal || e.terminal.name !== codexTerminalName) return;

            const cmdValue = e.execution?.commandLine?.value;
            const startWord = String(c.codexCommand || "codex")
              .trim()
              .split(/\s+/)[0];

            if (!cmdValue || !String(cmdValue).includes(startWord)) {
              return;
            }

            if (typeof e.execution?.read !== "function") {
              logLine(
                "[shell-read] execution.read() not available; cannot fallback-capture via shell integration",
              );
              return;
            }

            const execId = shellReadState.attachedExecutionId + 1;
            shellReadState.attachedExecutionId = execId;
            shellReadState.attachedTerminalName = e.terminal.name;
            logLine(`[shell-read] Attached to codex execution stream (id=${execId})`);

            // Fire-and-forget reader; only writes when captureState.active is true.
            (async () => {
              try {
                const stream = e.execution.read();
                for await (const data of stream) {
                  // If a newer execution attached, stop processing old stream.
                  if (shellReadState.attachedExecutionId !== execId) {
                    break;
                  }
                  const cfgNow = getConfig();
                  appendCapture(cfgNow, e.terminal, data);
                }
              } catch (err) {
                console.error(err);
                logLine(`[shell-read] Error reading execution stream: ${String(err)}`);
              } finally {
                if (shellReadState.attachedExecutionId === execId) {
                  logLine(`[shell-read] Codex execution stream ended (id=${execId})`);
                }
              }
            })();
          } catch (err) {
            console.error(err);
          }
        }),
      );

      logLine("[activate] Shell integration execution stream listener registered");
    }
  } catch (err) {
    console.error(err);
    logLine(`[activate] Failed to register shell integration listener: ${String(err)}`);
  }

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalOrchestrator.startCodex", async () => {
      const c = getConfig();
      const t = getOrCreateTerminal(c.codexTerminalName);
      // Manual command: always re-send to allow retry without needing to reset state.
      await startTerminalIfNeeded(context, t, STATE_KEYS.startedCodex, c.codexCommand, true);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalOrchestrator.restartCodex", async () => {
      const c = getConfig();
      const didDispose = disposeTerminalByName(c.codexTerminalName);
      logLine(`[restart] Disposed Codex terminal: ${didDispose}`);
      // Reset started flag so autoStart/manual behaves consistently.
      await context.workspaceState.update(STATE_KEYS.startedCodex, false);

      const t = getOrCreateTerminal(c.codexTerminalName);
      await startTerminalIfNeeded(context, t, STATE_KEYS.startedCodex, c.codexCommand, true);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalOrchestrator.startOpenCode", async () => {
      const c = getConfig();
      const t = getOrCreateTerminal(c.opencodeTerminalName);
      // Manual command: always re-send to allow retry without needing to reset state.
      await startTerminalIfNeeded(context, t, STATE_KEYS.startedOpenCode, c.opencodeCommand, true);
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
    vscode.commands.registerCommand("ivyhouseTerminalOrchestrator.captureCodexOutput", async () => {
      const c = getConfig();
      const terminal = findTerminalByName(c.codexTerminalName);
      if (!terminal) {
        vscode.window.showErrorMessage(
          `Terminal '${c.codexTerminalName}' not found. Start it first (IvyHouse: Start Codex Terminal).`,
        );
        return;
      }

      const text = await vscode.window.showInputBox({
        title: `Capture output from ${c.codexTerminalName}`,
        prompt: "Command will be sent via terminal.sendText() and output will be captured briefly.",
        value: "/status",
      });

      if (typeof text !== "string" || text.trim() === "") return;

      const captureResult = startCapture(c, c.codexTerminalName);
      if (!captureResult) return;

      const { captureFile, capturePromise } = captureResult;
      terminal.show(true);
      terminal.sendText(text, true);

      if (!terminalDataWriteEventAvailable) {
        // Fallback: if we attached to the codex shell execution stream, we can still capture.
        const hasShellRead = shellReadState.attachedTerminalName === c.codexTerminalName;
        if (!hasShellRead) {
          const diag = formatDiagnostics(c);
          logLine("[capture] Proposed API not available and no shell-read stream attached");
          logLine(diag);
          stopCaptureWithPromise("no capture source");
          vscode.window.showErrorMessage(
            "目前無法擷取 Codex 輸出：Proposed API 未啟用，且尚未掛上 shell integration 串流。" +
              "\n\n請先執行：IvyHouse: Restart Codex Terminal（會重啟 Codex，讓 extension 能在啟動當下掛上讀取串流），" +
              "接著再跑一次 Capture。" +
              "\n\n也請確認 VS Code 設定 terminal.integrated.shellIntegration.enabled 為 true。",
          );
          return;
        }

        // We can still proceed; output will come via shell integration stream.
        vscode.window.showInformationMessage(
          `Capturing output (fallback via shell integration)... writing to ${captureFile}`,
        );
        await capturePromise;
        return;
      }

      // Proposed API path
      vscode.window.showInformationMessage(`Capturing output... writing to ${captureFile}`);
      await capturePromise;
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand(
      "ivyhouseTerminalOrchestrator.codexCaptureDiagnostics",
      async () => {
        const c = getConfig();
        const diag = formatDiagnostics(c);
        logLine("[diagnostics] Requested");
        logLine(diag);
        getOutputChannel().show(true);

        // Also validate we can create the capture file.
        const paths = resolveCapturePaths(c);
        if (!paths) {
          vscode.window.showErrorMessage("Workspace folder not found; cannot resolve capture paths.");
          return;
        }
        try {
          fs.mkdirSync(paths.dir, { recursive: true });
          if (!fs.existsSync(paths.lastFile)) {
            fs.writeFileSync(paths.lastFile, "", "utf8");
          }
          vscode.window.showInformationMessage(
            `Diagnostics written to Output panel. Capture file location: ${paths.lastFileDisplay}`,
          );
        } catch (err) {
          console.error(err);
          vscode.window.showErrorMessage(
            `Failed to create capture file under ${paths.lastFileDisplay}. See DevTools console for details.`,
          );
        }
      },
    ),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalOrchestrator.openLastCodexCapture", async () => {
      const c = getConfig();
      const paths = resolveCapturePaths(c);
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
    vscode.commands.registerCommand("ivyhouseTerminalOrchestrator.clearCodexCapture", async () => {
      const c = getConfig();
      const paths = resolveCapturePaths(c);
      if (!paths) {
        vscode.window.showErrorMessage("Workspace folder not found; cannot clear capture file.");
        return;
      }
      fs.mkdirSync(paths.dir, { recursive: true });
      fs.writeFileSync(paths.lastFile, "", "utf8");
      vscode.window.showInformationMessage(`Cleared ${paths.lastFile}`);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand(
      "ivyhouseTerminalOrchestrator.clearTerminalCaptureAfterQaPassAndLog",
      async () => {
        const c = getConfig();
        const root = getWorkspaceRootFsPath();
        if (!root) {
          vscode.window.showErrorMessage("Workspace folder not found; cannot clear terminal capture.");
          return;
        }

        const idxName = await vscode.window.showInputBox({
          title: "Clear terminal_capture (guarded)",
          prompt:
            "輸入 Idx-XXX（例如 Idx-024）。此命令只會在 .agent/logs/<Idx-XXX>_log.md 存在且偵測到 QA PASS 證據後才允許清空。",
          placeHolder: "Idx-024",
        });
        if (!idxName) return;
        const normalizedIdx = normalizeIdxName(idxName);
        if (!normalizedIdx) {
          vscode.window.showErrorMessage("Idx 格式不正確，請用 Idx-XXX（例如 Idx-024）。");
          return;
        }

        const logAbs = resolveIdxLogAbs(normalizedIdx);
        if (!logAbs || !fs.existsSync(logAbs)) {
          vscode.window.showErrorMessage(
            `找不到 log 檔：.agent/logs/${normalizedIdx}_log.md。請先確認 log 已建立後再清空。`,
          );
          return;
        }

        const qaEvidence = detectQaPassEvidenceFromCaptureDir(c);
        if (!qaEvidence.ok) {
          const choice = await vscode.window.showWarningMessage(
            `找不到 QA PASS 證據（${qaEvidence.reason}）。若你已人工確認 PASS，可選擇繼續清空。`,
            { modal: true },
            "取消",
            "我已確認 PASS，仍要清空",
          );
          if (choice !== "我已確認 PASS，仍要清空") return;
        }

        const captureDirAbs = resolveTerminalCaptureDirAbs(c);
        if (!captureDirAbs) {
          vscode.window.showErrorMessage("Workspace folder not found; cannot resolve capture dir.");
          return;
        }

        fs.mkdirSync(captureDirAbs, { recursive: true });

        const confirm = await vscode.window.showWarningMessage(
          `確認要清空 ${c.captureDir} 內所有檔案/子資料夾嗎？（log 已確認存在）`,
          { modal: true },
          "清空",
        );
        if (confirm !== "清空") return;

        const removed = clearDirectoryContents(captureDirAbs);
        logLine(
          `[cleanup] cleared captureDir=${c.captureDir} removed=${removed} idx=${normalizedIdx} qaEvidence=${qaEvidence.ok}`,
        );
        getOutputChannel().show(true);
        vscode.window.showInformationMessage(`已清空 ${c.captureDir}（移除 ${removed} 項）。`);
      },
    ),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalOrchestrator.resetSessionState", async () => {
      await context.workspaceState.update(STATE_KEYS.startedCodex, false);
      await context.workspaceState.update(STATE_KEYS.startedOpenCode, false);
      vscode.window.showInformationMessage("IvyHouse Terminal Orchestrator session state reset.");
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand(
      "ivyhouseTerminalOrchestrator.autoCaptureCodexStatus",
      async () => {
        const c = getConfig();
        const terminal = findTerminalByName(c.codexTerminalName);
        if (!terminal) {
          logLine(
            "[autoCapture] Codex terminal not found; cannot capture. (User may need to start it manually.)",
          );
          return;
        }

        const captureResult = startCapture(c, c.codexTerminalName);
        if (!captureResult) return;

        const { captureFile, capturePromise } = captureResult;
        logLine(`[autoCapture] Starting auto-capture for /status to ${captureFile}`);

        terminal.show(true);
        terminal.sendText("/status", true);

        // Await capture completion
        const reason = await capturePromise;
        logLine(`[autoCapture] Capture completed: ${reason}`);
      },
    ),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand(
      "ivyhouseTerminalOrchestrator.restartAndCaptureCodexStatus",
      async () => {
        const c = getConfig();
        logLine("[restartAndCapture] Restarting Codex and auto-capturing /status");

        // Dispose old terminal
        const didDispose = disposeTerminalByName(c.codexTerminalName);
        logLine(`[restartAndCapture] Disposed old Codex terminal: ${didDispose}`);
        await context.workspaceState.update(STATE_KEYS.startedCodex, false);

        // Create and start new terminal
        const t = getOrCreateTerminal(c.codexTerminalName);
        await startTerminalIfNeeded(context, t, STATE_KEYS.startedCodex, c.codexCommand, true);

        // Wait for shell integration to attach (onDidStartTerminalShellExecution will trigger)
        // Give it a reasonable time window (5 seconds) for codex to output its prompt
        logLine("[restartAndCapture] Waiting for codex to initialize...");
        await new Promise((resolve) => setTimeout(resolve, 5000));

        // Now capture /status
        const captureResult = startCapture(c, c.codexTerminalName);
        if (!captureResult) {
          logLine("[restartAndCapture] Failed to start capture");
          return;
        }

        const { captureFile, capturePromise } = captureResult;
        logLine(`[restartAndCapture] Sending /status for capture to ${captureFile}`);

        t.show(true);
        t.sendText("/status", true);

        // Await capture completion
        const reason = await capturePromise;
        logLine(`[restartAndCapture] Capture completed: ${reason}`);
      },
    ),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalOrchestrator.startWorkflowLoop", async () => {
      await startWorkflowLoop(context);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalOrchestrator.stopWorkflowLoop", async () => {
      stopWorkflowLoop("user requested");
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("ivyhouseTerminalOrchestrator.showWorkflowStatus", async () => {
      const status = formatWorkflowStatus();
      logLine("[workflow] status requested");
      logLine(status);
      getOutputChannel().show(true);
      vscode.window.showInformationMessage("Workflow status written to Output panel.");
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
