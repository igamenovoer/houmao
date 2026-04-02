## ADDED Requirements

### Requirement: Gemini easy specialists default to unattended headless launch posture
`houmao-mgr project easy specialist create --tool gemini` SHALL treat Gemini as a maintained unattended easy-launch lane for headless use.

By default, Gemini easy specialists SHALL persist `launch.prompt_mode: unattended` into both the project-local specialist metadata and the generated compatibility preset.

`--no-unattended` SHALL remain the explicit opt-out that persists `launch.prompt_mode: as_is`.

`houmao-mgr project easy instance launch` SHALL continue to require `--headless` for Gemini specialists even when the stored specialist launch posture is unattended.

#### Scenario: Default Gemini easy specialist persists unattended launch posture
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name gemini-reviewer --tool gemini --api-key gm-test`
- **THEN** the persisted specialist metadata records `launch.prompt_mode: unattended`
- **AND THEN** the generated compatibility preset records the same unattended launch posture

#### Scenario: Gemini easy specialist can still opt out to as-is launch posture
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name gemini-reviewer --tool gemini --api-key gm-test --no-unattended`
- **THEN** the persisted specialist metadata records `launch.prompt_mode: as_is`
- **AND THEN** the generated compatibility preset records the same `as_is` launch posture

#### Scenario: Gemini easy instance launch remains headless-only
- **WHEN** a Gemini specialist already exists
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist gemini-reviewer --name gemini-reviewer-1` without `--headless`
- **THEN** the command fails clearly
- **AND THEN** it identifies that Gemini specialists remain headless-only on the easy instance surface
