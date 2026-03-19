## ADDED Requirements

### Requirement: `houmao-server` exposes a pair-owned install surface for child-managed profile state
`houmao-server` SHALL expose a Houmao-owned install surface that lets paired clients install agent profiles into the server-managed child CAO state without direct access to the hidden `child_cao` filesystem layout.

That install surface SHALL accept the install inputs needed by the supported pair, including the provider plus agent source or profile reference needed for the install operation.

`houmao-server` SHALL resolve child-managed filesystem state internally. The public contract SHALL NOT require callers to provide or compute child-home paths or other `child_cao` storage details.

#### Scenario: Pair client installs profile through the public server authority
- **WHEN** a paired client submits a profile-install request to `houmao-server` for provider `codex`
- **THEN** `houmao-server` performs that install against its managed child CAO state
- **AND THEN** the caller does not need to inspect or mutate the hidden `child_cao` filesystem layout directly

#### Scenario: Failed pair-owned install returns an explicit server-owned error
- **WHEN** the underlying install operation fails while `houmao-server` is handling a pair-owned install request
- **THEN** `houmao-server` returns an explicit failure through the public Houmao surface
- **AND THEN** the caller does not need to infer failure indirectly from missing files under internal child storage

### Requirement: Session detail responses preserve terminal summary metadata needed by pair clients
For the CAO-compatible `GET /sessions/{session_name}` route, `houmao-server` SHALL preserve the session-detail structure and terminal-summary metadata exposed by the supported CAO source closely enough that paired Houmao clients can consume that response as a typed contract.

At minimum, the session-detail response SHALL let a pair client identify the created terminal id together with the tmux session and tmux window metadata carried by the supported CAO session summary.

#### Scenario: Session detail exposes terminal window metadata for paired clients
- **WHEN** a caller queries `GET /sessions/{session_name}` through `houmao-server` for a live session whose terminal summary includes tmux window metadata in the supported CAO source
- **THEN** the `houmao-server` response preserves that terminal summary metadata on the compatibility route
- **AND THEN** paired Houmao clients can persist that tmux window identity into registration or runtime artifacts without scraping unrelated routes

#### Scenario: Session detail remains compatible for callers that ignore extra terminal summary fields
- **WHEN** a CAO-compatible caller reads the `GET /sessions/{session_name}` response but ignores terminal summary fields it does not use
- **THEN** the compatibility response still succeeds as a valid session-detail view
- **AND THEN** preserving tmux session or window metadata does not force callers onto a separate Houmao-only route just to use the pair
