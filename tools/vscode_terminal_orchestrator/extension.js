/* eslint-disable no-console */
const vscode = require("vscode");
const http = require("http");
const fs = require("fs");
const path = require("path");
const childProcess = require("child_process");
const crypto = require("crypto");

const STATE_KEYS = {
  startedCodex: "ivyhouseTerminalOrchestrator.startedCodex",
  startedOpenCode: "ivyhouseTerminalOrchestrator.startedOpenCode",
};

const WORKFLOW_STATE_KEYS = {
  workflowRunId: "ivyhouseTerminalOrchestrator.workflowRunId",
  planId: "ivyhouseTerminalOrchestrator.workflowPlanId",
  state: "ivyhouseTerminalOrchestrator.workflowState",
  engineerRawLogAbs: "ivyhouseTerminalOrchestrator.workflowEngineerRawLogAbs",
  qaRawLogAbs: "ivyhouseTerminalOrchestrator.workflowQaRawLogAbs",
  startedAtIso: "ivyhouseTerminalOrchestrator.workflowStartedAtIso",
};

let sendtextBridgeServer;
let sendtextBridgeServerStartedAtIso;

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
    workflowPollIntervalMs: cfg.get("workflowPollIntervalMs", 10000),
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
    workflowPostSendEnterDelayMs: cfg.get("workflowPostSendEnterDelayMs", 250),
    workflowPostSendEnterCount: cfg.get("workflowPostSendEnterCount", 1),
    workflowQaEngineerSummaryMaxChars: cfg.get("workflowQaEngineerSummaryMaxChars", 1800),

    sendtextBridgeEnabled: cfg.get("sendtextBridgeEnabled", true),
    // Security hard rule: host must be 127.0.0.1. Setting exists for documentation parity only.
    sendtextBridgeHost: cfg.get("sendtextBridgeHost", "127.0.0.1"),
    sendtextBridgePort: cfg.get("sendtextBridgePort", 8765),
    sendtextBridgeMaxPayloadBytes: cfg.get("sendtextBridgeMaxPayloadBytes", 32768),
    sendtextBridgeMaxRequestBytes: cfg.get("sendtextBridgeMaxRequestBytes", 65536),
    sendtextBridgeRateLimit: cfg.get("sendtextBridgeRateLimit", 1.0),
    sendtextBridgeRateBurst: cfg.get("sendtextBridgeRateBurst", 2),
  };
}

function normalizeIp(remoteAddress) {
  const s = String(remoteAddress || "");
  if (!s) return "";
  if (s === "::1") return "127.0.0.1";
  // Node reports IPv4 connections as ::ffff:127.0.0.1
  if (s.startsWith("::ffff:")) return s.slice("::ffff:".length);
  return s;
}

function jsonResponse(res, statusCode, obj) {
  try {
    const body = JSON.stringify(obj);
    res.statusCode = statusCode;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.setHeader("Cache-Control", "no-store");
    res.end(body);
  } catch {
    try {
      res.statusCode = 500;
      res.end("{\"error\":\"internal_error\"}");
    } catch {
      // ignore
    }
  }
}

function readJsonBody(req, maxBytes) {
  return new Promise((resolve, reject) => {
    const limit = Math.max(0, Number(maxBytes) || 0);
    const chunks = [];
    let size = 0;
    req.on("data", (chunk) => {
      const buf = Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk || ""), "utf8");
      size += buf.length;
      if (limit > 0 && size > limit) {
        reject(new Error("request_too_large"));
        try {
          req.destroy();
        } catch {
          // ignore
        }
        return;
      }
      chunks.push(buf);
    });
    req.on("end", () => {
      const raw = Buffer.concat(chunks).toString("utf8");
      if (!raw) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(raw));
      } catch {
        reject(new Error("invalid_json"));
      }
    });
    req.on("error", () => reject(new Error("request_error")));
  });
}

function loadSendtextBridgeToken(rootAbs) {
  // Priority 1: environment variable
  const envToken = process.env.IVY_SENDTEXT_BRIDGE_TOKEN;
  if (envToken && String(envToken).trim()) return String(envToken).trim();

  // Priority 2: token file
  if (!rootAbs) return undefined;
  const p = path.join(rootAbs, ".service", "sendtext_bridge", "token");
  try {
    if (!fs.existsSync(p)) return undefined;
    const s = fs.readFileSync(p, "utf8");
    const token = String(s || "").trim();
    return token || undefined;
  } catch {
    return undefined;
  }
}

function extractBearerToken(req) {
  const auth = String(req.headers?.authorization || "").trim();
  if (auth.toLowerCase().startsWith("bearer ")) {
    return auth.slice("bearer ".length).trim();
  }
  const x = req.headers?.["x-ivy-token"];
  if (typeof x === "string" && x.trim()) return x.trim();
  return undefined;
}

function ensureAllowedTerminalName(cfg, terminalKind) {
  const kind = String(terminalKind || "").trim();
  if (kind === "codex") return cfg.codexTerminalName;
  if (kind === "opencode") return cfg.opencodeTerminalName;
  return undefined;
}

function appendSendtextBridgeAuditEvent(cfg, evt) {
  try {
    const root = getWorkspaceRootFsPath();
    if (!root) return;
    const dirAbs = path.join(root, cfg.captureDir);
    fs.mkdirSync(dirAbs, { recursive: true });
    const fileAbs = path.join(dirAbs, "sendtext_bridge_events.jsonl");
    fs.appendFileSync(fileAbs, JSON.stringify(evt) + "\n", "utf8");
  } catch {
    // ignore
  }
}

function createRequestId() {
  try {
    return `req_${crypto.randomBytes(8).toString("hex")}`;
  } catch {
    return `req_${Date.now()}`;
  }
}

function rateLimiterCreate(cfg) {
  // Token bucket per IP (memory-only). Intended as a light local safeguard.
  const limitPerSec = Math.max(0, Number(cfg.sendtextBridgeRateLimit) || 0);
  const burst = Math.max(0, Number(cfg.sendtextBridgeRateBurst) || 0);
  const buckets = new Map();

  function take(ip) {
    if (limitPerSec <= 0 || burst <= 0) return { ok: true };
    const now = Date.now();
    const key = ip || "";
    const prev = buckets.get(key) || { tokens: burst, lastMs: now };
    const elapsed = Math.max(0, now - prev.lastMs);
    const refill = (elapsed / 1000) * limitPerSec;
    const tokens = Math.min(burst, prev.tokens + refill);
    if (tokens < 1) {
      buckets.set(key, { tokens, lastMs: now });
      const retryAfter = Math.ceil((1 - tokens) / limitPerSec);
      return { ok: false, retryAfter: Math.max(1, retryAfter) };
    }
    buckets.set(key, { tokens: tokens - 1, lastMs: now });
    return { ok: true };
  }

  return { take };
}

async function sendInstructionWithIdx024Pipeline(cfg, terminalKind, text, submit, mode) {
  const terminalName = ensureAllowedTerminalName(cfg, terminalKind);
  if (!terminalName) {
    return { ok: false, error: "invalid_terminal_kind" };
  }

  const terminal = findTerminalByName(terminalName);
  if (!terminal) {
    return { ok: false, error: "terminal_not_found", terminalName };
  }

  try {
    terminal.show(true);
  } catch {
    // ignore
  }

  const kind = terminalKind === "codex" ? "codex" : "opencode";
  const normalized = normalizeInstruction(text, kind);
  const payloadBytes = Buffer.from(normalized, "utf8");
  const maxPayload = Math.max(0, Number(cfg.sendtextBridgeMaxPayloadBytes) || 0);
  if (maxPayload > 0 && payloadBytes.length > maxPayload) {
    return { ok: false, error: "payload_too_large", textBytes: payloadBytes.length, maxBytes: maxPayload };
  }

  const chunked =
    String(mode || "").toLowerCase() === "chunked" ||
    (kind === "codex" && normalized.length > 500);

  const parts = [];
  if (!chunked) {
    parts.push(normalized);
  } else {
    const CHUNK_SIZE = 500;
    let remaining = normalized;
    while (remaining.length > 0) {
      if (remaining.length <= CHUNK_SIZE) {
        parts.push(remaining);
        break;
      }
      const slice = remaining.slice(0, CHUNK_SIZE);
      const nl = slice.lastIndexOf("\n");
      if (nl > Math.floor(CHUNK_SIZE * 0.4)) {
        parts.push(slice.slice(0, nl + 1));
        remaining = remaining.slice(nl + 1);
      } else {
        parts.push(slice);
        remaining = remaining.slice(CHUNK_SIZE);
      }
    }
  }

  try {
    for (const part of parts) {
      // Do not auto-submit each chunk; only submit at the end.
      terminal.sendText(part, false);
      await sleepMs(kind === "codex" ? 35 : 15);
    }
    if (submit) {
      await workflowSendEnter(terminalName, kind, 1);
    }
  } catch (err) {
    return { ok: false, error: "send_failed", details: String(err || "") };
  }

  return {
    ok: true,
    terminalKind: kind,
    terminalName,
    submit: Boolean(submit),
    mode: chunked ? "chunked" : "single",
    textBytes: payloadBytes.length,
    payloadSha256: sha256Hex(normalized),
  };
}

function extractPlanSections(planText) {
  const s = String(planText || "");
  if (!s.trim()) return "";

  // Extract high-signal sections. Keep logic simple and robust to minor template variations.
  function extractByHeading(title) {
    const esc = String(title).replace(/[-/\\^$*+?.()|[\\]{}]/g, "\\$&");
    const re = new RegExp(`(^|\\n)##\\s+${esc}\\s*\\n([\\s\\S]*?)(?=\\n##\\s+|$)`, "m");
    const m = s.match(re);
    if (!m) return "";
    return `## ${title}\n` + String(m[2] || "").trim() + "\n";
  }

  const goal = extractByHeading("Goal");
  const spec = extractByHeading("SPEC");

  const out = [goal, spec].filter(Boolean).join("\n").trim();
  return out || s.trim();
}

function resolvePlanAbs(planId, scope) {
  const root = getWorkspaceRootFsPath();
  if (!root) return undefined;
  const idx = normalizeIdxName(planId);
  if (!idx) return undefined;
  if (scope === "project") return path.join(root, "doc", "plans", `${idx}_plan.md`);
  return path.join(root, ".agent", "plans", `${idx}_plan.md`);
}

async function startWorkflowLoopCore(context, params) {
  const cfg = getConfig();
  const engineerTerminalName = params?.engineerTerminalName || cfg.opencodeTerminalName;
  const qaTerminalName = params?.qaTerminalName || cfg.codexTerminalName;
  const taskDescription = String(params?.taskDescription || "").trim();
  const normalizedIdx = normalizeIdxName(params?.idxName || "");
  const workflowRunId = String(params?.workflowRunId || "").trim();

  if (!taskDescription) {
    throw new Error("missing taskDescription");
  }
  if (!engineerTerminalName || !qaTerminalName || engineerTerminalName === qaTerminalName) {
    throw new Error("invalid terminal selection");
  }

  // This mirrors startWorkflowLoop(), but without UI prompts.
  if (workflowLoopState.active) {
    throw new Error("workflow already running");
  }

  const paths = resolveWorkflowLogPaths(cfg);
  if (!paths) {
    throw new Error("workspace folder not found; cannot create workflow logs");
  }

  fs.mkdirSync(paths.dirAbs, { recursive: true });
  fs.writeFileSync(paths.engineerLogAbs, "", "utf8");
  fs.writeFileSync(paths.qaLogAbs, "", "utf8");
  fs.writeFileSync(paths.engineerRawLogAbs, "", "utf8");
  fs.writeFileSync(paths.qaRawLogAbs, "", "utf8");
  fs.writeFileSync(paths.eventLogAbs, "", "utf8");

  // Idx-030: generate session nonce (8 bytes = 16 hex chars)
  const sessionNonce = crypto.randomBytes(8).toString("hex");

  const scriptOk = isScriptAvailable();
  let captureMode = "none";
  if (scriptOk) {
    captureMode = "script";
  } else if (terminalDataWriteEventAvailable) {
    captureMode = "terminalData";
  }

  if (captureMode === "none") {
    throw new Error(
      "Workflow loop cannot start: missing `script` and Proposed API terminalDataWriteEvent is not enabled",
    );
  }

  workflowLoopState = {
    active: true,
    phase: WORKFLOW_PHASE.waitEngineerDone,
    captureMode,
    startedAtMs: Date.now(),
    round: 1,
    taskDescription,
    idxName: normalizedIdx,
    engineerTerminalName,
    qaTerminalName,
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
    pollIntervalMs: Math.max(200, Number(cfg.workflowPollIntervalMs) || 10000),
    maxRounds: Math.max(1, Number(cfg.workflowMaxRounds) || 10),
    timeoutMs: Math.max(1000, Number(cfg.workflowTimeoutMs) || 1800000),
    timer: undefined,
    tickBusy: false,
    // Idx-030: unified completion detection fields
    sessionNonce,
    engineerNudgeCount: 0,
    engineerNudgeMaxPerRound: 3,
    fixNudgeCount: 0,
    fixNudgeMaxPerRound: 3,
    qaNudgeCount: 0,
    qaNudgeMaxPerRound: 3,
    envVerified: false,
  };

  appendWorkflowEvent({
    action: "workflow_start",
    captureMode,
    engineerTerminalName: workflowLoopState.engineerTerminalName,
    qaTerminalName: workflowLoopState.qaTerminalName,
    engineerRawLog: paths.engineerRawLogDisplay,
    qaRawLog: paths.qaRawLogDisplay,
    idxName: workflowLoopState.idxName,
    workflowRunId,
  });

  // Persist minimal status for /workflow/status (survives window reload).
  try {
    await context.workspaceState.update(WORKFLOW_STATE_KEYS.workflowRunId, workflowRunId || "");
    await context.workspaceState.update(WORKFLOW_STATE_KEYS.planId, normalizedIdx || "");
    await context.workspaceState.update(WORKFLOW_STATE_KEYS.state, "running");
    await context.workspaceState.update(WORKFLOW_STATE_KEYS.engineerRawLogAbs, paths.engineerRawLogAbs);
    await context.workspaceState.update(WORKFLOW_STATE_KEYS.qaRawLogAbs, paths.qaRawLogAbs);
    await context.workspaceState.update(WORKFLOW_STATE_KEYS.startedAtIso, new Date().toISOString());
  } catch {
    // ignore
  }

  // Start / restart terminals to ensure clean session.
  for (const terminalName of [engineerTerminalName, qaTerminalName]) {
    const stateKey = getStateKeyForTerminal(cfg, terminalName);
    if (stateKey) {
      await context.workspaceState.update(stateKey, false);
    }
    disposeTerminalByName(terminalName);
    await waitForTerminalToClose(terminalName, 3000);
  }

  const engineerStart = getStartCommandForTerminal(cfg, engineerTerminalName);
  const qaStart = getStartCommandForTerminal(cfg, qaTerminalName);
  if (!engineerStart || !qaStart) {
    stopWorkflowLoop("invalid terminal selection");
    throw new Error("unsupported terminal selection");
  }

  // Idx-030: inject session nonce via terminal env
  const workflowEnv = { WORKFLOW_SESSION_NONCE: sessionNonce };
  const engineerTerm = getOrCreateTerminal(engineerTerminalName, workflowEnv);
  const qaTerm = getOrCreateTerminal(qaTerminalName, workflowEnv);
  workflowLoopState.engineerTerminal = engineerTerm;
  workflowLoopState.qaTerminal = qaTerm;

  if (captureMode === "script") {
    const engineerCmd =
      `script -q -f -c ${bashSingleQuote(engineerStart)} ` +
      bashSingleQuote(workflowLoopState.engineerRawLogAbs);
    const qaCmd =
      `script -q -f -c ${bashSingleQuote(qaStart)} ` + bashSingleQuote(workflowLoopState.qaRawLogAbs);

    const engineerKey = getStateKeyForTerminal(cfg, engineerTerminalName);
    const qaKey = getStateKeyForTerminal(cfg, qaTerminalName);
    const ok1 = await startTerminalIfNeeded(context, engineerTerm, engineerKey, engineerCmd, true);
    const ok2 = await startTerminalIfNeeded(context, qaTerm, qaKey, qaCmd, true);
    if (!ok1 || !ok2) {
      stopWorkflowLoop("failed to start terminals (script mode)");
      throw new Error("failed to start terminals (script mode)");
    }
  } else {
    const engineerKey = getStateKeyForTerminal(cfg, engineerTerminalName);
    const qaKey = getStateKeyForTerminal(cfg, qaTerminalName);
    const ok1 = await startTerminalIfNeeded(context, engineerTerm, engineerKey, engineerStart, true);
    const ok2 = await startTerminalIfNeeded(context, qaTerm, qaKey, qaStart, true);
    if (!ok1 || !ok2) {
      stopWorkflowLoop("failed to start terminals (terminalData mode)");
      throw new Error("failed to start terminals (terminalData mode)");
    }
  }

  // Avoid false-positive marker detection from transcript echo of our own prompt.
  workflowLoopState.engineerPauseUntilMs = Date.now() + 2000;
  const firstSendOk = await workflowSendInstructionWithRetry(
    cfg,
    workflowLoopState.engineerTerminalName,
    buildEngineerPrompt(workflowLoopState.taskDescription),
  );
  if (!firstSendOk || !workflowLoopState.active) {
    throw new Error("failed to send first prompt to engineer");
  }

  if (workflowLoopState.engineerRawLogAbs) {
    await sleepMs(400);
    workflowLoopState.engineerOffset = safeGetFileSize(workflowLoopState.engineerRawLogAbs);
    workflowLoopState.engineerMarkerBuf = "";
  }

  workflowLoopState.timer = setInterval(() => {
    workflowTick(getConfig()).catch((err) => {
      console.error(err);
    });
  }, workflowLoopState.pollIntervalMs);

  return {
    ok: true,
    engineerRawLogDisplay: paths.engineerRawLogDisplay,
    qaRawLogDisplay: paths.qaRawLogDisplay,
    workflowRunId,
    planId: normalizedIdx,
  };
}

async function startWorkflowLoopNonInteractive(context, planId, scope) {
  const normalizedIdx = normalizeIdxName(planId);
  if (!normalizedIdx) {
    throw new Error("invalid planId");
  }

  const planAbs = resolvePlanAbs(normalizedIdx, scope);
  if (!planAbs || !fs.existsSync(planAbs)) {
    throw new Error(`plan not found: ${String(planAbs || "")}`);
  }

  const planText = fs.readFileSync(planAbs, "utf8");
  const extracted = extractPlanSections(planText);
  const workflowRunId = `wf_${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}_${crypto
    .randomBytes(3)
    .toString("hex")}`;

  // Mark state = starting first (so /workflow/status is meaningful during startup).
  try {
    await context.workspaceState.update(WORKFLOW_STATE_KEYS.workflowRunId, workflowRunId);
    await context.workspaceState.update(WORKFLOW_STATE_KEYS.planId, normalizedIdx);
    await context.workspaceState.update(WORKFLOW_STATE_KEYS.state, "starting");
    await context.workspaceState.update(WORKFLOW_STATE_KEYS.startedAtIso, new Date().toISOString());
  } catch {
    // ignore
  }

  const cfg = getConfig();
  const result = await startWorkflowLoopCore(context, {
    engineerTerminalName: cfg.opencodeTerminalName,
    qaTerminalName: cfg.codexTerminalName,
    taskDescription: extracted,
    idxName: normalizedIdx,
    workflowRunId,
  });
  return {
    status: "started",
    workflowRunId,
    planId: normalizedIdx,
    extractedSections: extracted,
    ...result,
  };
}

function getWorkflowStatusForApi(context) {
  const state =
    (workflowLoopState && workflowLoopState.active && "running") ||
    context.workspaceState.get(WORKFLOW_STATE_KEYS.state, "idle");
  const workflowRunId = context.workspaceState.get(WORKFLOW_STATE_KEYS.workflowRunId, "");
  const planId = context.workspaceState.get(WORKFLOW_STATE_KEYS.planId, "");
  const startedAtIso = context.workspaceState.get(WORKFLOW_STATE_KEYS.startedAtIso, "");

  // Prefer active raw logs, then persisted.
  const activeEngineer = workflowLoopState?.engineerRawLogAbs;
  const activeQa = workflowLoopState?.qaRawLogAbs;
  const persistedEngineer = context.workspaceState.get(WORKFLOW_STATE_KEYS.engineerRawLogAbs, "");
  const persistedQa = context.workspaceState.get(WORKFLOW_STATE_KEYS.qaRawLogAbs, "");

  let rawLogAbs;
  let lastOutputSource = "none";
  if (activeEngineer) {
    rawLogAbs = activeEngineer;
    lastOutputSource = "active_engineer";
  } else if (activeQa) {
    rawLogAbs = activeQa;
    lastOutputSource = "active_qa";
  } else if (persistedEngineer) {
    rawLogAbs = persistedEngineer;
    lastOutputSource = "persisted_engineer";
  } else if (persistedQa) {
    rawLogAbs = persistedQa;
    lastOutputSource = "persisted_qa";
  }

  let lastOutputTs;
  let lastRawLogSizeBytes;
  try {
    if (rawLogAbs && fs.existsSync(rawLogAbs)) {
      const st = fs.statSync(rawLogAbs);
      lastOutputTs = st.mtime.toISOString();
      lastRawLogSizeBytes = Number(st.size) || 0;
    } else if (rawLogAbs) {
      lastOutputSource = "raw_log_not_found";
    }
  } catch {
    // ignore
  }

  return {
    workflowRunId,
    planId,
    state,
    startedAtIso,
    lastOutputTs,
    lastRawLogSizeBytes,
    lastOutputSource,
  };
}

function startSendtextBridgeServer(context) {
  const cfg = getConfig();
  if (!cfg.sendtextBridgeEnabled) {
    logLine("[bridge] disabled by setting: sendtextBridgeEnabled=false");
    return;
  }

  if (sendtextBridgeServer) {
    return;
  }

  const limiter = rateLimiterCreate(cfg);
  const host = "127.0.0.1";
  const port = Math.max(1, Math.min(65535, Number(cfg.sendtextBridgePort) || 8765));
  sendtextBridgeServerStartedAtIso = new Date().toISOString();

  const server = http.createServer(async (req, res) => {
    const method = String(req.method || "GET").toUpperCase();
    const url = String(req.url || "/");
    const endpoint = url.split("?")[0];
    const ip = normalizeIp(req.socket?.remoteAddress);
    const requestId = createRequestId();

    const tokenConfigured = loadSendtextBridgeToken(getWorkspaceRootFsPath());
    const tokenHash = tokenConfigured ? sha256Hex(tokenConfigured) : "";
    const provided = extractBearerToken(req);
    const authed = Boolean(tokenConfigured) && Boolean(provided) && provided === tokenConfigured;

    const rate = limiter.take(ip);
    if (!rate.ok) {
      const evt = {
        ts: new Date().toISOString(),
        endpoint,
        result: "rate_limited",
        requestId,
        tokenHash,
        ip,
        retryAfter: rate.retryAfter,
      };
      appendSendtextBridgeAuditEvent(cfg, evt);
      jsonResponse(res, 429, { error: "rate_limited", retryAfter: rate.retryAfter, requestId });
      return;
    }

    if (method === "GET" && endpoint === "/healthz") {
      jsonResponse(res, 200, {
        status: "ok",
        ts: new Date().toISOString(),
        serverStartedAt: sendtextBridgeServerStartedAtIso,
      });
      return;
    }

    const protectedEndpoints = new Set(["/send", "/workflow/start", "/workflow/status"]);
    if (protectedEndpoints.has(endpoint)) {
      if (!tokenConfigured) {
        const evt = {
          ts: new Date().toISOString(),
          endpoint,
          result: "rejected",
          error: "token_not_configured",
          requestId,
          tokenHash,
          ip,
        };
        appendSendtextBridgeAuditEvent(cfg, evt);
        jsonResponse(res, 503, { error: "token_not_configured", requestId });
        return;
      }
      if (!authed) {
        const evt = {
          ts: new Date().toISOString(),
          endpoint,
          result: "rejected",
          error: "unauthorized",
          requestId,
          tokenHash,
          ip,
        };
        appendSendtextBridgeAuditEvent(cfg, evt);
        jsonResponse(res, 401, { error: "unauthorized", requestId });
        return;
      }
    }

    if (method === "POST" && endpoint === "/send") {
      let body;
      try {
        body = await readJsonBody(req, cfg.sendtextBridgeMaxRequestBytes);
      } catch (err) {
        const code = String(err?.message || "");
        jsonResponse(res, code === "request_too_large" ? 413 : 400, {
          error: code || "bad_request",
          requestId,
        });
        return;
      }

      const terminalKind = body?.terminalKind;
      const text = body?.text;
      const submit = Boolean(body?.submit);
      const mode = body?.mode || "single";

      const sendRes = await sendInstructionWithIdx024Pipeline(cfg, terminalKind, text, submit, mode);

      const evt = {
        ts: new Date().toISOString(),
        endpoint: "/send",
        result: sendRes.ok ? "success" : "error",
        requestId,
        terminalKind: sendRes.terminalKind || String(terminalKind || ""),
        submit,
        mode: sendRes.mode || String(mode || ""),
        textBytes: sendRes.textBytes || 0,
        payloadSha256: sendRes.payloadSha256 || "",
        tokenHash,
        ip,
        error: sendRes.ok ? undefined : sendRes.error,
      };
      appendSendtextBridgeAuditEvent(cfg, evt);

      if (!sendRes.ok) {
        jsonResponse(res, 400, { error: sendRes.error, requestId });
        return;
      }

      jsonResponse(res, 200, {
        status: "sent",
        terminalKind: sendRes.terminalKind,
        textBytes: sendRes.textBytes,
        requestId,
      });
      return;
    }

    if (method === "POST" && endpoint === "/workflow/start") {
      let body;
      try {
        body = await readJsonBody(req, cfg.sendtextBridgeMaxRequestBytes);
      } catch (err) {
        const code = String(err?.message || "");
        jsonResponse(res, code === "request_too_large" ? 413 : 400, {
          error: code || "bad_request",
          requestId,
        });
        return;
      }

      const planId = body?.planId;
      const scope = body?.scope || "workflow";

      try {
        const started = await startWorkflowLoopNonInteractive(context, planId, scope);
        appendSendtextBridgeAuditEvent(cfg, {
          ts: new Date().toISOString(),
          endpoint: "/workflow/start",
          result: "success",
          requestId,
          tokenHash,
          ip,
          planId: started.planId,
          workflowRunId: started.workflowRunId,
        });
        jsonResponse(res, 200, started);
      } catch (err) {
        const msg = String(err || "");
        try {
          await context.workspaceState.update(WORKFLOW_STATE_KEYS.state, "error");
        } catch {
          // ignore
        }
        appendSendtextBridgeAuditEvent(cfg, {
          ts: new Date().toISOString(),
          endpoint: "/workflow/start",
          result: "error",
          requestId,
          tokenHash,
          ip,
          error: msg,
        });
        jsonResponse(res, 400, { error: "workflow_start_failed", details: msg, requestId });
      }
      return;
    }

    if (method === "GET" && endpoint === "/workflow/status") {
      const status = getWorkflowStatusForApi(context);
      appendSendtextBridgeAuditEvent(cfg, {
        ts: new Date().toISOString(),
        endpoint: "/workflow/status",
        result: "success",
        requestId,
        tokenHash,
        ip,
        workflowRunId: status.workflowRunId,
        planId: status.planId,
        state: status.state,
      });
      jsonResponse(res, 200, status);
      return;
    }

    jsonResponse(res, 404, { error: "not_found", requestId });
  });

  server.on("error", (err) => {
    const msg = String(err || "");
    logLine(`[bridge] server error: ${msg}`);
  });

  try {
    server.listen(port, host, () => {
      logLine(`[bridge] SendText Bridge listening on http://${host}:${port}`);
    });
    sendtextBridgeServer = server;
  } catch (err) {
    const msg = String(err || "");
    logLine(`[bridge] failed to listen: ${msg}`);
  }
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

function getOrCreateTerminal(name, env = undefined) {
  const existing = findTerminalByName(name);
  if (existing) return existing;
  const options = { name };
  if (env && typeof env === "object") {
    options.env = env;
  }
  return vscode.window.createTerminal(options);
}

function sleepMs(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function sendTerminalSequenceToActive(sequenceText) {
  try {
    await vscode.commands.executeCommand("workbench.action.terminal.sendSequence", {
      text: String(sequenceText || ""),
    });
    return true;
  } catch {
    return false;
  }
}

async function workflowSendEnter(terminalName, kind, count = 1) {
  const t = findTerminalByName(terminalName);
  if (!t) return false;

  try {
    // Important: sendSequence targets the active terminal.
    // Do NOT preserve focus here; we want this terminal to become active.
    t.show(false);
  } catch {
    // ignore
  }

  // Give VS Code a brief moment to focus the terminal before sending sequences.
  await sleepMs(40);

  const n = Math.max(1, Number(count) || 1);
  for (let i = 0; i < n; i += 1) {
    // Prefer sendSequence (more like real keypress) when the terminal is active.
    // If VS Code cannot focus the terminal reliably, fall back to writing CR directly
    // into the terminal input stream (does not depend on active terminal).
    const isActive = vscode.window.activeTerminal?.name === t.name;
    const ok = isActive ? await sendTerminalSequenceToActive("\r") : false;
    if (!ok) {
      try {
        t.sendText("\r", false);
      } catch {
        // ignore
      }
    }
    await sleepMs(kind === "codex" ? 120 : 60);
  }
  return true;
}

async function workflowDisableBracketedPasteIfPossible(terminalName, kind) {
  if (kind !== "codex") return false;
  const t = findTerminalByName(terminalName);
  if (!t) return false;
  try {
    t.show(true);
  } catch {
    // ignore
  }
  await sleepMs(40);
  // Disable xterm bracketed paste mode: CSI ? 2004 l
  return await sendTerminalSequenceToActive("\u001b[?2004l");
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
  idxName: undefined,
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
  qaWrongMarkerNudgedRound: 0,
  qaPromptSentinel: "",
  qaSeenPromptSentinel: false,
  // When we send a prompt, transcript logs will include our input (including marker strings).
  // For QA, we rely on prompt sentinel gating (qaPromptSentinel + qaSeenPromptSentinel) to avoid
  // parsing prompt echo; do not depend on offset fast-forward.
  qaNudgeCount: 0,
  qaNudgeMaxPerRound: 2,
  engineerPauseUntilMs: 0,
  qaPauseUntilMs: 0,
  pollIntervalMs: 10000,
  maxRounds: 10,
  timeoutMs: 1800000,
  timer: undefined,
  tickBusy: false,
  // Idx-030: unified completion detection
  sessionNonce: undefined, // 16-char hex nonce for session isolation
  engineerNudgeCount: 0, // near-miss nudge counter for Engineer phase
  engineerNudgeMaxPerRound: 3, // max nudges before exhaustion
  fixNudgeCount: 0, // near-miss nudge counter for Fix phase
  fixNudgeMaxPerRound: 3,
  envVerified: false, // delayed env verification flag
};

function normalizeInstruction(text, kind = "opencode") {
  // Normalize instruction differently depending on terminal kind.
  // - opencode: existing behaviour (collapse to single line)
  // - codex: keep newlines, strip control chars, and collapse excessive blank lines
  const s = String(text || "");
  if (kind === "codex") {
    // Strip ANSI and non-printable control chars except keep LF
    const noAnsi = stripAnsi(s).replace(/\r/g, "\n");
    // Remove other C0 control chars but preserve newline (LF)
    const kept = noAnsi.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, "");
    // Collapse more than 2 consecutive blank lines into 2
    const collapsedBlankLines = kept.replace(/\n{3,}/g, "\n\n");
    // Trim leading / trailing whitespace but preserve internal newlines
    return collapsedBlankLines.replace(/^[ \t\n]+|[ \t\n]+$/g, "");
  }

  // Fallback / opencode: collapse to a single line (original behaviour)
  return s.replace(/\r?\n+/g, " ").replace(/\s+/g, " ").trim();
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
    // CSI 可能包含 '?' 參數（例如 \x1b[?25h），終止字元也不一定是字母。
    .replace(/\x1b\[[0-9;?]*[ -/]*[@-~]/g, "")
    .replace(/\x1b\][^\x07]*(\x07|\x1b\\)/g, "")
    .replace(/\x1b\([^)]/g, "");
}

function detectCompletionMarker(buf, markerName) {
  // Prefer strict standalone-line detection, but fall back to token detection.
  // Real-world interactive TUIs may:
  // - remove newlines (screen redraw capture)
  // - output markers without brackets (e.g. ENGINEER_DONE)
  // - use fullwidth brackets
  // We allow those variants while still trying to avoid false positives via
  // prompt-echo guards (pause + offset fast-forward) and boundary checks.
  const m = String(markerName || "").trim();
  if (!m) return { found: false, mode: "none" };

  const esc = m.replace(/[-/\\^$*+?.()|[\\]{}]/g, "\\$&");
  const s = String(buf || "");

  const bracketedAscii = `\\[\\s*${esc}\\s*\\]`;
  const bracketedFullwidth = `【\\s*${esc}\\s*】|［\\s*${esc}\\s*］`;
  const anyBracketed = `(?:${bracketedAscii}|${bracketedFullwidth})`;

  // Strict: marker must appear as its own line.
  const strictRe = new RegExp(`(^|\\n)\\s*(?:${anyBracketed}|${esc})\\s*(\\r?\\n|$)`, "m");
  if (strictRe.test(s)) {
    // Best-effort classify the mode.
    const strictBracketRe = new RegExp(`(^|\\n)\\s*(?:${anyBracketed})\\s*(\\r?\\n|$)`, "m");
    return { found: true, mode: strictBracketRe.test(s) ? "strict_bracket" : "strict_bare" };
  }

  // Fallback: token detection bounded by ASCII word-ish chars.
  // This is intentionally weaker and relies on prompt-echo guards.
  const tokenBracketRe = new RegExp(`(^|[^A-Z0-9_])(?:${anyBracketed})([^A-Z0-9_]|$)`, "m");
  if (tokenBracketRe.test(s)) return { found: true, mode: "token_bracket" };

  const tokenBareRe = new RegExp(`(^|[^A-Z0-9_])${esc}([^A-Z0-9_]|$)`, "m");
  if (tokenBareRe.test(s)) return { found: true, mode: "token_bare" };

  return { found: false, mode: "none" };
}

function hasCompletionMarker(buf, markerName) {
  return detectCompletionMarker(buf, markerName).found;
}

function getQaResult(buf) {
  // Accept both strict and spaced variants. Do NOT require newline boundaries;
  // TUIs may not emit newlines in captured transcripts.
  const s = String(buf || "");
  if (/QA_RESULT\s*=\s*PASS\b/i.test(s)) return "PASS";
  if (/QA_RESULT\s*=\s*FAIL\b/i.test(s)) return "FAIL";
  return undefined;
}

/**
 * Idx-030: Unified completion detection for Engineer/QA/Fix phases.
 *
 * Format (5 lines, tail-only):
 *   [ENGINEER_DONE] | [QA_DONE] | [FIX_DONE]
 *   TIMESTAMP=YYYY-MM-DDTHH:mm:ssZ
 *   NONCE=<16-char-hex>
 *   TASK_ID=Idx-NNN
 *   ENGINEER_RESULT=COMPLETE | QA_RESULT=PASS|FAIL | FIX_ROUND=N
 *
 * @param {string} buf - raw terminal buffer
 * @param {string} phase - one of: "ENGINEER", "QA", "FIX"
 * @param {string} expectedNonce - session nonce from workflowLoopState
 * @param {string} expectedTaskId - e.g. "Idx-030"
 * @returns {{ ok: true, result: string } | { ok: false, nearMiss?: {...} }}
 */
function detectCompletionWithIdx030Format(buf, phase, expectedNonce, expectedTaskId) {
  const s = String(buf || "");
  const lines = s
    .split(/\r?\n/)
    .map((l) => String(l || "").trim())
    .filter(Boolean);

  // Tail-only: last 5 non-empty lines
  const tail = lines.slice(-5);
  if (tail.length < 5) {
    // Not enough lines => incomplete output (not a near-miss yet)
    return { ok: false };
  }

  const nearMiss = {};

  // Line 1: marker
  const expectedMarker = phase === "ENGINEER" ? "[ENGINEER_DONE]" :
                         phase === "QA" ? "[QA_DONE]" :
                         "[FIX_DONE]";

  function isMarkerLine(line, marker) {
    const v = String(line || "").trim();
    const esc = marker.replace(/[[\]]/g, "\\$&");
    return new RegExp(`^${esc}$`, "i").test(v) ||
           new RegExp(`^【${marker.slice(1, -1)}】$`, "i").test(v) ||
           new RegExp(`^［${marker.slice(1, -1)}］$`, "i").test(v);
  }

  const line1 = tail[0];
  const hasMarker = isMarkerLine(line1, expectedMarker);

  if (!hasMarker) {
    // Check if marker-like but malformed
    const markerName = expectedMarker.slice(1, -1); // remove brackets
    if (new RegExp(markerName, "i").test(line1)) {
      nearMiss.markerMalformed = true;
      nearMiss.line1 = line1;
      return { ok: false, nearMiss };
    }

    // Fix #4: Check for extraTailNoise - marker present but not in final 5 lines
    // Scan last 20 non-empty lines to detect if marker appears elsewhere
    const widerTail = lines.slice(-20);
    let markerFoundAtIndex = -1;
    for (let i = 0; i < widerTail.length; i++) {
      if (isMarkerLine(widerTail[i], expectedMarker)) {
        markerFoundAtIndex = i;
        break; // Find first occurrence (earliest in the window)
      }
    }

    // If marker found in wider window but not at correct position (last 5 lines, line 1)
    // => Tool outputted completion then added extra text
    if (markerFoundAtIndex !== -1) {
      const correctPosition = widerTail.length - 5; // Where it should be in wider window
      if (markerFoundAtIndex < correctPosition) {
        nearMiss.extraTailNoise = true;
        nearMiss.markerFoundAt = markerFoundAtIndex;
        nearMiss.expectedAt = correctPosition;
        return { ok: false, nearMiss };
      }
    }

    // Not even close
    return { ok: false };
  }

  // Line 2: TIMESTAMP
  const line2 = tail[1];
  const timestampMatch = line2.match(/^TIMESTAMP\s*=\s*(.+)$/i);
  if (!timestampMatch) {
    nearMiss.missingTimestamp = true;
    nearMiss.line2 = line2;
    return { ok: false, nearMiss };
  }
  const timestamp = timestampMatch[1].trim();
  // Validate ISO 8601 UTC format: YYYY-MM-DDTHH:mm:ssZ
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(timestamp)) {
    nearMiss.timestampInvalid = true;
    nearMiss.timestamp = timestamp;
    nearMiss.line2 = line2;
    return { ok: false, nearMiss };
  }

  // Line 3: NONCE
  const line3 = tail[2];
  const nonceMatch = line3.match(/^NONCE\s*=\s*(.+)$/i);
  if (!nonceMatch) {
    nearMiss.missingNonce = true;
    nearMiss.line3 = line3;
    return { ok: false, nearMiss };
  }
  const nonce = nonceMatch[1].trim();

  // Fix #5: Detect literal placeholders (env var or angle brackets)
  const nonceLooksLikeLiteral =
    nonce === "$WORKFLOW_SESSION_NONCE" ||
    nonce === "${WORKFLOW_SESSION_NONCE}" ||
    /^<[^>]+>$/.test(nonce); // e.g., "<nonce>", "<16-char-hex>"

  if (nonceLooksLikeLiteral) {
    nearMiss.nonceLooksLikeEnvVar = true;
    nearMiss.nonce = nonce;
    nearMiss.expectedNonce = expectedNonce;
    nearMiss.line3 = line3;
    return { ok: false, nearMiss };
  }

  if (nonce !== expectedNonce) {
    nearMiss.nonceMismatch = true;
    nearMiss.nonce = nonce;
    nearMiss.expectedNonce = expectedNonce;
    nearMiss.line3 = line3;
    return { ok: false, nearMiss };
  }

  // Line 4: TASK_ID
  const line4 = tail[3];
  const taskIdMatch = line4.match(/^TASK_ID\s*=\s*(.+)$/i);
  if (!taskIdMatch) {
    nearMiss.missingTaskId = true;
    nearMiss.line4 = line4;
    return { ok: false, nearMiss };
  }
  const taskId = taskIdMatch[1].trim();
  // Normalize comparison (case-insensitive, flexible hyphen/underscore)
  const normalizeId = (id) => String(id || "").toLowerCase().replace(/[-_]/g, "");
  if (normalizeId(taskId) !== normalizeId(expectedTaskId)) {
    nearMiss.taskIdMismatch = true;
    nearMiss.taskId = taskId;
    nearMiss.expectedTaskId = expectedTaskId;
    nearMiss.line4 = line4;
    return { ok: false, nearMiss };
  }

  // Line 5: phase-specific result
  const line5 = tail[4];
  let result;
  if (phase === "ENGINEER") {
    const m = line5.match(/^ENGINEER_RESULT\s*=\s*(.+)$/i);
    if (!m) {
      nearMiss.missingEngineerResult = true;
      nearMiss.line5 = line5;
      return { ok: false, nearMiss };
    }
    result = m[1].trim().toUpperCase();
    if (result !== "COMPLETE") {
      nearMiss.engineerResultInvalid = true;
      nearMiss.engineerResult = result;
      nearMiss.line5 = line5;
      return { ok: false, nearMiss };
    }
  } else if (phase === "QA") {
    const m = line5.match(/^QA_RESULT\s*=\s*(.+)$/i);
    if (!m) {
      nearMiss.missingQaResult = true;
      nearMiss.line5 = line5;
      return { ok: false, nearMiss };
    }
    result = m[1].trim().toUpperCase();
    if (result !== "PASS" && result !== "FAIL") {
      nearMiss.qaResultInvalid = true;
      nearMiss.qaResult = result;
      nearMiss.line5 = line5;
      return { ok: false, nearMiss };
    }
  } else if (phase === "FIX") {
    const m = line5.match(/^FIX_ROUND\s*=\s*(\d+)$/i);
    if (!m) {
      nearMiss.missingFixRound = true;
      nearMiss.line5 = line5;
      return { ok: false, nearMiss };
    }
    result = m[1].trim();
  }

  // All checks passed
  return { ok: true, result, timestamp, nonce, taskId };
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
  const postSendEnterDelayMs = Math.max(0, Number(cfg.workflowPostSendEnterDelayMs) || 0);
  const postSendEnterCount = Math.max(0, Number(cfg.workflowPostSendEnterCount) || 0);
  const effectivePrimeEnterCount = kind === "opencode" ? primeEnterCount : 0;

  // Codex CLI is particularly sensitive to bracketed-paste timing; treat submit as best-effort
  // and ensure we send enough post-send Enters with sufficient delay.
  const effectivePostSendEnterCount =
    kind === "codex" ? Math.max(2, postSendEnterCount) : postSendEnterCount;

  // Normalize per-terminal-kind. For opencode keep single-line behaviour; for codex keep newlines.
  const payload = normalizeInstruction(text, kind);
  // Use actualSentContent as base; we will finalize finalSentContent inside retry loop
  let actualSentContent = payload;

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
    // suffix for retries so human-readable note can be appended
    const retrySuffix = attempt > 1 ? "（若你已開始處理請忽略此重送）" : "";
    const finalSentContent = actualSentContent + retrySuffix;
    const payloadHash = sha256Hex(finalSentContent);
    const payloadLen = finalSentContent.length;

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
    if (effectivePrimeEnterCount > 0) {
      await workflowSendEnter(terminalName, kind, effectivePrimeEnterCount);
    }

    // Codex-specific: try to disable bracketed paste before injecting a large prompt.
    if (kind === "codex") {
      const disabled = await workflowDisableBracketedPasteIfPossible(terminalName, kind);
      if (disabled) {
        appendWorkflowEvent({
          action: "codex_bracketed_paste_disabled",
          terminalName,
          kind,
          attempt,
        });
      }
    }

    // For codex, use chunked send to avoid very long single paste which triggers
    // bracketed-paste UI and leads to [Pasted Content ...] artifacts.
    let sendMode = "single";
    let chunkCount = 1;
    let chunkSize = actualSentContent.length;
    if (kind === "codex") {
      // chunk size tunable; choose conservative default
      const CHUNK_SIZE = 500; // chars
      if (actualSentContent.length > CHUNK_SIZE) {
        sendMode = "chunked";
        // split into reasonably sized chunks on newline boundaries where possible
        const parts = [];
        let remaining = actualSentContent;
        while (remaining.length > 0) {
          if (remaining.length <= CHUNK_SIZE) {
            parts.push(remaining);
            break;
          }
          // try to cut at last newline within chunk size
          const slice = remaining.slice(0, CHUNK_SIZE);
          const nl = slice.lastIndexOf("\n");
          if (nl > Math.floor(CHUNK_SIZE * 0.4)) {
            parts.push(slice.slice(0, nl + 1));
            remaining = remaining.slice(nl + 1);
          } else {
            parts.push(slice);
            remaining = remaining.slice(CHUNK_SIZE);
          }
        }
        chunkCount = parts.length;
        chunkSize = Math.max(0, Math.min(CHUNK_SIZE, Math.ceil(actualSentContent.length / chunkCount)));

        appendWorkflowEvent({
          action: "send_chunked_prepare",
          terminalName,
          kind,
          attempt,
          sendMode,
          chunkCount,
          chunkSize,
        });

        // Actually send chunks sequentially with a small delay
        try {
          for (let ci = 0; ci < parts.length; ci += 1) {
            const piece = parts[ci];
            // sendText without newline; submission handled by post-send Enter
            const t = findTerminalByName(terminalName);
            try {
              t.show(true);
            } catch {
              // ignore
            }
            try {
              t.sendText(String(piece), false);
            } catch (err) {
              appendWorkflowEvent({ action: "send_chunk_error", terminalName, kind, attempt, chunkIndex: ci });
              throw err;
            }
            // small sleep to avoid overwhelming paste handling
            await sleepMs(40 + Math.min(60, Math.round(chunkSize / 10)));
          }
          // If this is a retry, append the retry suffix as a final tiny chunk so the
          // actual sent content matches reported payload hash/len.
          if (attempt > 1 && retrySuffix) {
            try {
              const t2 = findTerminalByName(terminalName);
              try {
                t2.show(true);
              } catch {}
              t2.sendText(String(retrySuffix), false);
              await sleepMs(40);
            } catch (err) {
              // ignore
            }
          }
        } catch (err) {
          appendWorkflowEvent({ action: "send_error_chunked", terminalName, kind, attempt });
          return false;
        }

        // after chunked send, log chunked-sent event and include actual payload hash/len
        appendWorkflowEvent({
          action: "send_chunked_sent",
          terminalName,
          kind,
          attempt,
          sendMode,
          chunkCount,
          chunkSize,
          payloadSha256: payloadHash,
          payloadLen: payloadLen,
        });
      } else {
        // small enough to send single
        sendMode = "single";
      }
    }

    let ok;
    if (kind === "codex" && sendMode === "single") {
      ok = workflowSendInstruction(terminalName, actualSentContent + (attempt > 1 ? "（若你已開始處理請忽略此重送）" : ""));
    } else if (kind === "codex" && sendMode === "chunked") {
      // already sent chunks above; mark as ok
      ok = true;
    } else {
      // opencode or other: single-shot
      ok = workflowSendInstruction(terminalName, actualSentContent + (attempt > 1 ? "（若你已開始處理請忽略此重送）" : ""));
    }
    if (!ok) {
      appendWorkflowEvent({ action: "send_error", terminalName, kind, attempt });
      return false;
    }

    // Some TUIs show a "Pasted Content ..." buffer and won't submit immediately.
    // Send an additional Enter *after* a short delay to better simulate a real submit.
    if (effectivePostSendEnterCount > 0) {
      // Heuristic: bigger payloads need a longer delay before Enter, otherwise the Enter
      // may be delivered while the terminal is still processing the bracketed paste.
      const extraDelayMs =
        kind === "codex"
          ? payloadLen > 8000
            ? 1800
            : payloadLen > 2000
              ? 1200
              : payloadLen > 300
                ? 900
                : 600
          : payloadLen > 15000
            ? 1500
            : payloadLen > 8000
              ? 900
              : payloadLen > 2000
                ? 400
                : 0;
      const effectiveDelayMs = Math.max(0, postSendEnterDelayMs + extraDelayMs);

      if (effectiveDelayMs > 0) {
        await sleepMs(effectiveDelayMs);
      }
      try {
        await workflowSendEnter(terminalName, kind, effectivePostSendEnterCount);
        appendWorkflowEvent({
          action: "post_send_enter",
          terminalName,
          kind,
          attempt,
          postSendEnterDelayMs: effectiveDelayMs,
          postSendEnterCount: effectivePostSendEnterCount,
        });
      } catch {
        // ignore
      }
    }

    // Codex-specific: if the UI is still showing a paste buffer indicator, nudge submit again.
    // This is intentionally best-effort; it only fires when transcript already changed.
    if (kind === "codex") {
      try {
        await sleepMs(900);
        const tail = cleanForTail(tailFile(rawLogAbs, 64 * 1024));
        const pasteMatch = /\[Pasted Content\s+(\d+)\s+chars\]/i.exec(tail);
        if (pasteMatch) {
          const pastedChars = Number(pasteMatch[1] || 0);
          // One more delayed Enter burst to ensure submit.
          await sleepMs(1200);
          await workflowSendEnter(terminalName, kind, 1);
          await sleepMs(600);
          await workflowSendEnter(terminalName, kind, 1);
          appendWorkflowEvent({
            action: "codex_submit_nudge",
            terminalName,
            kind,
            attempt,
            reason: "pasted_content_detected",
            pastedChars,
            sendMode: sendMode,
            chunkCount: chunkCount,
            chunkSize: chunkSize,
          });

          // If paste buffer indicator present, attempt one-time recovery sequence:
          // send Escape, Ctrl+C, then re-submit Enter burst.
          try {
            const t = findTerminalByName(terminalName);
            await sleepMs(80);
            // ESC
            await sendTerminalSequenceToActive("\u001b");
            await sleepMs(40);
            // Ctrl+C
            await sendTerminalSequenceToActive("\u0003");
            await sleepMs(120);
            // Post-recovery submit nudges
            await workflowSendEnter(terminalName, kind, 1);
            await sleepMs(240);
            await workflowSendEnter(terminalName, kind, 1);
            appendWorkflowEvent({ action: "codex_submit_recovery", terminalName, kind, attempt, pastedChars });
          } catch (err) {
            // ignore
          }
        }
      } catch {
        // ignore
      }
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
  const hasDone = hasCompletionMarker(cleaned, WORKFLOW_MARKER_NAMES.qaDone);
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

  // Normalize according to terminal kind
  const cfg = getConfig();
  const kind = detectWorkflowTerminalKind(cfg, terminalName);
  const payload = normalizeInstruction(text, kind);

  try {
    t.show(true);
  } catch (err) {
    logLine(`[workflow] show() failed: ${String(err || "")}`);
  }

  try {
    // Paste without implicit newline; submission is handled by workflowSendInstructionWithRetry
    // via its post-send Enter (with adaptive delay for large pastes).
    // For codex we may be sending already-chunked content; still call sendText for final single-shot.
    t.sendText(payload, false);
    return true;
  } catch (err) {
    const msg = String(err || "");
    logLine(`[workflow] sendText failed (terminal may be disposed): ${msg}`);
    stopWorkflowLoop(`sendText failed: ${terminalName}`);
    return false;
  }
}

function buildEngineerPrompt(taskDescription) {
  // Idx-030: Updated prompt with 5-line completion format (no line numbers to avoid inducing numbered output)
  const nonce = workflowLoopState?.sessionNonce || "<nonce>";
  const taskId = workflowLoopState?.idxName || "Idx-XXX";

  return (
    "你是 Engineer（負責實作）。請遵守 repo 規範：不要在此終端執行 git 指令（git/pytest/ruff 請用 Project terminal）。" +
    ` 任務：${taskDescription}。` +
    " 請勿自行做 QA；只要完成實作即可。" +
    " 完成時請『精確輸出』以下 5 行作為你的最後 5 行輸出：\n\n" +
    "```\n" +
    "[ENGINEER_DONE]\n" +
    "TIMESTAMP=<當前UTC時間，格式：YYYY-MM-DDTHH:mm:ssZ>\n" +
    `NONCE=${nonce}\n` +
    `TASK_ID=${taskId}\n` +
    "ENGINEER_RESULT=COMPLETE\n" +
    "```\n\n" +
    "請勿輸出編號或多餘文字。完成標記必須是最後 5 個非空白行。"
  );
}

function sanitizeSummaryForPrompt(summary) {
  // Summaries are injected into prompts that may be echoed into transcripts.
  // Remove any marker-like standalone lines to avoid false-positive detection.
  let s = stripAnsi(String(summary || "")).replace(/\r/g, "\n");

  // Remove marker tokens anywhere (not just standalone lines).
  // Remove bracketed markers with optional surrounding spaces.
  s = s.replace(/\[\s*ENGINEER_DONE\s*\]/g, "");
  s = s.replace(/\[\s*FIX_DONE\s*\]/g, "");
  s = s.replace(/\[\s*QA_DONE\s*\]/g, "");
  // Fullwidth bracket variants.
  s = s.replace(/［\s*ENGINEER_DONE\s*］/g, "");
  s = s.replace(/［\s*FIX_DONE\s*］/g, "");
  s = s.replace(/［\s*QA_DONE\s*］/g, "");
  s = s.replace(/\bENGINEER_DONE\b/g, "");
  s = s.replace(/\bFIX_DONE\b/g, "");
  s = s.replace(/\bQA_DONE\b/g, "");
  s = s.replace(/QA_RESULT\s*=\s*(PASS|FAIL)\b/gi, "");
  // Idx-030: Remove additional completion format lines
  s = s.replace(/TIMESTAMP\s*=\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z/gi, "");
  s = s.replace(/NONCE\s*=\s*[a-f0-9]{8,16}/gi, ""); // Fix #6: Support 8-16 char nonces
  s = s.replace(/TASK_ID\s*=\s*Idx-\d+/gi, "");
  s = s.replace(/ENGINEER_RESULT\s*=\s*COMPLETE/gi, "");
  s = s.replace(/FIX_ROUND\s*=\s*\d+/gi, "");

  // Then drop any remaining standalone marker-like lines.
  const lines = s.split("\n");
  const kept = lines.filter((line) => {
    const t = String(line || "").trim();
    if (!t) return true;
    if (t === WORKFLOW_MARKERS.engineerDone) return false;
    if (t === WORKFLOW_MARKERS.fixDone) return false;
    if (t === WORKFLOW_MARKERS.qaDone) return false;
    if (t === WORKFLOW_MARKER_NAMES.engineerDone) return false;
    if (t === WORKFLOW_MARKER_NAMES.fixDone) return false;
    if (t === WORKFLOW_MARKER_NAMES.qaDone) return false;
    if (/^QA_RESULT\s*=\s*(PASS|FAIL)\s*$/i.test(t)) return false;
    // Idx-030: Filter standalone Idx-030 completion lines
    if (/^TIMESTAMP\s*=\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\s*$/i.test(t)) return false;
    if (/^NONCE\s*=\s*[a-f0-9]{8,16}\s*$/i.test(t)) return false; // Fix #6: Support 8-16 char nonces
    if (/^TASK_ID\s*=\s*Idx-\d+\s*$/i.test(t)) return false;
    if (/^ENGINEER_RESULT\s*=\s*COMPLETE\s*$/i.test(t)) return false;
    if (/^FIX_ROUND\s*=\s*\d+\s*$/i.test(t)) return false;
    return true;
  });
  return kept.join("\n").trimEnd();
}

function summarizeEngineerOutputForQaPrompt(rawEngineerSummary, maxChars) {
  const maxLen = Math.max(300, Number(maxChars) || 1800);
  const original = String(rawEngineerSummary || "");

  let s = stripAnsi(original).replace(/\r/g, "\n");
  // Many TUIs redraw progress bars in-place; break common redraw separators into lines.
  s = s.replace(/▣·+/g, "\n");
  s = s.replace(/📁/g, "\n📁");
  s = s.replace(/(修改檔案\s*：)/g, "\n$1");
  s = s.replace(/(新增檔案\s*：)/g, "\n$1");
  s = s.replace(/\s+-\s+/g, "\n- ");
  s = s.replace(/[ \t]+\n/g, "\n");
  s = s.replace(/\n{3,}/g, "\n\n");

  const filePathExtractRe = /[A-Za-z0-9._/\-]+\.(?:py|md|toml|json|yml|yaml|txt|js|ts|css|html)\b/g;
  const filePathTestRe = /[A-Za-z0-9._/\-]+\.(?:py|md|toml|json|yml|yaml|txt|js|ts|css|html)\b/;
  const commandRe = /\b(?:python|pytest|ruff|pre-commit)\b[^\n]{0,180}/g;
  const errorRe = /(Traceback\b|\bERROR\b|\bFAIL\b|Exception\b|AssertionError\b|ImportError\b|ModuleNotFoundError\b|KeyError\b)/i;

  const files = Array.from(
    new Set((s.match(filePathExtractRe) || []).map((p) => String(p || "").trim())),
  )
    .filter(Boolean)
    .slice(0, 40);

  const commands = Array.from(
    new Set(
      (s.match(commandRe) || [])
        .map((c) => String(c || "").trim())
        .filter(Boolean)
        .map((c) => c.replace(/\s+/g, " ")),
    ),
  ).slice(0, 20);

  const lines = s
    .split("\n")
    .map((line) => String(line || "").trim())
    .filter(Boolean);

  const highlights = [];
  const seen = new Set();
  for (const line of lines) {
    if (highlights.length >= 12) break;
    if (line.length > 420) continue;
    const key = line.toLowerCase();
    if (seen.has(key)) continue;
    const interesting =
      errorRe.test(line) ||
      filePathTestRe.test(line) ||
      /\bpython\b|\bpytest\b|\bruff\b|\bpre-commit\b/i.test(line) ||
      /檔案變更|變更清單|修改檔案|新增檔案/i.test(line);
    if (!interesting) continue;
    seen.add(key);
    highlights.push(line);
  }

  const pieces = [];
  pieces.push("（coordinator 摘要：已去除進度/重複；原始 transcript 仍在 .service/terminal_capture/）");
  if (files.length > 0) {
    pieces.push("\n【可能涉及的檔案】\n" + files.map((p) => `- ${p}`).join("\n"));
  }
  if (commands.length > 0) {
    pieces.push("\n【可能的驗證指令】\n" + commands.map((c) => `- ${c}`).join("\n"));
  }
  if (highlights.length > 0) {
    pieces.push("\n【關鍵輸出片段】\n" + highlights.map((h) => `- ${h}`).join("\n"));
  }

  let out = pieces.join("\n").trim();
  if (!out) out = "(no engineer output captured)";
  if (out.length > maxLen) {
    out = out.slice(0, Math.max(0, maxLen - 20)).trimEnd() + "\n...(已截斷)";
  }
  return out;
}

function buildQaPrompt(round, taskDescription, engineerSummary, promptSentinel) {
  // Idx-030: Updated prompt with 5-line completion format (no line numbers)
  const nonce = workflowLoopState?.sessionNonce || "<nonce>";
  const taskId = workflowLoopState?.idxName || "Idx-XXX";

  return (
    `你是 QA（第 ${round} 輪）。請審查 Engineer 的變更是否符合 plan/whitelist 與 repo 規範。\n` +
    "完成時請『精確輸出』以下 5 行作為你的最後 5 行輸出：\n\n" +
    "```\n" +
    "[QA_DONE]\n" +
    "TIMESTAMP=<當前UTC時間，格式：YYYY-MM-DDTHH:mm:ssZ>\n" +
    `NONCE=${nonce}\n` +
    `TASK_ID=${taskId}\n` +
    "QA_RESULT=<PASS 或 FAIL>\n" +
    "```\n\n" +
    "請勿輸出編號或多餘文字。完成標記必須是最後 5 個非空白行。\n" +
    "注意：不要輸出 [ENGINEER_DONE] 或 [FIX_DONE]。\n\n" +
    `任務背景：${taskDescription}\n\n` +
    "Engineer 輸出摘要（供你審查判斷）：\n" +
    (engineerSummary ? engineerSummary : "(no engineer output captured)") +
    (promptSentinel ? `\n\n${promptSentinel}` : "")
  );
}

function buildQaCorrectivePrompt(wrongMarkerType, promptSentinel) {
  // Idx-030 Fix: Update to 5-line format, no line numbers
  const nonce = workflowLoopState?.sessionNonce || "<nonce>";
  const taskId = workflowLoopState?.idxName || "Idx-XXX";

  const wrongText =
    wrongMarkerType === "ENGINEER_DONE"
      ? "你剛才誤輸出了 Engineer 的完成標記。"
      : wrongMarkerType === "FIX_DONE"
        ? "你剛才誤輸出了 Fix 的完成標記。"
        : "你剛才誤輸出了不屬於 QA 的完成標記。";

  return (
    wrongText +
    "請現在精確輸出以下 5 行作為你的最後 5 行輸出：\n\n" +
    "```\n" +
    "[QA_DONE]\n" +
    "TIMESTAMP=<當前UTC時間，格式：YYYY-MM-DDTHH:mm:ssZ>\n" +
    `NONCE=${nonce}\n` +
    `TASK_ID=${taskId}\n` +
    "QA_RESULT=<PASS 或 FAIL>\n" +
    "```\n\n" +
    "請勿輸出編號或多餘文字。完成標記必須是最後 5 個非空白行。" +
    (promptSentinel ? `\n\n${promptSentinel}` : "")
  );
}

/**
 * Idx-030: Build nudge prompt for Engineer/QA/Fix near-miss completion.
 */
function buildIdx030NearMissNudgePrompt(phase, nearMiss, expectedNonce, expectedTaskId, promptSentinel) {
  const markerName = phase === "ENGINEER" ? "[ENGINEER_DONE]" :
                     phase === "QA" ? "[QA_DONE]" :
                     "[FIX_DONE]";

  const resultLine = phase === "ENGINEER" ? "ENGINEER_RESULT=COMPLETE" :
                     phase === "QA" ? "QA_RESULT=<PASS 或 FAIL>" :
                     `FIX_ROUND=${workflowLoopState.round}`;

  const parts = [
    "你的輸出格式接近正確但不完整或有誤。請重新輸出『精確遵守』以下 5 行格式（必須是你輸出的最後 5 行）：",
    "",
    "```",
    `${markerName}`,
    `TIMESTAMP=<ISO8601-UTC格式：YYYY-MM-DDTHH:mm:ssZ>`,
    `NONCE=${expectedNonce}`,
    `TASK_ID=${expectedTaskId}`,
    `${resultLine}`,
    "```",
    "",
    "格式要求：",
    "- 每一行必須獨立成行（不要合併）",
    "- TIMESTAMP 必須是 UTC 時區（以 Z 結尾）",
    "- NONCE 必須完全一致",
    "- TASK_ID 必須匹配當前任務",
    "- 請勿輸出編號或多餘文字",
  ];

  const hints = [];
  if (nearMiss?.markerMalformed) {
    hints.push(`- 第 1 行格式不正確：${nearMiss.line1}`);
  }
  if (nearMiss?.missingTimestamp) {
    hints.push(`- 缺少 TIMESTAMP 行（應為第 2 行）`);
  }
  if (nearMiss?.timestampInvalid) {
    hints.push(`- TIMESTAMP 格式錯誤：${nearMiss.timestamp}（必須是 YYYY-MM-DDTHH:mm:ssZ）`);
  }
  if (nearMiss?.missingNonce) {
    hints.push(`- 缺少 NONCE 行（應為第 3 行）`);
  }
  if (nearMiss?.nonceMismatch) {
    hints.push(`- NONCE 不匹配：你輸出 ${nearMiss.nonce}，期望 ${expectedNonce}`);
  }
  if (nearMiss?.nonceLooksLikeEnvVar) {
    hints.push(`- NONCE 看起來是環境變數字面值，請輸出實際 nonce 值（例如 ${expectedNonce}）`);
  }
  if (nearMiss?.missingTaskId) {
    hints.push(`- 缺少 TASK_ID 行（應為第 4 行）`);
  }
  if (nearMiss?.taskIdMismatch) {
    hints.push(`- TASK_ID 不匹配：你輸出 ${nearMiss.taskId}，期望 ${expectedTaskId}`);
  }
  if (nearMiss?.missingEngineerResult) {
    hints.push(`- 缺少 ENGINEER_RESULT 行（應為第 5 行）`);
  }
  if (nearMiss?.engineerResultInvalid) {
    hints.push(`- ENGINEER_RESULT 值錯誤：${nearMiss.engineerResult}（必須是 COMPLETE）`);
  }
  if (nearMiss?.missingQaResult) {
    hints.push(`- 缺少 QA_RESULT 行（應為第 5 行）`);
  }
  if (nearMiss?.qaResultInvalid) {
    hints.push(`- QA_RESULT 值錯誤：${nearMiss.qaResult}（必須是 PASS 或 FAIL）`);
  }
  if (nearMiss?.missingFixRound) {
    hints.push(`- 缺少 FIX_ROUND 行（應為第 5 行）`);
  }
  if (nearMiss?.extraTailNoise) {
    hints.push(`- 你在完成標記後又輸出了多餘文字，請重新輸出，且讓這 5 行成為最後 5 個非空白行`);
  }

  if (hints.length > 0) {
    parts.push("", "偵測到的問題：", ...hints);
  }

  if (promptSentinel) {
    parts.push("", promptSentinel);
  }

  return parts.join("\n");
}

function buildFixPrompt(round, qaSummary) {
  // Idx-030: Updated prompt with 5-line completion format (no line numbers)
  const nonce = workflowLoopState?.sessionNonce || "<nonce>";
  const taskId = workflowLoopState?.idxName || "Idx-XXX";

  return (
    `QA 第 ${round} 輪結果為 FAIL，請依以下 QA 摘要修正：\n\n` +
    qaSummary +
    "\n\n修正完成時請『精確輸出』以下 5 行作為你的最後 5 行輸出：\n\n" +
    "```\n" +
    "[FIX_DONE]\n" +
    "TIMESTAMP=<當前UTC時間，格式：YYYY-MM-DDTHH:mm:ssZ>\n" +
    `NONCE=${nonce}\n` +
    `TASK_ID=${taskId}\n` +
    `FIX_ROUND=${round}\n` +
    "```\n\n" +
    "請勿輸出編號或多餘文字。完成標記必須是最後 5 個非空白行。"
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

      // Idx-030: unified Engineer completion detection
      if (workflowLoopState.phase === WORKFLOW_PHASE.waitEngineerDone) {
        const completion = detectCompletionWithIdx030Format(
          workflowLoopState.engineerMarkerBuf,
          "ENGINEER",
          workflowLoopState.sessionNonce,
          workflowLoopState.idxName || "Idx-XXX"
        );

        if (completion.ok) {
          logLine("[workflow] detected ENGINEER_DONE (Idx-030 format)");
          appendWorkflowEvent({
            action: "engineer_done_detected",
            format: "idx030",
            terminalName: workflowLoopState.engineerTerminalName,
            fromPhase: WORKFLOW_PHASE.waitEngineerDone,
            toPhase: WORKFLOW_PHASE.waitQaDone,
            round: workflowLoopState.round,
            timestamp: completion.timestamp,
            nonce: completion.nonce,
            taskId: completion.taskId,
            result: completion.result,
            engineerOffset: workflowLoopState.engineerOffset,
            engineerRawLogSize: workflowLoopState.engineerRawLogAbs
              ? safeGetFileSize(workflowLoopState.engineerRawLogAbs)
              : undefined,
          });

          const engineerSummary = fs.existsSync(workflowLoopState.engineerLogAbs)
            ? fs.readFileSync(workflowLoopState.engineerLogAbs, "utf8")
            : "";

          const engineerSummarySanitized = sanitizeSummaryForPrompt(engineerSummary);
          const engineerSummaryForQa = summarizeEngineerOutputForQaPrompt(
            engineerSummarySanitized,
            cfg.workflowQaEngineerSummaryMaxChars,
          );
          appendWorkflowEvent({
            action: "qa_prompt_summarized",
            round: workflowLoopState.round,
            engineerSummaryLen: String(engineerSummarySanitized || "").length,
            qaSummaryLen: String(engineerSummaryForQa || "").length,
            maxChars: Number(cfg.workflowQaEngineerSummaryMaxChars) || 1800,
          });

          workflowLoopState.phase = WORKFLOW_PHASE.waitQaDone;
          workflowLoopState.qaWrongMarkerNudgedRound = 0;
          workflowLoopState.qaNudgeCount = 0;
          workflowLoopState.qaPromptSentinel = `PROMPT_END_ID=qa_${workflowLoopState.round}_${Date.now()}`;
          workflowLoopState.qaSeenPromptSentinel = false;
          workflowLoopState.qaPauseUntilMs = Date.now() + 2000;
          await workflowSendInstructionWithRetry(
            cfg,
            workflowLoopState.qaTerminalName,
            buildQaPrompt(
              workflowLoopState.round,
              workflowLoopState.taskDescription,
              engineerSummaryForQa,
              workflowLoopState.qaPromptSentinel,
            ),
          );
          return;
        }

        // Near-miss handling
        if (completion.nearMiss) {
          if (workflowLoopState.engineerNudgeCount >= workflowLoopState.engineerNudgeMaxPerRound) {
            appendWorkflowEvent({
              action: "workflow_stop",
              reason: "engineer_completion_verification_exhausted",
              round: workflowLoopState.round,
              detail: "Engineer completion format errors persist despite nudges",
              nearMiss: completion.nearMiss,
              nudgeCount: workflowLoopState.engineerNudgeCount,
            });
            stopWorkflowLoop("Engineer completion verification exhausted");
            return;
          }

          workflowLoopState.engineerNudgeCount += 1;
          appendWorkflowEvent({
            action: "engineer_completion_format_error_detected",
            round: workflowLoopState.round,
            nearMiss: completion.nearMiss,
            nudgeAttempt: workflowLoopState.engineerNudgeCount,
          });

          workflowLoopState.engineerPauseUntilMs = Date.now() + 1500;
          await workflowSendInstructionWithRetry(
            cfg,
            workflowLoopState.engineerTerminalName,
            buildIdx030NearMissNudgePrompt(
              "ENGINEER",
              completion.nearMiss,
              workflowLoopState.sessionNonce,
              workflowLoopState.idxName || "Idx-XXX",
              undefined
            ),
          );
          return;
        }
      }

      // Idx-030: unified Fix completion detection
      if (workflowLoopState.phase === WORKFLOW_PHASE.waitFixDone) {
        const completion = detectCompletionWithIdx030Format(
          workflowLoopState.engineerMarkerBuf,
          "FIX",
          workflowLoopState.sessionNonce,
          workflowLoopState.idxName || "Idx-XXX"
        );

        if (completion.ok) {
          logLine("[workflow] detected FIX_DONE (Idx-030 format)");
          workflowLoopState.round += 1;
          if (workflowLoopState.round > workflowLoopState.maxRounds) {
            stopWorkflowLoop("max rounds exceeded");
            return;
          }

          appendWorkflowEvent({
            action: "fix_done_detected",
            format: "idx030",
            terminalName: workflowLoopState.engineerTerminalName,
            fromPhase: WORKFLOW_PHASE.waitFixDone,
            toPhase: WORKFLOW_PHASE.waitQaDone,
            round: workflowLoopState.round,
            timestamp: completion.timestamp,
            nonce: completion.nonce,
            taskId: completion.taskId,
            fixRound: completion.result,
          });

          const engineerSummary = fs.existsSync(workflowLoopState.engineerLogAbs)
            ? fs.readFileSync(workflowLoopState.engineerLogAbs, "utf8")
            : "";

          const engineerSummarySanitized = sanitizeSummaryForPrompt(engineerSummary);
          const engineerSummaryForQa = summarizeEngineerOutputForQaPrompt(
            engineerSummarySanitized,
            cfg.workflowQaEngineerSummaryMaxChars,
          );
          appendWorkflowEvent({
            action: "qa_prompt_summarized",
            round: workflowLoopState.round,
            engineerSummaryLen: String(engineerSummarySanitized || "").length,
            qaSummaryLen: String(engineerSummaryForQa || "").length,
            maxChars: Number(cfg.workflowQaEngineerSummaryMaxChars) || 1800,
          });

          workflowLoopState.phase = WORKFLOW_PHASE.waitQaDone;
          workflowLoopState.qaWrongMarkerNudgedRound = 0;
          workflowLoopState.qaNudgeCount = 0;
          workflowLoopState.qaPromptSentinel = `PROMPT_END_ID=qa_${workflowLoopState.round}_${Date.now()}`;
          workflowLoopState.qaSeenPromptSentinel = false;
          workflowLoopState.qaPauseUntilMs = Date.now() + 2000;
          await workflowSendInstructionWithRetry(
            cfg,
            workflowLoopState.qaTerminalName,
            buildQaPrompt(
              workflowLoopState.round,
              workflowLoopState.taskDescription,
              engineerSummaryForQa,
              workflowLoopState.qaPromptSentinel,
            ),
          );
          return;
        }

        // Near-miss handling
        if (completion.nearMiss) {
          if (workflowLoopState.fixNudgeCount >= workflowLoopState.fixNudgeMaxPerRound) {
            appendWorkflowEvent({
              action: "workflow_stop",
              reason: "fix_completion_verification_exhausted",
              round: workflowLoopState.round,
              detail: "Fix completion format errors persist despite nudges",
              nearMiss: completion.nearMiss,
              nudgeCount: workflowLoopState.fixNudgeCount,
            });
            stopWorkflowLoop("Fix completion verification exhausted");
            return;
          }

          workflowLoopState.fixNudgeCount += 1;
          appendWorkflowEvent({
            action: "fix_completion_format_error_detected",
            round: workflowLoopState.round,
            nearMiss: completion.nearMiss,
            nudgeAttempt: workflowLoopState.fixNudgeCount,
          });

          workflowLoopState.engineerPauseUntilMs = Date.now() + 1500;
          await workflowSendInstructionWithRetry(
            cfg,
            workflowLoopState.engineerTerminalName,
            buildIdx030NearMissNudgePrompt(
              "FIX",
              completion.nearMiss,
              workflowLoopState.sessionNonce,
              workflowLoopState.idxName || "Idx-XXX",
              undefined
            ),
          );
          return;
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

    // Gate marker parsing until we see the end-of-prompt sentinel.
    if (!workflowLoopState.qaSeenPromptSentinel) {
      const sentinel = String(workflowLoopState.qaPromptSentinel || "").trim();
      if (!sentinel) {
        // Fallback: if no sentinel was set, proceed as before.
        workflowLoopState.qaSeenPromptSentinel = true;
      } else {
        const idx = workflowLoopState.qaMarkerBuf.lastIndexOf(sentinel);
        if (idx === -1) return;

        workflowLoopState.qaSeenPromptSentinel = true;
        appendWorkflowEvent({
          action: "qa_prompt_sentinel_seen",
          round: workflowLoopState.round,
          sentinel,
        });
        workflowLoopState.qaMarkerBuf = workflowLoopState.qaMarkerBuf
          .slice(idx + sentinel.length)
          .trimStart();
      }
    }

    // Wrong-marker detection (QA 輸出 Engineer/Fix markers)
    const wrongEngineerDone = hasCompletionMarker(workflowLoopState.qaMarkerBuf, WORKFLOW_MARKER_NAMES.engineerDone);
    const wrongFixDone = hasCompletionMarker(workflowLoopState.qaMarkerBuf, WORKFLOW_MARKER_NAMES.fixDone);
    if (wrongEngineerDone || wrongFixDone) {
      if (!workflowLoopState.qaTerminalName) return;

      if (workflowLoopState.qaNudgeCount >= workflowLoopState.qaNudgeMaxPerRound) {
        appendWorkflowEvent({
          action: "workflow_stop",
          reason: "qa_completion_unstable",
          round: workflowLoopState.round,
          detail: "QA repeatedly output wrong markers despite corrections",
          wrongEngineerDone,
          wrongFixDone,
          nudgeCount: workflowLoopState.qaNudgeCount,
        });
        stopWorkflowLoop("QA completion unstable (wrong markers)");
        return;
      }

      workflowLoopState.qaNudgeCount += 1;
      workflowLoopState.qaWrongMarkerNudgedRound = workflowLoopState.round;
      appendWorkflowEvent({
        action: "qa_wrong_marker_detected",
        round: workflowLoopState.round,
        wrongEngineerDone,
        wrongFixDone,
        nudgeAttempt: workflowLoopState.qaNudgeCount,
      });

      const wrongMarkerType = wrongEngineerDone ? "ENGINEER_DONE" : "FIX_DONE";
      const sentinel = generatePromptSentinel(
        "qa_corrective",
        workflowLoopState.round,
        workflowLoopState.qaNudgeCount,
      );
      workflowLoopState.qaPromptSentinel = sentinel;
      workflowLoopState.qaSeenPromptSentinel = false;
      workflowLoopState.qaPauseUntilMs = Date.now() + 1500;
      await workflowSendInstructionWithRetry(
        cfg,
        workflowLoopState.qaTerminalName,
        buildQaCorrectivePrompt(wrongMarkerType, sentinel),
      );
      return;
    }

    // Completion / near-miss detection (Idx-030 SPEC)
    const completion = detectCompletionWithIdx030Format(
      workflowLoopState.qaMarkerBuf,
      "QA",
      workflowLoopState.sessionNonce,
      workflowLoopState.idxName || "Idx-XXX"
    );

    if (!completion.ok) {
      if (completion.nearMiss) {
        if (!workflowLoopState.qaTerminalName) return;

        if (workflowLoopState.qaNudgeCount >= workflowLoopState.qaNudgeMaxPerRound) {
          appendWorkflowEvent({
            action: "workflow_stop",
            reason: "qa_completion_verification_exhausted",
            round: workflowLoopState.round,
            detail: "QA completion format errors persist despite nudges",
            nearMiss: completion.nearMiss,
            nudgeCount: workflowLoopState.qaNudgeCount,
          });
          stopWorkflowLoop("QA completion verification exhausted");
          return;
        }

        workflowLoopState.qaNudgeCount += 1;
        appendWorkflowEvent({
          action: "qa_completion_format_error_detected",
          format: "idx030",
          round: workflowLoopState.round,
          nearMiss: completion.nearMiss,
          nudgeAttempt: workflowLoopState.qaNudgeCount,
        });

        const sentinel = generatePromptSentinel(
          "qa_nudge",
          workflowLoopState.round,
          workflowLoopState.qaNudgeCount,
        );
        workflowLoopState.qaPromptSentinel = sentinel;
        workflowLoopState.qaSeenPromptSentinel = false;
        workflowLoopState.qaPauseUntilMs = Date.now() + 1500;
        await workflowSendInstructionWithRetry(
          cfg,
          workflowLoopState.qaTerminalName,
          buildIdx030NearMissNudgePrompt(
            "QA",
            completion.nearMiss,
            workflowLoopState.sessionNonce,
            workflowLoopState.idxName || "Idx-XXX",
            sentinel
          ),
        );
        return;
      }

      return;
    }

    const qaResult = completion.result;
    appendWorkflowEvent({
      action: qaResult === "PASS" ? "qa_pass_detected" : "qa_fail_detected",
      format: "idx030",
      timestamp: completion.timestamp,
      nonce: completion.nonce,
      taskId: completion.taskId,
      result: qaResult,
    });

    if (qaResult === "PASS") {
      logLine("[workflow] detected QA PASS (Idx-030 format)");
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

    logLine("[workflow] detected QA FAIL (Idx-030 format)");

    if (workflowLoopState.round >= workflowLoopState.maxRounds) {
      stopWorkflowLoop("FAIL (max rounds reached)");
      return;
    }

    const qaSummary = fs.existsSync(workflowLoopState.qaLogAbs)
      ? fs.readFileSync(workflowLoopState.qaLogAbs, "utf8")
      : "";

    workflowLoopState.phase = WORKFLOW_PHASE.waitFixDone;
    workflowLoopState.fixNudgeCount = 0; // Reset fix nudge counter
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

  // Idx-030 Fix: Unify with startWorkflowLoopCore to ensure nonce/env/state consistency
  const workflowRunId = `wf_${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}_${crypto
    .randomBytes(3)
    .toString("hex")}`;

  try {
    await context.workspaceState.update(WORKFLOW_STATE_KEYS.workflowRunId, workflowRunId);
    await context.workspaceState.update(WORKFLOW_STATE_KEYS.planId, normalizedIdx || "");
    await context.workspaceState.update(WORKFLOW_STATE_KEYS.state, "starting");
    await context.workspaceState.update(WORKFLOW_STATE_KEYS.startedAtIso, new Date().toISOString());
  } catch {
    // ignore
  }

  const result = await startWorkflowLoopCore(context, {
    engineerTerminalName: engineerPick.label,
    qaTerminalName: qaPick.label,
    taskDescription: taskDescription.trim(),
    idxName: normalizedIdx,
    workflowRunId,
  });

  vscode.window.showInformationMessage(
    `Workflow loop started. Logs: ${result.engineerRawLogDisplay}, ${result.qaRawLogDisplay}`,
  );
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
  vscode.window
    .showWarningMessage(
      "IvyHouse Terminal Orchestrator 已棄用（DEPRECATED）。請改用 IvyHouse Terminal Injector + IvyHouse Terminal Monitor。",
    )
    .then(
      () => {
        // ignore
      },
      () => {
        // ignore
      },
    );
  logLine(
    `[activate] Proposed API onDidWriteTerminalData available: ${terminalDataWriteEventAvailable}`,
  );

  // Start localhost-only HTTP bridge server for Coordinator automation.
  try {
    startSendtextBridgeServer(context);
  } catch (err) {
    logLine(`[bridge] failed to start: ${String(err || "")}`);
  }

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

function stopSendtextBridgeServer() {
  const s = sendtextBridgeServer;
  sendtextBridgeServer = undefined;
  if (!s) return;
  try {
    s.close();
    logLine("[bridge] server stopped");
  } catch {
    // ignore
  }
}

function deactivate() {
  stopSendtextBridgeServer();
}

module.exports = {
  activate,
  deactivate,
};
