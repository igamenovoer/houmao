## Purpose
Define the operator-facing `houmao-mgr system-skills` CLI for listing, installing, and inspecting Houmao-owned system skills.
## Requirements
### Requirement: `houmao-mgr system-skills` exposes the current Houmao-owned skill installation surface
`houmao-mgr` SHALL expose a top-level `system-skills` command family for the current Houmao-owned system-skill set.

At minimum, that command family SHALL include:

- `list`
- `install`
- `status`

#### Scenario: Help shows the system-skill command family
- **WHEN** an operator runs `houmao-mgr system-skills --help`
- **THEN** the help output lists `list`, `install`, and `status`
- **AND THEN** the command family is presented as the Houmao-owned system-skill installation surface for the current skill set

### Requirement: `houmao-mgr system-skills list` reports the current installable Houmao-owned skill inventory and named sets
`houmao-mgr system-skills list` SHALL report the current installable Houmao-owned skill inventory and the current named skill sets from the packaged catalog.

That output SHALL identify the configured CLI default set list and the fixed internal auto-install set lists.

#### Scenario: List reports named sets and default set markers
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports the current installable Houmao-owned skill names
- **AND THEN** it reports the current named skill sets
- **AND THEN** it identifies the configured CLI default set list and internal auto-install set lists

### Requirement: `houmao-mgr system-skills install` targets an explicit tool home and set-based selection
`houmao-mgr system-skills install` SHALL require a supported tool identifier and SHALL accept an optional target home override rather than inferring a project overlay or a running managed session.

When `--home` is omitted, the command SHALL resolve the effective target home with this precedence:

1. explicit `--home`
2. tool-native home env var
3. project-scoped default home

The tool-native home env vars SHALL be:

- Claude: `CLAUDE_CONFIG_DIR`
- Codex: `CODEX_HOME`
- Gemini: `GEMINI_CLI_HOME`

The project-scoped default homes SHALL be:

- Claude: `<cwd>/.claude`
- Codex: `<cwd>/.codex`
- Gemini: `<cwd>`

For Gemini, the resolved effective home SHALL remain the home root itself, and Houmao-owned installed skills SHALL project under `<effective-home>/.gemini/skills/`.

The command SHALL support these selection inputs:

- repeatable `--set <name>` for named set selection,
- repeatable `--skill <name>` for explicit current-skill selection.

When neither `--set` nor `--skill` is provided, the command SHALL use the CLI default set list from the packaged catalog.

The command SHALL NOT expose `--default` as part of the supported public install surface.

The command SHALL also support `--symlink` to request symlink projection mode for that explicit install.

If `--symlink` is omitted, the command SHALL use copied projection mode.

If `--symlink` is provided, the command SHALL use the shared Houmao system-skill installer in symlink projection mode and SHALL NOT silently fall back to copied projection.

The command SHALL use the shared Houmao system-skill installer for projection and ownership tracking.

#### Scenario: Explicit home override wins over tool-native env redirection
- **WHEN** `CODEX_HOME=/tmp/codex-from-env`
- **AND WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-explicit --skill houmao-manage-specialist`
- **THEN** the command installs the selected skill into `/tmp/codex-explicit`
- **AND THEN** it does not redirect that install to `/tmp/codex-from-env`

#### Scenario: Omitted home uses the tool-native env redirect first
- **WHEN** `CLAUDE_CONFIG_DIR=/tmp/claude-home`
- **AND WHEN** an operator runs `houmao-mgr system-skills install --tool claude`
- **THEN** the command installs the current Houmao-owned skill list resolved from the CLI default set list into `/tmp/claude-home`
- **AND THEN** it uses copied projection mode unless `--symlink` is supplied

#### Scenario: Omitted home falls back to the project-scoped Codex default
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex` from `/workspace/repo`
- **AND WHEN** no `CODEX_HOME` is set
- **AND WHEN** no `--home`, `--set`, or `--skill` is supplied
- **THEN** the command installs the current Houmao-owned skill list resolved from the CLI default set list into `/workspace/repo/.codex`
- **AND THEN** overlapping set members are deduplicated by first occurrence

#### Scenario: Omitted home uses the project root as the Gemini default home
- **WHEN** an operator runs `houmao-mgr system-skills install --tool gemini --set user-control` from `/workspace/repo`
- **AND WHEN** no `GEMINI_CLI_HOME` is set
- **AND WHEN** no `--home` is supplied
- **THEN** the command uses `/workspace/repo` as the effective Gemini home
- **AND THEN** the selected skills are installed under `/workspace/repo/.gemini/skills/`

#### Scenario: Install combines named sets and explicit skills
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home --set user-control --skill houmao-agent-email-comms`
- **THEN** the command installs the resolved current Houmao-owned skill list from the named set plus the explicit skill into the explicit target home
- **AND THEN** it does not silently replace that explicit selection with another internal default selection

#### Scenario: Install applies one selected skill in symlink mode
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home --skill houmao-manage-specialist --symlink`
- **THEN** the command installs that selected Houmao-owned skill into the explicit target home using symlink projection mode
- **AND THEN** it does not silently replace that symlink request with copied projection

#### Scenario: Install fails when a selected set is unknown
- **WHEN** an operator runs `houmao-mgr system-skills install --tool gemini --home /tmp/gemini-home --set unknown-set`
- **THEN** the command fails explicitly
- **AND THEN** it does not guess another named set or continue with partial selection

#### Scenario: Install rejects the removed default flag
- **WHEN** an operator runs `houmao-mgr system-skills install --tool gemini --default`
- **THEN** the command exits non-zero because `--default` is not part of the current command surface
- **AND THEN** the operator must omit both `--set` and `--skill` to request CLI-default selection

### Requirement: `houmao-mgr system-skills status` reports Houmao-owned install state for one target home
`houmao-mgr system-skills status` SHALL report the Houmao-owned current-skill installation state for one effective target tool home.

The command SHALL require a supported tool identifier and SHALL accept an optional target home override.

When `--home` is omitted, the command SHALL resolve the effective target home with this precedence:

1. explicit `--home`
2. tool-native home env var
3. project-scoped default home

The project-scoped default homes SHALL be:

- Claude: `<cwd>/.claude`
- Codex: `<cwd>/.codex`
- Gemini: `<cwd>`

At minimum, the reported state SHALL identify:

- the target tool,
- the effective resolved home path,
- whether Houmao-owned install state exists,
- which current Houmao-owned skills are recorded as installed in that home,
- the recorded projection mode for each installed current Houmao-owned skill.

#### Scenario: Status uses tool-native env redirection when home is omitted
- **WHEN** `CLAUDE_CONFIG_DIR=/tmp/claude-home`
- **AND WHEN** an operator runs `houmao-mgr system-skills status --tool claude`
- **THEN** the command inspects `/tmp/claude-home` as the effective target home
- **AND THEN** it reports the resolved home path in the result

#### Scenario: Status falls back to the project-scoped Gemini default home
- **WHEN** an operator runs `houmao-mgr system-skills status --tool gemini` from `/workspace/repo`
- **AND WHEN** no `GEMINI_CLI_HOME` is set
- **AND WHEN** no `--home` is supplied
- **THEN** the command inspects `/workspace/repo` as the effective Gemini home
- **AND THEN** it reports install state for that effective home rather than for `/workspace/repo/.gemini`

#### Scenario: Status reports an untouched target home
- **WHEN** an operator runs `houmao-mgr system-skills status --tool codex` from `/workspace/repo`
- **AND WHEN** no `CODEX_HOME` is set
- **AND WHEN** `/workspace/repo/.codex` has no Houmao-owned current-skill install state
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

### Requirement: `houmao-mgr system-skills` surfaces the renamed specialist-management skill in current inventory
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory when reporting, installing, and inspecting Houmao-owned skills.

For the user-control skill set, that current inventory SHALL surface `houmao-manage-specialist` rather than `houmao-create-specialist`.

When `system-skills install` resolves the default or `user-control` selection, the reported installed skill names and subsequent `system-skills status` output SHALL use `houmao-manage-specialist` as the current specialist-management skill name.

#### Scenario: List reports the renamed specialist-management skill
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-manage-specialist` in the current Houmao-owned skill inventory
- **AND THEN** the `user-control` set resolves the renamed skill instead of `houmao-create-specialist`

#### Scenario: Default install and status report the renamed skill
- **WHEN** an operator installs the CLI default system-skill selection into a target tool home
- **THEN** the install result reports `houmao-manage-specialist` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-manage-specialist` as the installed specialist-management skill

### Requirement: `houmao-mgr system-skills` surfaces the user-control named set and credential-management skill
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-manage-credentials` as an installable packaged skill.

The reported named sets SHALL include `user-control` as the packaged non-mailbox user-controlled-agent skill set.

When `system-skills install` resolves a selection that includes `user-control`, the reported installed skill names and later `system-skills status` output SHALL include `houmao-manage-credentials` whenever that install completed successfully.

#### Scenario: List reports the user-control set and credential-management skill
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-manage-credentials` in the current Houmao-owned skill inventory
- **AND THEN** it reports `user-control` as the named set that groups the packaged user-controlled-agent skills

#### Scenario: User-control install and status report the credential-management skill
- **WHEN** an operator installs a system-skill selection that includes `user-control` into a target tool home
- **THEN** the install result reports `houmao-manage-credentials` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-manage-credentials` as installed when that selection completed successfully

### Requirement: `houmao-mgr system-skills` surfaces the user-control agent-definition skill
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-manage-agent-definition` as an installable packaged skill.

When `system-skills install` resolves a selection that includes `user-control`, the reported installed skill names and later `system-skills status` output SHALL include `houmao-manage-agent-definition` whenever that install completed successfully.

#### Scenario: List reports the user-control agent-definition skill
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-manage-agent-definition` in the current Houmao-owned skill inventory
- **AND THEN** it reports that skill as part of the packaged `user-control` skill family

#### Scenario: User-control install and status report the agent-definition skill
- **WHEN** an operator installs a system-skill selection that includes `user-control` into a target tool home
- **THEN** the install result reports `houmao-manage-agent-definition` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-manage-agent-definition` as installed when that selection completed successfully

### Requirement: `houmao-mgr system-skills` surfaces the packaged agent-instance lifecycle skill and updated CLI-default selection
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and fixed set lists when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-manage-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway` as installable packaged skills.

The reported named sets SHALL include the dedicated agent-instance lifecycle set, the dedicated agent-messaging set, and the dedicated agent-gateway set.

When `system-skills install` resolves the packaged CLI-default set list, the resolved installed skill names and later `system-skills status` output SHALL include:

- `houmao-manage-specialist`
- `houmao-manage-credentials`
- `houmao-manage-agent-definition`
- `houmao-manage-agent-instance`
- `houmao-agent-messaging`
- `houmao-agent-gateway`

Omitting both `--set` and `--skill` SHALL remain one supported path that resolves the packaged CLI-default set list.

#### Scenario: List reports the packaged lifecycle, messaging, and gateway skills with their sets
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-manage-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway` in the current Houmao-owned skill inventory
- **AND THEN** it reports the dedicated named sets that resolve those skills

#### Scenario: Omitted-selection install reports the packaged non-mailbox Houmao skills
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home`
- **AND WHEN** no `--set` or `--skill` is supplied
- **THEN** the install result reports `houmao-manage-specialist`, `houmao-manage-credentials`, `houmao-manage-agent-definition`, `houmao-manage-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports those skills as installed when the CLI-default install completed successfully

### Requirement: `houmao-mgr system-skills` surfaces the unified mailbox skill inventory
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory and named sets when reporting, installing, and inspecting Houmao-owned mailbox skills.

That current mailbox inventory SHALL surface:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`
- `houmao-mailbox-mgr`

That current mailbox inventory SHALL NOT surface the removed top-level mailbox skill names:

- `houmao-email-via-agent-gateway`
- `houmao-email-via-filesystem`
- `houmao-email-via-stalwart`

If the packaged catalog reports both `mailbox-core` and `mailbox-full`, `mailbox-core` SHALL resolve to the current mailbox worker pair built from `houmao-process-emails-via-gateway` and `houmao-agent-email-comms`, while `mailbox-full` SHALL resolve to that worker pair plus `houmao-mailbox-mgr`.

When `system-skills install` resolves a selection that includes mailbox skills, the reported installed skill names and later `system-skills status` output SHALL use only the current mailbox skill names.

#### Scenario: List reports the unified mailbox worker and mailbox-admin skills with current mailbox sets
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-process-emails-via-gateway`, `houmao-agent-email-comms`, and `houmao-mailbox-mgr` in the current Houmao-owned skill inventory
- **AND THEN** it does not report `houmao-email-via-agent-gateway`, `houmao-email-via-filesystem`, or `houmao-email-via-stalwart` as current installable skills
- **AND THEN** `mailbox-core` and `mailbox-full` are reported with distinct current membership

#### Scenario: Mailbox-full install and status report the mailbox-admin skill
- **WHEN** an operator installs a system-skill selection that includes `mailbox-full` into a target tool home
- **THEN** the install result reports `houmao-process-emails-via-gateway`, `houmao-agent-email-comms`, and `houmao-mailbox-mgr` as the current mailbox skill names for that selection
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports those same current mailbox skill names as installed when that selection completed successfully

#### Scenario: Mailbox-core remains the narrow worker pair
- **WHEN** an operator installs a system-skill selection that includes `mailbox-core` and no broader mailbox set
- **THEN** the resolved mailbox skill list includes `houmao-process-emails-via-gateway` and `houmao-agent-email-comms`
- **AND THEN** it does not automatically add `houmao-mailbox-mgr` through the narrower mailbox-core selection
