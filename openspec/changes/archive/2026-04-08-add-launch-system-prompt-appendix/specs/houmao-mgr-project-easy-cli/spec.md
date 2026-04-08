## ADDED Requirements

### Requirement: `project easy instance launch` supports one-shot launch-owned system-prompt appendix
`houmao-mgr project easy instance launch` SHALL accept optional launch-owned system-prompt appendix input through:

- `--append-system-prompt-text`
- `--append-system-prompt-file`

Those options SHALL be mutually exclusive.

When either option is supplied, the provided appendix SHALL affect only the current easy-instance launch and SHALL NOT rewrite the stored specialist or easy profile.

When the selected easy profile already contributes a launch-profile prompt overlay, the appendix SHALL be appended after overlay resolution within the delegated native managed launch.

#### Scenario: Easy-profile-backed launch appends one-shot prompt text without rewriting the profile
- **WHEN** easy profile `alice` stores a reusable prompt overlay
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile alice --append-system-prompt-text "Treat gateway diagnostics as high priority."`
- **THEN** the current easy-instance launch appends that prompt text after the resolved profile overlay
- **AND THEN** easy profile `alice` remains unchanged after the launch

#### Scenario: Specialist-backed launch appends file-based prompt content for one launch
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --append-system-prompt-file /tmp/appendix.md`
- **THEN** the delegated managed launch includes the file content as a launch appendix for that instance launch
- **AND THEN** a later easy-instance launch without the appendix option does not inherit that file content

#### Scenario: Easy-instance launch rejects conflicting appendix inputs
- **WHEN** an operator supplies both `--append-system-prompt-text` and `--append-system-prompt-file` on one `houmao-mgr project easy instance launch` invocation
- **THEN** the command fails clearly before delegating to native managed launch
- **AND THEN** it does not start a managed session for that invalid launch request
