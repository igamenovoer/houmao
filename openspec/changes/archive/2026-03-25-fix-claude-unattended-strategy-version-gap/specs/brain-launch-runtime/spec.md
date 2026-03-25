## MODIFIED Requirements

### Requirement: Runtime launch resolves operator prompt policy from the actual tool version
When a resolved brain manifest requests an operator prompt policy that forbids startup operator prompts, the runtime SHALL resolve that policy against the actual installed CLI tool version and backend before starting the provider process.

Tool-version detection SHALL probe the actual launch executable with a subprocess `--version` call and SHALL fail unattended launch before provider start if the executable is missing or the version output cannot be parsed for that tool family.

Compatible strategy resolution SHALL match the detected executable version against launch-policy strategy declarations of supported version ranges rather than relying on nearest-lower or latest-known fallback.

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

### Requirement: Runtime supports a transient strategy override for controlled experiments
The runtime SHALL support `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY=<strategy-id>` as a transient strategy-selection override for controlled unattended-launch experiments.

For runtime-managed launches, the override SHALL be read from the launch caller's process environment during launch-plan composition even when the selected runtime env payload does not otherwise project that variable into the provider's final runtime environment.

The runtime SHALL NOT persist that override into brain recipes or resolved brain manifests, and it SHALL NOT require the override variable to be present in the selected credential-env allowlist solely for strategy resolution.

#### Scenario: Environment override selects a specific unattended strategy
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` is set to a known compatible strategy id
- **THEN** the runtime selects that strategy instead of normal version-based lookup
- **AND THEN** `launch_policy_provenance` records that selection source was an environment override
- **AND THEN** the resolved brain manifest remains unchanged

#### Scenario: Runtime-managed launch sees process-level strategy override
- **WHEN** a runtime-managed session requests `operator_prompt_mode = unattended`
- **AND WHEN** the parent process environment sets `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY`
- **AND WHEN** the selected runtime env payload does not include that variable
- **THEN** launch-plan policy resolution still honors the override for strategy selection
- **AND THEN** the override variable is not required to be injected into the provider's final runtime env solely to make the override work

#### Scenario: Override does not change the detected executable version
- **WHEN** a runtime-managed session requests `operator_prompt_mode = unattended`
- **AND WHEN** `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` selects a known strategy id
- **THEN** the runtime still records the real detected executable version in launch-policy provenance and diagnostics
- **AND THEN** the override changes strategy selection without pretending the executable is a different version

### Requirement: Runtime refuses startup-prompt-forbidden launch when policy cannot be satisfied
The system SHALL fail before provider process start when a requested startup-prompt-forbidden launch policy cannot be satisfied for the detected tool version, backend, or launch context.

That failure SHALL preserve enough structured detail for higher-level launch surfaces to report that backend selection completed but provider startup was blocked by launch-policy compatibility.

#### Scenario: Unsupported version blocks unattended launch before provider start
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** no compatible strategy exists for the detected tool version and backend under the declared supported-version ranges
- **THEN** the runtime fails the launch before starting the provider process
- **AND THEN** the error identifies the requested policy, tool, backend, and detected version
- **AND THEN** higher-level callers can distinguish that no provider process was started

#### Scenario: Unsupported unattended backend fails closed
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** the selected backend is `gemini_headless` and no unattended strategy family exists for that backend
- **THEN** the runtime fails the launch before starting the provider process
- **AND THEN** the error identifies that unattended Gemini support is not part of this change
