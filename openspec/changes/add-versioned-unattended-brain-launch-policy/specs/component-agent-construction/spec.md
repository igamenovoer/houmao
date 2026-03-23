## ADDED Requirements

### Requirement: Brain construction accepts operator prompt policy intent
The system SHALL let callers declare an operator prompt policy when constructing a brain, including a mode that requests unattended launch behavior where startup operator prompts are forbidden.

The selected policy SHALL be available through:

- declarative recipe YAML at `launch_policy.operator_prompt_mode`
- direct build inputs at `BuildRequest.operator_prompt_mode`

Allowed values SHALL be `interactive` and `unattended`. Omitting the field SHALL preserve the normal interactive/default launch posture.

#### Scenario: Developer constructs a brain with unattended prompt policy
- **WHEN** a developer constructs a brain using direct inputs or a declarative recipe that requests `operator_prompt_mode = unattended`
- **THEN** the construction input includes that requested launch policy alongside tool, skills, config profile, and credential profile
- **AND THEN** the requested policy remains secret-free metadata that does not embed API keys, tokens, inline credential material, or credential file contents

### Requirement: Brain manifest persists unresolved launch policy intent
The system SHALL persist requested operator prompt policy in the resolved brain manifest as abstract launch intent rather than as pre-resolved provider-version-specific CLI flags or runtime state patches.

The resolved manifest SHALL store that request at `launch_policy.operator_prompt_mode`.

#### Scenario: Manifest records unattended intent without provider-specific patch details
- **WHEN** a brain is constructed with `operator_prompt_mode = unattended`
- **THEN** the resolved brain manifest records that requested policy at `launch_policy.operator_prompt_mode`
- **AND THEN** the manifest does not treat version-resolved strategy ids, provider trust entries, or concrete injected CLI args as construction-time inputs

### Requirement: Brain construction does not require tool-specific no-prompt config as input
The system SHALL allow callers to request unattended launch without supplying user-authored per-tool config/state files whose only purpose is suppressing startup prompts.

The resolved brain manifest SHALL continue to capture credential/profile references and abstract unattended intent, while leaving runtime-owned prompt-suppression config synthesis to launch-time strategy resolution.

#### Scenario: Developer requests unattended launch with minimal credential inputs
- **WHEN** a developer constructs a brain with `operator_prompt_mode = unattended`
- **AND WHEN** they provide only the normal credential inputs for that tool family, such as API-key env vars, endpoint env vars, or `auth.json`
- **THEN** brain construction succeeds without requiring extra user-authored no-prompt config files
- **AND THEN** the manifest records abstract unattended intent rather than synthetic provider config contents
