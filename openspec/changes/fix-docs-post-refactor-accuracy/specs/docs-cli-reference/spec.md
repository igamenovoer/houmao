## MODIFIED Requirements

### Requirement: houmao-passive-server reference documents registry-driven model

The CLI reference SHALL include a page for `houmao-passive-server` documenting its registry-driven discovery model, serve command, and API surface derived from `passive_server/` module docstrings. The page SHALL position passive-server as the clean, CAO-free server path.

The comparison table SHALL list the correct default ports: 9891 for `houmao-passive-server` and 9889 for `houmao-server`.

#### Scenario: Reader understands passive vs active server difference

- **WHEN** a reader compares passive-server and houmao-server pages
- **THEN** they understand that passive-server is stateless/registry-driven with no CAO dependency, while houmao-server is the CAO-compatible path

#### Scenario: Comparison table shows correct default ports

- **WHEN** a reader checks the comparison table in houmao-passive-server.md
- **THEN** the default port for `houmao-passive-server` is listed as 9891
- **AND THEN** the default port for `houmao-server` is listed as 9889

### Requirement: houmao-mgr reference documents all command groups

The CLI reference SHALL include a page for `houmao-mgr` documenting its active command groups (`admin`, `agents`, `brains`, `mailbox`, `project`, and `server`) with subcommand summaries derived from `srv_ctrl/commands/` module docstrings, Click decorators, and live help output.

The CLI reference SHALL make the major nested managed-agent and project command families discoverable either inline or through dedicated linked pages. At minimum, that coverage SHALL include:

- `agents launch`, `join`, `list`, `state`, `prompt`, `stop`, `interrupt`, and `relaunch`,
- `agents turn`,
- `agents gateway` (including `tui` and `mail-notifier` subgroups),
- `agents mail`,
- `agents mailbox`,
- `agents cleanup`,
- `project agents`,
- `project easy`,
- `project mailbox`,
- `admin cleanup`.

When the CLI reference documents `agents mail`, that coverage SHALL include the current subcommands `resolve-live`, `status`, `check`, `send`, `reply`, and `mark-read`, and it SHALL explain:

- the selector rules for explicit targeting versus current-session targeting inside the owning managed tmux session,
- the structured `resolve-live` result contract for current mailbox discovery, including the returned mailbox binding and optional `gateway.base_url`,
- that mailbox-specific shell export is not part of the supported `resolve-live` contract,
- the authority-aware result semantics that distinguish verified execution from non-authoritative TUI submission fallback.

When the CLI reference documents `agents gateway`, that coverage SHALL include the `tui` subgroup (`state`, `history`, `watch`, `note-prompt`) and the `mail-notifier` subgroup (`status`, `enable`, `disable`) with full option tables and descriptions.

The `brains build` options table in the CLI reference SHALL reflect the current live CLI flag names: `--preset`, `--setup`, and `--auth`. The table SHALL NOT list retired flag names `--recipe`, `--config-profile`, or `--cred-profile`.

When the `houmao-mgr` reference describes Claude credential lanes for `project easy specialist create --tool claude`, it SHALL distinguish the prefixed easy-specialist flag names (`--claude-auth-token`, `--claude-oauth-token`, `--claude-config-dir`) from the unprefixed `project agents tools claude auth` flag names (`--auth-token`, `--oauth-token`, `--config-dir`). It SHALL state that both surfaces accept the same credential semantics but use different flag-name conventions.

#### Scenario: Reader finds current agent lifecycle and project command groups
- **WHEN** a reader looks up `houmao-mgr`
- **THEN** they find documented subcommands for `agents`, `brains`, `mailbox`, `project`, `server`, and `admin`
- **AND THEN** the CLI reference does not present removed or outdated project group names such as `agent-tools` as the supported public project surface

#### Scenario: Reader can discover nested managed-agent and project command families
- **WHEN** a reader needs details for `agents gateway`, `agents turn`, `agents mail`, `agents mailbox`, `project agents`, `project easy`, `project mailbox`, or `admin cleanup`
- **THEN** the CLI reference provides a direct path to formal reference coverage for those nested families
- **AND THEN** the reader does not need to reconstruct those command surfaces only from source code or scattered prose pages

#### Scenario: Reader can find `agents mail resolve-live` and targeting rules
- **WHEN** a reader looks up `houmao-mgr agents mail`
- **THEN** the CLI reference documents `resolve-live`, `mark-read`, and the other mailbox follow-up commands in that family
- **AND THEN** the reader can see when omitted selectors resolve the current managed tmux session and when explicit `--agent-id` or `--agent-name` is required
- **AND THEN** the page explains that `resolve-live` returns structured mailbox data rather than mailbox-specific shell export

#### Scenario: Reader can find `agents mail` result-strength guidance
- **WHEN** a reader looks up `houmao-mgr agents mail` result behavior
- **THEN** the CLI reference explains when the command returns verified authoritative results versus non-authoritative submission-only fallback
- **AND THEN** the page points the reader to the supported verification paths for non-authoritative outcomes

#### Scenario: Reader finds brain management commands
- **WHEN** a reader looks up `houmao-mgr brains`
- **THEN** they find documented subcommands for load, list, and build operations

#### Scenario: Reader finds correct brains build flag names
- **WHEN** a reader looks up `houmao-mgr brains build` options in the CLI reference
- **THEN** the options table lists `--preset`, `--setup`, and `--auth`
- **AND THEN** the table does NOT list `--recipe`, `--config-profile`, or `--cred-profile`

#### Scenario: Example commands in paired reference docs use current flag names
- **WHEN** a reader copies a `houmao-mgr brains build` example command from any docs page
- **THEN** the command uses `--setup` and `--auth` instead of `--config-profile` and `--cred-profile`
- **AND THEN** the command does not fail with an unrecognized option error

#### Scenario: Reader finds gateway tui and mail-notifier subgroups documented
- **WHEN** a reader looks up `houmao-mgr agents gateway`
- **THEN** the CLI reference includes `tui state`, `tui history`, `tui watch`, `tui note-prompt` with option tables
- **AND THEN** the CLI reference includes `mail-notifier status`, `mail-notifier enable`, `mail-notifier disable` with option tables

#### Scenario: Reader sees correct Claude auth flag-name distinction
- **WHEN** a reader looks up Claude credential lanes in the `houmao-mgr` reference
- **THEN** the page shows that `project agents tools claude auth` uses `--auth-token`, `--oauth-token`, `--config-dir`
- **AND THEN** the page shows that `project easy specialist create --tool claude` uses `--claude-auth-token`, `--claude-oauth-token`, `--claude-config-dir`
- **AND THEN** the page states that both surfaces accept the same credential semantics

## ADDED Requirements

### Requirement: Easy-specialist launch options table includes mail-account-dir

The `docs/getting-started/easy-specialists.md` options table for `project easy instance launch` SHALL include the `--mail-account-dir` option with its default (None) and its description as an optional private filesystem mailbox directory to symlink into the shared root.

#### Scenario: Reader finds mail-account-dir in the instance launch table

- **WHEN** a reader checks the options table for `project easy instance launch` in `easy-specialists.md`
- **THEN** the table includes a row for `--mail-account-dir` with default `None`
- **AND THEN** the description explains it is an optional private filesystem mailbox directory to symlink into the shared root
