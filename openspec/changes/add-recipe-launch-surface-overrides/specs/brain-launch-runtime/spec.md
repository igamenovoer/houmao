## ADDED Requirements

### Requirement: Runtime resolves the effective launch overrides for the selected backend before provider start
The system SHALL resolve the effective launch overrides during launch-plan composition using the resolved brain manifest, the selected backend, runtime launch policy, and backend-reserved protocol controls.

That resolution SHALL apply launch-override precedence in this order:

1. adapter-owned launch defaults persisted in the brain manifest
2. recipe-requested launch overrides persisted in the brain manifest
3. direct-build launch overrides when present in the manifest for that built brain
4. backend-aware launch-override translation and validation
5. runtime-owned launch policy application
6. backend-reserved protocol args and runtime continuity controls

#### Scenario: Runtime resolves a Claude headless launch override with a supported typed param
- **WHEN** a Claude brain manifest requests `launch_overrides.tool_params.include_partial_messages = true`
- **AND WHEN** the selected backend is `claude_headless`
- **THEN** launch-plan composition resolves that request into effective Claude headless launch behavior before provider start
- **AND THEN** the resulting launch plan preserves runtime-owned continuity and machine-readable output controls

### Requirement: Headless backend code owns only protocol-required launch args
For headless backends, runtime backend code SHALL own only the launch args and controls required by the headless protocol itself.

Optional provider launch behavior SHALL be resolved from declarative tool-launch metadata plus the requested `launch_overrides`, not invented as backend-only policy in headless `.py` code.

#### Scenario: Headless backend appends protocol-required args after optional launch resolution
- **WHEN** a headless launch uses optional provider behavior from tool-adapter defaults or `launch_overrides`
- **THEN** runtime resolution applies that optional behavior before final backend command assembly
- **AND THEN** the backend appends only the protocol-required headless args such as resume, machine-readable output mode, or provider-required subcommands

### Requirement: Runtime records effective launch-override provenance
The system SHALL persist and surface typed launch-override provenance for started sessions rather than exposing only one flattened executable-plus-args snapshot.

That provenance SHALL identify at minimum:

- the adapter-default launch snapshot used for the build
- the requested recipe or direct-build launch overrides
- the selected backend used for resolution
- the effective translated launch behavior after runtime resolution
- whether runtime launch policy or backend-reserved controls changed the final launch shape

#### Scenario: Session metadata explains why effective launch args differ from recipe intent
- **WHEN** a started session uses resolved launch behavior that differs from the raw requested override because runtime policy or backend-owned controls changed the final launch shape
- **THEN** persisted launch metadata records both the requested launch-overrides intent and the effective resolved launch behavior
- **AND THEN** debugging consumers can identify which layer changed the final launch plan

### Requirement: Runtime fails closed when the selected backend cannot honor a requested launch override
The system SHALL reject launch-override requests before provider start when the selected backend cannot honor the requested launch-overrides contract or when the request conflicts with backend-reserved controls.

The runtime SHALL NOT silently ignore unsupported launch-override requests as though they were effective.

#### Scenario: REST-backed launch rejects a launch override it cannot honor
- **WHEN** a resolved brain manifest requests a launch override that the selected `cao_rest` or `houmao_server_rest` backend does not support end to end
- **THEN** launch-plan composition fails before provider start
- **AND THEN** the error identifies that the rejected launch-override field is unsupported for that backend

#### Scenario: Runtime rejects a conflicting reserved protocol override
- **WHEN** a launch-overrides request attempts to remove, replace, or contradict a backend-reserved protocol control such as resume or machine-readable output mode
- **THEN** the runtime fails before provider start
- **AND THEN** the error identifies the request as conflicting with runtime-owned backend behavior

### Requirement: Runtime requires schema-version-2 brain manifests for the launch-overrides contract
Runtime launch planning for this contract SHALL require resolved brain manifests written with `schema_version = 2`.

The runtime SHALL NOT provide a compatibility reader that synthesizes the new launch-overrides contract from schema-version-1 manifests.

#### Scenario: Legacy schema-version-1 brain manifest is rejected with rebuild guidance
- **WHEN** a developer attempts to launch a brain home whose resolved brain manifest still uses `schema_version = 1`
- **THEN** launch-plan construction fails before provider start
- **AND THEN** the error directs the developer to rebuild the affected brain home with the current builder
