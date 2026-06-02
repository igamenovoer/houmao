## MODIFIED Requirements

### Requirement: houmao-mgr reference documents all command groups
The CLI reference SHALL include a page for `houmao-mgr` documenting its active public command groups (`admin`, `agents`, `internals`, `mailbox`, `project`, and `system-skills`) with subcommand summaries derived from `srv_ctrl/commands/` module docstrings, Click decorators, and live help output.

The CLI reference SHALL NOT document top-level `houmao-mgr credentials`, top-level `houmao-mgr brains`, or top-level `houmao-mgr server` command groups as maintained public manager surfaces.

The CLI reference SHALL document `houmao-mgr agents` as a namespace with explicit `global`, `single`, `self`, and `external` scopes. It SHALL NOT document direct root-level `houmao-mgr agents launch`, `houmao-mgr agents mail`, `houmao-mgr agents gateway`, or similar direct agent action paths as maintained public command paths.

The CLI reference SHALL make the major nested managed-agent, project, and internal command families discoverable either inline or through dedicated linked pages. At minimum, that coverage SHALL include:

- `agents global list`,
- `agents single --agent-id <id>` and `agents single --agent-name <name>` group-level selectors,
- `agents single state`, `prompt`, `stop`, `interrupt`, and `relaunch`,
- `agents single turn`,
- `agents single gateway` including `tui`, `mail-notifier`, and `reminders` subgroups,
- `agents single mail`,
- `agents single mailbox`,
- `agents single memory`,
- `agents single cleanup`,
- `agents self join`,
- `agents self identity`,
- `agents self state`,
- `agents self prompt`,
- `agents self interrupt`,
- `agents self relaunch`,
- `agents self turn`,
- `agents self gateway`,
- `agents self mail`,
- `agents self mailbox`,
- `agents self memory`,
- `agents external register`, `list`, `get`, `verify`, and `remove`,
- `project --project-dir`,
- `project agents`,
- `project credentials`,
- `project`,
- `project mailbox`,
- `admin cleanup`,
- `internals graph` (via a dedicated linked page `docs/reference/cli/internals.md`),
- `internals native-agent credentials`,
- `internals native-agent brain build`.

When the CLI reference documents `agents global`, it SHALL explain that global commands operate on no individual agent or on multiple local managed agents as a registry/fleet. It SHALL explain that `agents global` does not target exactly one selected agent and does not use `--agent-id` or `--agent-name`.

When the CLI reference documents `agents single`, it SHALL explain that one-agent operations use a group-level `--agent-id <id>` or `--agent-name <name>` selector and SHALL NOT use current-session fallback.

When the CLI reference documents `agents single`, it SHALL explain that selected-agent lifecycle controls such as direct `prompt`, `interrupt`, `stop`, `relaunch`, and `cleanup` belong to `single`. It SHALL explain that `single relaunch` has broad selected-agent lifecycle authority, including stopped relaunchable-record revival and degraded/stale active-record recovery where supported.

When the CLI reference documents `agents self`, it SHALL explain that `self join` adopts the caller's current tmux session into Houmao management as one local managed-agent identity, and that other self commands resolve the target from the caller's current managed tmux session without `--agent-id`, `--agent-name`, or `--current-session`.

When the CLI reference documents `agents self`, it SHALL explain that `self` is not a selector-mode alias for `agents single`. It SHALL document `agents self prompt`, `agents self interrupt`, and `agents self relaunch` as current-session commands.

When the CLI reference documents `agents self relaunch`, it SHALL explain that the command refreshes only the active tmux-backed surface for the caller's current managed session. It SHALL state that selected-agent stopped-record revival and degraded/stale active-record recovery remain under `agents single --agent-id <id> relaunch` or `agents single --agent-name <name> relaunch`.

When the CLI reference documents `agents self`, it SHALL explain that `agents self stop` and `agents self cleanup` are not maintained public paths.

When the CLI reference documents `agents external`, it SHALL explain that external commands bring external agents into Houmao's shared registry as remotely owned or communication-only references, and that lifecycle management for those external agents is not controlled by this user's `houmao-mgr`.

When the CLI reference documents `agents single mail` and `agents self mail`, that coverage SHALL include the current subcommands `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`, and it SHALL explain:

- the selector rules for explicit single-agent targeting versus current-session self targeting,
- the structured `resolve-live` result contract for current mailbox discovery, including the returned mailbox binding and optional `gateway.base_url`,
- that mailbox-specific shell export is not part of the supported `resolve-live` contract,
- the authority-aware result semantics that distinguish verified execution from non-authoritative TUI submission fallback.

When the CLI reference documents gateway commands, that coverage SHALL include the `tui` subgroup (`state`, `history`, `watch`, `note-prompt`), the `mail-notifier` subgroup (`status`, `enable`, `disable`), and the `reminders` subgroup (`list`, `get`, `create`, `set`, `remove`) with full option tables and descriptions for the maintained single and self paths.

The internal native-agent brain-build options table in the CLI reference SHALL reflect the current live CLI flag names retained by the internal build surface, including `--preset`, `--setup`, and `--auth` when those inputs remain supported. The table SHALL NOT list retired flag names `--recipe`, `--config-profile`, or `--cred-profile`.

When the `houmao-mgr` reference describes Claude credential lanes for `project specialist create --tool claude`, it SHALL distinguish the prefixed specialist flag names (`--claude-auth-token`, `--claude-oauth-token`, `--claude-config-dir`) from the unprefixed dedicated credential-management flag names used by `project credentials claude` and `internals native-agent credentials claude` (`--auth-token`, `--oauth-token`, `--config-dir`). It SHALL state that both surfaces accept the same credential semantics but use different flag-name conventions.

#### Scenario: Reader finds current public command groups
- **WHEN** a reader looks up `houmao-mgr`
- **THEN** they find documented public subcommands for `agents`, `internals`, `mailbox`, `project`, `system-skills`, and `admin`
- **AND THEN** they do not find top-level `credentials`, top-level `brains`, or `server` documented as maintained public manager command groups
- **AND THEN** the CLI reference does not present removed or outdated project group names as the supported public project surface

#### Scenario: Reader sees explicit agents scopes
- **WHEN** a reader opens the `houmao-mgr agents` reference
- **THEN** the page presents `agents global`, `agents single`, `agents self`, and `agents external` as the maintained agent scopes
- **AND THEN** it does not present direct root-level `agents launch`, `agents gateway`, `agents mail`, or `agents turn` as maintained public paths

#### Scenario: Reader sees agents scope cardinality rules
- **WHEN** a reader opens the `houmao-mgr agents` reference
- **THEN** the page explains that `agents global` is for zero-or-many local managed-agent operations, `agents single` is for exactly one explicitly selected local managed agent, and `agents self` is for the one local managed agent held by the caller's current tmux session
- **AND THEN** the page explains that `agents external` manages external-agent registry/reference onboarding without local lifecycle authority

#### Scenario: Reader can discover internal brain and credential command families
- **WHEN** a reader looks up `houmao-mgr` command groups in the CLI reference
- **THEN** they find an `internals` section that points to `docs/reference/cli/internals.md`
- **AND THEN** that internals reference documents direct native-agent credentials and brain build commands

#### Scenario: Reader can discover nested managed-agent and project command families
- **WHEN** a reader needs details for `agents global list`, `agents single gateway`, `agents single turn`, `agents single mail`, `agents self join`, `agents self relaunch`, `agents self gateway`, `agents self mail`, `agents self turn`, `agents external register`, `project agents`, `project credentials`, `project`, `project mailbox`, or `admin cleanup`
- **THEN** the CLI reference provides a direct path to formal reference coverage for those nested families
- **AND THEN** the reader does not need to reconstruct those command surfaces only from source code or scattered prose pages

#### Scenario: Reader sees single versus self authority boundary
- **WHEN** a reader looks up selected-agent lifecycle commands such as `stop` or `relaunch`
- **THEN** the CLI reference shows them under `houmao-mgr agents single --agent-id <id> ...` and `houmao-mgr agents single --agent-name <name> ...`
- **AND THEN** it explains that `houmao-mgr agents self relaunch` is current-session active refresh only, not selected-agent stopped/degraded recovery
- **AND THEN** it does not present `houmao-mgr agents self stop` or `houmao-mgr agents self cleanup` as maintained public paths

#### Scenario: Reader can find explicit single and self mail targeting rules
- **WHEN** a reader looks up managed-agent mail commands
- **THEN** the CLI reference documents `resolve-live`, `list`, `read`, `archive`, and the other mailbox follow-up commands in the single and self mail families
- **AND THEN** the reader can see that `agents single mail` uses a group-level explicit selector while `agents self mail` resolves the current managed tmux session
- **AND THEN** the page explains that `resolve-live` returns structured mailbox data rather than mailbox-specific shell export

#### Scenario: Reader can find managed-agent mail result-strength guidance
- **WHEN** a reader looks up managed-agent mail result behavior
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
- **WHEN** a reader looks up managed-agent gateway commands
- **THEN** the CLI reference includes `tui state`, `tui history`, `tui watch`, `tui note-prompt` with option tables
- **AND THEN** the CLI reference includes `mail-notifier status`, `mail-notifier enable`, `mail-notifier disable` with option tables

#### Scenario: Reader sees correct Claude auth flag-name distinction
- **WHEN** a reader looks up Claude credential lanes in the `houmao-mgr` reference
- **THEN** the page shows that `project credentials claude` and `internals native-agent credentials claude` use `--auth-token`, `--oauth-token`, `--config-dir`
- **AND THEN** the page shows that `project specialist create --tool claude` uses `--claude-auth-token`, `--claude-oauth-token`, `--claude-config-dir`
- **AND THEN** the page states that both surfaces accept the same credential semantics

## ADDED Requirements

### Requirement: CLI reference documents agents scoped migration examples
The CLI reference SHALL include migration examples that map removed ambiguous `houmao-mgr agents ...` command paths to the maintained scoped paths.

At minimum, the migration examples SHALL cover:

- `houmao-mgr agents list` to `houmao-mgr agents global list`,
- `houmao-mgr agents stop --agent-id <id>` to `houmao-mgr agents single --agent-id <id> stop`,
- `houmao-mgr agents prompt --agent-name <name>` to `houmao-mgr agents single --agent-name <name> prompt`,
- `houmao-mgr agents join --agent-name <name>` to `houmao-mgr agents self join --agent-name <name>`,
- `houmao-mgr agents external register ...` to `houmao-mgr agents external register ...` as the direct external-reference family,
- implicit current-session `houmao-mgr agents prompt --prompt <text>` to `houmao-mgr agents self prompt --prompt <text>`,
- implicit current-session `houmao-mgr agents interrupt` to `houmao-mgr agents self interrupt`,
- implicit current-session `houmao-mgr agents relaunch` to `houmao-mgr agents self relaunch`,
- implicit current-session `houmao-mgr agents gateway prompt` to `houmao-mgr agents self gateway prompt`,
- explicit one-agent `houmao-mgr agents gateway prompt --agent-id <id>` to `houmao-mgr agents single --agent-id <id> gateway prompt`,
- implicit current-session `houmao-mgr agents mail read --message-ref <ref>` to `houmao-mgr agents self mail read --message-ref <ref>`,
- project-profile launch through `houmao-mgr project [--project-dir <dir>] agents launch --profile <name>`.

#### Scenario: Reader sees migration table for scoped agents commands
- **WHEN** a reader opens the managed-agent CLI reference after the scoped split
- **THEN** the page includes examples mapping old ambiguous command paths to `agents global`, `agents single`, `agents self`, `agents external`, or `project agents`
- **AND THEN** current-session examples use `agents self` rather than `--current-session`
