## Context

The workbench tmux pane attaches to host tmux through the local Fastify server. The server receives raw PTY chunks from `tmux attach-session` and forwards those chunks to the browser as `output` messages. The browser writes each chunk into an xterm `Terminal` instance.

The current browser terminal is created with `convertEol: true`. xterm documents that option as a convenience for non-PTY data sources because it rewrites every `\n` as `\r\n`. A tmux attachment is a PTY-backed terminal stream, and full-screen TUIs such as Claude rely on exact cursor movement, line wrapping, alternate-screen, and line-clear semantics. Rewriting newline behavior in the browser can leave xterm's internal cell buffer different from tmux's intended screen, which then appears as stale edge regions during long autonomous output.

An earlier repaint-focused change added refresh hooks, delayed fits, and resize synchronization. Those are still useful for real layout changes, but they cannot repair an xterm buffer that was parsed incorrectly.

## Goals / Non-Goals

**Goals:**

- Parse tmux attachment output as raw terminal bytes in the browser xterm instance.
- Remove browser-side newline conversion from tmux panes.
- Preserve server-side raw PTY forwarding and the existing browser/server WebSocket protocol.
- Add deterministic coverage for PTY-style newline and clear behavior that would fail if `convertEol` is enabled.
- Keep recent detach, resize, scroll, and repaint behavior unless this fix proves one of those follow-up hooks is no longer needed.

**Non-Goals:**

- Do not replace tmux, xterm, node-pty, or the pending cross-runtime PTY backend.
- Do not change AG-UI event schemas, tmux WebSocket message shapes, or storage formats.
- Do not add durable terminal byte storage, replay, or reduced runtime terminal buffers.
- Do not treat this as a mouse-wheel scrolling bug; wheel routing stays covered by the prior change.

## Decisions

### Remove `convertEol` from tmux xterm construction

The tmux pane should construct `Terminal` without `convertEol: true`, leaving xterm's default PTY-oriented line-feed handling intact.

Alternative considered: set `convertEol: false` explicitly. Omitting the option is closer to Tailmux and xterm defaults, but an explicit `false` is acceptable if tests need direct option evidence.

### Keep the server bridge byte-transparent

The server should continue to forward `terminal.onData((chunk) => output chunk)` without newline normalization. The browser is the place where the incorrect transformation currently happens, and moving conversion to the server would make the PTY stream less transparent.

Alternative considered: normalize server output to `\r\n`. That is wrong for a tmux PTY stream and would preserve the same class of bug at a different layer.

### Test terminal control semantics, not only visible text

Fixture output such as `fixture attached ...\r\n` does not exercise the bug. The regression test should write a small PTY-style byte sequence into the tmux pane that uses cursor positioning, bare `\n`, line clear, or alternate-screen operations. The assertion should verify that old edge text is cleared or overwritten without resizing the browser.

Candidate sequence shape:

```text
wide-edge-marker
\x1b[1G\n
\x1b[2Kshort
```

The exact sequence can be adjusted during implementation, but it should fail under newline rewriting and pass when xterm parses the stream as a PTY.

Alternative considered: rely only on a real Claude manual smoke. The real smoke is important, but the deterministic fixture should catch accidental reintroduction of non-PTY newline conversion.

### Preserve repaint hooks until raw parsing is verified

The delayed fit and refresh hooks added in the previous pass should remain during the first implementation. If raw PTY parsing fixes the user-visible issue, later cleanup can decide whether any refresh hook is redundant.

Alternative considered: revert the repaint changes as part of this fix. That mixes two concerns and risks regressing the earlier layout/scroll behavior.

## Risks / Trade-offs

- Plain fixture output may depend on `convertEol` for line-oriented display -> Use `\r\n` in fixture messages where a carriage return is intended, matching PTY output conventions.
- The bug may have a second cause in renderer dimensions or tmux sizing -> Keep manual smoke evidence that compares browser view, xterm size, and tmux pane size after the newline fix.
- xterm rendering may differ between headless and interactive Chromium -> Use deterministic text/cell assertions for CI and a screenshot-producing manual smoke for real TUI validation.
- Removing `convertEol` can make malformed non-PTY fixture strings display differently -> Treat that as a fixture bug, not a tmux pane requirement.

## Migration Plan

This is a browser implementation fix with no persisted data migration.

1. Remove tmux pane newline conversion.
2. Add deterministic fixture coverage for PTY-style newline and clear behavior.
3. Run focused workbench tmux tests and typecheck.
4. Restart the local GUI server and validate against the real Claude/Kimi tmux session that reproduced edge artifacts.

Rollback is limited to restoring the previous terminal option. No server data or browser storage changes are required.

## Open Questions

- Should the implementation assert the terminal option directly in a unit test, or rely on behavior-only fixture coverage?
- Should a future cleanup remove any extra refresh hooks if raw PTY parsing makes them unnecessary?
