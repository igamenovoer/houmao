# Spec Delta

## Purpose

Let authorized operators watch or interact with the verified live tmux session of a managed agent through its running Houmao gateway.

## ADDED Requirements

### Requirement: The running gateway serves the browser terminal

The gateway SHALL serve the read-only entry at `/v1/terminal/view` and the interactive entry at `/v1/admin/terminal/attach`. The pages, browser assets, and corresponding WebSocket streams SHALL use the gateway's existing listener and owner-local origin. Terminal access SHALL require a running gateway and SHALL be independent of structured prompt readiness.

#### Scenario: A browser opens a busy agent's terminal

- **WHEN** an authorized operator opens the terminal of a verified live tmux-backed agent while structured prompt admission is closed
- **THEN** the browser loads the page and connects to the correct stream using the running gateway's existing port
- **AND THEN** the gateway creates only a terminal attachment, without starting another web listener or submitting a prompt

#### Scenario: The gateway is detached

- **WHEN** an operator requests a browser terminal for a live managed agent without a running gateway
- **THEN** the feature is unavailable until a gateway is explicitly attached
- **AND THEN** the request starts neither a gateway nor another web server

### Requirement: The browser attachment binds to the current managed tmux session

The gateway SHALL attach only to the session verified from its active managed agent's recorded owner, generation, socket, and live tmux identity. Eligibility SHALL use that binding across native run modes. A missing, stale, unverified, or replaced binding SHALL be refused without repairing it or creating a session or server.

#### Scenario: Multiple execution modes have live tmux sessions

- **WHEN** active TUI, headless, service, or Web agents have verified live tmux sessions
- **THEN** each eligible gateway can show its agent's session, including supervisor output for a supervised agent
- **AND THEN** the session view is available independently of the provider's other interaction surfaces

#### Scenario: Another tmux server has the same session name

- **WHEN** inherited tmux selectors point to a different server with a session of the same name
- **THEN** the gateway uses only the recorded owner socket and verified session identity

#### Scenario: The target changes during attachment

- **WHEN** a session or tmux server is replaced after entry was issued or while the client is attaching
- **THEN** the grant cannot attach to or disclose output from the replacement, even when the socket path, session name, or numeric ID is reused

### Requirement: Viewer connections expose terminal output only

A viewer SHALL receive live terminal output through a read-only tmux client. The gateway SHALL reject browser input and resize requests on the viewer stream and SHALL leave the live session's geometry and focus unaffected by opening, viewing, or closing the page.

#### Scenario: A viewer sends crafted input or a resize request

- **WHEN** a read-only WebSocket sends keyboard data, paste, a tmux command, or resize requests
- **THEN** none of the messages reaches the tmux session or changes its geometry or focus
- **AND THEN** terminal output remains available through an authorized view connection

### Requirement: Administrator connections provide a live interactive terminal

An authorized interactive attachment SHALL relay terminal bytes, keyboard input, paste, and bounded dimensions between the browser and the attached tmux client. It SHALL provide ordinary tmux client behavior. The gateway SHALL bound buffering for a stalled browser and SHALL preserve complete terminal bytes for a healthy connection.

#### Scenario: An administrator operates the live terminal

- **WHEN** the administrator types and pastes Unicode text and resizes the browser terminal
- **THEN** the live tmux application receives that input and the terminal displays its output using the negotiated client dimensions
- **AND THEN** an existing native tmux client remains attached

#### Scenario: The browser stops processing terminal output

- **WHEN** an attachment stops consuming output
- **THEN** the gateway bounds outstanding output and can close the stalled attachment without affecting other gateway operations or ending the managed agent

### Requirement: Attachment teardown preserves the managed agent

The gateway SHALL release only the PTY and tmux client it acquired when the browser disconnects, authorization is lost, the verified target is replaced, or the gateway shuts down. It SHALL refuse tmux configurations that would destroy the session on that detach or silently switch the client on session loss, without altering the configuration.

#### Scenario: A browser closes or the gateway stops

- **WHEN** the browser closes or the gateway shuts down with an attachment open
- **THEN** the gateway-owned attachment is closed and its process reaped
- **AND THEN** the agent and existing tmux clients continue running

#### Scenario: An unsafe detach configuration is active

- **WHEN** the effective tmux configuration would destroy the target on last detach or silently switch the client on target loss
- **THEN** admission refuses with an actionable diagnostic and leaves the session and its options intact

### Requirement: Installations include the browser terminal assets

Houmao wheels and source distributions SHALL include the terminal's browser-ready scripts, styles, and applicable license notices. Building from the source distribution and serving the viewer SHALL work with the standard Houmao Python installation and tmux, without Node, Bun, ttyd, or browser asset downloads.

#### Scenario: An installed gateway serves the viewer offline

- **WHEN** an operator installs a release wheel or a wheel rebuilt from the source distribution with Python tooling only
- **THEN** a browser can open the viewer and load every asset from the same gateway with outbound requests blocked
