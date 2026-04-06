# houmao-mgr-project-agents-roles Specification

## Purpose
Define the project-local `houmao-mgr project agents roles` workflow for managing prompt-only role roots inside the repo-local `.houmao/agents/roles/` tree.

## Requirements

### Requirement: `houmao-mgr project agents roles` mirrors the project-local role tree

`houmao-mgr` SHALL expose a project-local role administration subtree shaped as:

```text
houmao-mgr project agents roles <verb>
```

At minimum, `project agents roles` SHALL expose:

- `list`
- `get`
- `init`
- `set`
- `remove`

The help text for this subtree SHALL present it as management for project-local role prompts stored under `.houmao/agents/roles/`.

#### Scenario: Operator sees the project agents roles tree
- **WHEN** an operator runs `houmao-mgr project agents roles --help`
- **THEN** the help output lists `list`, `get`, `init`, `set`, and `remove`
- **AND THEN** the help output presents `project agents roles` as management for `.houmao/agents/roles/`

### Requirement: `project agents roles init/get/remove` manages role roots under the project overlay

`houmao-mgr project agents roles init --name <role>` SHALL create:

```text
<project-root>/.houmao/agents/roles/<role>/
└── system-prompt.md
```

`init` SHALL fail if that role directory already exists.

`houmao-mgr project agents roles get --name <role>` SHALL report one role as structured data, including the role path, the `system-prompt.md` path, whether the prompt file exists, and the names of any presets that currently reference that role.

`houmao-mgr project agents roles set --name <role>` SHALL mutate only the canonical `system-prompt.md` for that role. At minimum, it SHALL support:

- `--system-prompt <text>`
- `--system-prompt-file <path>`
- `--clear-system-prompt`

`houmao-mgr project agents roles remove --name <role>` SHALL delete the named role subtree and SHALL fail clearly when one or more named presets still reference that role.

`roles list` SHALL enumerate role directories even when they do not yet have any referencing preset files.

#### Scenario: Init creates a new role root and prompt file
- **WHEN** an operator runs `houmao-mgr project agents roles init --name researcher`
- **THEN** the command creates `.houmao/agents/roles/researcher/system-prompt.md`
- **AND THEN** the command returns the created role path as structured output

#### Scenario: Set rewrites the canonical role prompt
- **WHEN** `.houmao/agents/roles/researcher/system-prompt.md` exists
- **AND WHEN** an operator runs `houmao-mgr project agents roles set --name researcher --system-prompt "You are a careful reviewer."`
- **THEN** the command rewrites `.houmao/agents/roles/researcher/system-prompt.md`
- **AND THEN** the command does not create or mutate any preset files as a side effect

#### Scenario: Remove fails clearly while presets still reference the role
- **WHEN** `.houmao/agents/presets/researcher-codex-default.yaml` references `role: researcher`
- **AND WHEN** an operator runs `houmao-mgr project agents roles remove --name researcher`
- **THEN** the command fails clearly
- **AND THEN** it reports that named presets still reference that role

#### Scenario: List includes prompt-only roles
- **WHEN** `.houmao/agents/roles/researcher/system-prompt.md` exists
- **AND WHEN** no preset files currently reference that role
- **AND WHEN** an operator runs `houmao-mgr project agents roles list`
- **THEN** the command still lists `researcher` as an existing project-local role
