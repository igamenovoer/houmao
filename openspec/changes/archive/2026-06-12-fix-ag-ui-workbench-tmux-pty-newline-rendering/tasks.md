## 1. Terminal PTY Parsing

- [x] 1.1 Remove `convertEol: true` from the tmux pane xterm `Terminal` construction.
- [x] 1.2 Confirm tmux output still flows through the existing ephemeral output sink without browser runtime or storage persistence.
- [x] 1.3 Keep server tmux output forwarding byte-transparent and avoid adding newline normalization in the bridge.

## 2. Deterministic Regression Coverage

- [x] 2.1 Add a deterministic tmux fixture path or helper that emits PTY-style control output with edge text, bare line feed, cursor movement, and clear or overwrite semantics.
- [x] 2.2 Add a focused workbench browser test that attaches a tmux pane, triggers the PTY-style output, and verifies stale edge text is absent without resizing the browser.
- [x] 2.3 Ensure existing fixture messages that require new lines use explicit PTY-style `\r\n` where appropriate.
- [x] 2.4 Keep existing tmux switch, scroll, resize, and repaint tests passing after the newline parsing change.

## 3. Real Tmux Validation

- [x] 3.1 Run a focused real-tmux smoke or manual probe against a throwaway or active Claude/Kimi TUI session that emits long autonomous output.
- [x] 3.2 Record evidence that xterm/browser dimensions and host tmux pane dimensions are synchronized during the smoke.
- [x] 3.3 Verify that long autonomous TUI output no longer leaves stale edge regions without mouse scrolling or browser resize.

## 4. Verification

- [x] 4.1 Run `bun run typecheck` in `apps/ag-ui-workbench`.
- [x] 4.2 Run focused Playwright coverage for tmux browser behavior.
- [x] 4.3 Run focused runtime/server tmux tests if touched by the implementation.
- [x] 4.4 Restart the local GUI server and confirm the user-facing workbench loads with the fix.
