## ADDED Requirements

### Requirement: Runtime launch resolves operator prompt policy from the actual tool version
When a resolved brain manifest requests an operator prompt policy that forbids startup operator prompts, the runtime SHALL resolve that policy against the actual installed CLI tool version and backend before starting the provider process.

Tool-version detection SHALL probe the actual launch executable with a subprocess `--version` call and SHALL fail unattended launch before provider start if the executable is missing or the version output cannot be parsed for that tool family.

#### Scenario: Runtime detects tool version and selects a compatible unattended strategy
- **WHEN** a session starts from a brain manifest that requests `operator_prompt_mode = unattended`
- **AND WHEN** the detected tool version and backend match a compatible launch policy strategy
- **THEN** the runtime selects exactly one compatible strategy before starting the provider process
- **AND THEN** the runtime applies that strategy's launch actions for the resolved working directory and runtime home

#### Scenario: Missing or unparseable tool version blocks unattended launch
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** the runtime cannot execute or parse `<tool> --version` for the selected executable
- **THEN** the runtime fails the launch before provider start
- **AND THEN** the error reports the executable probe failure as the reason unattended resolution could not proceed

### Requirement: Runtime unattended launch can synthesize provider startup state from minimal credentials
When unattended launch is requested, the runtime SHALL allow the selected strategy to synthesize or patch runtime-owned provider config/state from minimal credential inputs and minimal caller launch args.

The runtime SHALL NOT require pre-existing user-owned tool config files solely to suppress startup prompts.

#### Scenario: Fresh runtime home launches unattended from minimal provider credentials
- **WHEN** a session starts from a brain manifest that requests `operator_prompt_mode = unattended`
- **AND WHEN** the runtime home is fresh and only normal credential inputs are available for the selected tool, such as `auth.json`, API-key env vars, or an env-only custom-provider configuration that disables built-in login
- **THEN** the selected strategy may create or patch runtime-owned provider config/state before process start
- **AND THEN** unattended launch does not depend on pre-existing user-authored no-prompt config files

### Requirement: Runtime launch records launch policy provenance
The system SHALL persist and surface launch policy provenance for startup-prompt-forbidden launches using a typed `launch_policy_provenance` structure rather than only untyped backend metadata.

That typed provenance SHALL include at minimum:

- requested `operator_prompt_mode`
- detected tool version
- selected strategy identifier
- selection source
- override env var name when an override is active

#### Scenario: Session metadata records resolved unattended strategy
- **WHEN** the runtime starts a session using a resolved unattended launch strategy
- **THEN** persisted launch metadata includes a typed `launch_policy_provenance` structure with the requested policy mode, detected tool version, selected strategy identifier, and selection source
- **AND THEN** redacted session-facing metadata omits secret values while preserving strategy provenance for debugging

### Requirement: Runtime supports a transient strategy override for controlled experiments
The runtime SHALL support `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY=<strategy-id>` as a transient strategy-selection override for controlled unattended-launch experiments.

The runtime SHALL NOT persist that override into brain recipes or resolved brain manifests.

#### Scenario: Environment override selects a specific unattended strategy
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` is set to a known compatible strategy id
- **THEN** the runtime selects that strategy instead of normal version-based lookup
- **AND THEN** `launch_policy_provenance` records that selection source was an environment override
- **AND THEN** the resolved brain manifest remains unchanged

### Requirement: Runtime refuses startup-prompt-forbidden launch when policy cannot be satisfied
The system SHALL fail before provider process start when a requested startup-prompt-forbidden launch policy cannot be satisfied for the detected tool version, backend, or launch context.

#### Scenario: Unsupported version blocks unattended launch before provider start
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** no compatible strategy exists for the detected tool version and backend
- **THEN** the runtime fails the launch before starting the provider process
- **AND THEN** the error identifies the requested policy, tool, backend, and detected version

#### Scenario: Unsupported unattended backend fails closed
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** the selected backend is `gemini_headless` and no unattended strategy family exists for that backend
- **THEN** the runtime fails the launch before starting the provider process
- **AND THEN** the error identifies that unattended Gemini support is not part of this change

### Requirement: Runtime unattended launch covers startup operator prompts beyond classic permission dialogs
For `operator_prompt_mode = unattended`, the runtime SHALL treat version-supported startup operator prompts that block provider readiness as part of the launch policy surface, even when those prompts are not labeled as permission prompts by the provider.

#### Scenario: Codex startup prompt is suppressed even when it is a model migration notice
- **WHEN** a supported Codex version would otherwise stop at a startup model migration notice after trust and approval defaults are already satisfied
- **AND WHEN** `operator_prompt_mode = unattended`
- **THEN** the selected strategy treats that startup notice as part of unattended launch compatibility
- **AND THEN** the session either starts without that prompt or fails before provider start if no compatible suppression strategy exists

### Requirement: Shared launch-policy application is used across raw and runtime-managed launches
The system SHALL apply unattended launch policy through one shared Python launch-policy entrypoint across generated raw launch helpers and runtime-managed session backends.

Generated `launch.sh` helpers SHALL remain shell wrappers that invoke that shared Python entrypoint before the final tool `exec`.

#### Scenario: Raw launch helper uses the shared Python launch-policy entrypoint
- **WHEN** a generated brain `launch.sh` helper launches a brain with `operator_prompt_mode = unattended`
- **THEN** the shell helper invokes the shared Python launch-policy entrypoint before the final tool `exec`
- **AND THEN** raw helper launches resolve and apply the same unattended strategy family as runtime-managed launches

#### Scenario: CAO-backed sessions use the same local launch-policy engine
- **WHEN** a runtime-managed unattended launch starts through `cao_rest` or `houmao_server_rest`
- **THEN** the local runtime resolves and applies the same launch-policy engine before CAO-compatible terminal startup
- **AND THEN** CAO-backed sessions do not bypass version detection, override handling, or fail-closed unattended checks

### Requirement: Strategy-owned launch args are not silently overridden
When unattended launch is requested, the selected strategy SHALL own the no-prompt CLI args it requires.

The runtime SHALL normalize exact duplicate strategy-owned args but SHALL reject contradictory `launch_args_override` input before provider start.

#### Scenario: Conflicting launch override blocks unattended launch
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** caller-supplied `launch_args_override` conflicts with a strategy-owned no-prompt arg or removes required strategy behavior
- **THEN** the runtime fails the launch before provider start
- **AND THEN** the error identifies the conflicting override and selected strategy
