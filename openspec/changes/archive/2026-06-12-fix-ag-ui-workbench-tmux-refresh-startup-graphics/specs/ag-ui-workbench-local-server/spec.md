## ADDED Requirements

### Requirement: Tmux attach bridge applies attachment resize messages
The workbench local server tmux bridge SHALL apply valid browser resize messages to the active tmux attachment.

Resize messages SHALL be scoped to the WebSocket attachment that received them.

The bridge SHALL reject or ignore resize messages that arrive before a tmux session is attached, after the attachment closes, or with invalid column or row values.

The bridge SHALL continue to report deterministic attachment errors instead of silently ending the WebSocket when resize handling fails.

#### Scenario: Resize after attach updates tmux pane size
- **WHEN** the browser attaches to a real tmux session through the workbench tmux WebSocket
- **AND WHEN** the browser sends a resize message with valid terminal columns and rows after the attachment succeeds
- **THEN** the server applies those columns and rows to the active tmux attachment
- **AND THEN** a host tmux pane-size query reports the requested size or the nearest size tmux can represent

#### Scenario: Resize before attach is rejected deterministically
- **WHEN** the browser opens a tmux attach WebSocket but has not attached to a session
- **AND WHEN** the browser sends a resize message
- **THEN** the server rejects or ignores the message deterministically as not attached
- **AND THEN** the server does not crash or mark an unrelated tmux session resized

### Requirement: Tmux bridge diagnostics distinguish attach exit from resize failure
The workbench local server SHALL emit deterministic tmux WebSocket error details for attach failure, attach process exit, invalid input, read-only input, and resize failure.

The browser SHALL be able to surface these details without conflating them all into a generic attachment-ended message.

#### Scenario: Resize failure is visible as resize failure
- **WHEN** a browser tmux attachment is active
- **AND WHEN** applying a valid resize message fails in the bridge
- **THEN** the server sends or records an error detail that identifies resize handling
- **AND THEN** the browser does not report only a generic `[tmux] attachment ended` message for that failure
