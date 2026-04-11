## MODIFIED Requirements

### Requirement: houmao-mgr reference documents all command groups

The CLI reference SHALL include a page for `houmao-mgr` documenting its active command groups (`admin`, `agents`, `brains`, `credentials`, `internals`, `mailbox`, `project`, and `server`) with subcommand summaries derived from `srv_ctrl/commands/` module docstrings, Click decorators, and live help output.

The CLI reference SHALL make the major nested managed-agent and project command families discoverable either inline or through dedicated linked pages. At minimum, that coverage SHALL include:

- `agents launch`, `join`, `list`, `state`, `prompt`, `stop`, `interrupt`, and `relaunch`,
- `agents turn`,
- `agents gateway` (including `tui` and `mail-notifier` subgroups),
- `agents mail`,
- `agents mailbox`,
- `agents cleanup`,
- `project agents`,
- `project credentials`,
- `project easy`,
- `project mailbox`,
- `admin cleanup`,
- `internals graph` (via a dedicated linked page `docs/reference/cli/internals.md`).

When the CLI reference documents `agents mail`, that coverage SHALL include the current subcommands `resolve-live`, `status`, `check`, `send`, `reply`, and `mark-read`, and it SHALL explain:

- the selector rules for explicit targeting versus current-session targeting inside the owning managed tmux session,
- the structured `resolve-live` result contract for current mailbox discovery, including the returned mailbox binding and optional `gateway.base_url`,
- that mailbox-specific shell export is not part of the supported `resolve-live` contract,
- the authority-aware result semantics that distinguish verified execution from non-authoritative TUI submission fallback.

When the CLI reference documents `agents gateway`, that coverage SHALL include the `tui` subgroup (`state`, `history`, `watch`, `note-prompt`) and the `mail-notifier` subgroup (`status`, `enable`, `disable`) with full option tables and descriptions.

The `brains build` options table in the CLI reference SHALL reflect the current live CLI flag names: `--preset`, `--setup`, and `--auth`. The table SHALL NOT list retired flag names `--recipe`, `--config-profile`, or `--cred-profile`.

When the `houmao-mgr` reference describes Claude credential lanes for `project easy specialist create --tool claude`, it SHALL distinguish the prefixed easy-specialist flag names (`--claude-auth-token`, `--claude-oauth-token`, `--claude-config-dir`) from the unprefixed dedicated credential-management flag names used by `project credentials claude` and `credentials claude --agent-def-dir <path>` (`--auth-token`, `--oauth-token`, `--config-dir`). It SHALL state that both surfaces accept the same credential semantics but use different flag-name conventions.

#### Scenario: Reader finds current agent lifecycle and project command groups

- **WHEN** a reader looks up `houmao-mgr`
- **THEN** they find documented subcommands for `agents`, `brains`, `credentials`, `internals`, `mailbox`, `project`, `server`, and `admin`
- **AND THEN** the CLI reference does not present removed or outdated project group names such as `agent-tools` as the supported public project surface

#### Scenario: Reader can discover nested managed-agent and project command families

- **WHEN** a reader needs details for `agents gateway`, `agents turn`, `agents mail`, `agents mailbox`, `project agents`, `project credentials`, `project easy`, `project mailbox`, or `admin cleanup`
- **THEN** the CLI reference provides a direct path to formal reference coverage for those nested families
- **AND THEN** the reader does not need to reconstruct those command surfaces only from source code or scattered prose pages

#### Scenario: Reader can discover the internals graph command family

- **WHEN** a reader looks up `houmao-mgr` command groups in the CLI reference
- **THEN** they find an `internals` section that points to `docs/reference/cli/internals.md`
- **AND THEN** they do not need to discover the internals group by running `houmao-mgr --help` or reading source code

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
