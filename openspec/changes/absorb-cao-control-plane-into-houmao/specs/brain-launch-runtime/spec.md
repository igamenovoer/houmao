## MODIFIED Requirements

### Requirement: Optional CAO backend via REST boundary
The system SHALL optionally support CAO-compatible session control through a REST boundary without requiring the core runtime to depend on CAO internals.

For supported operator workflows after this change, that CAO-compatible control SHALL be reached through the Houmao-owned pair authority rather than through public `houmao-cli` flows that create or control standalone `cao_rest` sessions.

The runtime MAY retain internal CAO-compatible adapter code for parity, debugging, or transition purposes, but public runtime-management CLI entrypoints that would create or control standalone CAO-backed sessions SHALL fail fast with explicit migration guidance to `houmao-server` and `houmao-srv-ctrl`.

For supported loopback compatibility authorities (`http://localhost:<port>`,
`http://127.0.0.1:<port>` with explicit ports), runtime-owned HTTP communication SHALL bypass ambient proxy environment variables by default by ensuring loopback entries exist in `NO_PROXY` and `no_proxy`.

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY` or `no_proxy` and will respect caller-provided values.

When the runtime uses a pair-backed compatibility authority internally, it SHALL pass the resolved working directory through to that authority as launch input and SHALL NOT impose a repo-owned validation rule that requires the workdir to live under the user home tree, the tool home, or a deprecated launcher home.

#### Scenario: Deprecated raw CAO-backed runtime start fails with migration guidance
- **WHEN** a developer invokes `houmao-cli` in a way that would start a standalone `cao_rest` session
- **THEN** the command exits non-zero with explicit guidance to use `houmao-server` and `houmao-srv-ctrl`
- **AND THEN** it does not create a new standalone CAO-backed session as a supported operator workflow

#### Scenario: Deprecated raw CAO-backed runtime control fails with migration guidance
- **WHEN** a developer invokes a runtime-management CLI command that would send input to, interrupt, or stop a standalone `cao_rest` session through the deprecated public path
- **THEN** the command exits non-zero with explicit guidance to move to the supported pair
- **AND THEN** it does not silently fall back to mutating standalone CAO state behind the user's back

#### Scenario: Loopback pair-compatible communication bypasses caller proxy env by default
- **WHEN** a developer starts or resumes a pair-backed compatibility session using loopback authority `http://127.0.0.1:9990`
- **AND WHEN** caller environment includes `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`
- **THEN** runtime-owned HTTP communication to that loopback compatibility authority bypasses those proxy endpoints by default
