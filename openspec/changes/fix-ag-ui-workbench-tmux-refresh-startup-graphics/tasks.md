## 1. Tmux Repaint and Resize Reproduction

- [x] 1.1 Add or update a deterministic workbench Playwright test that verifies tmux post-attach size delivery when the pane fits before attach succeeds.
- [x] 1.2 Add or update tmux repaint coverage so host wheel scrolling refreshes visible terminal rows without resizing the browser window.
- [x] 1.3 Add a real-tmux smoke or manual-capable Playwright probe that records xterm columns/rows, terminal host dimensions, tmux pane size, and screenshots before scroll, after scroll, and after resize.

## 2. Tmux Repaint and Resize Implementation

- [x] 2.1 Update `TmuxTabPanel` to track measured terminal size separately from the size delivered to the current attachment.
- [x] 2.2 Dispatch one resize for the current measured size after attach succeeds when that size was measured during the attaching state.
- [x] 2.3 Keep same-size fit and repaint events from dispatching redundant resize actions after the current attachment has received the measured size.
- [x] 2.4 Add terminal-host wheel handling that keeps wheel events inside xterm, scrolls the terminal viewport, and schedules a full visible-row refresh.
- [x] 2.5 Verify tmux pane CSS and xterm host sizing so the terminal canvas/screen fills the attached pane without stale edge regions.

## 3. Tmux Bridge Diagnostics

- [x] 3.1 Add or update server-side tests for valid resize handling on an active tmux attachment.
- [x] 3.2 Add or update server-side tests for resize messages sent before attach, after close, or with invalid dimensions.
- [x] 3.3 Make tmux bridge resize failures report deterministic resize-specific details instead of collapsing into only `[tmux] attachment ended`.

## 4. Launch Validation Scope

- [x] 4.1 Add a unit or CLI test where an unrelated stale preset with `houmao-agent-ag-ui` does not block launching a selected valid specialist.
- [x] 4.2 Add a unit or CLI test where selecting the stale source itself fails before managed-agent registry publication and names the offending selector.
- [x] 4.3 Refactor project launch resolution so `houmao-mgr project agents launch` validates only the selected specialist/profile/preset and required dependencies.
- [x] 4.4 Update the project-local stale `test-kimi-code-tui` preset to use current `houmao-interop-ag-ui` when AG-UI is intended, or remove the AG-UI system-skill selector when it is not.

## 5. First-Connect Graphics Smoke

- [x] 5.1 Fix the real-agent smoke Plotly chart assertion so multiple SVG layers inside one chart container count as a visible chart.
- [x] 5.2 Add or update a smoke path that starts a fresh or freshly relaunched Houmao agent, opens a clean Playwright browser session, connects once, and verifies a template graphic without disconnect/reconnect.
- [x] 5.3 Record smoke evidence that distinguishes render failure, publish-delivery failure, active-thread routing failure, and locator failure.

## 6. Verification

- [x] 6.1 Run focused unit tests for project launch and system-skill validation.
- [x] 6.2 Run focused workbench Playwright tests for tmux repaint, tmux resize, and template graphic visibility.
- [x] 6.3 Run the real-agent GUI smoke with a fresh browser and newly launched or relaunched agent.
- [x] 6.4 Run `openspec status --change fix-ag-ui-workbench-tmux-refresh-startup-graphics` and confirm all artifacts remain apply-ready.
