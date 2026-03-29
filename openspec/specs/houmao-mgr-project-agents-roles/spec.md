# houmao-mgr-project-agents-roles Specification

## Purpose
Define the project-local `houmao-mgr project agents roles` workflow for managing role roots and presets inside the repo-local `.houmao/agents/roles/` tree.

## Requirements

### Requirement: `houmao-mgr project agents roles` mirrors the project-local role tree

`houmao-mgr` SHALL expose a project-local role administration subtree shaped as:

```text
houmao-mgr project agents roles <verb>
houmao-mgr project agents roles presets <verb>
```

At minimum, `project agents roles` SHALL expose:

- `list`
- `get`
- `scaffold`
- `init`
- `remove`
- `presets`

At minimum, `project agents roles presets` SHALL expose:

- `list`
- `get`
- `add`
- `remove`

The help text for this subtree SHALL present it as management for project-local roles stored under `.houmao/agents/roles/`.

#### Scenario: Operator sees the project agents roles tree
- **WHEN** an operator runs `houmao-mgr project agents roles --help`
- **THEN** the help output lists `list`, `get`, `scaffold`, `init`, `remove`, and `presets`
- **AND THEN** the help output presents `project agents roles` as management for `.houmao/agents/roles/`

#### Scenario: Operator sees preset verbs for project roles
- **WHEN** an operator runs `houmao-mgr project agents roles presets --help`
- **THEN** the help output lists `list`, `get`, `add`, and `remove`
- **AND THEN** the help output presents those commands as operations on `roles/<role>/presets/<tool>/<setup>.yaml`

### Requirement: `project agents roles scaffold` creates a structurally complete starter slice with placeholders

`houmao-mgr project agents roles scaffold` SHALL create a structurally complete starter slice for one role.

At minimum, `scaffold` SHALL require:

- `--name <role>`
- one or more `--tool <tool>`

At minimum, `scaffold` SHALL create:

- `.houmao/agents/roles/<role>/system-prompt.md`
- one preset per requested tool under `.houmao/agents/roles/<role>/presets/<tool>/<setup>.yaml`

When the operator passes `--skill <skill>`, `scaffold` SHALL create placeholder `skills/<skill>/SKILL.md` files for any requested skill names that do not already exist.

When the selected auth bundle does not already exist, `scaffold` SHALL create a placeholder auth bundle for each requested tool under `.houmao/agents/tools/<tool>/auth/<auth>/`, using the tool adapter contract to determine supported env vars and required auth files.

When the selected setup does not already exist and is not `default`, `scaffold` SHALL clone that tool's `default` setup bundle into the requested setup name before writing presets that reference it.

The scaffold output SHALL be parser-valid and structurally complete, but it MAY contain placeholder content that the operator must replace before real launches succeed.

#### Scenario: Scaffold creates a complete starter slice for one tool
- **WHEN** an operator runs `houmao-mgr project agents roles scaffold --name researcher --tool claude --auth default --skill notes`
- **THEN** the command creates `.houmao/agents/roles/researcher/system-prompt.md`
- **AND THEN** it creates `.houmao/agents/roles/researcher/presets/claude/default.yaml`
- **AND THEN** it creates `.houmao/agents/skills/notes/SKILL.md` when that skill was missing
- **AND THEN** it creates `.houmao/agents/tools/claude/auth/default/` with placeholder auth content when that bundle was missing

#### Scenario: Scaffold can create parallel presets for multiple tools
- **WHEN** an operator runs `houmao-mgr project agents roles scaffold --name researcher --tool claude --tool codex --auth default`
- **THEN** the command creates one preset under `roles/researcher/presets/claude/`
- **AND THEN** it creates one preset under `roles/researcher/presets/codex/`

### Requirement: `project agents roles init/get/remove` manages role roots under the project overlay

`houmao-mgr project agents roles init --name <role>` SHALL create:

```text
<project-root>/.houmao/agents/roles/<role>/
└── system-prompt.md
```

`init` SHALL fail if that role directory already exists.

`init` MAY also create one initial preset when the operator supplies `--tool`, using the same canonical preset path model as `project agents roles presets add`.

`houmao-mgr project agents roles get --name <role>` SHALL report one role as structured data, including the role path, the `system-prompt.md` path, whether the prompt file exists, and any discovered preset summaries.

`houmao-mgr project agents roles remove --name <role>` SHALL delete the named role subtree.

`roles list` SHALL enumerate role directories even when they do not yet contain any preset files.

#### Scenario: Init creates a new role root and prompt file
- **WHEN** an operator runs `houmao-mgr project agents roles init --name researcher`
- **THEN** the command creates `.houmao/agents/roles/researcher/system-prompt.md`
- **AND THEN** the command returns the created role path as structured output

#### Scenario: List includes prompt-only roles
- **WHEN** `.houmao/agents/roles/researcher/system-prompt.md` exists
- **AND WHEN** no preset files exist yet under that role
- **AND WHEN** an operator runs `houmao-mgr project agents roles list`
- **THEN** the command still lists `researcher` as an existing project-local role

### Requirement: `project agents roles presets` manages minimal path-derived preset scaffolds

`houmao-mgr project agents roles presets add --role <role> --tool <tool>` SHALL create one preset file directly under:

```text
<project-root>/.houmao/agents/roles/<role>/presets/<tool>/<setup>.yaml
```

When `--setup` is omitted, `presets add` SHALL default to `default`.

At minimum, `presets add` SHALL support authoring:

- `skills` through repeated `--skill`
- optional `auth` through `--auth`
- optional `launch.prompt_mode` through `--prompt-mode`

`presets add` SHALL fail if the target preset file already exists.

`presets get` SHALL report parsed preset data and the source path as structured output. When advanced blocks such as `mailbox` or `extra` already exist, `get` SHALL report them as structured data, but this change SHALL NOT require corresponding flag-driven editing commands for those blocks.

`presets list` SHALL enumerate existing preset files for the selected role.

`presets remove` SHALL delete one preset file.

#### Scenario: Add creates a minimal default preset for one role and tool
- **WHEN** an operator runs `houmao-mgr project agents roles presets add --role researcher --tool claude --auth default --skill notes --prompt-mode unattended`
- **THEN** the command creates `.houmao/agents/roles/researcher/presets/claude/default.yaml`
- **AND THEN** the written preset stores `skills`, `auth`, and `launch.prompt_mode` using the canonical preset schema

#### Scenario: Get reports the parsed preset rather than requiring raw YAML inspection
- **WHEN** `.houmao/agents/roles/researcher/presets/claude/default.yaml` exists
- **AND WHEN** an operator runs `houmao-mgr project agents roles presets get --role researcher --tool claude --setup default`
- **THEN** the command returns the preset path and parsed fields such as `skills`, `auth`, and `launch`
