## Context

The workbench tmux pane currently creates an xterm surface per selected session and sends attach, input, resize, detach, and scroll actions through runtime tmux effects. The runtime stores one WebSocket attachment per pane id and already ignores stale socket events when the socket is no longer current. The server bridge stores `sessionName` inside each WebSocket handler and implements mouse-wheel scroll by running host tmux commands against that session.

Server-side scroll is intentional. Passing wheel input through the PTY path did not refresh the GUI reliably, so the workbench must keep the server-owned scroll command path. The bug is that a dropdown session switch can leave the old tmux attach client or stale attachment identity influencing later scroll behavior. Tailmux is the local reference for this lifecycle shape: each browser session owns a socket and session name, and server WebSocket close explicitly detaches the tmux client before killing the PTY attach process.

## Goals / Non-Goals

**Goals:**

- Make selecting a different tmux session in the same workbench tmux pane behave as detach previous, then attach selected.
- Ensure input, resize, and scroll after a switch target only the newly selected session.
- Ensure stale output, close, exit, or error events from an older attachment cannot update the current pane state.
- Release the server-side tmux attach client for the previous session when an attachment closes.
- Preserve server-side tmux-command scrolling so browser repaint remains reliable.
- Add deterministic regression coverage for switch, detach, and scroll routing.

**Non-Goals:**

- Do not replace tmux with another terminal/session manager.
- Do not send wheel scrolling as raw PTY passthrough input.
- Do not add Houmao managed-agent lifecycle control to tmux pane detach or close.
- Do not change the private browser tmux WebSocket protocol unless an implementation detail requires a backward-compatible field.
- Do not solve the broader Bun/Node PTY backend selection change here.

## Decisions

### Keep one attachment generation per pane

The runtime should continue to store a single current attachment for each pane id, but each attach should have an explicit generation or socket id that gates output, attach success, close, exit, error, input, resize, and scroll handling. Existing stale-socket checks already compare the current socket object; the implementation should keep or strengthen that invariant and include tests for switch races.

Alternative considered: rely only on `paneId` and active session name. That is weaker because stale close or exit events can arrive after a new attachment starts and share the same pane id.

### Treat dropdown selection as an explicit replacement

`TmuxTabPanel` should keep calling its local close path before opening a new xterm and requesting the new attach. The runtime attach path should also keep detaching any existing socket before opening the replacement socket. The important behavior is that this replacement covers all command paths, including scroll, not only terminal output and keyboard input.

Alternative considered: reuse one WebSocket and send a second attach message for the new session. The server bridge intentionally rejects attaching twice on one socket, and replacing the socket gives a cleaner ownership boundary.

### Explicitly detach the server-side tmux client on close

The server bridge should release the tmux attach client on WebSocket close, client close, attach process exit, and errors. The Tailmux reference explicitly detaches the tmux client before killing the PTY attach process. The workbench should mirror that cleanup intent more narrowly by matching the `node-pty` attach process PID against `tmux list-clients` output, detaching only the matching `client_tty`, and then killing the PTY process. If tmux has already removed the matching client, cleanup can rely on the process kill path without logging an ordinary close as a failure.

Alternative considered: only kill the PTY process. That may be sufficient in some cases, but the observed bug suggests tmux can still retain stale client state or scroll targeting after the browser switched sessions.

### Keep scroll scoped to the WebSocket attachment

Scroll messages should remain browser-to-server messages handled by `scrollTmuxAttachment(sessionName, message)` on the server. The server should use the session bound to that WebSocket handler, and the runtime should send scroll only on the current socket for the pane.

Alternative considered: send tmux copy-mode key sequences through the PTY. That was rejected because it regresses the GUI refresh behavior that led to server-side scroll handling.

### Extend fixture and fake-socket tests

The fixture bridge already echoes `fixture scrolled <session>`, which is enough to assert browser-level routing after a session switch. Runtime fake-socket tests can assert that switching closes the first socket, opens a second socket, and sends scroll only through the second socket. Server tests can assert cleanup behavior with an injected or observable detach hook if the implementation adds one.

Alternative considered: depend only on manual real-tmux validation. Manual validation remains useful, but this bug is a lifecycle race that should have deterministic coverage.

## Risks / Trade-offs

- Explicit tmux detach may detach more than the intended attach client if targeted too broadly → target the tmux client whose `client_pid` matches the browser-owned attach process and skip detach when that exact client is not present.
- Stale socket events may still arrive after the replacement starts → keep current-socket/generation checks around every message, close, error, and exit handler.
- Closing the previous attachment may briefly set the pane state to disconnected during a switch → ensure stale disconnect events from the old generation do not overwrite the new attaching or attached state.
- Fixture tests may not reproduce real tmux copy-mode details → cover routing deterministically in fixture tests and keep a real tmux smoke for the attach-client cleanup path.
- The pending cross-runtime PTY backend may touch the same server files → keep this change narrow and express cleanup through the backend-neutral bridge lifecycle.

## Migration Plan

1. Add or strengthen runtime attachment generation handling and tests for switch races.
2. Add explicit server-side tmux attach-client detach during WebSocket cleanup.
3. Keep server-side scroll routing and validate it against the current attachment after a switch.
4. Add Playwright fixture coverage for switching sessions, wheel scrolling, and confirming the second session receives the scroll.
5. Run focused runtime, server, and workbench Playwright tests.

Rollback is straightforward: revert the runtime switch-routing and server cleanup changes. No persistent data migration is needed.

## Open Questions

- Can the server identify the exact tmux client created by the attach process across both `node-pty` and the pending Bun terminal backend, or should the first implementation use a guarded session-targeted detach like Tailmux?
- Should the browser emit a distinct switch action for clearer state transitions, or is the existing detach plus attach action sequence sufficient once generation checks are tested?
