# houmao-mgr-project-agents-presets Specification

## Purpose
Define the project-local low-level recipe workflow, with `project agents recipes` as the canonical surface and `project agents presets` preserved as the compatibility alias for the same resources under `.houmao/agents/presets/`.
## Requirements
### Requirement: `houmao-mgr project agents presets` mirrors the project-local preset tree

`houmao-mgr` SHALL expose a canonical low-level recipe administration subtree shaped as:

```text
houmao-mgr project agents recipes <verb>
```

`houmao-mgr` SHALL preserve:

```text
houmao-mgr project agents presets <verb>
```

as a compatibility alias for the same named low-level recipe resources.

At minimum, the canonical or compatibility surface SHALL expose:

- `list`
- `get`
- `add`
- `set`
- `remove`

The help text for both surfaces SHALL present them as management for project-local named recipe resources stored under `.houmao/agents/presets/`.

#### Scenario: Operator sees canonical recipe management and preset compatibility
- **WHEN** an operator runs `houmao-mgr project agents recipes --help`
- **THEN** the help output lists `list`, `get`, `add`, `set`, and `remove`
- **AND THEN** it presents `project agents recipes` as management for named recipe resources stored under `.houmao/agents/presets/`

#### Scenario: Preset subtree remains a compatibility alias
- **WHEN** an operator runs `houmao-mgr project agents presets --help`
- **THEN** the help output still resolves the same low-level resource family
- **AND THEN** it identifies `presets` as the compatibility entrypoint for the canonical recipe surface

### Requirement: `project agents presets` manages named preset resources
`houmao-mgr project agents recipes add --name <recipe> --role <role> --tool <tool>` SHALL create one recipe file directly under:

```text
<project-root>/.houmao/agents/presets/<recipe>.yaml
```

At minimum, recipe file content SHALL include:

- required `role`
- required `tool`
- required `setup`
- required `skills`
- optional `auth`
- optional `launch`
- optional `mailbox`
- optional `extra`

When `--setup` is omitted, recipe add SHALL default to `default`.

At minimum, recipe add SHALL support authoring:

- `skills` through repeated `--skill`
- optional `auth` through `--auth`
- optional `launch.prompt_mode` through `--prompt-mode`
- optional `launch.model` through `--model`
- optional `launch.model.reasoning.level` through `--reasoning-level`

Allowed `--prompt-mode` values SHALL be `unattended` and `as_is`.

When `--prompt-mode` is omitted, recipe add SHALL author the default unattended posture rather than authoring pass-through startup behavior implicitly.

Recipe reasoning levels authored on this surface SHALL be stored as non-negative tool/model-specific preset indices rather than as normalized `1..10` values.

Recipe add SHALL fail if the target recipe file already exists.

`recipes get --name <recipe>` SHALL report the recipe name, source path, and parsed fields as structured output.

`recipes list` SHALL enumerate existing recipe files and SHALL support filtering by `--role` and `--tool`.

`recipes set --name <recipe>` SHALL patch the named recipe resource without replacing unspecified advanced blocks. At minimum, it SHALL support updating:

- `role`
- `tool`
- `setup`
- `auth`
- `skills`
- `launch.prompt_mode`
- `launch.model`
- `launch.model.reasoning.level`

`recipes set` SHALL support clearing the stored model through `--clear-model`.

`recipes set` SHALL support clearing the stored reasoning level through `--clear-reasoning-level`.

When a recipe already contains `mailbox` or `extra`, `recipes get` SHALL report those blocks and `recipes set` SHALL preserve them unless a future dedicated flag edits them explicitly.

`recipes remove --name <recipe>` SHALL delete one recipe file.

The compatibility `project agents presets ...` surface SHALL operate on the same named recipe resources and SHALL preserve equivalent behavior.

Named recipes SHALL remain the reusable source objects that explicit launch profiles reference.

The system SHALL reject creation or mutation that would make two recipes share the same `(role, tool, setup)` tuple.

#### Scenario: Add creates a named recipe with stored model when requested
- **WHEN** an operator runs `houmao-mgr project agents recipes add --name researcher-codex-default --role researcher --tool codex --auth default --skill notes --model gpt-5.4 --reasoning-level 3`
- **THEN** the command creates `.houmao/agents/presets/researcher-codex-default.yaml`
- **AND THEN** the written recipe stores `role: researcher`, `tool: codex`, `setup: default`, `skills`, `auth`, `launch.prompt_mode: unattended`, model `gpt-5.4`, and reasoning level `3`

#### Scenario: Set patches one named recipe model without dropping advanced blocks
- **WHEN** `.houmao/agents/presets/researcher-codex-default.yaml` exists with `mailbox` and `extra` blocks
- **AND WHEN** an operator runs `houmao-mgr project agents recipes set --name researcher-codex-default --model gpt-5.4-mini --add-skill notes`
- **THEN** the command updates only the edited recipe fields
- **AND THEN** the recipe still retains its pre-existing `mailbox` and `extra` blocks

#### Scenario: Set can clear the stored recipe model
- **WHEN** `.houmao/agents/presets/researcher-codex-default.yaml` exists with `launch.model: gpt-5.4`
- **AND WHEN** an operator runs `houmao-mgr project agents recipes set --name researcher-codex-default --clear-model`
- **THEN** the command removes the stored recipe model selection
- **AND THEN** other `launch` fields remain intact unless edited explicitly

#### Scenario: Set can clear the stored recipe reasoning level
- **WHEN** `.houmao/agents/presets/researcher-codex-default.yaml` exists with stored reasoning level `3`
- **AND WHEN** an operator runs `houmao-mgr project agents recipes set --name researcher-codex-default --clear-reasoning-level`
- **THEN** the command removes the stored recipe reasoning selection
- **AND THEN** other `launch` fields remain intact unless edited explicitly

#### Scenario: Duplicate role-tool-setup tuple is rejected
- **WHEN** `.houmao/agents/presets/researcher-codex-default.yaml` already declares `role: researcher`, `tool: codex`, and `setup: default`
- **AND WHEN** an operator runs `houmao-mgr project agents recipes add --name researcher-main --role researcher --tool codex`
- **THEN** the command fails clearly
- **AND THEN** it reports that the `(role, tool, setup)` tuple must remain unique

