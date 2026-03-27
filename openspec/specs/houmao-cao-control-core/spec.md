## Purpose
Define the Houmao-owned native control core that serves the CAO-compatible control slice for the supported pair.
## Requirements
### Requirement: Houmao-owned control core is the native authority for CAO-compatible session and terminal lifecycle
The system SHALL provide a Houmao-owned control core that is the authoritative implementation for the CAO-compatible control slice preserved by the supported pair.

That control core SHALL own at minimum:

- session creation and deletion
- terminal creation and deletion
- terminal metadata lookup
- working-directory lookup
- terminal output retrieval
- prompt input delivery
- control-input delivery
- exit delivery
- compatibility-surface health checks

The supported pair SHALL NOT require a supervised child `cao-server` process or an installed `cao` executable in order to satisfy those operations.

#### Scenario: Pair creates a compatibility terminal without a child CAO process
- **WHEN** `houmao-server` receives a supported `POST /cao/sessions/{session_name}/terminals` request
- **THEN** it satisfies that request through the Houmao-owned control core
- **AND THEN** the request does not depend on starting or reaching a separate child `cao-server` process

#### Scenario: Pair control works without installed `cao`
- **WHEN** `houmao-mgr` executes a supported CAO-compatible pair command that creates, inspects, or mutates a session
- **THEN** the command succeeds through Houmao-owned control components
- **AND THEN** it does not require `cao` to be installed on `PATH`

### Requirement: Control core keeps internal control models separate from CAO compatibility projection
The control core SHALL expose Houmao-owned internal models for live control and provider state, and it SHALL project CAO-compatible HTTP and CLI payloads through explicit compatibility adapters rather than reusing CAO payload types as the internal authority model.

Compatibility-only fields, route naming, and CLI wording SHALL remain confined to those projection adapters so that future upstream CAO behavior can be imported at clear insertion points without redefining the native control core.

#### Scenario: Internal control state projects into CAO-compatible terminal payloads
- **WHEN** the control core returns terminal state that includes Houmao-owned internal metadata
- **THEN** the `/cao/terminals/{terminal_id}` compatibility response projects the CAO-compatible fields required by the pinned contract
- **AND THEN** Houmao-only internal fields do not become the required native control model for the compatibility route

#### Scenario: Upstream provider behavior has an explicit insertion point
- **WHEN** maintainers decide to import a useful upstream CAO provider quirk or launch behavior
- **THEN** they update the relevant Houmao provider adapter or compatibility projection seam
- **AND THEN** they do not need to restore CAO as a runtime framework dependency to add that behavior

### Requirement: V1 control-core provider coverage preserves the current pair compatibility launch surface
The control core SHALL preserve the current pair compatibility launch surface accepted by `houmao-mgr launch` and `houmao-mgr cao launch` in v1.

At minimum, the v1 provider-adapter registry SHALL cover these provider identifiers:

- `kiro_cli`
- `claude_code`
- `codex`
- `gemini_cli`
- `kimi_cli`
- `q_cli`

If a later change intentionally retires or narrows that set, it SHALL do so explicitly rather than by leaving a previously supported pair provider unspecified during CAO absorption.

#### Scenario: Current pair compatibility provider identifiers remain launchable in v1
- **WHEN** a supported pair launch flow requests provider `kimi_cli`
- **THEN** the control core resolves that provider through a Houmao-owned provider adapter path
- **AND THEN** the pair does not require external CAO runtime delegation to satisfy that provider selection

### Requirement: Session-backed compatibility launch projects from native agent definitions at launch time
The control core SHALL resolve session-backed launch inputs from native agent definitions at launch time rather than from a preinstalled compatibility profile store.

At minimum, session-backed `create_session()` and `create_terminal()` behavior SHALL:

- resolve the effective native agent-definition root for the launch
- resolve the requested native selector to a supported v1 tool-lane recipe
- derive the native brain-home and launch inputs needed for provider startup
- construct any compatibility projection or provider-specific sidecars needed by the CAO-backed transport

The launch-time compatibility projection consumed by provider startup SHALL remain profile-shaped in v1 so existing provider-adapter command construction can continue using a synthesized compatibility-profile-like object while its source of truth moves to native launch data.

The control core SHALL NOT require a public install phase or persistent operator-managed compatibility profile state in order to launch a supported pair session.

Provider-specific profile-shaped sidecars MAY still be written internally when a provider requires them, but those artifacts SHALL be launch-scoped implementation details rather than preinstalled public state.

The first cut SHALL use ephemeral launch-scoped sidecars rather than a cross-session compatibility-artifact cache.

#### Scenario: Session creation resolves native launch inputs without preinstall
- **WHEN** the supported pair creates a session-backed agent through the Houmao-owned control core
- **THEN** the control core resolves that launch from native agent-definition inputs at launch time
- **AND THEN** the launch does not depend on a prior compatibility profile install step

#### Scenario: Provider-specific sidecars remain internal to launch-time projection
- **WHEN** a provider still requires a profile-shaped file or sidecar to start
- **THEN** the control core materializes that artifact from the resolved native launch target during launch
- **AND THEN** the operator does not manage that artifact through a separate public install workflow

### Requirement: Brain-only compatibility launch remains a supported empty-system-prompt case
For session-backed compatibility launch, the control core SHALL support native launch targets that have no role binding or no matching role package.

When that happens, the resolved role prompt SHALL be the empty string.

The control core SHALL treat that case as a valid brain-only launch, not as a compatibility-profile validation failure.

#### Scenario: Recipe-backed launch without role package stays valid
- **WHEN** the control core resolves a session-backed launch target that has a valid brain recipe and no role package
- **THEN** the launch remains valid
- **AND THEN** the provider starts with an empty system prompt rather than a missing-role error

### Requirement: Compatibility inbox queue remains terminal-scoped and separate from Houmao mailbox
Because the supported `/cao/*` compatibility surface remains exposed in v1, the CAO-compatible inbox route family under `/cao/terminals/{terminal_id}/inbox/messages` SHALL remain a terminal-scoped compatibility queue or minimal compatibility stub owned by the control core.

That compatibility inbox SHALL NOT become the Houmao mailbox transport, message store, unread-state model, or gateway notifier trigger.
The supported pair SHALL NOT replace those routes with a default unsupported-route error merely because Houmao mailbox remains separate.

#### Scenario: Compatibility inbox enqueue does not create a mailbox message
- **WHEN** a caller posts a CAO-compatible inbox message to `/cao/terminals/{terminal_id}/inbox/messages`
- **THEN** the control core records or delivers that message as terminal-scoped compatibility work
- **AND THEN** the Houmao mailbox store does not create a new mailbox message for that enqueue

#### Scenario: Compatibility inbox route remains supported in v1
- **WHEN** a caller uses one of the preserved `/cao/terminals/{terminal_id}/inbox/messages` routes in the supported pair
- **THEN** the control core returns the documented compatibility response shape
- **AND THEN** the server does not respond with an unsupported-route failure solely because mailbox and inbox remain separate

#### Scenario: Mailbox unread state is unaffected by compatibility inbox traffic
- **WHEN** compatibility inbox traffic wakes or queues work for a terminal
- **THEN** Houmao mailbox unread counts and gateway notifier decisions continue to depend only on mailbox state
- **AND THEN** they do not treat compatibility inbox records as mailbox messages

### Requirement: Pinned CAO source remains the control-core parity oracle
The control core SHALL treat the pinned CAO checkout as the parity oracle for CAO-compatible behavior and as a reference source for selectively importing future upstream capability changes.

The control core SHALL NOT require that oracle to be live in the supported product path in order to serve the pair.

#### Scenario: Control-core verification compares behavior to pinned CAO
- **WHEN** maintainers verify CAO-compatible control behavior after changing the Houmao control core
- **THEN** they compare the Houmao behavior against the pinned CAO source or an oracle built from it
- **AND THEN** the supported pair runtime still runs without CAO as a required dependency

### Requirement: Compatibility startup waits are config-backed and overrideable
The Houmao-owned CAO-compatible control core SHALL source its synchronous compatibility startup waits and provider warmup delays from supported server configuration rather than from unoverrideable inline operational timing literals.

At minimum, supported server configuration SHALL cover:

- shell-readiness timeout
- shell-readiness polling interval
- provider-readiness timeout
- provider-readiness polling interval
- Codex warmup delay

The default compatibility startup values SHALL be:

- shell-readiness timeout = `10.0` seconds
- shell-readiness polling interval = `0.5` seconds
- provider-readiness timeout = `45.0` seconds
- provider-readiness polling interval = `1.0` seconds
- Codex warmup delay = `2.0` seconds

The Codex warmup delay override SHALL allow `0.0` so operators can disable the delay explicitly.

When operators do not override these values, the control core SHALL preserve the documented defaults above.

#### Scenario: Default server config preserves compatibility startup defaults
- **WHEN** `houmao-server` starts without explicit compatibility startup timeout overrides
- **THEN** compatibility session and terminal creation use the documented default startup waits and warmup delay
- **AND THEN** the server does not require source edits to keep those defaults

#### Scenario: Server override changes compatibility startup timing
- **WHEN** `houmao-server` starts with explicit compatibility startup timing overrides
- **THEN** compatibility session and terminal creation use those configured startup waits instead of inline literals
- **AND THEN** setting the configured Codex warmup delay to `0.0` disables the extra Codex sleep
