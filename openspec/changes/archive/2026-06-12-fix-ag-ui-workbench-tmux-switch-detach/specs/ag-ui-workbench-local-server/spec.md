## ADDED Requirements

### Requirement: Tmux bridge releases attach clients when attachments close
The workbench local server tmux bridge SHALL release the tmux attach client associated with a browser WebSocket attachment when that attachment closes.

The bridge SHALL perform this cleanup for client close messages, browser WebSocket close, WebSocket errors, and attach process exits.

The bridge SHALL release only the browser-owned tmux attach client and SHALL NOT stop, restart, shut down, interrupt, or kill the underlying tmux session or Houmao managed agent.

The bridge SHALL tolerate tmux detach cleanup failures by reporting or logging deterministic diagnostics without crashing the workbench server.

#### Scenario: Client close releases only the attach client
- **WHEN** a browser tmux WebSocket is attached to session `houmao-alpha`
- **AND WHEN** the browser sends a close message or closes the WebSocket
- **THEN** the server detaches or terminates the browser-owned tmux attach client for `houmao-alpha`
- **AND THEN** the underlying `houmao-alpha` tmux session remains alive

#### Scenario: Attach process exit does not stop the tmux session
- **WHEN** a tmux attach process exits for a browser attachment
- **THEN** the server cleans up that attachment's process and WebSocket state
- **AND THEN** the server does not issue tmux kill-session or any Houmao managed-agent lifecycle command

### Requirement: Tmux scroll commands are scoped to the owning attachment
The workbench local server tmux bridge SHALL execute scroll commands against the tmux session bound to the WebSocket attachment that received the scroll message.

The bridge SHALL reject or ignore scroll messages that arrive before a successful attach or after the attachment has been cleaned up.

The bridge SHALL keep mouse-wheel scroll handling server-side rather than forwarding raw wheel or copy-mode input through the PTY passthrough path.

#### Scenario: Scroll uses the WebSocket-bound session
- **WHEN** a browser WebSocket is attached to session `utility-shell`
- **AND WHEN** that WebSocket sends a scroll-up message
- **THEN** the server runs the tmux scroll operation against `utility-shell`
- **AND THEN** the server does not scroll any previous session that used the same workbench pane

#### Scenario: Scroll before attach is rejected
- **WHEN** a browser opens a tmux attach WebSocket but has not attached to a session
- **AND WHEN** the browser sends a scroll message
- **THEN** the server rejects or ignores the message deterministically as not attached
- **AND THEN** no tmux session receives a scroll command
