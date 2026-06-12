# How to run a tmux PTY bridge across Node and Bun

## Problem

Use this hint when a browser terminal or tmux tab works under Node but immediately ends under Bun with a message such as `[tmux] attachment ended`. In `apps/ag-ui-workbench`, the failing path was the Fastify tmux bridge spawning `tmux attach-session` through `node-pty`. The same `tmux attach-session` stayed alive under Node, but under Bun 1.3.13 the `node-pty` child exited immediately with no useful terminal output.

This is a runtime PTY backend problem, not a tmux session problem, when these checks hold:

```bash
# tmux itself can see the session
tmux has-session -t <session-name>

# the workbench can list sessions
curl -sS http://127.0.0.1:5177/__houmao_tmux/sessions

# Node can keep a node-pty child alive, but Bun cannot
node -e 'const pty=require("node-pty"); const t=pty.spawn("bash",["-lc","echo ok; sleep 2"],{}); t.onData(d=>process.stdout.write(d)); t.onExit(e=>console.log(e));'
bun -e 'import pty from "node-pty"; const t=pty.spawn("bash",["-lc","echo ok; sleep 2"],{}); t.onData(d=>process.stdout.write(d)); t.onExit(e=>console.log(e));'
```

## Short Answer

Do not try to make `node-pty` the single PTY backend across Node and Bun. `node-pty` documents Node/Electron as its supported runtime, and upstream Bun and `node-pty` issues show Bun compatibility failures. Keep the workbench server on Node when using the current `node-pty` bridge, or branch behind a tiny internal PTY interface:

- Node backend: use `node-pty`.
- Bun 1.3.5 or newer backend: use Bun's first-party `Bun.Terminal` / `Bun.spawn(..., { terminal })`.
- Fallback for older or unstable Bun: run a small Node PTY sidecar and connect to it from the Bun server over WebSocket or IPC.

In this workspace, the immediate operational fix was to restart the workbench server under Node:

```bash
cd apps/ag-ui-workbench
./node_modules/.bin/esbuild src/server/cli.ts --bundle --platform=node --format=esm --packages=external --outfile=src/server/.manual-workbench-server.mjs
node src/server/.manual-workbench-server.mjs --dev --host 127.0.0.1 --port 5177
```

That fixes the current `node-pty` implementation. A durable cross-runtime fix should add a backend abstraction rather than relying on the generated manual wrapper.

## Steps

1. Prove the failure is in the PTY backend:

```bash
cd apps/ag-ui-workbench

bun -e 'import pty from "node-pty"; const t=pty.spawn("bash",["-lc","echo hello; tty; sleep 2; echo done"],{name:"xterm-256color",cols:80,rows:24,cwd:process.env.HOME,env:{...process.env,TERM:"xterm-256color"}}); t.onData(d=>process.stdout.write(d)); t.onExit(e=>{console.log("EXIT", e); process.exit(0)});'

node -e 'const pty=require("node-pty"); const t=pty.spawn("bash",["-lc","echo hello; tty; sleep 2; echo done"],{name:"xterm-256color",cols:80,rows:24,cwd:process.env.HOME,env:{...process.env,TERM:"xterm-256color"}}); t.onData(d=>process.stdout.write(d)); t.onExit(e=>{console.log("EXIT", e); process.exit(0)});'
```

2. If Bun exits immediately and Node prints terminal output, keep the current server on Node or implement runtime branching.

3. Introduce one internal interface so the rest of the tmux bridge does not care which runtime owns the PTY:

```ts
interface WorkbenchPty {
  write(data: string | Uint8Array): void;
  resize(cols: number, rows: number): void;
  kill(): void;
  onData(listener: (data: string | Uint8Array) => void): void;
  onExit(listener: (event: { exitCode: number | null; signal?: string | number | null }) => void): void;
}
```

4. Use `node-pty` only in the Node implementation:

```ts
import * as pty from "node-pty";

const term = pty.spawn("tmux", ["attach-session", "-t", sessionName], {
  name: "xterm-256color",
  cols,
  rows,
  cwd: process.env.HOME,
  env: tmuxAttachEnvironment(process.env),
});
```

5. Use `Bun.Terminal` only in the Bun implementation:

```ts
const terminal = new Bun.Terminal({
  cols,
  rows,
  data(_terminal, data) {
    onData(new TextDecoder().decode(data));
  },
});

const proc = Bun.spawn(["tmux", "attach-session", "-t", sessionName], {
  terminal,
  cwd: process.env.HOME,
  env: tmuxAttachEnvironment(process.env),
});

proc.exited.then((exitCode) => onExit({ exitCode }));
```

6. Preserve the current tmux environment cleanup in both backends. Strip `TMUX` and `TMUX_PANE` from the child environment and set `TERM=xterm-256color`, otherwise nested tmux behavior can be surprising.

7. Keep the browser and xterm.js code unchanged. The browser side only needs output bytes, input bytes, resize, and close events.

## Examples

Runtime dispatch can be as small as:

```ts
function isBunRuntime(): boolean {
  return typeof Bun !== "undefined" && Boolean(Bun.version);
}

function spawnTmuxPty(message: ClientAttachMessage): WorkbenchPty {
  if (isBunRuntime() && typeof Bun.Terminal === "function") {
    return spawnBunTerminalTmux(message);
  }
  return spawnNodePtyTmux(message);
}
```

Do not import `node-pty` at module top level in code that may run under Bun. Load the Node backend dynamically inside the Node branch, or split backends into separate files and import only the selected backend.

## Local Findings

Observed in this repo on June 12, 2026:

- `bun --version` was `1.3.13`.
- `node --version` was `v25.9.0`.
- `node-pty` under Bun exited immediately for both `bash` and `tmux attach-session`.
- `node-pty` under Node kept `bash` and `tmux attach-session` alive and streamed terminal output.
- `Bun.Terminal` under Bun successfully attached to a tmux probe session and emitted tmux screen data.

## Source Notes

- Bun's Node.js compatibility page says Bun aims for Node compatibility but still lists `node:child_process` gaps, so parity cannot be assumed for native PTY behavior.
- Bun's Node-API page says Bun implements most, not all, of Node-API. A native addon can load and still fail at runtime if it relies on deeper Node/V8/libuv behavior.
- `node-pty`'s README states Node.JS 16 or Electron 19 is required. It does not list Bun as a supported runtime.
- `microsoft/node-pty` issue 632 reports Bun support problems and is closed as out of scope.
- `oven-sh/bun` issue 7362 reports `node-pty` cannot run from Bun and is closed as not planned.
- `microsoft/node-pty` issue 748 reports a later beta/N-API Bun failure at spawn time.
- Bun 1.3.5 introduced first-party PTY support through `Bun.Terminal`, and current Bun child-process docs describe `terminal`, `write`, `resize`, `close`, and lifecycle behavior.

## Sources

- Bun Node.js compatibility: https://bun.com/docs/runtime/nodejs-compat
- Bun Node-API compatibility: https://bun.com/docs/runtime/node-api
- Bun child process terminal support: https://bun.com/docs/runtime/child-process
- Bun Terminal API reference: https://bun.com/reference/bun/Terminal
- Bun 1.3.5 release notes: https://bun.com/blog/bun-v1.3.5
- node-pty README: https://github.com/microsoft/node-pty
- node-pty Bun support issue 632: https://github.com/microsoft/node-pty/issues/632
- Bun node-pty issue 7362: https://github.com/oven-sh/bun/issues/7362
- node-pty beta Bun build issue 748: https://github.com/microsoft/node-pty/issues/748
- bun-pty alternative package: https://github.com/sursaone/bun-pty
