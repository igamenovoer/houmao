## ADDED Requirements

### Requirement: Config draft intent failures include draft-specific fix guides
`houmao-mgr internals config-drafts generate --intent` SHALL include a draft-specific fix guide when the supplied intent JSON cannot be parsed or does not satisfy the selected draft's expected intent shape.

The fix guide SHALL include the selected config-draft id, the `--intent` input source, a JSON Schema-style expected shape, and a valid example for the selected draft id. For initial config drafts, the expected shape SHALL show a top-level object with an object-valued `fields` property.

The fix guide SHALL identify required fields and allowed enum values from the selected `ConfigDraft` metadata.

#### Scenario: Flat specialist intent explains fields wrapper
- **WHEN** an agent runs `houmao-mgr internals config-drafts generate --id project.specialist --intent '{"name":"general-kimi","tool":"claude","credential":"kimi-coding"}'`
- **THEN** the command fails with a diagnostic that explains the intent fields must be nested under a top-level `fields` object
- **AND THEN** the diagnostic includes a JSON Schema-style shape requiring `fields.name`, `fields.tool`, and `fields.credential`
- **AND THEN** the diagnostic includes an example shaped as `{"fields":{"name":"general-kimi","tool":"claude","credential":"kimi-coding"}}`
- **AND THEN** the diagnostic does not suggest that shell quoting is the primary fix

#### Scenario: Missing required draft field still shows schema and example
- **WHEN** an agent runs `houmao-mgr internals config-drafts generate --id project.profile --intent '{"fields":{"name":"reviewer-fast","specialist":"reviewer"}}'`
- **THEN** the command fails with a diagnostic that identifies `credential` as missing
- **AND THEN** the diagnostic includes a JSON Schema-style shape requiring `fields.name`, `fields.specialist`, and `fields.credential`
- **AND THEN** the diagnostic includes a valid `project.profile` example

#### Scenario: Invalid enum value shows allowed choices
- **WHEN** an agent runs `houmao-mgr internals config-drafts generate --id project.specialist --intent '{"fields":{"name":"reviewer","tool":"openai","credential":"reviewer-creds"}}'`
- **THEN** the command fails with a diagnostic that identifies `tool` as invalid
- **AND THEN** the diagnostic includes the allowed `tool` choices from the config-draft metadata
- **AND THEN** the diagnostic includes a valid `project.specialist` example

#### Scenario: Invalid JSON still shows selected draft guidance
- **WHEN** an agent runs `houmao-mgr internals config-drafts generate --id project.profile --intent '{"fields":'`
- **THEN** the command fails with a diagnostic that identifies invalid JSON
- **AND THEN** the diagnostic includes the selected `project.profile` intent schema and example when the draft id is registered

### Requirement: Config draft JSON guidance is reflected in agent-facing docs and skills
Agent-facing guidance for config-draft generation SHALL show the object-valued `fields` mapping in command examples or nearby prose wherever it instructs agents to pass JSON to `houmao-mgr internals config-drafts generate --intent`.

Packaged system skills SHALL NOT use bare `--intent '<json>'` as the only example for config-draft generation when the expected envelope matters for correct execution.

#### Scenario: Agent-definition skill shows fields envelope
- **WHEN** an agent reads packaged `houmao-agent-definition` guidance for specialist, profile, launch-dossier, or create-agent-fast-forward config drafts
- **THEN** the guidance shows or states that the JSON intent shape is `{"fields":{...}}`
- **AND THEN** the examples do not invite a flat top-level `name`, `tool`, `specialist`, `recipe`, or `credential` object

#### Scenario: CLI reference shows repairable intent shape
- **WHEN** an operator reads config-draft documentation in the `houmao-mgr` CLI reference
- **THEN** the documented `generate --intent` examples show the required `fields` mapping
- **AND THEN** the documented examples match the schema shown in command failure fix guides
