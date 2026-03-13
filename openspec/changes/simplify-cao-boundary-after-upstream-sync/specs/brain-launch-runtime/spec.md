## MODIFIED Requirements

### Requirement: Optional CAO backend via REST boundary
The system SHALL optionally support launching and driving sessions via CAO
using CAO's REST API, without requiring the core runtime to depend on CAO
internals.

For supported loopback CAO base URLs (`http://localhost:<port>`,
`http://127.0.0.1:<port>` with explicit ports), runtime-owned CAO HTTP
communication SHALL bypass ambient proxy environment variables by default by
ensuring loopback entries exist in `NO_PROXY`/`no_proxy`.

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY`
or `no_proxy` and will respect caller-provided values (for example, to enable
traffic-watching development proxies).

When starting a CAO-backed session, the runtime SHALL pass the resolved working
directory through to CAO as launch input and SHALL NOT impose a repo-owned
validation rule that requires the workdir to live under the user home tree, the
tool home, or the launcher home.

#### Scenario: CAO-backed session launch and messaging
- **WHEN** a developer starts a CAO-backed session and provides a CAO API base URL at session start
- **THEN** the system creates a CAO session/terminal using the resolved working directory, sends prompts, and fetches replies using CAO REST endpoints
- **AND THEN** the system persists the CAO API base URL and terminal identity in the session manifest
- **AND THEN** subsequent prompt and stop operations target the CAO terminal using only the persisted session manifest fields (no CAO base URL override)

#### Scenario: Loopback CAO runtime communication bypasses caller proxy env on a non-default port
- **WHEN** a developer starts or resumes a CAO-backed session using loopback CAO base URL `http://127.0.0.1:9991`
- **AND WHEN** caller environment includes `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`
- **THEN** runtime-owned CAO HTTP communication bypasses those proxy endpoints by default
- **AND THEN** loopback CAO connectivity depends on local CAO availability rather than external proxy availability

#### Scenario: Preserve mode respects caller `NO_PROXY` for loopback
- **WHEN** a developer starts or resumes a CAO-backed session using a supported loopback CAO base URL
- **AND WHEN** caller environment includes `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`
- **THEN** runtime-owned CAO HTTP communication uses caller-provided proxy and `NO_PROXY` settings

#### Scenario: CAO-backed launch does not reject a workdir outside launcher home
- **WHEN** a developer starts a CAO-backed session whose resolved workdir is outside the launcher home or user home tree
- **AND WHEN** the installed CAO server accepts that workdir
- **THEN** the runtime passes the resolved workdir through to CAO
- **AND THEN** the runtime does not fail solely because that workdir is outside those home paths

### Requirement: CAO parsing mode is explicit and constrained
For CAO-backed sessions, the system SHALL resolve a parsing mode at session start from configuration.

Allowed values are exactly:
- `cao_only`
- `shadow_only`

The selected mode SHALL be persisted in session runtime state so resumed operations use the same parsing mode.

`cao_only` SHALL remain the generic CAO-native mode for CAO-backed sessions.
`shadow_only` SHALL be used only for tools that have a runtime-owned shadow parser family.

Default mapping SHALL be:
- `tool=claude` -> `shadow_only`
- `tool=codex` -> `shadow_only`

#### Scenario: Session start resolves parsing mode from tool default (Claude)
- **WHEN** a caller starts a CAO-backed session without explicitly specifying parsing mode
- **AND WHEN** the tool is `claude`
- **THEN** the resolved parsing mode is `shadow_only`

#### Scenario: Session start resolves parsing mode from tool default (Codex)
- **WHEN** a caller starts a CAO-backed session without explicitly specifying parsing mode
- **AND WHEN** the tool is `codex`
- **THEN** the resolved parsing mode is `shadow_only`

#### Scenario: Session start accepts explicit `cao_only`
- **WHEN** a caller starts a CAO-backed session and explicitly specifies `parsing_mode=cao_only`
- **THEN** the resolved parsing mode is `cao_only`

#### Scenario: Session start fails when parsing mode cannot be resolved
- **WHEN** a caller starts a CAO-backed session and configuration does not provide an explicit parsing mode or a valid tool default
- **THEN** the system rejects the start request with an explicit validation error

#### Scenario: Unknown parsing mode is rejected
- **WHEN** a caller requests a parsing mode other than `cao_only` or `shadow_only`
- **THEN** the system rejects the request with an explicit unsupported-mode error

#### Scenario: `shadow_only` is rejected when no runtime shadow parser exists
- **WHEN** a caller requests `parsing_mode=shadow_only` for a CAO-backed tool that does not have a runtime-owned shadow parser family
- **THEN** the system rejects the request with an explicit unsupported-mode error
