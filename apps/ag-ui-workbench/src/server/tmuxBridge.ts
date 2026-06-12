import { execFile } from "node:child_process";
import type { IncomingMessage, ServerResponse } from "node:http";
import { promisify } from "node:util";
import * as pty from "node-pty";
import { WebSocket } from "ws";

const execFileAsync = promisify(execFile);
export const TMUX_PREFIX = "/__houmao_tmux";
const MAX_SESSION_NAME_LENGTH = 256;
const TMUX_FIXTURE_ENV = "HOUMAO_AG_UI_WORKBENCH_TMUX_FIXTURE";

type AttachMode = "read-write" | "read-only";

interface TmuxSessionRow {
  sessionName: string;
  windowCount: number;
  attached: boolean;
  createdAtUtc: string;
}

let fixtureSessionRows: TmuxSessionRow[] | null = null;

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

interface ClientCloseMessage {
  type: "close";
}

type ClientMessage = ClientAttachMessage | ClientInputMessage | ClientResizeMessage | ClientCloseMessage;

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

export function handleTmuxAttachSocket(ws: WebSocket): void {
  if (tmuxFixtureEnabled()) {
    handleFixtureTmuxAttachSocket(ws);
    return;
  }
  let attachedMode: AttachMode | null = null;
  let terminal: pty.IPty | null = null;

  const cleanup = () => {
    const current = terminal;
    terminal = null;
    if (current) {
      try {
        current.kill();
      } catch {
        // The attach process may already be gone.
      }
    }
  };

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
        terminal = spawnTmuxAttach(message.value);
        attachedMode = message.value.mode;
      } catch (error) {
        sendWs(ws, {
          type: "error",
          code: "tmux_attach_failed",
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
        sendWs(ws, {
          type: "exit",
          exitCode: event.exitCode,
          signal: event.signal,
        });
        terminal = null;
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
      terminal.resize(safeDimension(message.value.cols, 80), safeDimension(message.value.rows, 24));
      return;
    }
    cleanup();
    ws.close(1000, "client requested close");
  });

  ws.on("close", cleanup);
  ws.on("error", cleanup);
}

function handleFixtureTmuxAttachSocket(ws: WebSocket): void {
  let attachedMode: AttachMode | null = null;
  let sessionName: string | null = null;
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
      sendWs(ws, {
        type: "attached",
        sessionName,
        mode: attachedMode,
      });
      sendWs(ws, {
        type: "output",
        data: `fixture attached ${sessionName}\r\n`,
      });
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

function spawnTmuxAttach(message: ClientAttachMessage): pty.IPty {
  const args = ["attach-session"];
  if (message.mode === "read-only") {
    args.push("-r");
  }
  args.push("-t", message.sessionName);
  return pty.spawn("tmux", args, {
    name: "xterm-256color",
    cols: safeDimension(message.cols, 80),
    rows: safeDimension(message.rows, 24),
    cwd: process.env.HOME,
    env: tmuxAttachEnvironment(process.env),
  });
}

export function tmuxAttachEnvironment(
  source: NodeJS.ProcessEnv = process.env,
): NodeJS.ProcessEnv {
  const { TMUX: _tmux, TMUX_PANE: _tmuxPane, ...env } = source;
  return { ...env, TERM: "xterm-256color" };
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
        cols: typeof record.cols === "number" ? record.cols : 80,
        rows: typeof record.rows === "number" ? record.rows : 24,
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
  ];
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return typeof error === "string" ? error : "";
}
