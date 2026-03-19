## ADDED Requirements

### Requirement: Runtime can start sessions through an optional `houmao-server` REST backend
The runtime SHALL support an optional `houmao-server` REST-backed mode for live interactive sessions.

When that mode is selected, the runtime SHALL:

- create or attach the live session through `houmao-server`
- persist the `houmao-server` base URL plus session and terminal identity in the session manifest
- treat `houmao-server` as the server authority for later control operations
- keep any `houmao-server` upstream-adapter details out of the public runtime backend identity
- treat `houmao-server` as part of the supported `houmao-server + houmao-srv-ctrl` pair rather than as a mixed-pair bridge to raw `cao`

For supported loopback `houmao-server` base URLs, runtime-owned HTTP communication SHALL bypass ambient proxy environment variables by default by ensuring loopback entries exist in `NO_PROXY` and `no_proxy`.

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY` or `no_proxy` and will respect caller-provided values.

#### Scenario: Starting a `houmao-server` session persists server identity
- **WHEN** a developer starts a new interactive session using the `houmao-server` REST-backed mode
- **THEN** the runtime persists a session manifest that records the `houmao-server` base URL and terminal identity needed for resume and later control
- **AND THEN** subsequent runtime control does not need a separate CAO base URL override for that session

#### Scenario: Runtime does not promise mixed-pair bridging through `houmao-server`
- **WHEN** a developer uses the `houmao-server` REST-backed mode
- **THEN** the runtime treats that session as part of the `houmao-server` Houmao-managed path
- **AND THEN** it does not claim support for mixing that path with raw `cao` client workflows behind the scenes

#### Scenario: Loopback `houmao-server` communication bypasses ambient proxy env by default
- **WHEN** a developer starts or resumes a `houmao-server`-backed session using loopback base URL `http://127.0.0.1:9890`
- **AND WHEN** caller environment includes `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`
- **THEN** runtime-owned HTTP communication to that loopback `houmao-server` endpoint bypasses those proxy endpoints by default

### Requirement: `houmao-server` runtime sessions use a first-class persisted backend identity
Runtime-owned sessions that use the `houmao-server` REST-backed mode SHALL persist a first-class backend identity named `houmao_server_rest`.

Those persisted sessions SHALL use dedicated `houmao-server`-specific persisted sections rather than reusing `cao_rest`-specific sections for their public contract.

At minimum, the persisted `houmao-server` section SHALL carry the public `houmao-server` transport identity needed for resume and follow-up control, including:

- `api_base_url`
- server session identity
- terminal identity

The persisted public contract for `houmao_server_rest` SHALL keep child-CAO adapter details out of the runtime-owned manifest.

#### Scenario: Session manifest records `houmao_server_rest` rather than `cao_rest`
- **WHEN** a developer starts a runtime-owned session through the `houmao-server` REST-backed mode
- **THEN** the persisted session manifest records `backend = "houmao_server_rest"`
- **AND THEN** the manifest uses a dedicated `houmao-server` persisted section instead of overloading `cao` metadata

### Requirement: Runtime-owned artifacts remain authoritative for `houmao-server` sessions
For `houmao_server_rest` sessions, the runtime-owned session root and manifest SHALL remain the authoritative durable artifacts for later discovery and follow-up control.

When transitional shared-registry publication is used for a `houmao_server_rest` session, the registry runtime pointers SHALL point back to that runtime-owned manifest and session root.

Gateway and mailbox follow-up behavior that still depends on manifest-backed authority in v1 SHALL use those same runtime-owned artifacts for `houmao_server_rest` sessions.

#### Scenario: Registry and follow-up flows point back to the runtime-owned `houmao-server` manifest
- **WHEN** a `houmao_server_rest` session is published into the transitional shared registry
- **THEN** the registry runtime pointers reference the Houmao-owned session manifest and session root for that session
- **AND THEN** later resolution, gateway attach, and mailbox follow-up flows can keep using manifest-backed authority without reinterpreting the session as `cao_rest`

### Requirement: Runtime control of `houmao-server` sessions routes through `houmao-server`
For `houmao-server`-backed sessions, runtime control operations that inspect or mutate the live session SHALL route through `houmao-server` rather than bypassing it with direct CAO calls.

At minimum, `houmao-server`-routed operations in this change SHALL include:

- status inspection
- prompt submission
- control-input submission
- interrupt
- stop-session

When the runtime cannot reach the configured `houmao-server` for a `houmao-server`-backed session, runtime control SHALL fail explicitly. It SHALL NOT silently fall back to mutating the underlying CAO terminal directly behind `houmao-server`'s back.

Stopping a `houmao-server`-backed session through the runtime SHALL stop the live session through `houmao-server` and SHALL leave the persisted session in a stopped or unavailable condition consistent with the server response.

#### Scenario: Prompt submission for a `houmao-server` session goes through `houmao-server`
- **WHEN** a developer submits a prompt to a `houmao-server`-backed session
- **THEN** the runtime routes that request through the configured `houmao-server` endpoint
- **AND THEN** the runtime does not inject the prompt directly into CAO or another upstream backend outside `houmao-server`

#### Scenario: Stop-session for a `houmao-server` session does not bypass the server authority
- **WHEN** a developer stops a `houmao-server`-backed session through the runtime
- **THEN** the runtime routes that stop request through `houmao-server`
- **AND THEN** it does not bypass the server by directly deleting or interrupting the underlying CAO terminal
