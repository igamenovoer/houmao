## Purpose
Define the operator-facing `houmao-mgr system-skills` CLI for listing, installing, and inspecting Houmao-owned system skills.
## Requirements
### Requirement: `houmao-mgr system-skills` exposes the current Houmao-owned skill installation surface
`houmao-mgr` SHALL expose a top-level `system-skills` command family for the current Houmao-owned system-skill set.

At minimum, that command family SHALL include:

- `list`
- `install`
- `status`
- `uninstall`

#### Scenario: Help shows the system-skill command family
- **WHEN** an operator runs `houmao-mgr system-skills --help`
- **THEN** the help output lists `list`, `install`, `status`, and `uninstall`
- **AND THEN** the command family is presented as the Houmao-owned system-skill installation surface for the current skill set

### Requirement: `houmao-mgr system-skills list` reports the current installable Houmao-owned skill inventory and named sets
`houmao-mgr system-skills list` SHALL report the current installable Houmao-owned skill inventory and the current named skill sets from the packaged catalog.

The reported current named skill sets SHALL be `core` and `all`.

That output SHALL identify the configured CLI default set list and the fixed internal auto-install set lists.

#### Scenario: List reports core and all with default set markers
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports the current installable Houmao-owned skill names
- **AND THEN** it reports `core` and `all` as the current named skill sets
- **AND THEN** it identifies `managed_launch_sets = ["core"]`, `managed_join_sets = ["core"]`, and `cli_default_sets = ["all"]`

### Requirement: `houmao-mgr system-skills install` targets an explicit tool home and set-based selection
`houmao-mgr system-skills install` SHALL require a supported tool identifier or a comma-separated list of supported tool identifiers through `--tool`.

The command SHALL support these selection inputs:

- repeatable `--skill-set <name>` for current named system-skill set selection,
- repeatable `--skill <name>` for explicit current-skill selection.

The current named system-skill sets accepted by `--skill-set` SHALL be `core` and `all`.

When neither `--skill-set` nor `--skill` is provided, the command SHALL use the CLI default set list from the packaged catalog, which resolves `all` in this change.

The command SHALL NOT expose `--set` or `--default` as part of the supported public install surface.

For multi-tool installs, the command SHALL apply the same selected sets, explicit skills, and resolved projection mode to every selected tool.

#### Scenario: Omitted-selection install uses all
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home`
- **AND WHEN** no `--skill-set` or `--skill` is supplied
- **THEN** the command installs the current Houmao-owned skill list resolved from `cli_default_sets = ["all"]`
- **AND THEN** the resolved list includes current utility skills

#### Scenario: Explicit core install is accepted
- **WHEN** an operator runs `houmao-mgr system-skills install --tool gemini --home /tmp/gemini-home --skill-set core`
- **THEN** the command installs the current Houmao-owned skill list resolved from `core`
- **AND THEN** the resolved list excludes utility skills that are only in `all`

#### Scenario: Removed granular set names are rejected
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --skill-set user-control`
- **THEN** the command fails explicitly before installing any selected skill
- **AND THEN** the error treats `user-control` as an unknown set rather than mapping it to `core`

### Requirement: `houmao-mgr system-skills` surfaces the renamed specialist-management skill in current inventory
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory when reporting, installing, and inspecting Houmao-owned skills.

For the user-control skill set, that current inventory SHALL surface `houmao-specialist-mgr` rather than `houmao-manage-specialist`.

When `system-skills install` resolves the default or `user-control` selection, the reported installed skill names and subsequent `system-skills status` output SHALL use `houmao-specialist-mgr` as the current specialist-management skill name.

#### Scenario: List reports the renamed specialist-management skill
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-specialist-mgr` in the current Houmao-owned skill inventory
- **AND THEN** the `user-control` set resolves the renamed skill instead of `houmao-manage-specialist`

#### Scenario: Default install and status report the renamed skill
- **WHEN** an operator installs the CLI default system-skill selection into a target tool home
- **THEN** the install result reports `houmao-specialist-mgr` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-specialist-mgr` as the installed specialist-management skill

### Requirement: `houmao-mgr system-skills` surfaces the user-control project-management skill
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-project-mgr` as an installable packaged skill.

When `system-skills install` resolves a selection that includes `user-control`, the reported installed skill names and later `houmao-mgr system-skills status` output SHALL include `houmao-project-mgr` whenever that install completed successfully.

#### Scenario: List reports the user-control project-management skill
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-project-mgr` in the current Houmao-owned skill inventory
- **AND THEN** it reports that skill as part of the packaged `user-control` skill family

#### Scenario: User-control install and status report the project-management skill
- **WHEN** an operator installs a system-skill selection that includes `user-control` into a target tool home
- **THEN** the install result reports `houmao-project-mgr` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-project-mgr` as installed when that selection completed successfully

### Requirement: `houmao-mgr system-skills` surfaces the user-control named set and credential-management skill
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-credential-mgr` as an installable packaged skill.

The reported named sets SHALL include `user-control` as the packaged non-mailbox user-controlled-agent skill set.

When `system-skills install` resolves a selection that includes `user-control`, the reported installed skill names and later `system-skills status` output SHALL include `houmao-credential-mgr` whenever that install completed successfully.

#### Scenario: List reports the user-control set and credential-management skill
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-credential-mgr` in the current Houmao-owned skill inventory
- **AND THEN** it reports `user-control` as the named set that groups the packaged user-controlled-agent skills

#### Scenario: User-control install and status report the credential-management skill
- **WHEN** an operator installs a system-skill selection that includes `user-control` into a target tool home
- **THEN** the install result reports `houmao-credential-mgr` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-credential-mgr` as installed when that selection completed successfully

### Requirement: `houmao-mgr system-skills` surfaces the user-control agent-definition skill
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-agent-definition` as an installable packaged skill.

When `system-skills install` resolves a selection that includes `user-control`, the reported installed skill names and later `system-skills status` output SHALL include `houmao-agent-definition` whenever that install completed successfully.

#### Scenario: List reports the user-control agent-definition skill
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-agent-definition` in the current Houmao-owned skill inventory
- **AND THEN** it reports that skill as part of the packaged `user-control` skill family

#### Scenario: User-control install and status report the agent-definition skill
- **WHEN** an operator installs a system-skill selection that includes `user-control` into a target tool home
- **THEN** the install result reports `houmao-agent-definition` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-agent-definition` as installed when that selection completed successfully

### Requirement: `houmao-mgr system-skills` surfaces the packaged agent-instance lifecycle skill and updated CLI-default selection
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and fixed set lists when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway` as installable packaged skills.

The reported named sets SHALL include the dedicated agent-instance lifecycle set, the dedicated agent-messaging set, and the dedicated agent-gateway set.

When `system-skills install` resolves the packaged CLI-default set list, the resolved installed skill names and later `system-skills status` output SHALL include:

- `houmao-project-mgr`
- `houmao-specialist-mgr`
- `houmao-credential-mgr`
- `houmao-agent-definition`
- `houmao-agent-instance`
- `houmao-agent-messaging`
- `houmao-agent-gateway`

Omitting both `--set` and `--skill` SHALL remain one supported path that resolves the packaged CLI-default set list.

#### Scenario: List reports the packaged lifecycle, messaging, and gateway skills with their sets
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway` in the current Houmao-owned skill inventory
- **AND THEN** it reports the dedicated named sets that resolve those skills

#### Scenario: Omitted-selection install reports the packaged non-mailbox Houmao skills
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home`
- **AND WHEN** no `--set` or `--skill` is supplied
- **THEN** the install result reports `houmao-project-mgr`, `houmao-specialist-mgr`, `houmao-credential-mgr`, `houmao-agent-definition`, `houmao-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway` in the resolved current skill list
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

### Requirement: `houmao-mgr system-skills` surfaces the packaged advanced-usage skill
`houmao-mgr system-skills` SHALL use the packaged current-system-skill inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-adv-usage-pattern` as an installable packaged skill.

The reported named sets SHALL include the dedicated advanced-usage set for that skill.

When `system-skills install` resolves the packaged managed-home or CLI-default selection that includes the advanced-usage set, the reported installed skill names and later `system-skills status` output SHALL include `houmao-adv-usage-pattern` whenever that install completed successfully.

#### Scenario: List reports the advanced-usage skill and set
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-adv-usage-pattern` in the current Houmao-owned skill inventory
- **AND THEN** it reports the dedicated advanced-usage named set in the current packaged set inventory

#### Scenario: Default install and status report the advanced-usage skill
- **WHEN** an operator installs a packaged default system-skill selection into a target tool home
- **THEN** the install result reports `houmao-adv-usage-pattern` in the resolved current skill list when the default set list includes the advanced-usage set
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-adv-usage-pattern` as installed when that selection completed successfully

### Requirement: `houmao-mgr system-skills` surfaces the packaged `houmao-touring` skill and touring set
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-touring` as an installable packaged skill.

The reported named sets SHALL include the dedicated `touring` set.

When `system-skills install` resolves the packaged default set list for any supported tool home, the resolved installed skill names and later `system-skills status` output SHALL include `houmao-touring`.

Omitting both `--set` and `--skill` SHALL remain a supported path that resolves the packaged default set list including the touring set.

#### Scenario: List reports the touring skill and named set
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-touring` in the current Houmao-owned skill inventory
- **AND THEN** it reports the dedicated `touring` named set among the packaged named sets

#### Scenario: Default install and status report the touring skill
- **WHEN** an operator installs the packaged default system-skill selection into a target tool home
- **THEN** the install result reports `houmao-touring` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-touring` as installed when that selection completed successfully

#### Scenario: Explicit touring-set install resolves the guided-tour skill
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home --set touring`
- **THEN** the command resolves `houmao-touring` from the dedicated `touring` named set
- **AND THEN** it installs that packaged skill into the target tool home through the shared system-skill installer

### Requirement: `houmao-mgr system-skills` surfaces the packaged `houmao-agent-inspect` skill and named set
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-agent-inspect` as an installable packaged skill.

The reported named sets SHALL include the dedicated `agent-inspect` set containing `houmao-agent-inspect`.

When `system-skills install` resolves the packaged default set list for a supported tool home, the resolved installed skill names and later `system-skills status` output SHALL include `houmao-agent-inspect`.

Omitting both `--set` and `--skill` SHALL remain a supported path that resolves the packaged default set list including the `agent-inspect` set.

#### Scenario: List reports the packaged inspect skill and named set
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-agent-inspect` in the current Houmao-owned skill inventory
- **AND THEN** it reports the dedicated `agent-inspect` named set in the current packaged set inventory

#### Scenario: Omitted-selection install and status report the inspect skill
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home`
- **AND WHEN** no `--set` or `--skill` is supplied
- **THEN** the install result reports `houmao-agent-inspect` in the resolved current skill list when the packaged default set list includes `agent-inspect`
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-agent-inspect` as installed when the default install completed successfully

### Requirement: `houmao-mgr system-skills` surfaces both packaged pairwise skill variants
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` as installable packaged skills.

When `system-skills install` resolves a selection that includes `user-control`, the reported installed skill names and later `houmao-mgr system-skills status` output SHALL include both pairwise variants whenever that installation completed successfully.

#### Scenario: List reports both packaged pairwise skill variants
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` in the current Houmao-owned skill inventory
- **AND THEN** it reports both skills as part of the packaged `user-control` skill family

#### Scenario: User-control install and status report both pairwise variants
- **WHEN** an operator installs a system-skill selection that includes `user-control` into a target tool home
- **THEN** the install result reports both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports both pairwise variants as installed when that selection completed successfully

### Requirement: `houmao-mgr system-skills` surfaces the packaged generic loop planner
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-agent-loop-generic` as an installable packaged skill.

That current inventory SHALL NOT surface `houmao-agent-loop-relay` as an installable packaged skill after the generic replacement is introduced.

When `system-skills install` resolves a selection that includes `user-control`, the reported installed skill names and later `houmao-mgr system-skills status` output SHALL include `houmao-agent-loop-generic` whenever that installation completed successfully.

When `system-skills install` resolves a selection that includes `user-control`, the reported installed skill names and later `houmao-mgr system-skills status` output SHALL NOT include `houmao-agent-loop-relay` after the generic replacement is introduced.

#### Scenario: List reports packaged generic loop planner
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-agent-loop-generic` in the current Houmao-owned skill inventory
- **AND THEN** it reports that skill as part of the packaged `user-control` skill family

#### Scenario: List no longer reports relay loop planner
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command does not report `houmao-agent-loop-relay` as a current installable skill

#### Scenario: User-control install and status report generic loop planner
- **WHEN** an operator installs a system-skill selection that includes `user-control` into a target tool home
- **THEN** the install result reports `houmao-agent-loop-generic` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-agent-loop-generic` as installed when that selection completed successfully

### Requirement: `houmao-mgr system-skills` surfaces managed-memory guidance
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and fixed set lists when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-memory-mgr` as an installable packaged skill.

The reported named sets SHALL include the dedicated managed-memory set that resolves `houmao-memory-mgr`.

When `system-skills install` resolves the packaged CLI-default set list, the resolved installed skill names and later `system-skills status` output SHALL include `houmao-memory-mgr`.

#### Scenario: List reports the packaged memory-management skill and set
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-memory-mgr` in the current Houmao-owned skill inventory
- **AND THEN** it reports the dedicated named set that resolves that skill

#### Scenario: Omitted-selection install and status report memory-management guidance
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home`
- **AND WHEN** no `--set` or `--skill` is supplied
- **THEN** the install result reports `houmao-memory-mgr` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-memory-mgr` as installed when the CLI-default install completed successfully

### Requirement: `houmao-mgr system-skills` supports Copilot homes
`houmao-mgr system-skills install` and `houmao-mgr system-skills status` SHALL accept `copilot` as a supported `--tool` value.

When `--tool copilot` and `--home` is omitted, the command SHALL resolve the effective target home with this precedence:

1. explicit `--home`
2. `COPILOT_HOME`
3. `<cwd>/.github`

For Copilot, the resolved effective home SHALL remain the home root itself, and Houmao-owned installed skills SHALL project under `<effective-home>/skills/`.

The command SHALL NOT add or require a Copilot-specific `--scope` flag.

#### Scenario: Omitted home falls back to the project-scoped Copilot default
- **WHEN** an operator runs `houmao-mgr system-skills install --tool copilot --set user-control` from `/workspace/repo`
- **AND WHEN** no `COPILOT_HOME` is set
- **AND WHEN** no `--home` is supplied
- **THEN** the command uses `/workspace/repo/.github` as the effective Copilot home
- **AND THEN** the selected skills are installed under `/workspace/repo/.github/skills/`

#### Scenario: Omitted home uses Copilot env redirection first
- **WHEN** `COPILOT_HOME=/tmp/copilot-home`
- **AND WHEN** an operator runs `houmao-mgr system-skills install --tool copilot --skill houmao-specialist-mgr`
- **THEN** the command installs the selected skill into `/tmp/copilot-home/skills/houmao-specialist-mgr/`
- **AND THEN** it does not redirect that install to the current repository's `.github` directory

#### Scenario: Explicit home supports personal Copilot installs without a scope flag
- **WHEN** an operator runs `houmao-mgr system-skills install --tool copilot --home ~/.copilot --skill houmao-agent-messaging`
- **THEN** the command installs the selected skill into the expanded `~/.copilot/skills/houmao-agent-messaging/` path
- **AND THEN** it does not require a separate `--scope personal` option

#### Scenario: Copilot status reports a project-scoped default home
- **WHEN** an operator runs `houmao-mgr system-skills status --tool copilot` from `/workspace/repo`
- **AND WHEN** no `COPILOT_HOME` is set
- **AND WHEN** no `--home` is supplied
- **THEN** the command inspects `/workspace/repo/.github` as the effective Copilot home
- **AND THEN** it reports install state for skills under `/workspace/repo/.github/skills/`

### Requirement: `houmao-mgr system-skills status` discovers current projected skills from the filesystem
`houmao-mgr system-skills status` SHALL report current packaged Houmao-owned skill projections discovered in one effective target tool home.

The command SHALL require a supported tool identifier and SHALL accept an optional target home override.

When `--home` is omitted, the command SHALL resolve the effective target home with this precedence:

1. tool-native home env var
2. project-scoped default home

For status invocations with `--home`, explicit `--home` SHALL take precedence over tool-native home env vars and project-scoped defaults.

The project-scoped default homes SHALL be:

- Claude: `<cwd>/.claude`
- Codex: `<cwd>/.codex`
- Copilot: `<cwd>/.github`
- Gemini: `<cwd>`

At minimum, the reported state SHALL identify:

- the target tool,
- the effective resolved home path,
- which current Houmao-owned skill projection paths are present in that home,
- the inferred projection mode for each discovered current Houmao-owned skill.

The command SHALL infer `copy` for a discovered current skill directory and `symlink` for a discovered current skill symlink.

The command SHALL NOT require, parse, validate, or report Houmao install-state metadata inside the target home.

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
- **AND THEN** it reports discovered current skill projections under `/workspace/repo/.gemini/skills/`

#### Scenario: Status reports an untouched target home
- **WHEN** an operator runs `houmao-mgr system-skills status --tool codex` from `/workspace/repo`
- **AND WHEN** no `CODEX_HOME` is set
- **AND WHEN** `/workspace/repo/.codex` has no current packaged Houmao-owned skill projection paths
- **THEN** the command reports no installed current Houmao-owned skills for that home
- **AND THEN** it does not require or mention install-state metadata

#### Scenario: Status reports discovered copied projections
- **WHEN** an operator runs `houmao-mgr system-skills status --tool gemini --home /tmp/gemini-home`
- **AND WHEN** current Houmao-owned skills exist in that home as copied directories
- **THEN** the command reports the discovered current skill names for that home
- **AND THEN** it reports `copy` as the inferred projection mode for those discovered skills

#### Scenario: Status reports discovered symlink projections
- **WHEN** an operator runs `houmao-mgr system-skills status --tool codex --home /tmp/codex-home`
- **AND WHEN** current Houmao-owned skills exist in that home as symlinks
- **THEN** the command reports the discovered current skill names for that home
- **AND THEN** it reports `symlink` as the inferred projection mode for those discovered skills

#### Scenario: Status ignores obsolete install-state files
- **WHEN** a target home contains an obsolete `.houmao/system-skills/install-state.json`
- **AND WHEN** an operator runs `houmao-mgr system-skills status` for that home
- **THEN** the command reports discovered current skill projection paths from the filesystem
- **AND THEN** it does not fail because of the obsolete install-state file

### Requirement: `houmao-mgr system-skills uninstall` removes all known Houmao-owned skills from resolved homes
`houmao-mgr system-skills uninstall` SHALL require a supported tool identifier or a comma-separated list of supported tool identifiers through `--tool`.

The supported tool identifiers SHALL include:

- `claude`
- `codex`
- `copilot`
- `gemini`

When `--tool` contains commas, the command SHALL parse the value as an ordered tool list, trimming whitespace around each entry.

The command SHALL reject an empty parsed tool entry, an unsupported tool entry, or a duplicate parsed tool entry before mutating any target home.

The command SHALL accept an optional target home override only when the parsed tool list contains exactly one tool. When the parsed tool list contains more than one tool, the command SHALL reject `--home` before mutating any target home.

When `--home` is omitted, the command SHALL resolve the effective target home for each selected tool with this precedence:

1. tool-native home env var
2. project-scoped default home

For single-tool uninstalls with `--home`, explicit `--home` SHALL take precedence over the tool-native home env var and project-scoped default home.

The tool-native home env vars SHALL be:

- Claude: `CLAUDE_CONFIG_DIR`
- Codex: `CODEX_HOME`
- Copilot: `COPILOT_HOME`
- Gemini: `GEMINI_CLI_HOME`

The project-scoped default homes SHALL be:

- Claude: `<cwd>/.claude`
- Codex: `<cwd>/.codex`
- Copilot: `<cwd>/.github`
- Gemini: `<cwd>`

For Gemini, the resolved effective home SHALL remain the home root itself, and Houmao-owned skills SHALL be removed from `<effective-home>/.gemini/skills/`.

The command SHALL NOT accept `--skill`, `--skill-set`, `--set`, `--default`, `--symlink`, or another selection flag. Uninstall SHALL always target every current Houmao-owned skill name in the packaged catalog.

For each current catalog-known Houmao-owned skill, the command SHALL compute the exact current tool-native destination path and remove that path when it exists as a directory, file, or symlink.

The command SHALL NOT remove parent skill roots, unrelated tool-home content, unrecognized `houmao-*` paths, legacy family-namespaced paths, or obsolete install-state files.

The command SHALL be idempotent. Missing current Houmao-owned skill paths SHALL be reported as absent or skipped rather than treated as failures.

The command SHALL NOT create a missing resolved target home, parent skill root, or skill directory just to perform uninstall.

For single-tool uninstalls, the structured result SHALL use a single-uninstall payload with scalar `tool` and `home_path` fields.

For multi-tool uninstalls, the structured result SHALL contain the parsed `tools` list and one single-uninstall-shaped result entry per selected tool.

At minimum, each single-tool uninstall result SHALL report removed skill names, removed projected relative dirs, absent skill names, and absent projected relative dirs.

#### Scenario: Single-tool uninstall removes current copied and symlinked skill paths
- **WHEN** an operator runs `houmao-mgr system-skills uninstall --tool codex --home /tmp/codex-home`
- **AND WHEN** `/tmp/codex-home` contains current Houmao-owned skill paths as copied directories, symlinks, or files under `skills/`
- **THEN** the command removes those current catalog-known Houmao skill paths
- **AND THEN** the structured result reports the removed skill names and projected relative dirs

#### Scenario: Uninstall leaves unrelated content in place
- **WHEN** an operator runs `houmao-mgr system-skills uninstall --tool codex --home /tmp/codex-home`
- **AND WHEN** `/tmp/codex-home` contains `skills/custom-user-skill/`, legacy family-namespaced paths, parent skill roots, or obsolete `.houmao/system-skills/install-state.json`
- **THEN** the command leaves those paths in place
- **AND THEN** it removes only exact current catalog-known Houmao system-skill projection paths

#### Scenario: Uninstall is idempotent for missing skill paths
- **WHEN** an operator runs `houmao-mgr system-skills uninstall --tool claude --home /tmp/claude-home`
- **AND WHEN** some current Houmao-owned skill projection paths are missing
- **THEN** the command succeeds
- **AND THEN** the structured result reports the missing current skill paths as absent or skipped

#### Scenario: Uninstall does not create a missing home
- **WHEN** an operator runs `houmao-mgr system-skills uninstall --tool codex --home /tmp/missing-codex-home`
- **AND WHEN** `/tmp/missing-codex-home` does not exist
- **THEN** the command succeeds without creating `/tmp/missing-codex-home`
- **AND THEN** the structured result reports current catalog-known Houmao skills as absent

#### Scenario: Uninstall uses tool-native env redirection when home is omitted
- **WHEN** `CODEX_HOME=/tmp/codex-from-env`
- **AND WHEN** an operator runs `houmao-mgr system-skills uninstall --tool codex`
- **THEN** the command uses `/tmp/codex-from-env` as the effective target home
- **AND THEN** it removes current catalog-known Houmao system-skill projection paths from that home

#### Scenario: Uninstall supports comma-separated multi-tool homes
- **WHEN** an operator runs `houmao-mgr system-skills uninstall --tool claude,codex,copilot,gemini` from `/workspace/repo`
- **AND WHEN** no tool-native home env vars are set
- **AND WHEN** no `--home` is supplied
- **THEN** the command resolves `/workspace/repo/.claude`, `/workspace/repo/.codex`, `/workspace/repo/.github`, and `/workspace/repo` as the target homes
- **AND THEN** the Gemini current skill paths are removed from `/workspace/repo/.gemini/skills/`
- **AND THEN** the structured result contains `tools` and an `uninstallations` entry for each selected tool

#### Scenario: Multi-tool uninstall rejects explicit home override
- **WHEN** an operator runs `houmao-mgr system-skills uninstall --tool codex,claude --home /tmp/tool-home`
- **THEN** the command fails explicitly before removing any skill path
- **AND THEN** the error explains that `--home` is only valid when `--tool` names exactly one tool

#### Scenario: Uninstall rejects install-only selection flags
- **WHEN** an operator runs `houmao-mgr system-skills uninstall --tool codex --skill houmao-specialist-mgr`
- **THEN** the command exits non-zero because selection flags are not part of the uninstall surface
- **AND THEN** the operator must omit selection flags to remove all current known Houmao system skills for that home

#### Scenario: Status after uninstall reports no current installed Houmao-owned skills
- **WHEN** an operator uninstalls Houmao system skills from a Codex home
- **AND WHEN** the operator later runs `houmao-mgr system-skills status --tool codex --home <that-home>`
- **THEN** status reports no installed current Houmao-owned skills for that home

### Requirement: `houmao-mgr system-skills` surfaces the LLM Wiki utility skill and utils set
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and named sets when reporting, installing, inspecting, and removing `houmao-utils-llm-wiki`.

When `system-skills install` resolves an explicit `utils` set selection, the reported installed skill names and later `system-skills status` output SHALL include `houmao-utils-llm-wiki` whenever that install completed successfully.

When `system-skills install` resolves the packaged CLI-default selection, the resolved installed skill names SHALL NOT include `houmao-utils-llm-wiki`.

`system-skills uninstall` SHALL remove `houmao-utils-llm-wiki` when that current catalog-known skill path exists in the resolved home.

#### Scenario: Operator lists the utility skill and named set
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the output includes `houmao-utils-llm-wiki` in the current skill inventory
- **AND THEN** the output includes the `utils` named set
- **AND THEN** the managed-launch, managed-join, and CLI-default set lists do not include `utils`

#### Scenario: Operator installs the utility set explicitly
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --skill-set utils`
- **THEN** the resolved skill list includes `houmao-utils-llm-wiki`
- **AND THEN** the skill is projected into the Codex home under `skills/houmao-utils-llm-wiki/`

#### Scenario: Operator installs the utility skill explicitly
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --skill houmao-utils-llm-wiki`
- **THEN** the resolved skill list includes `houmao-utils-llm-wiki`
- **AND THEN** the skill is projected into the Codex home under `skills/houmao-utils-llm-wiki/`

#### Scenario: CLI-default install omits the utility skill
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex`
- **THEN** the resolved CLI-default skill list does not include `houmao-utils-llm-wiki`

#### Scenario: Uninstall removes an installed utility skill path
- **WHEN** a Codex home contains `skills/houmao-utils-llm-wiki/`
- **AND WHEN** an operator runs `houmao-mgr system-skills uninstall --tool codex --home <home>`
- **THEN** the command removes `skills/houmao-utils-llm-wiki/`

### Requirement: `houmao-mgr system-skills` surfaces utility skills through all
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and fixed set lists when reporting, installing, and inspecting Houmao-owned utility skills.

That current inventory SHALL surface `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr` as installable packaged skills.

The reported named sets SHALL include `all` as the set that contains the utility skills and SHALL NOT report `utils` as a current installable set.

When `system-skills install` resolves the packaged CLI-default set list, the resolved installed skill names and later `system-skills status` output SHALL include `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr`.

#### Scenario: List reports utility skills and all
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr` in the current Houmao-owned skill inventory
- **AND THEN** it reports `all` as the named set that includes those utility skills
- **AND THEN** it does not report `utils` as a current named set

#### Scenario: Omitted-selection install and status report utility skills
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home`
- **AND WHEN** no `--skill-set` or `--skill` is supplied
- **THEN** the install result reports `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports those utility skills as installed when the CLI-default install completed successfully
