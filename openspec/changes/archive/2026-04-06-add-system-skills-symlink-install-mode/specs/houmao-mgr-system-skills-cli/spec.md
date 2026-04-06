## MODIFIED Requirements

### Requirement: `houmao-mgr system-skills install` targets an explicit tool home and set-based selection

`houmao-mgr system-skills install` SHALL target an explicit tool home rather than inferring a project overlay or a running managed session.

The command SHALL require a supported tool identifier and a target home path.

The command SHALL support these selection inputs:

- repeatable `--set <name>` for named set selection,
- repeatable `--skill <name>` for explicit current-skill selection,
- `--default` for the CLI default set list from the packaged catalog.

The command SHALL also support `--symlink` to request symlink projection mode for that explicit install.

The command SHALL fail explicitly when neither selection mode is provided.

If `--symlink` is omitted, the command SHALL use copied projection mode.

If `--symlink` is provided, the command SHALL use the shared Houmao system-skill installer in symlink projection mode and SHALL NOT silently fall back to copied projection.

The command SHALL use the shared Houmao system-skill installer for projection and ownership tracking.

#### Scenario: Install applies the CLI default set list to an explicit Claude home with copied projection

- **WHEN** an operator runs `houmao-mgr system-skills install --tool claude --home /tmp/claude-home --default`
- **THEN** the command installs the current Houmao-owned skill list resolved from the CLI default set list into `/tmp/claude-home`
- **AND THEN** it does so through the shared Houmao system-skill installer in copied projection mode rather than through mailbox-specific installation logic

#### Scenario: Install applies multiple named sets to an explicit home

- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home --set mailbox-core --set mailbox-full`
- **THEN** the command installs the resolved current Houmao-owned skill list from those named sets into the explicit target home
- **AND THEN** overlapping set members are deduplicated by first occurrence

#### Scenario: Install combines named sets and explicit skills

- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home --set mailbox-core --skill houmao-email-via-filesystem`
- **THEN** the command installs the resolved current Houmao-owned skill list from the named set plus the explicit skill into the explicit target home
- **AND THEN** it does not silently replace that explicit selection with the CLI default set list

#### Scenario: Install applies one selected skill in symlink mode

- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home --skill houmao-manage-specialist --symlink`
- **THEN** the command installs that selected Houmao-owned skill into the explicit target home using symlink projection mode
- **AND THEN** it does not silently replace that symlink request with copied projection

#### Scenario: Install fails when selection is omitted

- **WHEN** an operator runs `houmao-mgr system-skills install --tool gemini --home /tmp/gemini-home`
- **THEN** the command fails explicitly
- **AND THEN** it does not guess a default or all-skills selection without operator input

#### Scenario: Install fails when a selected set is unknown

- **WHEN** an operator runs `houmao-mgr system-skills install --tool gemini --home /tmp/gemini-home --set unknown-set`
- **THEN** the command fails explicitly
- **AND THEN** it does not guess another named set or continue with partial selection

### Requirement: `houmao-mgr system-skills status` reports Houmao-owned install state for one target home

`houmao-mgr system-skills status` SHALL report the Houmao-owned current-skill installation state for one explicit target tool home.

At minimum, the reported state SHALL identify:

- the target tool,
- whether Houmao-owned install state exists,
- which current Houmao-owned skills are recorded as installed in that home,
- the recorded projection mode for each installed current Houmao-owned skill.

#### Scenario: Status reports an untouched target home

- **WHEN** an operator runs `houmao-mgr system-skills status --tool codex --home /tmp/codex-home`
- **AND WHEN** that home has no Houmao-owned current-skill install state
- **THEN** the command reports that no Houmao-owned install state is present
- **AND THEN** it does not claim that any current Houmao-owned skills are installed in that home

#### Scenario: Status reports installed current Houmao-owned skills with copied projection

- **WHEN** an operator runs `houmao-mgr system-skills status --tool gemini --home /tmp/gemini-home`
- **AND WHEN** Houmao has already installed current Houmao-owned skills into that home using copied projection
- **THEN** the command reports the recorded installed current skill names for that home
- **AND THEN** it reports that Houmao-owned install state exists for the target home
- **AND THEN** it reports `copy` as the recorded projection mode for those installed skills

#### Scenario: Status reports installed current Houmao-owned skills with symlink projection

- **WHEN** an operator runs `houmao-mgr system-skills status --tool codex --home /tmp/codex-home`
- **AND WHEN** Houmao has already installed current Houmao-owned skills into that home using symlink projection
- **THEN** the command reports the recorded installed current skill names for that home
- **AND THEN** it reports `symlink` as the recorded projection mode for those installed skills
