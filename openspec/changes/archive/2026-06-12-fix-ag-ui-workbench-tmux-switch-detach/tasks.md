## 1. Regression Coverage

- [x] 1.1 Add a runtime fake-socket test that attaches pane `tmux-1` to session A, switches to session B, and verifies the first socket is closed before the second socket receives attach.
- [x] 1.2 Extend runtime coverage so stale output, attached, close, exit, and error events from the first socket do not update pane state or write to the second terminal sink after the switch.
- [x] 1.3 Add runtime coverage that `tmux/scrollRequested` after a switch sends the scroll message only through the current session B socket.
- [x] 1.4 Extend the fixture-backed Playwright switch test so wheel scrolling after switching from `houmao-alpha` to `utility-shell` produces `fixture scrolled utility-shell` and does not produce a new alpha scroll.
- [x] 1.5 Add or extend server tmux bridge tests for scroll-before-attach rejection and WebSocket-bound scroll session routing.

## 2. Runtime and Pane Lifecycle

- [x] 2.1 Audit `TmuxTabPanel` session-picker attach flow and keep the explicit local close before creating the replacement xterm surface.
- [x] 2.2 Strengthen `installTmuxEffects()` attachment identity handling so every socket event path is gated by the current pane attachment generation or socket identity.
- [x] 2.3 Ensure `detach(paneId)` deletes the previous attachment before new attach state can be affected by old close or exit events.
- [x] 2.4 Ensure input, resize, and scroll dispatch paths read only the current attachment for the pane and drop requests when the current socket is not open.

## 3. Server Attachment Cleanup

- [x] 3.1 Review `extern/tracked/tailmux/server.js` cleanup behavior and translate the relevant explicit tmux detach-client pattern to the workbench bridge.
- [x] 3.2 Add a guarded server cleanup helper that releases the browser-owned tmux attach client for the WebSocket-bound session during close, error, client close messages, and attach process exit.
- [x] 3.3 Ensure cleanup kills or detaches only the attach client and does not issue `tmux kill-session` or any Houmao managed-agent lifecycle command.
- [x] 3.4 Preserve server-side `scrollTmuxAttachment()` behavior and keep scroll scoped to the session name bound to the receiving WebSocket.
- [x] 3.5 Make cleanup failures deterministic and non-fatal, using an error or log path that does not crash the workbench server.

## 4. Validation

- [x] 4.1 Run `bun test tests/runtime.spec.ts` or the project-supported targeted runtime test command in `apps/ag-ui-workbench`.
- [x] 4.2 Run the targeted workbench server tests covering tmux bridge attach, close, resize, and scroll behavior.
- [x] 4.3 Run the fixture-backed Playwright tests covering tmux session switching and mouse-wheel scrolling.
- [x] 4.4 Run `bun run typecheck` in `apps/ag-ui-workbench`.
- [x] 4.5 If tmux is available locally, run a manual real-tmux smoke that attaches session A, switches to session B, scrolls with the mouse wheel, and verifies session B scrolls while session A remains alive.
