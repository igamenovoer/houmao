## 1. PTY Backend Abstraction

- [x] 1.1 Create a server-side tmux PTY adapter module with a small runtime-neutral interface for write, resize, kill, data events, and exit events.
- [x] 1.2 Move Node `node-pty` spawning behind the Node adapter and remove the top-level `node-pty` import from `tmuxBridge.ts`.
- [x] 1.3 Add a Bun adapter that uses `Bun.Terminal` and `Bun.spawn(..., { terminal })` when Bun terminal support is available.
- [x] 1.4 Normalize adapter exit and output events so `tmuxBridge.ts` can preserve the current WebSocket message protocol; use Bun subprocess exit state (`proc.exited`/`exitCode`/`signalCode`) rather than treating `Bun.Terminal` PTY lifecycle callbacks as child-process exit status.
- [x] 1.5 Keep `tmuxAttachEnvironment()` shared by all real adapters so nested `TMUX` and `TMUX_PANE` values are stripped consistently.

## 2. Bridge Integration

- [x] 2.1 Update `handleTmuxAttachSocket()` to request a PTY adapter from an injectable runtime backend factory after attach-message validation.
- [x] 2.2 Preserve read-only input rejection, resize handling, scroll handling, close cleanup, and fixture mode behavior.
- [x] 2.3 Add deterministic error handling for unsupported runtime backends and adapter spawn failures before any `attached` message is sent.
- [x] 2.4 Ensure the Bun runtime path does not import or instantiate `node-pty` for real tmux attachments.

## 3. Tests

- [x] 3.1 Add unit coverage for backend selection under Node and under a fake Bun runtime with `Bun.Terminal`.
- [x] 3.2 Add unit coverage for unsupported Bun runtime behavior when `Bun.Terminal` is absent.
- [x] 3.3 Extend tmux bridge WebSocket tests to verify adapter output, input, resize, close, exit, and read-only behavior through an injected fake adapter.
- [x] 3.4 Keep existing fixture-mode Playwright tmux tests passing without depending on real tmux or real PTY backends.
- [x] 3.5 Reuse or update `scripts/demo/ag-ui-real-tmux-workbench-smoke/` as the opt-in local smoke for real Bun `Bun.Terminal` attachment to a throwaway tmux session.

## 4. Documentation and Validation

- [x] 4.1 Update `apps/ag-ui-workbench/README.md` to describe Node and Bun tmux PTY backend behavior, `bun run dev` versus `bun run dev:bun`, and the minimum Bun path.
- [x] 4.2 Update `context/hints/howto-run-tmux-pty-bridge-across-node-and-bun.md` if implementation details differ from the proposal.
- [x] 4.3 Run `bun run typecheck` in `apps/ag-ui-workbench`.
- [x] 4.4 Run targeted workbench server tests and fixture-backed Playwright tmux tests against the Node-backed `bun run dev` path.
- [x] 4.5 Run the existing real tmux attach smoke against `bun run dev:bun` when the host has Bun 1.3.5+ and tmux available.
