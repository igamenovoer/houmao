## MODIFIED Requirements

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

Allowed `--prompt-mode` values SHALL be `unattended` and `as_is`.

When `--prompt-mode` is omitted, `presets add` SHALL author the default unattended posture rather than authoring pass-through startup behavior implicitly.

`presets add` SHALL fail if the target preset file already exists.

`presets get` SHALL report parsed preset data and the source path as structured output. When advanced blocks such as `mailbox` or `extra` already exist, `get` SHALL report them as structured data, but this change SHALL NOT require corresponding flag-driven editing commands for those blocks.

`presets list` SHALL enumerate existing preset files for the selected role.

`presets remove` SHALL delete one preset file.

#### Scenario: Add creates a default unattended preset when prompt mode is omitted
- **WHEN** an operator runs `houmao-mgr project agents roles presets add --role researcher --tool claude --auth default --skill notes`
- **THEN** the command creates `.houmao/agents/roles/researcher/presets/claude/default.yaml`
- **AND THEN** the written preset stores `skills`, `auth`, and `launch.prompt_mode: unattended` using the canonical preset schema

#### Scenario: Add can author an explicit as-is preset
- **WHEN** an operator runs `houmao-mgr project agents roles presets add --role researcher --tool claude --auth default --skill notes --prompt-mode as_is`
- **THEN** the command creates `.houmao/agents/roles/researcher/presets/claude/default.yaml`
- **AND THEN** the written preset stores `launch.prompt_mode: as_is` using the canonical preset schema

#### Scenario: Get reports the parsed preset rather than requiring raw YAML inspection
- **WHEN** `.houmao/agents/roles/researcher/presets/claude/default.yaml` exists
- **AND WHEN** an operator runs `houmao-mgr project agents roles presets get --role researcher --tool claude --setup default`
- **THEN** the command returns the preset path and parsed fields such as `skills`, `auth`, and `launch`
