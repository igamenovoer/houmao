## ADDED Requirements

### Requirement: Pair-targeted install routes through `houmao-server`
When an operator targets a supported Houmao pair instance while installing an agent profile, `houmao-srv-ctrl` SHALL route that install through `houmao-server` rather than mutating whichever ambient local `HOME` happens to be active.

At minimum, `houmao-srv-ctrl install` SHALL support an additive `--port` selector that identifies the target public `houmao-server` listener.

When `--port` is present, `houmao-srv-ctrl` SHALL verify the supported pair before performing the install and SHALL report success or failure from that server-owned install path.

When `--port` is absent, CAO-compatible local install delegation MAY remain available as the non-pair-targeted behavior.

#### Scenario: Pair-targeted install does not require child-home knowledge
- **WHEN** an operator runs `houmao-srv-ctrl install projection-demo --provider codex --port 19989`
- **THEN** `houmao-srv-ctrl` targets the supported `houmao-server` instance at the selected public port
- **AND THEN** the install mutates that server's child-managed profile state without requiring the caller to know or compute any hidden child-home path

#### Scenario: Pair-targeted install rejects unsupported pair targets explicitly
- **WHEN** an operator runs `houmao-srv-ctrl install ... --port <port>` against an endpoint that is not a supported `houmao-server` pair target
- **THEN** `houmao-srv-ctrl` fails explicitly before performing a local delegated install
- **AND THEN** the operator does not accidentally mutate unrelated local CAO state while trying to target a pair instance

#### Scenario: Non-targeted install remains an additive extension
- **WHEN** an operator runs `houmao-srv-ctrl install projection-demo --provider codex` without `--port`
- **THEN** the command still accepts the CAO-compatible invocation shape without requiring Houmao-only targeting flags
- **AND THEN** pair-targeted routing remains an additive extension rather than a mandatory argument

### Requirement: Delegated launch preserves authoritative tmux window identity
When `houmao-srv-ctrl launch` completes successfully inside the supported pair, it SHALL recover tmux window identity from the pair authority's session-detail response and SHALL persist that window identity into Houmao-owned registration and runtime artifacts whenever the metadata is available.

This preservation SHALL use the authoritative session-detail response rather than deriving tmux window identity from `terminal_id` or another unrelated field.

#### Scenario: Launch registration preserves tmux window identity from session detail
- **WHEN** `houmao-srv-ctrl launch` receives a successful session-detail response whose terminal summary includes tmux window metadata
- **THEN** `houmao-srv-ctrl` includes that tmux window identity in the registration payload sent to `houmao-server`
- **AND THEN** the corresponding Houmao-owned runtime artifacts persist the same window identity for later tracking and resume flows

#### Scenario: Missing tmux window metadata does not fabricate a value
- **WHEN** a successful delegated launch does not expose tmux window metadata in the session-detail response
- **THEN** `houmao-srv-ctrl` leaves that field unset in its Houmao-owned follow-up artifacts
- **AND THEN** the CLI does not invent a replacement value from `terminal_id` or another incompatible field
