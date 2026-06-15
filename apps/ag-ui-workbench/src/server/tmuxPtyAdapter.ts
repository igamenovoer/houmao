export type TmuxAttachMode = "read-write" | "read-only";

export interface TmuxPtyAttachRequest {
  sessionName: string;
  mode: TmuxAttachMode;
  cols?: number;
  rows?: number;
}

export interface TmuxPtyExitEvent {
  exitCode: number | null;
  signal?: number | string | null;
}

export interface TmuxPtyAdapter {
  readonly pid?: number;
  write(data: string): void;
  resize(cols: number, rows: number): void;
  kill(): void;
  onData(listener: (data: string) => void): void;
  onExit(listener: (event: TmuxPtyExitEvent) => void): void;
}

export type TmuxPtyAdapterFactory = (request: TmuxPtyAttachRequest) => Promise<TmuxPtyAdapter>;

export class TmuxPtyBackendError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "TmuxPtyBackendError";
    this.code = code;
  }
}

interface NodePtyModule {
  spawn(file: string, args: string[], options: NodePtySpawnOptions): NodePtyProcess;
}

interface NodePtySpawnOptions {
  name: string;
  cols: number;
  rows: number;
  cwd?: string;
  env: NodeJS.ProcessEnv;
}

interface NodePtyProcess {
  readonly pid: number;
  write(data: string): void;
  resize(cols: number, rows: number): void;
  kill(): void;
  onData(listener: (data: string) => void): unknown;
  onExit(listener: (event: TmuxPtyExitEvent) => void): unknown;
}

type NodePtyLoader = () => Promise<NodePtyModule>;

interface BunRuntimeLike {
  version?: string;
  Terminal?: BunTerminalConstructor;
  spawn?: (command: string[], options: BunSpawnOptions) => BunSubprocessLike;
}

interface BunTerminalConstructor {
  new (options: BunTerminalOptions): BunTerminalLike;
}

interface BunTerminalOptions {
  cols: number;
  rows: number;
  name: string;
  data(terminal: BunTerminalLike, data: BunTerminalData): void;
}

type BunTerminalData = string | ArrayBuffer | ArrayBufferView;

interface BunSpawnOptions {
  terminal: BunTerminalLike;
  cwd?: string;
  env: NodeJS.ProcessEnv;
}

interface BunTerminalLike {
  write(data: string | ArrayBuffer | ArrayBufferView): number | void;
  resize(cols: number, rows: number): void;
  close(): void;
}

interface BunSubprocessLike {
  readonly pid?: number;
  readonly exited: Promise<number>;
  readonly exitCode?: number | null;
  readonly signalCode?: number | string | null;
  readonly terminal?: BunTerminalLike | null;
  kill(signal?: number | string): void;
}

export interface TmuxPtyAdapterFactoryOptions {
  bunRuntime?: BunRuntimeLike | null;
  nodePtyLoader?: NodePtyLoader;
  env?: NodeJS.ProcessEnv;
  cwd?: string;
}

const DEFAULT_COLS = 80;
const DEFAULT_ROWS = 24;

export function createTmuxPtyAdapterFactory(
  options: TmuxPtyAdapterFactoryOptions = {},
): TmuxPtyAdapterFactory {
  return (request) => createTmuxPtyAdapter(request, options);
}

export async function createTmuxPtyAdapter(
  request: TmuxPtyAttachRequest,
  options: TmuxPtyAdapterFactoryOptions = {},
): Promise<TmuxPtyAdapter> {
  const bunRuntime = options.bunRuntime === undefined ? detectBunRuntime() : options.bunRuntime;
  if (bunRuntime) {
    return createBunTerminalAdapter(request, bunRuntime, options);
  }
  return createNodePtyAdapter(request, options);
}

export function tmuxAttachEnvironment(source: NodeJS.ProcessEnv = process.env): NodeJS.ProcessEnv {
  const { TMUX: _tmux, TMUX_PANE: _tmuxPane, ...env } = source;
  return { ...env, TERM: "xterm-256color" };
}

async function createNodePtyAdapter(
  request: TmuxPtyAttachRequest,
  options: TmuxPtyAdapterFactoryOptions,
): Promise<TmuxPtyAdapter> {
  let pty: NodePtyModule;
  try {
    pty = await (options.nodePtyLoader ?? defaultNodePtyLoader)();
  } catch (error) {
    throw new TmuxPtyBackendError(
      "tmux_pty_backend_unavailable",
      `Node tmux PTY backend could not load node-pty: ${errorMessage(error) || "unknown error"}`,
    );
  }

  try {
    const ptyProcess = pty.spawn("tmux", tmuxAttachArgs(request), {
      name: "xterm-256color",
      cols: safeDimension(request.cols, DEFAULT_COLS),
      rows: safeDimension(request.rows, DEFAULT_ROWS),
      cwd: options.cwd ?? processHome(),
      env: tmuxAttachEnvironment(options.env ?? process.env),
    });
    return new NodePtyAdapter(ptyProcess);
  } catch (error) {
    throw new TmuxPtyBackendError(
      "tmux_attach_failed",
      errorMessage(error) || "Failed to attach tmux session.",
    );
  }
}

function createBunTerminalAdapter(
  request: TmuxPtyAttachRequest,
  bun: BunRuntimeLike,
  options: TmuxPtyAdapterFactoryOptions,
): TmuxPtyAdapter {
  if (typeof bun.Terminal !== "function" || typeof bun.spawn !== "function") {
    throw new TmuxPtyBackendError(
      "tmux_pty_backend_unavailable",
      "Bun tmux PTY backend requires Bun.Terminal and Bun.spawn terminal support.",
    );
  }

  try {
    const adapter = new BunTerminalAdapter();
    const terminal = new bun.Terminal({
      name: "xterm-256color",
      cols: safeDimension(request.cols, DEFAULT_COLS),
      rows: safeDimension(request.rows, DEFAULT_ROWS),
      data: (_terminal, data) => adapter.emitData(decodeTerminalData(data)),
    });
    const subprocess = bun.spawn(tmuxAttachCommand(request), {
      terminal,
      cwd: options.cwd ?? processHome(),
      env: tmuxAttachEnvironment(options.env ?? process.env),
    });
    adapter.attach(terminal, subprocess);
    return adapter;
  } catch (error) {
    if (error instanceof TmuxPtyBackendError) {
      throw error;
    }
    throw new TmuxPtyBackendError(
      "tmux_attach_failed",
      errorMessage(error) || "Failed to attach tmux session through Bun.Terminal.",
    );
  }
}

async function defaultNodePtyLoader(): Promise<NodePtyModule> {
  const module = await import("node-pty");
  return module as NodePtyModule;
}

class NodePtyAdapter implements TmuxPtyAdapter {
  readonly pid: number;
  private readonly process: NodePtyProcess;

  constructor(process: NodePtyProcess) {
    this.process = process;
    this.pid = process.pid;
  }

  write(data: string): void {
    this.process.write(data);
  }

  resize(cols: number, rows: number): void {
    this.process.resize(cols, rows);
  }

  kill(): void {
    this.process.kill();
  }

  onData(listener: (data: string) => void): void {
    this.process.onData(listener);
  }

  onExit(listener: (event: TmuxPtyExitEvent) => void): void {
    this.process.onExit(listener);
  }
}

class BunTerminalAdapter implements TmuxPtyAdapter {
  private terminal: BunTerminalLike | null = null;
  private subprocess: BunSubprocessLike | null = null;
  private readonly dataListeners: Array<(data: string) => void> = [];
  private readonly exitListeners: Array<(event: TmuxPtyExitEvent) => void> = [];
  private exitEvent: TmuxPtyExitEvent | null = null;

  get pid(): number | undefined {
    return this.subprocess?.pid;
  }

  attach(terminal: BunTerminalLike, subprocess: BunSubprocessLike): void {
    this.terminal = terminal;
    this.subprocess = subprocess;
    void subprocess.exited
      .then((exitCode) => {
        this.emitExit({
          exitCode: normalizeExitCode(subprocess.exitCode, exitCode),
          signal: subprocess.signalCode ?? null,
        });
      })
      .catch((error: unknown) => {
        console.warn(`Bun tmux PTY process exit tracking failed: ${errorMessage(error) || "unknown error"}`);
        this.emitExit({
          exitCode: 1,
          signal: null,
        });
      });
  }

  write(data: string): void {
    this.requireTerminal().write(data);
  }

  resize(cols: number, rows: number): void {
    this.requireTerminal().resize(cols, rows);
  }

  kill(): void {
    const subprocess = this.subprocess;
    const terminal = this.terminal;
    try {
      subprocess?.kill();
    } finally {
      terminal?.close();
    }
  }

  onData(listener: (data: string) => void): void {
    this.dataListeners.push(listener);
  }

  onExit(listener: (event: TmuxPtyExitEvent) => void): void {
    this.exitListeners.push(listener);
    if (this.exitEvent) {
      listener(this.exitEvent);
    }
  }

  emitData(data: string): void {
    for (const listener of this.dataListeners) {
      listener(data);
    }
  }

  private emitExit(event: TmuxPtyExitEvent): void {
    if (this.exitEvent) {
      return;
    }
    this.exitEvent = event;
    for (const listener of this.exitListeners) {
      listener(event);
    }
  }

  private requireTerminal(): BunTerminalLike {
    if (!this.terminal) {
      throw new Error("Bun terminal is not attached.");
    }
    return this.terminal;
  }
}

function detectBunRuntime(): BunRuntimeLike | null {
  const maybeGlobal = globalThis as typeof globalThis & { Bun?: BunRuntimeLike };
  const bun = maybeGlobal.Bun;
  if (!bun || typeof bun !== "object") {
    return null;
  }
  if (typeof bun.version !== "string" && typeof bun.Terminal !== "function") {
    return null;
  }
  return bun;
}

function tmuxAttachCommand(request: TmuxPtyAttachRequest): string[] {
  return ["tmux", ...tmuxAttachArgs(request)];
}

function tmuxAttachArgs(request: TmuxPtyAttachRequest): string[] {
  const args = ["attach-session"];
  if (request.mode === "read-only") {
    args.push("-r");
  }
  args.push("-t", request.sessionName);
  return args;
}

function safeDimension(value: number | undefined, fallback: number): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 2) {
    return fallback;
  }
  return Math.max(2, Math.min(500, Math.round(value)));
}

function processHome(): string | undefined {
  return process.env.HOME;
}

function normalizeExitCode(primary: number | null | undefined, fallback: number): number | null {
  if (typeof primary === "number" && Number.isFinite(primary)) {
    return primary;
  }
  return Number.isFinite(fallback) ? fallback : null;
}

function decodeTerminalData(data: BunTerminalData): string {
  if (typeof data === "string") {
    return data;
  }
  if (data instanceof ArrayBuffer) {
    return new TextDecoder().decode(data);
  }
  return new TextDecoder().decode(data);
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}
