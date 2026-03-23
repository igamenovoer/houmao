## ADDED Requirements

### Requirement: Runtime resolves the effective launch surface for the selected backend before provider start
The system SHALL resolve the effective launch surface during launch-plan composition using the resolved brain manifest, the selected backend, runtime launch policy, and backend-reserved protocol controls.

That resolution SHALL apply launch-surface precedence in this order:

1. adapter-owned launch defaults persisted in the brain manifest
2. recipe-requested launch-surface overrides persisted in the brain manifest
3. direct-build launch-surface overrides when present in the manifest for that built brain
4. backend-aware launch-surface translation and validation
5. runtime-owned launch policy application
6. backend-reserved protocol args and runtime continuity controls

#### Scenario: Runtime resolves a Claude headless launch surface with a supported typed param
- **WHEN** a Claude brain manifest requests `launch_surface.tool_params.include_partial_messages = true`
- **AND WHEN** the selected backend is `claude_headless`
- **THEN** launch-plan composition resolves that request into an effective Claude headless launch surface before provider start
- **AND THEN** the resulting launch plan preserves runtime-owned continuity and machine-readable output controls

### Requirement: Headless backend code owns only protocol-required launch args
For headless backends, runtime backend code SHALL own only the launch args and controls required by the headless protocol itself.

Optional provider launch behavior SHALL be resolved from declarative tool-launch metadata plus the requested `launch_surface`, not invented as backend-only policy in headless `.py` code.

#### Scenario: Headless backend appends protocol-required args after optional launch resolution
- **WHEN** a headless launch uses optional provider behavior from tool-adapter defaults or `launch_surface`
- **THEN** runtime resolution applies that optional behavior before final backend command assembly
- **AND THEN** the backend appends only the protocol-required headless args such as resume, machine-readable output mode, or provider-required subcommands

### Requirement: Runtime records effective launch-surface provenance
The system SHALL persist and surface typed launch-surface provenance for started sessions rather than exposing only one flattened executable-plus-args snapshot.

That provenance SHALL identify at minimum:

- the adapter-default launch-surface snapshot used for the build
- the requested recipe or direct-build launch-surface overrides
- the selected backend used for resolution
- the effective translated launch surface after runtime resolution
- whether runtime launch policy or backend-reserved controls changed the final launch shape

#### Scenario: Session metadata explains why effective launch args differ from recipe intent
- **WHEN** a started session uses a resolved launch surface that differs from the raw requested override because runtime policy or backend-owned controls changed the final launch shape
- **THEN** persisted launch metadata records both the requested launch-surface intent and the effective resolved launch surface
- **AND THEN** debugging consumers can identify which layer changed the final launch plan

### Requirement: Runtime fails closed when the selected backend cannot honor a requested launch-surface override
The system SHALL reject launch-surface requests before provider start when the selected backend cannot honor the requested launch-surface contract or when the request conflicts with backend-reserved controls.

The runtime SHALL NOT silently ignore unsupported launch-surface requests as though they were effective.

#### Scenario: CAO-backed launch rejects a launch-surface request it cannot honor
- **WHEN** a resolved brain manifest requests a launch-surface override that the selected `cao_rest` backend does not support end to end
- **THEN** launch-plan composition fails before provider start
- **AND THEN** the error identifies that the rejected launch-surface field is unsupported for `cao_rest`

#### Scenario: Runtime rejects a conflicting reserved protocol override
- **WHEN** a launch-surface request attempts to remove, replace, or contradict a backend-reserved protocol control such as resume or machine-readable output mode
- **THEN** the runtime fails before provider start
- **AND THEN** the error identifies the request as conflicting with runtime-owned backend behavior
