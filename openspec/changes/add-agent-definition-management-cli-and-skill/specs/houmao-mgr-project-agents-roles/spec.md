## MODIFIED Requirements

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
- `set`
- `remove`
- `presets`

At minimum, `project agents roles presets` SHALL expose:

- `list`
- `get`
- `add`
- `set`
- `remove`

The help text for this subtree SHALL present it as management for project-local roles stored under `.houmao/agents/roles/`.

#### Scenario: Operator sees the project agents roles tree
- **WHEN** an operator runs `houmao-mgr project agents roles --help`
- **THEN** the help output lists `list`, `get`, `scaffold`, `init`, `set`, `remove`, and `presets`
- **AND THEN** the help output presents `project agents roles` as management for `.houmao/agents/roles/`

#### Scenario: Operator sees preset verbs for project roles
- **WHEN** an operator runs `houmao-mgr project agents roles presets --help`
- **THEN** the help output lists `list`, `get`, `add`, `set`, and `remove`
- **AND THEN** the help output presents those commands as operations on `roles/<role>/presets/<tool>/<setup>.yaml`

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

### Requirement: `project agents roles set` updates the canonical role prompt

`houmao-mgr project agents roles set --name <role>` SHALL update the canonical `roles/<role>/system-prompt.md` file for one existing project-local role.

At minimum, `roles set` SHALL support these explicit prompt mutations:

- `--system-prompt <text>`
- `--system-prompt-file <path>`
- `--clear-system-prompt`

The command SHALL require at least one explicit prompt mutation and SHALL fail explicitly when none is provided.

The command SHALL fail explicitly when the named role does not exist.

When the operator clears the prompt, the command SHALL preserve the canonical `system-prompt.md` file path and update it to the valid promptless-role state rather than deleting the role root.

#### Scenario: Inline prompt update rewrites the canonical prompt file
- **WHEN** an operator runs `houmao-mgr project agents roles set --name researcher --system-prompt "You are a careful reviewer."`
- **THEN** the command rewrites `.houmao/agents/roles/researcher/system-prompt.md` with that prompt text
- **AND THEN** the structured result reports the updated role and prompt path

#### Scenario: Clearing the prompt keeps the canonical prompt file path
- **WHEN** an operator runs `houmao-mgr project agents roles set --name researcher --clear-system-prompt`
- **THEN** the command leaves `.houmao/agents/roles/researcher/system-prompt.md` in place as the canonical prompt file
- **AND THEN** that file becomes the valid empty-prompt representation for the role

#### Scenario: Missing prompt mutation fails explicitly
- **WHEN** an operator runs `houmao-mgr project agents roles set --name researcher`
- **THEN** the command fails explicitly
- **AND THEN** it does not silently preserve or rewrite the role prompt without an explicit mutation request

### Requirement: `project agents roles presets set` patches editable preset fields while preserving unrelated blocks

`houmao-mgr project agents roles presets set --role <role> --tool <tool>` SHALL patch one existing preset file directly under:

```text
<project-root>/.houmao/agents/roles/<role>/presets/<tool>/<setup>.yaml
```

When `--setup` is omitted, `presets set` SHALL target `default`.

At minimum, `presets set` SHALL support patching:

- auth reference through `--auth <bundle>` or `--clear-auth`
- skill membership through repeated `--add-skill`, repeated `--remove-skill`, and `--clear-skills`
- `launch.prompt_mode` through `--prompt-mode unattended|as_is` or `--clear-prompt-mode`

The command SHALL require at least one explicit mutation flag and SHALL fail explicitly when none is provided.

The command SHALL fail explicitly when the target preset file does not exist.

When patching the preset, the command SHALL preserve unrelated existing blocks and unedited fields, including:

- `mailbox`
- `extra`
- unedited `launch` subfields such as `env_records`

Skill-list patching SHALL preserve first-occurrence order:

- remove any named skills requested through `--remove-skill`
- if `--clear-skills` is present, reset the skill list before additions
- append `--add-skill` values in flag order while deduplicating by first occurrence

#### Scenario: Preset patch updates auth reference and prompt mode while preserving launch env
- **WHEN** a preset already stores `launch.env_records`
- **AND WHEN** an operator runs `houmao-mgr project agents roles presets set --role researcher --tool codex --auth reviewer-creds --prompt-mode as_is`
- **THEN** the command updates that preset's auth reference and `launch.prompt_mode`
- **AND THEN** it preserves the existing `launch.env_records` and other unrelated preset blocks

#### Scenario: Preset patch updates skill membership incrementally
- **WHEN** a preset currently lists `notes` and `mailbox`
- **AND WHEN** an operator runs `houmao-mgr project agents roles presets set --role researcher --tool claude --remove-skill mailbox --add-skill review`
- **THEN** the resulting preset skill list removes `mailbox`
- **AND THEN** it appends `review` without duplicating unchanged existing skills

#### Scenario: Missing preset mutation fails explicitly
- **WHEN** an operator runs `houmao-mgr project agents roles presets set --role researcher --tool claude`
- **THEN** the command fails explicitly
- **AND THEN** it does not silently rewrite the preset without a requested field change
