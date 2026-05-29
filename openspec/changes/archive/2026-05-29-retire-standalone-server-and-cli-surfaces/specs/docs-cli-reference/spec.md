## MODIFIED Requirements

### Requirement: houmao-mgr reference documents all command groups

The CLI reference SHALL include a page for `houmao-mgr` documenting its active command groups (`admin`, `agents`, `brains`, `credentials`, `internals`, `mailbox`, and `project`) with subcommand summaries derived from `srv_ctrl/commands/` module docstrings, Click decorators, and live help output.

The CLI reference SHALL NOT document a top-level `houmao-mgr server` command group as part of the maintained manager surface.

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

When the CLI reference documents `agents mail`, that coverage SHALL include the current subcommands `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`, and it SHALL explain:

- the selector rules for explicit targeting versus current-session targeting inside the owning managed tmux session,
- the structured `resolve-live` result contract for current mailbox discovery, including the returned mailbox binding and optional `gateway.base_url`,
- that mailbox-specific shell export is not part of the supported `resolve-live` contract,
- the authority-aware result semantics that distinguish verified execution from non-authoritative TUI submission fallback.

When the CLI reference documents `agents gateway`, that coverage SHALL include the `tui` subgroup (`state`, `history`, `watch`, `note-prompt`) and the `mail-notifier` subgroup (`status`, `enable`, `disable`) with full option tables and descriptions.

The `brains build` options table in the CLI reference SHALL reflect the current live CLI flag names: `--preset`, `--setup`, and `--auth`. The table SHALL NOT list retired flag names `--recipe`, `--config-profile`, or `--cred-profile`.

When the `houmao-mgr` reference describes Claude credential lanes for `project easy specialist create --tool claude`, it SHALL distinguish the prefixed easy-specialist flag names (`--claude-auth-token`, `--claude-oauth-token`, `--claude-config-dir`) from the unprefixed dedicated credential-management flag names used by `project credentials claude` and `credentials claude --agent-def-dir <path>` (`--auth-token`, `--oauth-token`, `--config-dir`). It SHALL state that both surfaces accept the same credential semantics but use different flag-name conventions.

#### Scenario: Reader finds current agent lifecycle and project command groups
- **WHEN** a reader looks up `houmao-mgr`
- **THEN** they find documented subcommands for `agents`, `brains`, `credentials`, `internals`, `mailbox`, `project`, and `admin`
- **AND THEN** they do not find `server` documented as a maintained top-level manager command group
- **AND THEN** the CLI reference does not present removed or outdated project group names such as `agent-tools` as the supported public project surface

#### Scenario: Reader can discover the internals graph command family
- **WHEN** a reader looks up `houmao-mgr` command groups in the CLI reference
- **THEN** they find an `internals` section that points to `docs/reference/cli/internals.md`
- **AND THEN** they do not need to discover the internals group by running `houmao-mgr --help` or reading source code

#### Scenario: Reader can discover nested managed-agent and project command families
- **WHEN** a reader needs details for `agents gateway`, `agents turn`, `agents mail`, `agents mailbox`, `project agents`, `project credentials`, `project easy`, `project mailbox`, or `admin cleanup`
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
- **THEN** the page shows that `project credentials claude` and `credentials claude --agent-def-dir <path>` use `--auth-token`, `--oauth-token`, `--config-dir`
- **AND THEN** the page shows that `project easy specialist create --tool claude` uses `--claude-auth-token`, `--claude-oauth-token`, `--claude-config-dir`
- **AND THEN** the page states that both surfaces accept the same credential semantics

### Requirement: CLI reference lists only retained server binaries
The CLI reference SHALL present `houmao-passive-server` as the retained server binary.

The CLI reference SHALL NOT list `houmao-server`, `houmao-cli`, or `houmao-cao-server` as active, deprecated-installable, or installable package entrypoints. Historical references MAY mention removed launchers only when explicitly framed as removed history or migration context.

#### Scenario: Reader sees the retained server binary
- **WHEN** a reader scans CLI reference entrypoint tables or server comparison sections
- **THEN** the retained server binary is `houmao-passive-server`
- **AND THEN** `houmao-server`, `houmao-cli`, and `houmao-cao-server` are not presented as commands the current package installs

### Requirement: houmao-passive-server reference documents registry-driven model

The CLI reference SHALL include a page for `houmao-passive-server` documenting its registry-driven discovery model, serve command, and API surface derived from `passive_server/` module docstrings. The page SHALL position passive-server as the maintained server path.

The page SHALL describe passive-server as the active API authority for collecting running Houmao agents and managing them through supported passive-server routes. It SHALL NOT compare passive-server against standalone `houmao-server` as another maintained deployment choice.

The comparison table, if present, SHALL list `houmao-passive-server` default port 9891 and SHALL NOT list a retained default port for standalone `houmao-server`.

#### Scenario: Reader understands passive-server is the maintained server path
- **WHEN** a reader opens the passive-server CLI reference
- **THEN** they understand that passive-server is the maintained registry-driven API server
- **AND THEN** the page does not tell the reader to choose standalone `houmao-server` instead for current workflows

#### Scenario: Comparison table shows passive-server default port only
- **WHEN** a reader checks the comparison table in `houmao-passive-server.md`
- **THEN** the default port for `houmao-passive-server` is listed as 9891
- **AND THEN** standalone `houmao-server` is not presented as a retained server binary with a current default port

### Requirement: CLI reference uses `.houmao` ambient resolution and deprecation-only legacy notes
Repo-owned CLI reference docs that describe agent-definition-directory resolution for active commands, or that mention deprecated or removed compatibility entrypoints, SHALL describe ambient agent-definition resolution as:

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
The CLI reference SHALL keep `houmao-cli`, standalone `houmao-server`, and `houmao-cao-server` only in explicit removed, historical, retirement, or migration context rather than presenting any of those surfaces as active or deprecated-installable operator workflows.

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

#### Scenario: Deprecated and removed entrypoints remain historical while using current precedence
- **WHEN** a reader scans the CLI reference for mentions of `houmao-cli`, `houmao-server`, or `houmao-cao-server`
- **THEN** those names appear only as removed or historical notes when needed
- **AND THEN** none appears as an installable current command
- **AND THEN** any documented ambient agent-definition resolution uses the current `.houmao` precedence contract including the discovery-mode env rather than preserving `.agentsys`

### Requirement: houmao-passive-server reference rewritten with operational depth

The CLI reference page `docs/reference/cli/houmao-passive-server.md` SHALL be rewritten from the current stub to a comprehensive reference covering:

- when to use passive-server as the maintained server API surface,
- the registry-driven discovery and observation model,
- the route families and capabilities available through the passive-server REST API,
- operational guidance for starting, configuring, and using passive-server in distributed agent coordination setups,
- the `serve` command with all current options,
- which `houmao-mgr` commands can target passive-server through supported pair-authority options.

The page SHALL NOT instruct users to choose standalone `houmao-server` as a maintained alternative.

#### Scenario: Reader understands when to use passive-server
- **WHEN** a reader opens the `houmao-passive-server` reference
- **THEN** they find guidance that positions passive-server as the maintained server API surface
- **AND THEN** they are not asked to choose between two maintained Houmao server executables

#### Scenario: passive-server API surface documented
- **WHEN** a reader needs to integrate with the passive-server
- **THEN** the page documents the available REST routes and their response contracts
- **AND THEN** the page notes which `houmao-mgr` commands are compatible with the passive-server

## REMOVED Requirements

### Requirement: houmao-server reference documents serve and query commands

**Reason**: `houmao-server` is no longer a packaged executable or maintained standalone operator surface.

**Migration**: Remove `docs/reference/cli/houmao-server.md` from active CLI reference navigation. Move any still-useful conceptual material to passive-server docs or internal developer notes without documenting `houmao-server` as an executable.
