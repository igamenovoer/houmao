## ADDED Requirements

### Requirement: CLI reference documents consolidated project targeting
The CLI reference SHALL document `houmao-mgr project --project-dir <dir> ...` as the maintained explicit project selection surface.

The reference SHALL explain that `--project-dir` selects the human-facing project directory and resolves the overlay at `<dir>/.houmao`.

The reference SHALL update examples for project credentials, specialists, profiles, managed-agent launch, skills, mailbox, and status so they use either omitted auto-discovery or the group-level `--project-dir` option.

#### Scenario: Reader finds explicit project selection
- **WHEN** a reader opens the `houmao-mgr project` CLI reference
- **THEN** the page documents `--project-dir <dir>` as a group-level option
- **AND THEN** the examples show `houmao-mgr project --project-dir /repo credentials codex list`

## MODIFIED Requirements

### Requirement: houmao-mgr reference documents all command groups
The CLI reference SHALL include a page for `houmao-mgr` documenting its active public command groups (`admin`, `agents`, `internals`, `mailbox`, `project`, and `system-skills`) with subcommand summaries derived from `srv_ctrl/commands/` module docstrings, Click decorators, and live help output.

The CLI reference SHALL NOT document top-level `houmao-mgr credentials`, top-level `houmao-mgr brains`, or top-level `houmao-mgr server` command groups as maintained public manager surfaces.

The CLI reference SHALL make the major nested managed-agent, project, and internal command families discoverable either inline or through dedicated linked pages. At minimum, that coverage SHALL include:

- `agents launch`, `join`, `list`, `state`, `prompt`, `stop`, `interrupt`, and `relaunch`,
- `agents turn`,
- `agents gateway` (including `tui` and `mail-notifier` subgroups),
- `agents mail`,
- `agents mailbox`,
- `agents cleanup`,
- `project --project-dir`,
- `project agents`,
- `project credentials`,
- `project`,
- `project mailbox`,
- `admin cleanup`,
- `internals graph` (via a dedicated linked page `docs/reference/cli/internals.md`),
- `internals native-agent credentials`,
- `internals native-agent brain build`.

When the CLI reference documents `agents mail`, that coverage SHALL include the current subcommands `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`, and it SHALL explain:

- the selector rules for explicit targeting versus current-session targeting inside the owning managed tmux session,
- the structured `resolve-live` result contract for current mailbox discovery, including the returned mailbox binding and optional `gateway.base_url`,
- that mailbox-specific shell export is not part of the supported `resolve-live` contract,
- the authority-aware result semantics that distinguish verified execution from non-authoritative TUI submission fallback.

When the CLI reference documents `agents gateway`, that coverage SHALL include the `tui` subgroup (`state`, `history`, `watch`, `note-prompt`) and the `mail-notifier` subgroup (`status`, `enable`, `disable`) with full option tables and descriptions.

The internal native-agent brain-build options table in the CLI reference SHALL reflect the current live CLI flag names retained by the internal build surface, including `--preset`, `--setup`, and `--auth` when those inputs remain supported. The table SHALL NOT list retired flag names `--recipe`, `--config-profile`, or `--cred-profile`.

When the `houmao-mgr` reference describes Claude credential lanes for `project specialist create --tool claude`, it SHALL distinguish the prefixed specialist flag names (`--claude-auth-token`, `--claude-oauth-token`, `--claude-config-dir`) from the unprefixed dedicated credential-management flag names used by `project credentials claude` and `internals native-agent credentials claude` (`--auth-token`, `--oauth-token`, `--config-dir`). It SHALL state that both surfaces accept the same credential semantics but use different flag-name conventions.

#### Scenario: Reader finds current public command groups
- **WHEN** a reader looks up `houmao-mgr`
- **THEN** they find documented public subcommands for `agents`, `internals`, `mailbox`, `project`, `system-skills`, and `admin`
- **AND THEN** they do not find top-level `credentials`, top-level `brains`, or `server` documented as maintained public manager command groups
- **AND THEN** the CLI reference does not present removed or outdated project group names as the supported public project surface

#### Scenario: Reader can discover internal brain and credential command families
- **WHEN** a reader looks up `houmao-mgr` command groups in the CLI reference
- **THEN** they find an `internals` section that points to `docs/reference/cli/internals.md`
- **AND THEN** that internals reference documents direct native-agent credentials and brain build commands

#### Scenario: Reader can discover nested managed-agent and project command families
- **WHEN** a reader needs details for `agents gateway`, `agents turn`, `agents mail`, `agents mailbox`, `project agents`, `project credentials`, `project`, `project mailbox`, or `admin cleanup`
- **THEN** the CLI reference provides a direct path to formal reference coverage for those nested families
- **AND THEN** the reader does not need to reconstruct those command surfaces only from source code or scattered prose pages

#### Scenario: Reader can find `agents mail resolve-live` and targeting rules
- **WHEN** a reader looks up `houmao-mgr agents mail`
- **THEN** the CLI reference documents `resolve-live`, `list`, `read`, `archive`, and the other mailbox follow-up commands in that family
- **AND THEN** the reader can see when omitted selectors resolve the current managed tmux session and when explicit `--agent-id` or `--agent-name` is required
- **AND THEN** the page explains that `resolve-live` returns structured mailbox data rather than mailbox-specific shell export

#### Scenario: Reader can find `agents mail` result-strength guidance
- **WHEN** a reader looks up `houmao-mgr agents mail` result behavior
- **THEN** the CLI reference explains when the command returns verified authoritative results versus non-authoritative submission-only fallback
- **AND THEN** the page points the reader to the supported verification paths for non-authoritative outcomes

#### Scenario: Reader finds internal brain management commands
- **WHEN** a reader looks up direct brain-build plumbing
- **THEN** they find `houmao-mgr internals native-agent brain build`

#### Scenario: Reader finds correct brain build flag names
- **WHEN** a reader looks up internal native-agent brain-build options in the CLI reference
- **THEN** the options table lists `--preset`, `--setup`, and `--auth` when those inputs remain part of the internal build contract
- **AND THEN** the table does NOT list `--recipe`, `--config-profile`, or `--cred-profile`

#### Scenario: Example commands in paired reference docs use current flag names
- **WHEN** a reader copies a direct brain-build example command from any docs page
- **THEN** the command uses the internal native-agent path and current flag names
- **AND THEN** the command does not fail with an unrecognized option error

#### Scenario: Reader finds gateway tui and mail-notifier subgroups documented
- **WHEN** a reader looks up `houmao-mgr agents gateway`
- **THEN** the CLI reference includes `tui state`, `tui history`, `tui watch`, `tui note-prompt` with option tables
- **AND THEN** the CLI reference includes `mail-notifier status`, `mail-notifier enable`, `mail-notifier disable` with option tables

#### Scenario: Reader sees correct Claude auth flag-name distinction
- **WHEN** a reader looks up Claude credential lanes in the `houmao-mgr` reference
- **THEN** the page shows that `project credentials claude` and `internals native-agent credentials claude` use `--auth-token`, `--oauth-token`, `--config-dir`
- **AND THEN** the page shows that `project specialist create --tool claude` uses `--claude-auth-token`, `--claude-oauth-token`, `--claude-config-dir`
- **AND THEN** the page states that both surfaces accept the same credential semantics

## REMOVED Requirements

### Requirement: CLI reference documents the dedicated credential-management families
**Reason**: Credential documentation no longer treats top-level `credentials` as a first-class public command family. Project credentials live under `project credentials`, while direct native-agent credentials live under internals.
**Migration**: Document `houmao-mgr project [--project-dir <dir>] credentials ...` and `houmao-mgr internals native-agent credentials ...`.

### Requirement: CLI reference documents the credential login helper
**Reason**: Login helper documentation remains, but it is no longer attached to a top-level credential target multiplexer.
**Migration**: Document login under `project credentials <tool> login` and retained `internals native-agent credentials <tool> login`.
