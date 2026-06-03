# houmao-mgr-project-agents-roles Specification

## Purpose
Define the project-local `houmao-mgr internals native-agent roles` workflow for managing prompt-only role roots inside the repo-local `.houmao/agents/roles/` tree.
## Requirements
### Requirement: `houmao-mgr internals native-agent roles` mirrors the project-local role tree

`houmao-mgr` SHALL expose a project-local role administration subtree shaped as:

```text
houmao-mgr internals native-agent roles <verb>
```

At minimum, `internals native-agent roles` SHALL expose:

- `list`
- `get`
- `init`
- `set`
- `remove`

The help text for this subtree SHALL present it as management for project-local role prompts stored under `.houmao/agents/roles/`.

#### Scenario: Operator sees the internals native-agent roles tree
- **WHEN** an operator runs `houmao-mgr internals native-agent roles --help`
- **THEN** the help output lists `list`, `get`, `init`, `set`, and `remove`
- **AND THEN** the help output presents `internals native-agent roles` as management for `.houmao/agents/roles/`

### Requirement: `internals native-agent roles init/get/remove` manages role roots under the project overlay

`houmao-mgr internals native-agent roles init --name <role>` SHALL create:

```text
<project-root>/.houmao/agents/roles/<role>/
└── system-prompt.md
```

`init` SHALL fail if that role directory already exists.

`houmao-mgr internals native-agent roles get --name <role>` SHALL report one role as structured data, including the role path, the `system-prompt.md` path, whether the prompt file exists, and the names of any presets that currently reference that role.

`houmao-mgr internals native-agent roles set --name <role>` SHALL mutate only the canonical `system-prompt.md` for that role. At minimum, it SHALL support:

- `--system-prompt <text>`
- `--system-prompt-file <path>`
- `--clear-system-prompt`

`houmao-mgr internals native-agent roles remove --name <role>` SHALL delete the named role subtree and SHALL fail clearly when one or more named presets still reference that role.

`roles list` SHALL enumerate role directories even when they do not yet have any referencing preset files.

#### Scenario: Init creates a new role root and prompt file
- **WHEN** an operator runs `houmao-mgr internals native-agent roles init --name researcher`
- **THEN** the command creates `.houmao/agents/roles/researcher/system-prompt.md`
- **AND THEN** the command returns the created role path as structured output

#### Scenario: Set rewrites the canonical role prompt
- **WHEN** `.houmao/agents/roles/researcher/system-prompt.md` exists
- **AND WHEN** an operator runs `houmao-mgr internals native-agent roles set --name researcher --system-prompt "You are a careful reviewer."`
- **THEN** the command rewrites `.houmao/agents/roles/researcher/system-prompt.md`
- **AND THEN** the command does not create or mutate any preset files as a side effect

#### Scenario: Remove fails clearly while presets still reference the role
- **WHEN** `.houmao/agents/presets/researcher-codex-default.yaml` references `role: researcher`
- **AND WHEN** an operator runs `houmao-mgr internals native-agent roles remove --name researcher`
- **THEN** the command fails clearly
- **AND THEN** it reports that named presets still reference that role

#### Scenario: List includes prompt-only roles
- **WHEN** `.houmao/agents/roles/researcher/system-prompt.md` exists
- **AND WHEN** no preset files currently reference that role
- **AND WHEN** an operator runs `houmao-mgr internals native-agent roles list`
- **THEN** the command still lists `researcher` as an existing project-local role

### Requirement: `internals native-agent roles get` can include prompt content on explicit request

`houmao-mgr internals native-agent roles get --name <role>` SHALL keep its summary-oriented structured output by default.

When the operator adds `--include-prompt`, the command SHALL include the current prompt text from `roles/<role>/system-prompt.md` in the structured payload for that role.

The default `get` output SHALL continue to report the role path, prompt path, prompt existence flag, and preset summaries even when prompt text is omitted.

#### Scenario: Default role inspection stays summary-oriented
- **WHEN** an operator runs `houmao-mgr internals native-agent roles get --name researcher`
- **THEN** the command reports the role path, prompt path, prompt existence flag, and preset summaries
- **AND THEN** it does not include prompt text unless the operator asked for it explicitly

#### Scenario: Explicit prompt inspection returns prompt content
- **WHEN** an operator runs `houmao-mgr internals native-agent roles get --name researcher --include-prompt`
- **THEN** the command includes the current prompt text from `roles/researcher/system-prompt.md` in the structured output
- **AND THEN** it does so without requiring direct filesystem reads outside the supported CLI surface

#### Scenario: Promptless role still returns explicit prompt content shape
- **WHEN** a role exists in the valid promptless state with an empty canonical `system-prompt.md`
- **AND WHEN** an operator runs `houmao-mgr internals native-agent roles get --name researcher --include-prompt`
- **THEN** the command reports the canonical prompt path and an empty prompt-text value for that role
- **AND THEN** it does not treat the empty prompt as a missing role or as a request failure

### Requirement: `internals native-agent roles` fail clearly when referenced preset files are malformed

When a maintained `houmao-mgr internals native-agent roles ...` command traverses project-local preset references and encounters malformed YAML or invalid preset content under `.houmao/agents/presets/`, the command SHALL fail as explicit CLI error output rather than leaking a Python traceback.

This SHALL apply at minimum to role flows that inspect or enforce preset references, including:

- `internals native-agent roles list`
- `internals native-agent roles get`
- `internals native-agent roles remove`

The error text SHALL identify the offending preset file path so the operator can repair or remove the malformed preset file.

#### Scenario: Role inspection fails clearly when a referenced preset file is malformed

- **WHEN** an operator runs `houmao-mgr internals native-agent roles get --name researcher`
- **AND WHEN** the role inspection path encounters malformed or invalid preset content under `.houmao/agents/presets/`
- **THEN** the command exits non-zero with explicit CLI error text
- **AND THEN** the error identifies the offending preset file path
- **AND THEN** the operator does not see a Python traceback

#### Scenario: Role listing fails clearly when the preset tree is malformed

- **WHEN** an operator runs `houmao-mgr internals native-agent roles list`
- **AND WHEN** the role listing path encounters malformed or invalid preset content under `.houmao/agents/presets/`
- **THEN** the command exits non-zero with explicit CLI error text
- **AND THEN** the error identifies the offending preset file path
- **AND THEN** the operator does not see a Python traceback
