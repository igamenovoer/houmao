## ADDED Requirements

### Requirement: `project easy specialist set` patches existing specialists
`houmao-mgr project easy specialist set --name <specialist>` SHALL patch one existing project-local easy specialist in the active project overlay.

The command SHALL preserve unspecified stored specialist fields by default.

At minimum, `project easy specialist set` SHALL support mutation of specialist prompt content, skill bindings, setup selection, credential display-name selection, launch prompt mode, launch-owned model name, launch-owned reasoning level, and persistent specialist env records.

The command SHALL expose clear flags for nullable or collection fields, including prompt content, skill bindings, prompt mode, model name, reasoning level, and persistent env records.

When no requested update or clear flag is supplied, the command SHALL fail clearly without rewriting the specialist.

The command SHALL NOT accept specialist rename or tool-lane mutation in this initial surface.

#### Scenario: Specialist set updates prompt without dropping skills
- **WHEN** specialist `researcher` stores prompt content and skill binding `notes`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --system-prompt "You are a focused repo researcher."`
- **THEN** specialist `researcher` stores the new prompt content
- **AND THEN** specialist `researcher` still stores skill binding `notes`

#### Scenario: Specialist set rejects empty update
- **WHEN** specialist `researcher` exists
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher` without any update or clear flags
- **THEN** the command fails clearly
- **AND THEN** specialist `researcher` remains unchanged

#### Scenario: Specialist set does not change tool lane
- **WHEN** specialist `researcher` uses tool lane `codex`
- **AND WHEN** an operator wants a Claude-backed replacement specialist
- **THEN** `project easy specialist set` does not provide a `--tool` mutation path
- **AND THEN** the operator must use specialist replacement or create a separate specialist instead

### Requirement: Specialist set supports targeted skill binding edits
`houmao-mgr project easy specialist set --name <specialist>` SHALL allow operators to edit specialist skill bindings without respecifying the entire specialist.

Repeatable `--with-skill <dir>` SHALL import the provided skill directory and bind that skill to the specialist.

Repeatable `--add-skill <name>` SHALL bind an existing project-local skill package by name.

Repeatable `--remove-skill <name>` SHALL remove the named skill binding from the specialist when present.

`--clear-skills` SHALL clear all skill bindings from the specialist.

Removing or clearing skill bindings SHALL NOT delete shared skill content only because one specialist no longer references it.

#### Scenario: Specialist set imports and adds a skill
- **WHEN** specialist `researcher` exists without skill `notes`
- **AND WHEN** `/tmp/notes-skill/SKILL.md` exists
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --with-skill /tmp/notes-skill`
- **THEN** specialist `researcher` stores skill binding `notes-skill`
- **AND THEN** the imported skill content is available through the project-local compatibility projection

#### Scenario: Specialist set removes one binding without deleting shared skill content
- **WHEN** specialist `researcher` and specialist `reviewer` both reference skill `notes`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --remove-skill notes`
- **THEN** specialist `researcher` no longer stores skill binding `notes`
- **AND THEN** skill content for `notes` remains available for specialist `reviewer`

### Requirement: Specialist set updates launch-owned source defaults
`houmao-mgr project easy specialist set --name <specialist>` SHALL allow operators to update launch-owned source defaults stored on the specialist.

`--prompt-mode unattended|as_is` SHALL set the stored specialist launch prompt mode.

`--clear-prompt-mode` SHALL remove the stored specialist launch prompt mode so downstream build and launch policy can resolve its default behavior.

`--model <name>` and `--reasoning-level <integer>=non-negative` SHALL update the stored launch-owned model configuration using the same partial merge semantics as reusable profile patch commands.

`--clear-model` and `--clear-reasoning-level` SHALL clear the corresponding stored launch-owned model configuration fields.

Repeatable `--env-set NAME=value` SHALL replace the stored persistent specialist env records with the provided mapping after applying the same validation used during specialist creation.

`--clear-env` SHALL remove all stored persistent specialist env records.

#### Scenario: Specialist set updates model while preserving reasoning
- **WHEN** specialist `reviewer` stores launch model `gpt-5.4` and reasoning level `4`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name reviewer --model gpt-5.4-mini`
- **THEN** specialist `reviewer` stores launch model `gpt-5.4-mini`
- **AND THEN** specialist `reviewer` still stores reasoning level `4`

#### Scenario: Specialist set rejects credential-owned env names
- **WHEN** specialist `researcher` uses the Codex tool lane
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --env-set OPENAI_API_KEY=sk-test`
- **THEN** the command fails clearly because `OPENAI_API_KEY` belongs to credential env for the selected tool
- **AND THEN** specialist `researcher` remains unchanged

### Requirement: Specialist set refreshes catalog-backed compatibility projection
After `project easy specialist set` updates stored specialist state, the command SHALL rematerialize the project agent catalog projection.

The projected role prompt and specialist-backed preset under `.houmao/agents/` SHALL reflect the updated stored specialist state.

If a specialist setup change changes the generated preset name, the command SHALL remove the previous specialist-owned projected preset file when no longer referenced by the updated specialist.

`project easy specialist set` SHALL NOT mutate running managed-agent sessions, runtime homes, or already-written launch manifests in place.

#### Scenario: Specialist set updates projected preset skills
- **WHEN** specialist `researcher` projects to `.houmao/agents/presets/researcher-codex-default.yaml`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --add-skill notes`
- **THEN** the stored specialist records skill binding `notes`
- **AND THEN** `.houmao/agents/presets/researcher-codex-default.yaml` includes skill `notes`

#### Scenario: Specialist set affects future launch only
- **WHEN** managed agent `researcher-1` is already running from specialist `researcher`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --system-prompt "Use the new review policy."`
- **THEN** specialist `researcher` stores the new prompt for future builds and launches
- **AND THEN** the command does not rewrite the running `researcher-1` runtime home or manifest in place
