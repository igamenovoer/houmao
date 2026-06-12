## ADDED Requirements

### Requirement: Tmux bridge selects a runtime-compatible PTY backend
The workbench local server SHALL attach browser tmux tabs through a PTY backend that is compatible with the JavaScript runtime hosting the server.

When the server runs under Node, the tmux bridge SHALL use the Node-compatible `node-pty` backend.

When the server runs under Bun and Bun exposes first-party terminal support, the tmux bridge SHALL use Bun's native terminal backend instead of `node-pty`.

The tmux bridge SHALL keep the existing private browser WebSocket protocol for attach, input, resize, close, output, attached, error, and exit messages.

The tmux bridge SHALL strip nested tmux environment variables and set a terminal type consistently for every real backend.

If no compatible PTY backend is available or backend selection fails, the tmux bridge SHALL send a deterministic tmux error message to the browser and SHALL NOT report a successful attachment.

#### Scenario: Node server attaches through node-pty
- **WHEN** the workbench local server runs under Node and the browser requests a valid tmux session attachment
- **THEN** the server spawns `tmux attach-session` through the Node PTY backend
- **AND THEN** the browser receives the existing `attached` and `output` WebSocket messages

#### Scenario: Bun server attaches through native terminal backend
- **WHEN** the workbench local server runs under Bun with native terminal support and the browser requests a valid tmux session attachment
- **THEN** the server spawns `tmux attach-session` through Bun's terminal backend
- **AND THEN** the server does not load or use `node-pty` for that attachment
- **AND THEN** the browser receives the existing `attached` and `output` WebSocket messages

#### Scenario: Unsupported runtime reports deterministic attach failure
- **WHEN** the browser requests a tmux attachment and the server cannot select a compatible PTY backend
- **THEN** the server sends an `error` WebSocket message with a deterministic tmux backend failure code
- **AND THEN** the browser does not receive an `attached` message for that request

#### Scenario: Runtime backend preserves tmux attachment controls
- **WHEN** a browser tmux tab attached through any real runtime backend sends terminal input, resize, or close messages
- **THEN** the server forwards allowed input to the attached tmux process
- **AND THEN** the server resizes the PTY for resize messages
- **AND THEN** the server terminates only the attachment process for close messages
- **AND THEN** the server does not stop, restart, shut down, or interrupt the underlying tmux session or Houmao managed agent
