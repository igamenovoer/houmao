## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the unified mailbox skill inventory
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory and named sets when reporting, installing, and inspecting Houmao-owned mailbox skills.

That current mailbox inventory SHALL surface:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`

That current mailbox inventory SHALL NOT surface the removed top-level mailbox skill names:

- `houmao-email-via-agent-gateway`
- `houmao-email-via-filesystem`
- `houmao-email-via-stalwart`

If the packaged catalog reports both `mailbox-core` and `mailbox-full`, each of those named sets SHALL resolve to the current mailbox skill selection built from `houmao-process-emails-via-gateway` and `houmao-agent-email-comms`.

When `system-skills install` resolves a selection that includes mailbox skills, the reported installed skill names and later `system-skills status` output SHALL use only the current mailbox skill names.

#### Scenario: List reports the unified mailbox skills and current mailbox sets
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-process-emails-via-gateway` and `houmao-agent-email-comms` in the current Houmao-owned skill inventory
- **AND THEN** it does not report `houmao-email-via-agent-gateway`, `houmao-email-via-filesystem`, or `houmao-email-via-stalwart` as current installable skills
- **AND THEN** any reported mailbox named sets resolve through the current two-skill mailbox inventory

#### Scenario: Mailbox install and status report the unified mailbox skill names
- **WHEN** an operator installs a system-skill selection that includes mailbox skills into a target tool home
- **THEN** the install result reports `houmao-process-emails-via-gateway` and `houmao-agent-email-comms` as the current mailbox skill names for that selection
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports those same current mailbox skill names as installed when that selection completed successfully
