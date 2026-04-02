# docs-cli-reference Specification

## Purpose
Define the documentation requirements for Houmao CLI reference content.
## Requirements
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

### Requirement: houmao-server reference documents serve and query commands

The CLI reference SHALL include a page for `houmao-server` documenting its commands (`serve`, `health`, `current-instance`, `register-launch`, `sessions`, and `terminals`) derived from `server/commands/` module docstrings and live help output.

The `serve` reference SHALL describe the implemented startup behavior and the current flag surface, including compatibility readiness and warmup flags when those flags are present in the live CLI.

#### Scenario: Reader understands server startup

- **WHEN** a reader looks up `houmao-server serve`
- **THEN** they find the current startup behavior plus the live configuration options for startup-child behavior, compatibility readiness timeouts or poll intervals, warmup timing, runtime root, API base URL, and supported TUI process overrides

#### Scenario: Reader finds query commands

- **WHEN** a reader looks up `houmao-server` query commands
- **THEN** they find documented coverage for `health`, `current-instance`, `register-launch`, `sessions`, and `terminals`
- **AND THEN** the page reflects the current command tree rather than a partial or stale subset

### Requirement: houmao-passive-server reference documents registry-driven model

The CLI reference SHALL include a page for `houmao-passive-server` documenting its registry-driven discovery model, serve command, and API surface derived from `passive_server/` module docstrings. The page SHALL position passive-server as the clean, CAO-free server path.

#### Scenario: Reader understands passive vs active server difference

- **WHEN** a reader compares passive-server and houmao-server pages
- **THEN** they understand that passive-server is stateless/registry-driven with no CAO dependency, while houmao-server is the CAO-compatible path

### Requirement: Deprecated entrypoints noted briefly

The CLI reference SHALL note that `houmao-cli` and `houmao-cao-server` are deprecated compatibility entrypoints. This SHALL be a brief note (1–2 sentences), not a full page.

#### Scenario: Deprecated CLIs not prominently featured

- **WHEN** a reader scans the CLI reference section
- **THEN** `houmao-cli` and `houmao-cao-server` appear only as deprecation notes, not as primary documentation

### Requirement: CLI reference uses `.houmao` ambient resolution and deprecation-only legacy notes
Repo-owned CLI reference docs that describe agent-definition-directory resolution for active commands, or that mention deprecated compatibility entrypoints, SHALL describe ambient agent-definition resolution as:

1. explicit CLI `--agent-def-dir`,
2. `HOUMAO_AGENT_DEF_DIR`,
3. the overlay directory selected by `HOUMAO_PROJECT_OVERLAY_DIR`,
4. ambient project-overlay discovery controlled by `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`,
5. default fallback `<cwd>/.houmao/agents`.

When the CLI reference describes `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`, it SHALL state that:

- `ancestor` is the default mode,
- `ancestor` resolves the nearest ancestor `.houmao/houmao-config.toml`,
- `cwd_only` restricts ambient lookup to `<cwd>/.houmao/houmao-config.toml`,
- the mode affects ambient discovery only and does not override `HOUMAO_PROJECT_OVERLAY_DIR`.

The CLI reference SHALL describe `HOUMAO_PROJECT_OVERLAY_DIR` as an absolute-path env override that selects the overlay directory directly for CI and controlled automation.
When the CLI reference explains the discovered project path, it SHALL describe `houmao-config.toml` as the discovery anchor at the selected overlay root and `agents/` as the compatibility projection used by file-tree consumers beneath that overlay root.
It SHALL NOT present `<cwd>/.agentsys/agents` as a supported default or fallback path.
The CLI reference SHALL keep `houmao-cli` and `houmao-cao-server` in explicit deprecation-only posture rather than re-elevating them to primary operator workflows.

#### Scenario: Reader sees the project-overlay env contract in the CLI precedence documentation
- **WHEN** a reader checks the CLI reference for agent-definition-directory resolution
- **THEN** the page describes `HOUMAO_PROJECT_OVERLAY_DIR` as the explicit overlay-root selector
- **AND THEN** the page describes `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` as the ambient discovery-mode selector used only when no explicit overlay root is set
- **AND THEN** the page explains the `ancestor` and `cwd_only` modes

#### Scenario: Reader sees `.houmao` ambient fallback in the CLI reference
- **WHEN** a reader checks the CLI reference for agent-definition-directory resolution
- **THEN** the page describes the `.houmao`-based precedence contract
- **AND THEN** it explains that cwd-only mode still falls back to `<cwd>/.houmao/agents`
- **AND THEN** it does not present `<cwd>/.agentsys/agents` as a supported fallback

#### Scenario: Deprecated entrypoints remain deprecation-only while using current precedence
- **WHEN** a reader scans the CLI reference for mentions of `houmao-cli` or `houmao-cao-server`
- **THEN** those mentions remain brief legacy and deprecation notes
- **AND THEN** any documented ambient agent-definition resolution uses the current `.houmao` precedence contract including the discovery-mode env rather than preserving `.agentsys`

### Requirement: CLI reference stubs completed for all agents subcommand pages

The CLI reference SHALL complete all truncated stub pages for `houmao-mgr agents` subcommand families. Specifically:

- `docs/reference/cli/agents-gateway.md` SHALL document all subcommands including the `tui` subgroup (`state`, `history`, `watch`, `note-prompt`) and the `mail-notifier` subgroup (`status`, `enable`, `disable`) with full option tables.
- `docs/reference/cli/agents-mail.md` SHALL document all subcommands (`resolve-live`, `status`, `check`, `send`, `reply`, `mark-read`) with full option tables and usage notes.
- `docs/reference/cli/agents-mailbox.md` SHALL document all subcommands (`register`, `unregister`, `status`) with full option tables.
- `docs/reference/cli/agents-turn.md` SHALL document all subcommands (`submit`, `status`, `events`, `stdout`, `stderr`) with full option tables.

Each completed page SHALL follow the style of `docs/reference/cli/admin-cleanup.md`: hand-written prose with option tables, brief usage context, and example commands where helpful.

#### Scenario: agents-gateway page covers tui and mail-notifier subgroups

- **WHEN** a reader opens `docs/reference/cli/agents-gateway.md`
- **THEN** they find complete documentation for `attach`, `detach`, `status`, `prompt`, `interrupt`, `send-keys`
- **AND THEN** they find complete documentation for `tui state`, `tui history`, `tui watch`, `tui note-prompt`
- **AND THEN** they find complete documentation for `mail-notifier status`, `mail-notifier enable`, `mail-notifier disable`

#### Scenario: agents-mail page covers all commands with targeting rules

- **WHEN** a reader opens `docs/reference/cli/agents-mail.md`
- **THEN** they find complete documentation for all 6 subcommands with option tables
- **AND THEN** the page is not truncated mid-content

#### Scenario: agents-turn page covers stdout and stderr commands

- **WHEN** a reader opens `docs/reference/cli/agents-turn.md`
- **THEN** they find complete documentation for `submit`, `status`, `events`, `stdout`, and `stderr` with option tables
- **AND THEN** the page is not truncated mid-content

### Requirement: houmao-passive-server reference rewritten with operational depth

The CLI reference page `docs/reference/cli/houmao-passive-server.md` SHALL be rewritten from the current 30-line stub to a comprehensive reference covering:

- When to use passive-server vs houmao-server: a comparison table showing that passive-server is stateless/registry-driven with no child process supervision, while houmao-server provides full session management.
- API contract: the routes and capabilities available through the passive-server REST API.
- Operational guidance: how to start, configure, and use the passive-server in a distributed agent coordination setup.
- The `serve` command with all current options.

#### Scenario: Reader understands when to use passive-server

- **WHEN** a reader opens the houmao-passive-server reference
- **THEN** they find a comparison table or section explaining passive-server vs houmao-server trade-offs
- **AND THEN** they can make an informed decision about which server to deploy

#### Scenario: passive-server API surface documented

- **WHEN** a reader needs to integrate with the passive-server
- **THEN** the page documents the available REST routes and their response contracts
- **AND THEN** the page notes which `houmao-mgr` commands are compatible with the passive-server
