## MODIFIED Requirements

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
- **AND WHEN** an operator runs `houmao-mgr project agents roles set --name researcher --system-prompt \"You are a careful reviewer.\"`
- **THEN** the command rewrites `.houmao/agents/roles/researcher/system-prompt.md`
- **AND THEN** the command does not create or mutate any preset files as a side effect

#### Scenario: Remove fails clearly while presets still reference the role
- **WHEN** `.houmao/agents/presets/researcher-codex-default.yaml` references `role: researcher`
- **AND WHEN** an operator runs `houmao-mgr project agents roles remove --name researcher`
- **THEN** the command fails clearly
- **AND THEN** it reports that named presets still reference that role

## REMOVED Requirements

### Requirement: `project agents roles scaffold` creates a structurally complete starter slice with placeholders
**Reason**: Roles now own only prompt content. Placeholder setup/auth/skill generation no longer fits the low-level role resource.
**Migration**: Use `houmao-mgr project agents roles init` plus `houmao-mgr project agents presets add` for low-level authoring, or use `houmao-mgr project easy specialist create` for higher-level convenience flows.

### Requirement: `project agents roles presets` manages minimal path-derived preset scaffolds
**Reason**: Presets are promoted to a first-class top-level resource under `project agents presets`.
**Migration**: Replace `houmao-mgr project agents roles presets ...` with `houmao-mgr project agents presets ...`, and move canonical preset files from `agents/roles/<role>/presets/<tool>/<setup>.yaml` to `agents/presets/<name>.yaml`.
