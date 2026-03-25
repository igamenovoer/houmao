## ADDED Requirements

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

## REMOVED Requirements

### Requirement: Houmao-owned profile store absorbs the minimum used CAO install behavior
**Reason**: The supported pair no longer uses a public install phase or a preinstalled compatibility profile store as the launch authority.

**Migration**: Resolve native launch targets at session creation time and synthesize any required compatibility artifacts internally from the native brain and optional role inputs.
