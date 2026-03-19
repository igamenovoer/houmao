## ADDED Requirements

### Requirement: Runtime can start sessions through an optional `houmao-server` REST backend
The runtime SHALL support an optional `houmao-server` REST-backed mode for live interactive sessions.

When that mode is selected, the runtime SHALL:

- create or attach the live session through `houmao-server`
- persist the `houmao-server` base URL plus session and terminal identity in the session manifest
- treat `houmao-server` as the server authority for later control operations
- keep any `houmao-server` upstream-adapter details out of the public runtime backend identity

For supported loopback `houmao-server` base URLs, runtime-owned HTTP communication SHALL bypass ambient proxy environment variables by default by ensuring loopback entries exist in `NO_PROXY` and `no_proxy`.

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY` or `no_proxy` and will respect caller-provided values.

#### Scenario: Starting a `houmao-server` session persists server identity
- **WHEN** a developer starts a new interactive session using the `houmao-server` REST-backed mode
- **THEN** the runtime persists a session manifest that records the `houmao-server` base URL and terminal identity needed for resume and later control
- **AND THEN** subsequent runtime control does not need a separate CAO base URL override for that session

#### Scenario: Loopback `houmao-server` communication bypasses ambient proxy env by default
- **WHEN** a developer starts or resumes a `houmao-server`-backed session using loopback base URL `http://127.0.0.1:9890`
- **AND WHEN** caller environment includes `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`
- **THEN** runtime-owned HTTP communication to that loopback `houmao-server` endpoint bypasses those proxy endpoints by default

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
