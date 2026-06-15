## ADDED Requirements

### Requirement: Tmux terminal panes preserve PTY output newline semantics
Tmux panes SHALL write tmux attachment output to xterm as a PTY terminal stream without browser-side newline conversion.

Tmux panes SHALL NOT enable xterm newline conversion intended for non-PTY data sources when rendering a tmux attachment.

Tmux panes SHALL preserve raw tmux control semantics for bare line feed, carriage return, cursor movement, line clear, alternate screen, wrapping, and long autonomous TUI redraws.

The behavior SHALL NOT require a browser resize, Dockview resize, mouse scroll, or terminal refresh workaround to clear stale edge cells caused by newline rewriting.

#### Scenario: Bare line feed keeps PTY cursor semantics
- **WHEN** a tmux pane receives PTY-style terminal output that includes a bare line feed after a line containing edge text
- **THEN** xterm applies normal PTY line-feed semantics without injecting an extra carriage return
- **AND THEN** subsequent cursor movement and line-clear sequences update the intended cells without leaving stale edge text

#### Scenario: Long alternate-screen TUI output does not leave newline-conversion artifacts
- **WHEN** a tmux pane is attached to a full-screen TUI running in tmux alternate screen
- **AND WHEN** the TUI emits long autonomous output that redraws tables, prompts, and status regions without user input
- **THEN** the visible terminal area reflects tmux's intended screen state
- **AND THEN** stale edge regions caused by browser-side newline rewriting are not visible

### Requirement: Workbench tests cover tmux PTY newline rendering
The deterministic workbench browser coverage SHALL include a tmux pane regression case for PTY-style control output that is sensitive to newline conversion.

The regression case SHALL use terminal control bytes rather than only line-oriented fixture messages ending in `\r\n`.

The regression case SHALL verify that edge text is cleared or overwritten without resizing the browser window or Dockview panel.

Manual or smoke validation for real tmux TUI sessions SHALL include evidence that the browser xterm size and host tmux pane size are synchronized while long autonomous output renders without stale edge artifacts.

#### Scenario: Fixture detects newline-conversion artifact
- **WHEN** the deterministic tmux fixture emits PTY-style output containing edge text, a bare line feed, cursor movement, and a line clear or overwrite
- **THEN** the workbench test verifies that the stale edge text is absent from the visible terminal cells
- **AND THEN** the test would fail if the tmux pane enabled browser-side newline conversion for the xterm instance

#### Scenario: Real tmux smoke records newline-rendering evidence
- **WHEN** a tester validates the workbench against a real tmux session running a Claude or Kimi TUI
- **AND WHEN** that TUI emits long output without user input
- **THEN** the smoke evidence records enough terminal geometry and visible rendering evidence to distinguish newline parsing errors from tmux pane-size mismatches
