## ADDED Requirements

### Requirement: `project agents roles get` can include prompt content on explicit request

`houmao-mgr project agents roles get --name <role>` SHALL keep its summary-oriented structured output by default.

When the operator adds `--include-prompt`, the command SHALL include the current prompt text from `roles/<role>/system-prompt.md` in the structured payload for that role.

The default `get` output SHALL continue to report the role path, prompt path, prompt existence flag, and preset summaries even when prompt text is omitted.

#### Scenario: Default role inspection stays summary-oriented

- **WHEN** an operator runs `houmao-mgr project agents roles get --name researcher`
- **THEN** the command reports the role path, prompt path, prompt existence flag, and preset summaries
- **AND THEN** it does not include prompt text unless the operator asked for it explicitly

#### Scenario: Explicit prompt inspection returns prompt content

- **WHEN** an operator runs `houmao-mgr project agents roles get --name researcher --include-prompt`
- **THEN** the command includes the current prompt text from `roles/researcher/system-prompt.md` in the structured output
- **AND THEN** it does so without requiring direct filesystem reads outside the supported CLI surface

#### Scenario: Promptless role still returns explicit prompt content shape

- **WHEN** a role exists in the valid promptless state with an empty canonical `system-prompt.md`
- **AND WHEN** an operator runs `houmao-mgr project agents roles get --name researcher --include-prompt`
- **THEN** the command reports the canonical prompt path and an empty prompt-text value for that role
- **AND THEN** it does not treat the empty prompt as a missing role or as a request failure
