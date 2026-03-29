## MODIFIED Requirements

### Requirement: Runtime launch resolves operator prompt policy from the actual tool version
When a resolved brain manifest requests an operator prompt policy that forbids startup operator prompts, the runtime SHALL resolve that policy against the actual installed CLI tool version and backend before starting the provider process.

Tool-version detection SHALL probe the actual launch executable with a subprocess `--version` call and SHALL fail unattended launch before provider start if the executable is missing or the version output cannot be parsed for that tool family.

Compatible strategy resolution SHALL match the detected executable version against launch-policy strategy declarations of supported version ranges rather than relying on nearest-lower or latest-known fallback.

When the resolved manifest requests `operator_prompt_mode = as_is`, the runtime SHALL NOT perform unattended strategy resolution, version-gated no-prompt mutation, or unattended-owned startup arg injection for that launch.

#### Scenario: Runtime detects tool version and selects a compatible unattended strategy
- **WHEN** a session starts from a brain manifest that requests `operator_prompt_mode = unattended`
- **AND WHEN** the detected tool version and backend match exactly one launch policy strategy's declared supported-version range
- **THEN** the runtime selects exactly one compatible strategy before starting the provider process
- **AND THEN** the runtime applies that strategy's launch actions for the resolved working directory and runtime home

#### Scenario: Missing or unparseable tool version blocks unattended launch
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** the selected launch executable is missing or its version output cannot be parsed for the requested tool family
- **THEN** the runtime fails the launch before provider start
- **AND THEN** the error reports the executable probe failure as the reason unattended resolution could not proceed

#### Scenario: As-is launch bypasses unattended strategy resolution
- **WHEN** a session starts from a brain manifest that requests `operator_prompt_mode = as_is`
- **THEN** the runtime does not require unattended strategy lookup before provider start
- **AND THEN** the runtime does not block launch solely because no unattended strategy exists for the detected tool version and backend

### Requirement: Runtime launch records launch policy provenance
The system SHALL persist and surface launch policy provenance for startup-prompt-forbidden launches using a typed `launch_policy_provenance` structure rather than only untyped backend metadata.

That typed provenance SHALL include at minimum:

- requested `operator_prompt_mode`
- detected tool version
- selected strategy identifier
- selection source
- override env var name when an override is active

When the runtime starts a session with `operator_prompt_mode = as_is`, it SHALL record the requested mode in launch-request metadata but SHALL NOT fabricate strategy provenance for a strategy that was never resolved.

#### Scenario: Session metadata records resolved unattended strategy
- **WHEN** the runtime starts a session using a resolved unattended launch strategy
- **THEN** persisted launch metadata includes a typed `launch_policy_provenance` structure with the requested policy mode, detected tool version, selected strategy identifier, and selection source
- **AND THEN** redacted session-facing metadata omits secret values while preserving strategy provenance for debugging

#### Scenario: As-is launch does not fabricate unattended provenance
- **WHEN** the runtime starts a session with `operator_prompt_mode = as_is`
- **THEN** session-facing launch metadata records that requested mode as part of launch-request diagnostics
- **AND THEN** the runtime does not persist a typed unattended strategy provenance block for that launch
