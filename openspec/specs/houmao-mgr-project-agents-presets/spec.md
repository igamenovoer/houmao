# houmao-mgr-project-agents-presets Specification

## Purpose
Define the project-local `houmao-mgr project agents presets` workflow for managing named preset resources under `.houmao/agents/presets/`.

## Requirements

### Requirement: `houmao-mgr project agents presets` mirrors the project-local preset tree

`houmao-mgr` SHALL expose a project-local preset administration subtree shaped as:

```text
houmao-mgr project agents presets <verb>
```

At minimum, `project agents presets` SHALL expose:

- `list`
- `get`
- `add`
- `set`
- `remove`

The help text for this subtree SHALL present it as management for project-local named presets stored under `.houmao/agents/presets/`.

#### Scenario: Operator sees the project agents presets tree
- **WHEN** an operator runs `houmao-mgr project agents presets --help`
- **THEN** the help output lists `list`, `get`, `add`, `set`, and `remove`
- **AND THEN** the help output presents `project agents presets` as management for `.houmao/agents/presets/`

### Requirement: `project agents presets` manages named preset resources

`houmao-mgr project agents presets add --name <preset> --role <role> --tool <tool>` SHALL create one preset file directly under:

```text
<project-root>/.houmao/agents/presets/<preset>.yaml
```

At minimum, preset file content SHALL include:

- required `role`
- required `tool`
- required `setup`
- required `skills`
- optional `auth`
- optional `launch`
- optional `mailbox`
- optional `extra`

When `--setup` is omitted, `presets add` SHALL default to `default`.

At minimum, `presets add` SHALL support authoring:

- `skills` through repeated `--skill`
- optional `auth` through `--auth`
- optional `launch.prompt_mode` through `--prompt-mode`

Allowed `--prompt-mode` values SHALL be `unattended` and `as_is`.

When `--prompt-mode` is omitted, `presets add` SHALL author the default unattended posture rather than authoring pass-through startup behavior implicitly.

`presets add` SHALL fail if the target preset file already exists.

`presets get --name <preset>` SHALL report the preset name, source path, and parsed fields as structured output.

`presets list` SHALL enumerate existing preset files and SHALL support filtering by `--role` and `--tool`.

`presets set --name <preset>` SHALL patch the named preset resource without replacing unspecified advanced blocks. At minimum, it SHALL support updating:

- `role`
- `tool`
- `setup`
- `auth`
- `skills`
- `launch.prompt_mode`

When a preset already contains `mailbox` or `extra`, `presets get` SHALL report those blocks and `presets set` SHALL preserve them unless a future dedicated flag edits them explicitly.

`presets remove --name <preset>` SHALL delete one preset file.

The system SHALL reject creation or mutation that would make two presets share the same `(role, tool, setup)` tuple.

#### Scenario: Add creates a named default unattended preset when prompt mode is omitted
- **WHEN** an operator runs `houmao-mgr project agents presets add --name researcher-claude-default --role researcher --tool claude --auth default --skill notes`
- **THEN** the command creates `.houmao/agents/presets/researcher-claude-default.yaml`
- **AND THEN** the written preset stores `role: researcher`, `tool: claude`, `setup: default`, `skills`, `auth`, and `launch.prompt_mode: unattended`

#### Scenario: Set patches one named preset without dropping advanced blocks
- **WHEN** `.houmao/agents/presets/researcher-codex-default.yaml` exists with `mailbox` and `extra` blocks
- **AND WHEN** an operator runs `houmao-mgr project agents presets set --name researcher-codex-default --auth reviewer-creds --add-skill notes`
- **THEN** the command updates only the edited preset fields
- **AND THEN** the preset still retains its pre-existing `mailbox` and `extra` blocks

#### Scenario: Duplicate role-tool-setup tuple is rejected
- **WHEN** `.houmao/agents/presets/researcher-codex-default.yaml` already declares `role: researcher`, `tool: codex`, and `setup: default`
- **AND WHEN** an operator runs `houmao-mgr project agents presets add --name researcher-main --role researcher --tool codex`
- **THEN** the command fails clearly
- **AND THEN** it reports that the `(role, tool, setup)` tuple must remain unique
