## Context

The AG-UI workbench local server owns host-side tmux attachment for browser tmux tabs. The current implementation lives in `apps/ag-ui-workbench/src/server/tmuxBridge.ts` and imports `node-pty` at module top level before spawning `tmux attach-session`.

The maintained workbench command is `bun run dev`, so the server normally runs under Bun. Local reproduction showed that `node-pty` can load under Bun 1.3.13 but immediately exits spawned PTY children, while the same `node-pty` code works under Node. Bun 1.3.5+ provides a first-party `Bun.Terminal` PTY API that successfully attaches to tmux in this workspace.

The browser tmux protocol already has the right shape: attach, input, resize, close, output, error, attached, and exit messages. The implementation should change the server-side PTY backend, not the browser contract.

## Goals / Non-Goals

**Goals:**

- Make the tmux bridge functional when the workbench server runs under Bun or Node.
- Preserve the existing browser WebSocket protocol and tmux pane UX.
- Keep Node-backed runs on `node-pty`, which remains the mature and documented Node PTY dependency.
- Use `Bun.Terminal` for Bun-backed runs when that API is present.
- Report deterministic backend-selection or spawn errors to the browser instead of only emitting a generic attachment-ended message.
- Keep fixture mode independent from real PTY backends so deterministic E2E tests stay hermetic.

**Non-Goals:**

- Do not replace tmux with a different terminal/session manager.
- Do not add Houmao managed-agent lifecycle control to the tmux tab.
- Do not require a new npm dependency for Bun 1.3.5+.
- Do not make `node-pty` a supported Bun backend.
- Do not expose the tmux bridge as a public Houmao protocol.

## Decisions

### Introduce a server-side PTY adapter interface

Create a small interface for the operations the tmux bridge needs:

- `write(data)`
- `resize(cols, rows)`
- `kill()`
- `onData(listener)`
- `onExit(listener)`

`handleTmuxAttachSocket()` will depend on this interface rather than directly on `node-pty`. This keeps input validation, read-only gating, WebSocket messages, cleanup, and fixture handling in the existing bridge while isolating runtime-specific PTY details.

Alternative considered: branch inline inside `spawnTmuxAttach()`. That is smaller initially, but it keeps backend details tangled with WebSocket behavior and makes Bun/Node tests harder to isolate.

### Select backend by JavaScript runtime and capability

Use a runtime guard such as `typeof Bun !== "undefined"` plus a `Bun.Terminal` capability check for the Bun backend. Use the Node backend otherwise.

The Node backend should dynamically import `node-pty` from the Node-only branch. The current top-level import should be removed so Bun can start the workbench and select its native terminal backend without first loading `node-pty`.

Alternative considered: always run the server under Node. That fixes today's operational failure but conflicts with the documented Bun workflow and leaves future Bun-backed local development fragile.

### Keep browser protocol stable

The WebSocket message shapes remain unchanged. The backend still sends:

- `attached` after a PTY session is successfully spawned
- `output` for terminal data
- `error` for validation, backend selection, read-only input, and spawn failures
- `exit` when the attached PTY process exits

The frontend can continue to show `[tmux] attachment ended` for ordinary exit events. For backend selection failures, the server should send an `error` first so the pane shows a concrete reason.

Alternative considered: add a new frontend error state. That is unnecessary unless later UX work needs richer status rendering.

### Preserve tmux environment handling in both backends

Both backends must use `tmuxAttachEnvironment()` so nested `TMUX` and `TMUX_PANE` variables are stripped and `TERM` is set to `xterm-256color`. This prevents the workbench server's own terminal context from leaking into attached tmux sessions.

### Add runtime-focused tests without depending on real user sessions

Keep fixture-mode Playwright tests as the deterministic browser path. Add server/unit coverage for backend selection and adapter behavior:

- Node path can be exercised with an injected fake `node-pty`-style backend or a mock factory.
- Bun path can be exercised by installing a temporary fake `globalThis.Bun.Terminal` and `Bun.spawn` shape, rather than requiring the test process itself to run under Bun.
- A manual or opt-in smoke may cover real `Bun.Terminal` against a throwaway tmux session where the host has Bun 1.3.5+ and tmux.

Alternative considered: run the full server test suite twice, once under Node and once under Bun. That is useful later but heavier than needed for this targeted change.

## Risks / Trade-offs

- Bun API drift or host running Bun before `Bun.Terminal` exists → return a deterministic `tmux_pty_backend_unavailable` error and document the minimum Bun path.
- TypeScript lacks Bun global types in the current package → define a narrow local runtime type instead of adding broad `bun-types` unless implementation proves it is cleaner.
- Dynamic import changes may affect bundling → keep backend modules small and use tests to verify `bun run build` and `bun run typecheck`.
- Bun terminal exit semantics differ from `node-pty` → normalize adapter exit events enough for the existing WebSocket protocol and document that `proc.exited` is the subprocess exit source.
- Real PTY tests can be flaky on hosts without tmux → keep CI coverage mostly fake-backed and leave real tmux/Bun smoke opt-in.

## Migration Plan

1. Add the PTY adapter module and move Node `node-pty` usage behind the Node backend.
2. Add the Bun `Bun.Terminal` backend with runtime capability detection.
3. Update `tmuxBridge.ts` to call the adapter factory and preserve existing WebSocket behavior.
4. Add deterministic tests for backend selection, read-only handling, resize/input delegation, and unsupported backend errors.
5. Update README and hint documentation with the new supported behavior.
6. Validate with `bun run typecheck`, `bun run e2e` or targeted Playwright tests, and an opt-in real tmux attach smoke under Bun.
