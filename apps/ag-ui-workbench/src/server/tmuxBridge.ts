import { execFile } from "node:child_process";
import type { IncomingMessage, ServerResponse } from "node:http";
import { promisify } from "node:util";
import { WebSocket } from "ws";

import {
  createTmuxPtyAdapterFactory,
  tmuxAttachEnvironment,
  TmuxPtyBackendError,
  type TmuxAttachMode,
  type TmuxPtyAdapter,
  type TmuxPtyAdapterFactory,
} from "./tmuxPtyAdapter";

const execFileAsync = promisify(execFile);
export const TMUX_PREFIX = "/__houmao_tmux";
const MAX_SESSION_NAME_LENGTH = 256;
const TMUX_FIXTURE_ENV = "HOUMAO_AG_UI_WORKBENCH_TMUX_FIXTURE";
const PTY_NEWLINE_FIXTURE_SESSION = "pty-newline-fixture";
const PTY_NEWLINE_STALE_MARKER = "STALE_EDGE_REGION";
const PTY_NEWLINE_FIXTURE_OUTPUT = `\x1b[2J\x1b[Hfresh${PTY_NEWLINE_STALE_MARKER}\n\x1b[1A\x1b[1Kshort\r\npty-newline-fixture-complete\r\n`;

type AttachMode = TmuxAttachMode;

interface TmuxSessionRow {
  sessionName: string;
  windowCount: number;
  attached: boolean;
  createdAtUtc: string;
}

interface TmuxResizeRecord {
  cols: number;
  rows: number;
}

interface FixtureAttachmentSnapshot {
  sessionName: string;
  mode: AttachMode;
  attachCols: number;
  attachRows: number;
  resizes: TmuxResizeRecord[];
}

let fixtureSessionRows: TmuxSessionRow[] | null = null;
let fixtureAttachments: FixtureAttachmentSnapshot[] = [];

interface ClientAttachMessage {
  type: "attach";
  sessionName: string;
  mode: AttachMode;
  cols?: number;
  rows?: number;
}

interface ClientInputMessage {
  type: "input";
  data: string;
}

interface ClientResizeMessage {
  type: "resize";
  cols: number;
  rows: number;
}

interface ClientScrollMessage {
  type: "scroll";
  direction: "up" | "down";
  lines: number;
}

interface ClientCloseMessage {
  type: "close";
}

type ClientMessage =
  | ClientAttachMessage
  | ClientInputMessage
  | ClientResizeMessage
  | ClientScrollMessage
  | ClientCloseMessage;

type TmuxCommandRunner = (file: string, args: string[]) => Promise<unknown>;

export interface TmuxAttachSocketOptions {
  ptyAdapterFactory?: TmuxPtyAdapterFactory;
}

export async function handleTmuxHttpRequest(req: IncomingMessage, res: ServerResponse): Promise<void> {
  const requestUrl = new URL(req.url ?? "/", "http://127.0.0.1");
  if (req.method === "GET" && requestUrl.pathname === "/status") {
    if (tmuxFixtureEnabled()) {
      sendJson(res, 200, {
        status: "ready",
        tmuxAvailable: true,
        fixture: true,
        routes: [
          `GET ${TMUX_PREFIX}/status`,
          `GET ${TMUX_PREFIX}/sessions`,
          `WS ${TMUX_PREFIX}/attach`,
          `POST ${TMUX_PREFIX}/fixture/reset`,
          `GET ${TMUX_PREFIX}/fixture/attachments`,
          `DELETE ${TMUX_PREFIX}/fixture/sessions/{sessionName}`,
        ],
      });
      return;
    }
    const availability = await tmuxAvailability();
    sendJson(res, 200, {
      status: availability.available ? "ready" : "unavailable",
      tmuxAvailable: availability.available,
      detail: availability.detail,
      routes: [
        `GET ${TMUX_PREFIX}/status`,
        `GET ${TMUX_PREFIX}/sessions`,
        `WS ${TMUX_PREFIX}/attach`,
      ],
    });
    return;
  }
  if (req.method === "GET" && requestUrl.pathname === "/sessions") {
    const sessions = await listTmuxSessions();
    sendJson(res, 200, sessions);
    return;
  }
  if (tmuxFixtureEnabled() && req.method === "POST" && requestUrl.pathname === "/fixture/reset") {
    resetFixtureSessions();
    sendJson(res, 200, {
      status: "ready",
      sessions: fixtureSessions(),
      attachments: fixtureAttachmentSnapshots(),
    });
    return;
  }
  if (tmuxFixtureEnabled() && req.method === "GET" && requestUrl.pathname === "/fixture/attachments") {
    sendJson(res, 200, {
      status: "ready",
      attachments: fixtureAttachmentSnapshots(),
    });
    return;
  }
  if (
    tmuxFixtureEnabled() &&
    req.method === "DELETE" &&
    requestUrl.pathname.startsWith("/fixture/sessions/")
  ) {
    const sessionName = decodeURIComponent(
      requestUrl.pathname.slice("/fixture/sessions/".length),
    );
    const removed = removeFixtureSession(sessionName);
    sendJson(res, 200, {
      status: removed ? "removed" : "missing",
      sessions: fixtureSessions(),
      attachments: fixtureAttachmentSnapshots(),
    });
    return;
  }
  sendJson(res, 404, {
    code: "tmux_route_not_found",
    detail: "Tmux bridge route not found.",
  });
}

async function listTmuxSessions(): Promise<{
  status: "ready" | "unavailable" | "error";
  tmuxAvailable: boolean;
  sessions: TmuxSessionRow[];
  detail?: string;
}> {
  if (tmuxFixtureEnabled()) {
    return {
      status: "ready",
      tmuxAvailable: true,
      sessions: fixtureSessions(),
    };
  }
  const availability = await tmuxAvailability();
  if (!availability.available) {
    return {
      status: "unavailable",
      tmuxAvailable: false,
      sessions: [],
      detail: availability.detail,
    };
  }
  try {
    const { stdout } = await execFileAsync("tmux", [
      "list-sessions",
      "-F",
      "#{session_name}\t#{session_windows}\t#{session_attached}\t#{session_created}",
    ]);
    return {
      status: "ready",
      tmuxAvailable: true,
      sessions: stdout
        .split("\n")
        .map((line) => line.trimEnd())
        .filter(Boolean)
        .map(parseSessionLine)
        .filter((session): session is TmuxSessionRow => session !== null),
    };
  } catch (error) {
    const message = errorMessage(error);
    if (message.includes("no server running") || message.includes("failed to connect to server")) {
      return {
        status: "ready",
        tmuxAvailable: true,
        sessions: [],
      };
    }
    return {
      status: "error",
      tmuxAvailable: true,
      sessions: [],
      detail: message || "Failed to list tmux sessions.",
    };
  }
}

function parseSessionLine(line: string): TmuxSessionRow | null {
  const [sessionName, windowsRaw, attachedRaw, createdRaw] = line.split("\t");
  if (!sessionName) {
    return null;
  }
  const windowCount = Number.parseInt(windowsRaw ?? "0", 10);
  const attachedCount = Number.parseInt(attachedRaw ?? "0", 10);
  const createdSeconds = Number.parseInt(createdRaw ?? "0", 10);
  return {
    sessionName,
    windowCount: Number.isFinite(windowCount) ? windowCount : 0,
    attached: Number.isFinite(attachedCount) && attachedCount > 0,
    createdAtUtc:
      Number.isFinite(createdSeconds) && createdSeconds > 0
        ? new Date(createdSeconds * 1000).toISOString()
        : "",
  };
}

async function tmuxAvailability(): Promise<{ available: boolean; detail?: string }> {
  try {
    await execFileAsync("tmux", ["-V"]);
    return { available: true };
  } catch (error) {
    return {
      available: false,
      detail: errorMessage(error) || "tmux is not available on this host.",
    };
  }
}

export function handleTmuxAttachSocket(ws: WebSocket, options: TmuxAttachSocketOptions = {}): void {
  if (tmuxFixtureEnabled()) {
    handleFixtureTmuxAttachSocket(ws);
    return;
  }
  const ptyAdapterFactory = options.ptyAdapterFactory ?? createTmuxPtyAdapterFactory();
  let attachedMode: AttachMode | null = null;
  let sessionName: string | null = null;
  let terminal: TmuxPtyAdapter | null = null;
  let cleanupDone = false;
  let messageQueue = Promise.resolve();

  const cleanup = () => {
    if (cleanupDone) {
      return;
    }
    cleanupDone = true;
    const current = terminal;
    const currentSessionName = sessionName;
    const currentAttachPid = current?.pid;
    terminal = null;
    sessionName = null;
    attachedMode = null;
    if (currentSessionName) {
      void detachTmuxAttachClient(currentSessionName, currentAttachPid);
    }
    if (current) {
      try {
        current.kill();
      } catch {
        // The attach process may already be gone.
      }
    }
  };

  ws.on("message", (data) => {
    messageQueue = messageQueue
      .then(() => handleTmuxClientMessage(data.toString()))
      .catch((error: unknown) => {
        sendWs(ws, {
          type: "error",
          code: "tmux_internal_error",
          detail: errorMessage(error) || "Tmux bridge failed while handling a client message.",
        });
        ws.close(1011, "tmux bridge internal error");
      });
  });

  ws.on("close", cleanup);
  ws.on("error", cleanup);

  async function handleTmuxClientMessage(raw: string): Promise<void> {
    const message = parseClientMessage(raw);
    if (!message.ok) {
      sendWs(ws, {
        type: "error",
        code: "tmux_invalid_message",
        detail: message.detail,
      });
      return;
    }
    if (message.value.type === "attach") {
      if (terminal) {
        sendWs(ws, {
          type: "error",
          code: "tmux_already_attached",
          detail: "This socket is already attached to a tmux session.",
        });
        return;
      }
      const validation = validateAttachMessage(message.value);
      if (!validation.ok) {
        sendWs(ws, {
          type: "error",
          code: "tmux_attach_invalid",
          detail: validation.detail,
        });
        return;
      }
      try {
        const nextTerminal = await ptyAdapterFactory(message.value);
        if (cleanupDone) {
          nextTerminal.kill();
          return;
        }
        terminal = nextTerminal;
        attachedMode = message.value.mode;
        sessionName = message.value.sessionName;
      } catch (error) {
        sendWs(ws, {
          type: "error",
          code: tmuxAttachErrorCode(error),
          detail: errorMessage(error) || "Failed to attach tmux session.",
        });
        ws.close(1011, "tmux attach failed");
        return;
      }
      terminal.onData((chunk) => {
        sendWs(ws, {
          type: "output",
          data: chunk,
        });
      });
      terminal.onExit((event) => {
        const alreadyCleanedUp = cleanupDone;
        cleanup();
        if (alreadyCleanedUp) {
          return;
        }
        sendWs(ws, {
          type: "exit",
          exitCode: event.exitCode,
          signal: event.signal,
        });
        ws.close(1000, "tmux attach exited");
      });
      sendWs(ws, {
        type: "attached",
        sessionName: message.value.sessionName,
        mode: message.value.mode,
      });
      return;
    }
    if (!terminal) {
      sendWs(ws, {
        type: "error",
        code: "tmux_not_attached",
        detail: "Attach to a tmux session before sending terminal messages.",
      });
      return;
    }
    if (message.value.type === "input") {
      if (attachedMode === "read-only") {
        sendWs(ws, {
          type: "error",
          code: "tmux_read_only",
          detail: "Input is disabled for this read-only tmux attachment.",
        });
        return;
      }
      terminal.write(message.value.data);
      return;
    }
    if (message.value.type === "resize") {
      const validation = validateResizeMessage(message.value);
      if (!validation.ok) {
        sendWs(ws, {
          type: "error",
          code: "tmux_resize_invalid",
          detail: validation.detail,
        });
        return;
      }
      try {
        terminal.resize(validation.cols, validation.rows);
      } catch (error) {
        sendWs(ws, {
          type: "error",
          code: "tmux_resize_failed",
          detail: `Failed to resize tmux attachment: ${errorMessage(error) || "unknown error"}`,
        });
      }
      return;
    }
    if (message.value.type === "scroll") {
      if (!sessionName) {
        sendWs(ws, {
          type: "error",
          code: "tmux_not_attached",
          detail: "Attach to a tmux session before sending terminal messages.",
        });
        return;
      }
      void scrollTmuxAttachment(sessionName, message.value).catch((error: unknown) => {
        sendWs(ws, {
          type: "error",
          code: "tmux_scroll_failed",
          detail: `Failed to scroll tmux attachment: ${errorMessage(error) || "unknown error"}`,
        });
      });
      return;
    }
    cleanup();
    ws.close(1000, "client requested close");
  }
}

function tmuxAttachErrorCode(error: unknown): string {
  if (error instanceof TmuxPtyBackendError) {
    return error.code;
  }
  return "tmux_attach_failed";
}

function handleFixtureTmuxAttachSocket(ws: WebSocket): void {
  let attachedMode: AttachMode | null = null;
  let sessionName: string | null = null;
  let attachmentSnapshot: FixtureAttachmentSnapshot | null = null;
  ws.on("message", (data) => {
    const message = parseClientMessage(data.toString());
    if (!message.ok) {
      sendWs(ws, {
        type: "error",
        code: "tmux_invalid_message",
        detail: message.detail,
      });
      return;
    }
    if (message.value.type === "attach") {
      const attachMessage = message.value;
      const validation = validateAttachMessage(attachMessage);
      if (!validation.ok) {
        sendWs(ws, {
          type: "error",
          code: "tmux_attach_invalid",
          detail: validation.detail,
        });
        return;
      }
      const exists = fixtureSessions().some(
        (session) => session.sessionName === attachMessage.sessionName,
      );
      if (!exists) {
        sendWs(ws, {
          type: "error",
          code: "tmux_attach_failed",
          detail: `Fixture tmux session ${attachMessage.sessionName} does not exist.`,
        });
        return;
      }
      attachedMode = attachMessage.mode;
      sessionName = attachMessage.sessionName;
      attachmentSnapshot = {
        sessionName,
        mode: attachedMode,
        attachCols: safeDimension(attachMessage.cols, 80),
        attachRows: safeDimension(attachMessage.rows, 24),
        resizes: [],
      };
      fixtureAttachments.push(attachmentSnapshot);
      sendWs(ws, {
        type: "attached",
        sessionName,
        mode: attachedMode,
      });
      sendWs(ws, {
        type: "output",
        data: `fixture attached ${sessionName}\r\n`,
      });
      if (sessionName === PTY_NEWLINE_FIXTURE_SESSION) {
        sendWs(ws, {
          type: "output",
          data: PTY_NEWLINE_FIXTURE_OUTPUT,
        });
      }
      return;
    }
    if (!sessionName) {
      sendWs(ws, {
        type: "error",
        code: "tmux_not_attached",
        detail: "Attach to a tmux session before sending terminal messages.",
      });
      return;
    }
    if (message.value.type === "input") {
      if (attachedMode === "read-only") {
        sendWs(ws, {
          type: "error",
          code: "tmux_read_only",
          detail: "Input is disabled for this read-only tmux attachment.",
        });
        return;
      }
      if (message.value.data.includes("\u0004")) {
        removeFixtureSession(sessionName);
        sendWs(ws, {
          type: "output",
          data: `fixture session ${sessionName} exited\r\n`,
        });
        sendWs(ws, {
          type: "exit",
          exitCode: 0,
          signal: 0,
        });
        ws.close(1000, "fixture session exited");
        return;
      }
      sendWs(ws, {
        type: "output",
        data: `fixture input ${message.value.data}\r\n`,
      });
      return;
    }
    if (message.value.type === "resize") {
      const validation = validateResizeMessage(message.value);
      if (!validation.ok) {
        sendWs(ws, {
          type: "error",
          code: "tmux_resize_invalid",
          detail: validation.detail,
        });
        return;
      }
      attachmentSnapshot?.resizes.push({
        cols: validation.cols,
        rows: validation.rows,
      });
      sendWs(ws, {
        type: "output",
        data: `fixture resized ${sessionName} ${validation.cols}x${validation.rows}\r\n`,
      });
      return;
    }
    if (message.value.type === "scroll") {
      sendWs(ws, {
        type: "output",
        data: `fixture scrolled ${sessionName} ${message.value.direction} ${safeScrollLines(message.value.lines)}\r\n`,
      });
      return;
    }
    sendWs(ws, {
      type: "exit",
      exitCode: 0,
      signal: 0,
    });
    ws.close(1000, "fixture close");
  });
}

export { tmuxAttachEnvironment };

export async function detachTmuxAttachClient(
  sessionName: string,
  attachPid?: number,
  runner: TmuxCommandRunner = execFileAsync,
): Promise<void> {
  const target = sessionName.trim();
  if (!target) {
    return;
  }
  if (typeof attachPid !== "number" || !Number.isFinite(attachPid)) {
    return;
  }
  try {
    const listResult = await runner("tmux", [
      "list-clients",
      "-F",
      "#{client_pid}\t#{client_tty}\t#{session_name}",
      "-t",
      target,
    ]);
    const clientTarget = tmuxClientTargetForPid(listResult, attachPid, target);
    if (!clientTarget) {
      return;
    }
    await runner("tmux", ["detach-client", "-t", clientTarget]);
  } catch (error) {
    console.warn(
      `Failed to detach tmux attach client for session ${target}: ${errorMessage(error) || "unknown error"}`,
    );
  }
}

function tmuxClientTargetForPid(result: unknown, attachPid: number, sessionName: string): string | null {
  const stdout =
    result && typeof result === "object" && "stdout" in result
      ? String((result as { stdout?: unknown }).stdout ?? "")
      : "";
  for (const line of stdout.split("\n")) {
    const [pidRaw, clientTty, clientSessionName] = line.split("\t");
    const pid = Number.parseInt(pidRaw ?? "", 10);
    if (pid === attachPid && clientTty && clientSessionName === sessionName) {
      return clientTty;
    }
  }
  return null;
}

function validateAttachMessage(message: ClientAttachMessage): { ok: true } | { ok: false; detail: string } {
  const sessionName = message.sessionName.trim();
  if (!sessionName) {
    return { ok: false, detail: "Tmux session name is required." };
  }
  if (sessionName.length > MAX_SESSION_NAME_LENGTH || sessionName.includes("\0")) {
    return { ok: false, detail: "Tmux session name is invalid." };
  }
  if (message.mode !== "read-write" && message.mode !== "read-only") {
    return { ok: false, detail: "Tmux attachment mode must be read-write or read-only." };
  }
  message.sessionName = sessionName;
  return { ok: true };
}

function validateResizeMessage(
  message: ClientResizeMessage,
): { ok: true; cols: number; rows: number } | { ok: false; detail: string } {
  const cols = message.cols;
  const rows = message.rows;
  if (!validDimension(cols) || !validDimension(rows)) {
    return {
      ok: false,
      detail: "Tmux resize columns and rows must be finite numbers between 2 and 500.",
    };
  }
  return { ok: true, cols: Math.round(cols), rows: Math.round(rows) };
}

async function scrollTmuxAttachment(
  sessionName: string,
  message: ClientScrollMessage,
): Promise<void> {
  const lines = safeScrollLines(message.lines);
  if (message.direction === "up") {
    await execFileAsync("tmux", ["copy-mode", "-e", "-t", sessionName]);
    await execFileAsync("tmux", ["send-keys", "-X", "-N", String(lines), "-t", sessionName, "scroll-up"]);
    return;
  }
  const inMode = await tmuxPaneInMode(sessionName);
  if (!inMode) {
    return;
  }
  await execFileAsync("tmux", ["send-keys", "-X", "-N", String(lines), "-t", sessionName, "scroll-down"]);
}

async function tmuxPaneInMode(sessionName: string): Promise<boolean> {
  const { stdout } = await execFileAsync("tmux", [
    "display-message",
    "-p",
    "-t",
    sessionName,
    "#{pane_in_mode}",
  ]);
  return stdout.trim() === "1";
}

function parseClientMessage(raw: string): { ok: true; value: ClientMessage } | { ok: false; detail: string } {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return { ok: false, detail: "WebSocket message is not valid JSON." };
  }
  if (!parsed || typeof parsed !== "object") {
    return { ok: false, detail: "WebSocket message must be an object." };
  }
  const record = parsed as Record<string, unknown>;
  if (record.type === "attach") {
    return {
      ok: true,
      value: {
        type: "attach",
        sessionName: typeof record.sessionName === "string" ? record.sessionName : "",
        mode: record.mode === "read-only" ? "read-only" : "read-write",
        cols: typeof record.cols === "number" ? record.cols : undefined,
        rows: typeof record.rows === "number" ? record.rows : undefined,
      },
    };
  }
  if (record.type === "input") {
    return {
      ok: true,
      value: {
        type: "input",
        data: typeof record.data === "string" ? record.data : "",
      },
    };
  }
  if (record.type === "resize") {
    return {
      ok: true,
      value: {
        type: "resize",
        cols: typeof record.cols === "number" ? record.cols : Number.NaN,
        rows: typeof record.rows === "number" ? record.rows : Number.NaN,
      },
    };
  }
  if (record.type === "scroll") {
    return {
      ok: true,
      value: {
        type: "scroll",
        direction: record.direction === "down" ? "down" : "up",
        lines: typeof record.lines === "number" ? record.lines : 5,
      },
    };
  }
  if (record.type === "close") {
    return {
      ok: true,
      value: { type: "close" },
    };
  }
  return { ok: false, detail: "Unsupported WebSocket message type." };
}

function safeDimension(value: number | undefined, fallback: number): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 2) {
    return fallback;
  }
  return Math.max(2, Math.min(500, Math.round(value)));
}

function validDimension(value: number): boolean {
  return Number.isFinite(value) && value >= 2 && value <= 500;
}

function safeScrollLines(value: number): number {
  if (!Number.isFinite(value)) {
    return 5;
  }
  return Math.max(1, Math.min(200, Math.round(value)));
}

function sendWs(ws: WebSocket, payload: unknown): void {
  if (ws.readyState !== WebSocket.OPEN) {
    return;
  }
  ws.send(JSON.stringify(payload));
}

function sendJson(res: ServerResponse, status: number, payload: unknown): void {
  if (res.writableEnded) {
    return;
  }
  res.statusCode = status;
  res.setHeader("content-type", "application/json; charset=utf-8");
  res.end(JSON.stringify(payload));
}

function tmuxFixtureEnabled(): boolean {
  return process.env[TMUX_FIXTURE_ENV] === "1";
}

function fixtureSessions(): TmuxSessionRow[] {
  if (!fixtureSessionRows) {
    fixtureSessionRows = defaultFixtureSessions();
  }
  return fixtureSessionRows.map((session) => ({ ...session }));
}

function resetFixtureSessions(): void {
  fixtureSessionRows = defaultFixtureSessions();
  fixtureAttachments = [];
}

function removeFixtureSession(sessionName: string): boolean {
  if (!fixtureSessionRows) {
    resetFixtureSessions();
  }
  const before = fixtureSessionRows?.length ?? 0;
  fixtureSessionRows = (fixtureSessionRows ?? []).filter(
    (session) => session.sessionName !== sessionName,
  );
  return fixtureSessionRows.length !== before;
}

function defaultFixtureSessions(): TmuxSessionRow[] {
  return [
    {
      sessionName: "houmao-alpha",
      windowCount: 1,
      attached: false,
      createdAtUtc: "2026-06-09T12:05:48.000Z",
    },
    {
      sessionName: "utility-shell",
      windowCount: 2,
      attached: true,
      createdAtUtc: "2026-06-09T12:06:00.000Z",
    },
    {
      sessionName: PTY_NEWLINE_FIXTURE_SESSION,
      windowCount: 1,
      attached: false,
      createdAtUtc: "2026-06-09T12:06:12.000Z",
    },
  ];
}

function fixtureAttachmentSnapshots(): FixtureAttachmentSnapshot[] {
  return fixtureAttachments.map((attachment) => ({
    ...attachment,
    resizes: attachment.resizes.map((resize) => ({ ...resize })),
  }));
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return typeof error === "string" ? error : "";
}
