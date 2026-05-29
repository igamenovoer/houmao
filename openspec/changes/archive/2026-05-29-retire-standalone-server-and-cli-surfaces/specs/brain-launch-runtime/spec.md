## MODIFIED Requirements

### Requirement: Optional CAO backend via REST boundary
The system SHALL treat any retained CAO-compatible REST boundary as internal compatibility support rather than as a maintained public operator workflow.

The system MAY retain internal CAO-compatible session-control adapters through a REST boundary without requiring the core runtime to depend on CAO internals.

For supported operator workflows after this change, public runtime management SHALL NOT be exposed through `houmao-cli` flows that create or control standalone `cao_rest` sessions, and SHALL NOT migrate users to standalone `houmao-server` as the replacement public path.

The runtime MAY retain internal CAO-compatible adapter code for parity, debugging, or transition purposes, but public runtime-management CLI entrypoints that would create or control standalone CAO-backed sessions SHALL be absent or fail fast with explicit migration guidance to maintained `houmao-mgr` local workflows and `houmao-passive-server` API workflows.

That public deprecation guard SHALL reject deprecated `backend="cao_rest"` operator selections at the CLI entrypoint layer before standalone runtime-session construction begins.

For supported loopback compatibility authorities (`http://localhost:<port>`,
`http://127.0.0.1:<port>` with explicit ports), runtime-owned HTTP communication SHALL bypass ambient proxy environment variables by default by ensuring loopback entries exist in `NO_PROXY` and `no_proxy`.

When `HOUMAO_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY` or `no_proxy` and will respect caller-provided values.

When the runtime uses an internal compatibility authority, it SHALL pass the resolved working directory through to that authority as launch input and SHALL NOT impose a repo-owned validation rule that requires the workdir to live under the user home tree, the tool home, or a deprecated launcher home.

#### Scenario: Deprecated raw CAO-backed runtime start fails with migration guidance
- **WHEN** a developer invokes removed or deprecated runtime CLI compatibility code in a way that would start a standalone `cao_rest` session
- **THEN** the command exits non-zero with explicit guidance to use maintained `houmao-mgr` or `houmao-passive-server` workflows
- **AND THEN** it does not create a new standalone CAO-backed session as a supported operator workflow

#### Scenario: CLI rejects deprecated backend selection before runtime construction
- **WHEN** a developer runs a removed or deprecated public runtime CLI start path with `--backend cao_rest`
- **THEN** the CLI rejects that request with migration guidance before constructing a standalone `CaoRestSession`
- **AND THEN** internal parity or debugging code paths are not implied to be removed by that public CLI rejection

#### Scenario: Deprecated raw CAO-backed runtime control fails with migration guidance
- **WHEN** a developer invokes a runtime-management CLI command that would send input to, interrupt, or stop a standalone `cao_rest` session through the deprecated public path
- **THEN** the command exits non-zero with explicit guidance to move to maintained manager or passive-server workflows
- **AND THEN** it does not silently fall back to mutating standalone CAO state behind the user's back

#### Scenario: Loopback pair-compatible communication bypasses caller proxy env by default
- **WHEN** a developer starts or resumes an internal pair-compatible session using loopback authority `http://127.0.0.1:9990`
- **AND WHEN** caller environment includes `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`
- **THEN** runtime-owned HTTP communication to that loopback compatibility authority bypasses those proxy endpoints by default

### Requirement: Shared launch-policy application is used across raw and runtime-managed launches
The system SHALL apply unattended launch policy through one shared Python launch-policy entrypoint across generated raw launch helpers and maintained runtime-managed session backends.

Generated `launch.sh` helpers SHALL remain shell wrappers that invoke that shared Python entrypoint before the final tool `exec`.

#### Scenario: Raw launch helper uses the shared Python launch-policy entrypoint
- **WHEN** a generated brain `launch.sh` helper launches a brain with `operator_prompt_mode = unattended`
- **THEN** the shell helper invokes the shared Python launch-policy entrypoint before the final tool `exec`
- **AND THEN** raw helper launches resolve and apply the same unattended strategy family as runtime-managed launches

#### Scenario: Runtime-managed sessions use the same local launch-policy engine
- **WHEN** a maintained runtime-managed unattended launch starts through local managed, headless, joined, or passive-server-owned launch flow
- **THEN** the local runtime resolves and applies the same launch-policy engine before provider startup
- **AND THEN** maintained runtime-managed sessions do not bypass version detection, override handling, or fail-closed unattended checks

### Requirement: Runtime fails closed when the selected backend cannot honor a requested launch override
The system SHALL reject launch-override requests before provider start when the selected backend cannot honor the requested launch-overrides contract or when the request conflicts with backend-reserved controls.

The runtime SHALL NOT silently ignore unsupported launch-override requests as though they were effective.

#### Scenario: Backend launch rejects a launch override it cannot honor
- **WHEN** a resolved brain manifest requests a launch override that the selected maintained backend cannot support end to end
- **THEN** launch-plan composition fails before provider start
- **AND THEN** the error identifies that the rejected launch-override field is unsupported for that backend

#### Scenario: Runtime rejects a conflicting reserved protocol override
- **WHEN** a launch-overrides request attempts to remove, replace, or contradict a backend-reserved protocol control such as resume or machine-readable output mode
- **THEN** the runtime fails before provider start
- **AND THEN** the error identifies the request as conflicting with runtime-owned backend behavior

## REMOVED Requirements

### Requirement: Runtime can start sessions through an optional `houmao-server` REST backend

**Reason**: `houmao_server_rest` and standalone `houmao-server` are retired as public runtime/session backends.

**Migration**: Use maintained local/headless manager launch flows or passive-server API-managed headless launches.

### Requirement: `houmao-server` runtime sessions use a first-class persisted backend identity

**Reason**: The public persisted backend identity `houmao_server_rest` is retired.

**Migration**: Do not create new manifests with `backend = "houmao_server_rest"`; use maintained local/headless backend identities and passive-server authority metadata.

### Requirement: Runtime-owned artifacts remain authoritative for `houmao-server` sessions

**Reason**: New runtime-owned `houmao_server_rest` sessions are no longer supported.

**Migration**: Runtime-owned artifacts remain authoritative for maintained local/headless sessions; passive-server-owned managed agents use passive-server authority records.

### Requirement: Runtime control of `houmao-server` sessions routes through `houmao-server`

**Reason**: Runtime control through standalone old-server authority is retired.

**Migration**: Route maintained control through local manager/runtime controllers, gateway authority, or passive-server APIs according to the active session authority.

### Requirement: Pair-managed `houmao_server_rest` sessions are tmux-backed, reserve window 0, and publish stable gateway attachability before live attach

**Reason**: Pair-managed `houmao_server_rest` sessions are no longer a maintained launch/session mode.

**Migration**: Keep tmux window-0 and gateway-attachability guarantees on maintained local/headless/joined sessions where those requirements still apply.

### Requirement: Supported pair-managed tmux sessions keep the agent in window 0 while auxiliary windows remain non-authoritative

**Reason**: This requirement is anchored to pair-managed `houmao_server_rest` topology and old-server support state.

**Migration**: Apply auxiliary-window boundaries to maintained gateway/local runtime capabilities instead of referencing standalone `houmao-server`.
