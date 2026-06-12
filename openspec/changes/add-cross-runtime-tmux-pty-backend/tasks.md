## 1. PTY Backend Abstraction

- [ ] 1.1 Create a server-side tmux PTY adapter module with a small runtime-neutral interface for write, resize, kill, data events, and exit events.
- [ ] 1.2 Move Node `node-pty` spawning behind the Node adapter and remove the top-level `node-pty` import from `tmuxBridge.ts`.
- [ ] 1.3 Add a Bun adapter that uses `Bun.Terminal` and `Bun.spawn(..., { terminal })` when Bun terminal support is available.
- [ ] 1.4 Normalize adapter exit and output events so `tmuxBridge.ts` can preserve the current WebSocket message protocol.
- [ ] 1.5 Keep `tmuxAttachEnvironment()` shared by all real adapters so nested `TMUX` and `TMUX_PANE` values are stripped consistently.

## 2. Bridge Integration

- [ ] 2.1 Update `handleTmuxAttachSocket()` to request a PTY adapter from the runtime backend factory after attach-message validation.
- [ ] 2.2 Preserve read-only input rejection, resize handling, close cleanup, and fixture mode behavior.
- [ ] 2.3 Add deterministic error handling for unsupported runtime backends and adapter spawn failures before any `attached` message is sent.
- [ ] 2.4 Ensure the Bun runtime path does not import or instantiate `node-pty` for real tmux attachments.

## 3. Tests

- [ ] 3.1 Add unit coverage for backend selection under Node and under a fake Bun runtime with `Bun.Terminal`.
- [ ] 3.2 Add unit coverage for unsupported Bun runtime behavior when `Bun.Terminal` is absent.
- [ ] 3.3 Extend tmux bridge WebSocket tests to verify adapter output, input, resize, close, and read-only behavior through an injected fake adapter.
- [ ] 3.4 Keep existing fixture-mode Playwright tmux tests passing without depending on real tmux or real PTY backends.
- [ ] 3.5 Add or document an opt-in local smoke for real Bun `Bun.Terminal` attachment to a throwaway tmux session.

## 4. Documentation and Validation

- [ ] 4.1 Update `apps/ag-ui-workbench/README.md` to describe Node and Bun tmux PTY backend behavior and the minimum Bun path.
- [ ] 4.2 Update `context/hints/howto-run-tmux-pty-bridge-across-node-and-bun.md` if implementation details differ from the proposal.
- [ ] 4.3 Run `bun run typecheck` in `apps/ag-ui-workbench`.
- [ ] 4.4 Run the targeted workbench server tests and fixture-backed Playwright tmux tests.
- [ ] 4.5 Run a manual real tmux attach smoke under Bun when the host has Bun 1.3.5+ and tmux available.
