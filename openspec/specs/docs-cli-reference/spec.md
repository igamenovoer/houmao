# docs-cli-reference Specification

## Purpose
Define the documentation requirements for Houmao CLI reference content.
## Requirements
### Requirement: CLI reference documents consolidated project targeting
The CLI reference SHALL document `houmao-mgr project --project-dir <dir> ...` as the maintained explicit project selection surface.

The reference SHALL explain that `--project-dir` selects the human-facing project directory and resolves the overlay at `<dir>/.houmao`.

The reference SHALL update examples for project credentials, specialists, profiles, managed-agent launch, skills, mailbox, and status so they use either omitted auto-discovery or the group-level `--project-dir` option.

#### Scenario: Reader finds explicit project selection
- **WHEN** a reader opens the `houmao-mgr project` CLI reference
- **THEN** the page documents `--project-dir <dir>` as a group-level option
- **AND THEN** the examples show `houmao-mgr project --project-dir /repo credentials codex list`

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
2. `HOUMAO_NATIVE_AGENT_ROOT`,
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

### Requirement: CLI reference stubs completed for all agents subcommand pages

The CLI reference SHALL complete all truncated stub pages for `houmao-mgr agents` subcommand families. Specifically:

- `docs/reference/cli/agents-gateway.md` SHALL document all subcommands including the `tui` subgroup (`state`, `history`, `watch`, `note-prompt`) and the `mail-notifier` subgroup (`status`, `enable`, `disable`) with full option tables.
- `docs/reference/cli/agents-mail.md` SHALL document all subcommands (`resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, `archive`) with full option tables and usage notes.
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

### Requirement: CLI reference documents the scoped `agents ... gateway reminders` subgroup
The CLI reference SHALL document `houmao-mgr agents single ... gateway reminders` and `houmao-mgr agents self gateway reminders` as first-class subgroups of the scoped gateway command family.

At minimum, that coverage SHALL include:

- `list`
- `get`
- `create`
- `set`
- `remove`

The `agents-gateway` reference page SHALL provide full option tables and brief usage guidance for those reminder commands.

That reminder coverage SHALL explain:

- the same scoped selected-agent or current-session targeting rules used by the rest of the gateway family,
- that reminder commands work through pair-managed authority when `--pair-port` is used,
- that ranking remains numeric,
- that `--before-all` places a reminder ahead of the current minimum ranking,
- that `--after-all` places a reminder after the current maximum ranking,
- that direct `/v1/reminders` remains the lower-level gateway contract underneath the CLI.

#### Scenario: Reader finds all reminder subcommands from the scoped gateway CLI reference
- **WHEN** a reader opens `docs/reference/cli/agents-gateway.md`
- **THEN** the page documents `reminders list`, `reminders get`, `reminders create`, `reminders set`, and `reminders remove`
- **AND THEN** the reminder subgroup appears alongside the other current scoped gateway operator surfaces rather than as an undocumented exception

#### Scenario: Reader can understand ranking placement flags from the CLI reference
- **WHEN** a reader looks up scoped `houmao-mgr agents single ... gateway reminders create|set` or `houmao-mgr agents self gateway reminders create|set`
- **THEN** the option tables and prose explain `--ranking`, `--before-all`, and `--after-all`
- **AND THEN** the page makes clear that ranking is numeric and that the convenience flags resolve to concrete numeric positions relative to the live reminder set

### Requirement: houmao-passive-server reference rewritten with operational depth

The CLI reference page `docs/reference/cli/houmao-passive-server.md` SHALL be rewritten from the current stub to a comprehensive reference covering:

- when to use passive-server as the maintained server API surface,
- the registry-driven discovery and observation model,
- passive-server as a global service over the shared registry rather than a Houmao project-bound command,
- the route families and capabilities available through the passive-server REST API,
- operational guidance for starting, configuring, and using passive-server in distributed agent coordination setups,
- the `serve` command with all current options,
- runtime-root and registry-root resolution, including `--runtime-root`, `--registry-root`, `HOUMAO_GLOBAL_RUNTIME_DIR`, `HOUMAO_GLOBAL_REGISTRY_DIR`, and global defaults,
- which `houmao-mgr` commands can target passive-server through supported pair-authority options.

The page SHALL NOT instruct users to choose standalone `houmao-server` as a maintained alternative.

The page SHALL NOT state that a Houmao project overlay is required to start `houmao-passive-server serve`.

#### Scenario: Reader understands when to use passive-server
- **WHEN** a reader opens the `houmao-passive-server` reference
- **THEN** they find guidance that positions passive-server as the maintained server API surface
- **AND THEN** they are not asked to choose between two maintained Houmao server executables

#### Scenario: passive-server API surface documented
- **WHEN** a reader needs to integrate with the passive-server
- **THEN** the page documents the available REST routes and their response contracts
- **AND THEN** the page notes which `houmao-mgr` commands are compatible with the passive-server

#### Scenario: Reader understands global-service root configuration
- **WHEN** a reader opens the `houmao-passive-server` reference
- **THEN** the page explains that `houmao-passive-server serve` can start without a Houmao project overlay
- **AND THEN** the page explains how to use `--registry-root` or `HOUMAO_GLOBAL_REGISTRY_DIR` when CI or tests need an isolated shared registry

### Requirement: CLI reference distinguishes Claude credential inputs from the optional state template
The `houmao-mgr` CLI reference SHALL describe Claude credential-providing inputs separately from the optional Claude state-template input on both maintained credential-management surfaces and the easy-specialist surface:

- `project credentials claude ...` or `internals native-agent credentials claude ... --native-agent-root <path>`
- `project specialist create --tool claude`

When the reference documents Claude-specific flags, it SHALL make clear that `claude_state.template.json` or `--claude-state-template-file` is optional runtime bootstrap state and not itself a credential-providing method.

#### Scenario: Reader sees the Claude state template documented separately in the CLI reference
- **WHEN** a reader looks up the Claude credential-management or easy-specialist options in `docs/reference/cli/houmao-mgr.md`
- **THEN** the page distinguishes credential-providing Claude inputs from the optional state-template input
- **AND THEN** it does not present the state-template input as one of the ways to authenticate Claude

### Requirement: CLI reference documents specialist editing controls
The `houmao-mgr` CLI reference SHALL document patch and replacement controls for reusable specialists.

For `project specialist`, the reference SHALL list `create`, `list`, `get`, `set`, and `remove`, and SHALL document `set` as the patch command that preserves unspecified stored specialist fields.

For `project specialist create`, the reference SHALL document `--yes` as the non-interactive confirmation for replacing an existing same-name specialist, and SHALL state that replacement uses create semantics where omitted optional fields may be cleared.

The reference SHALL state that `specialist set` updates the reusable specialist source for future launches and does not mutate running managed agents in place.

#### Scenario: Reader finds specialist set in CLI reference
- **WHEN** a reader looks up `houmao-mgr project specialist`
- **THEN** the CLI reference lists `set` alongside `create`, `list`, `get`, and `remove`
- **AND THEN** the reference explains that `set` mutates stored future source defaults rather than one running instance

#### Scenario: Reader finds specialist replacement guidance
- **WHEN** a reader looks up same-name specialist creation
- **THEN** the CLI reference explains when to use `--yes` for replacement
- **AND THEN** it distinguishes replacement from patching through `set`

### Requirement: CLI reference documents the root `houmao-mgr --version` option
The CLI reference page `docs/reference/cli/houmao-mgr.md` SHALL document `--version` as a root option on `houmao-mgr`.

That page SHALL include `--version` in the root synopsis or root option coverage alongside the existing root options.

That page SHALL explain that `houmao-mgr --version` prints the packaged Houmao version and exits successfully without requiring a subcommand.

#### Scenario: Reader sees `--version` in the houmao-mgr root option coverage
- **WHEN** a reader opens `docs/reference/cli/houmao-mgr.md`
- **THEN** the page documents `--version` as a root `houmao-mgr` option
- **AND THEN** the page does not imply that version reporting requires a subcommand

#### Scenario: Reader understands what the version option returns
- **WHEN** a reader looks up `houmao-mgr --version` in `docs/reference/cli/houmao-mgr.md`
- **THEN** the page explains that the command prints the packaged Houmao version
- **AND THEN** it explains that the command exits successfully after reporting that version

### Requirement: Managed-launch CLI reference documents `--workdir` and source-project pinning
The CLI reference pages that document `houmao-mgr agents self join` and `houmao-mgr project agents launch` SHALL describe `--workdir` as the current public runtime-cwd flag when that surface accepts it.

That coverage SHALL describe the default behavior as using the invocation cwd for launch-time runtime workdir and tmux-pane current path for join-time adopted workdir when `--workdir` is omitted.

That coverage SHALL explain that `--workdir` sets the launched or adopted agent cwd and does not retarget launch source project resolution.

For `project agents launch`, that coverage SHALL explain that the selected easy-project overlay and specialist source remain authoritative even when `--workdir` points somewhere else.

That coverage SHALL NOT present `--working-directory` as part of the current public CLI for `agents self join`.

#### Scenario: Reader sees `--workdir` on the managed launch surfaces
- **WHEN** a reader opens the CLI reference for `houmao-mgr agents self join` or `houmao-mgr project agents launch`
- **THEN** the documented runtime-cwd flag is `--workdir`
- **AND THEN** the reference does not describe `--working-directory` as the current join flag

#### Scenario: Reader understands source-project pinning for managed launch
- **WHEN** a reader looks up `houmao-mgr project agents launch --workdir`
- **THEN** the reference explains that `--workdir` changes the launched agent cwd
- **AND THEN** it explains that source overlay/runtime/jobs resolution remains pinned to the launch source project when one exists

#### Scenario: Reader understands easy launch keeps the selected overlay even with external workdir
- **WHEN** a reader looks up `houmao-mgr project agents launch --workdir`
- **THEN** the reference explains that the selected project overlay and specialist source remain authoritative
- **AND THEN** it explains that `--workdir` only changes the launched agent cwd

### Requirement: CLI reference documents scoped gateway targeting
The CLI reference pages `docs/reference/cli/agents-gateway.md` and `docs/reference/cli.md` SHALL document explicit selected-agent gateway commands as `houmao-mgr agents single --agent-id <id> gateway ...` or `houmao-mgr agents single --agent-name <name> gateway ...`.

That documentation SHALL describe `--pair-port` as the pair-authority override for the `agents single` gateway surface. It SHALL also explain that `--pair-port` is not the same thing as a gateway listener port override such as lower-level `--gateway-port`.

The `agents-gateway` reference SHALL distinguish outside-tmux selected-agent targeting through `agents single` from inside-tmux current-session targeting through `agents self`.

#### Scenario: CLI reference page lists the tmux-session selector and targeting boundary
- **WHEN** a reader opens `docs/reference/cli/agents-gateway.md`
- **THEN** the option tables and synopsis show `agents single --agent-id <id> gateway ...`, `agents single --agent-name <name> gateway ...`, and `agents self gateway ...`
- **AND THEN** the page explains that `agents single` is for explicit outside-tmux targeting while `agents self` is for the owning tmux session

#### Scenario: Top-level CLI guidance explains the port rule for tmux-session targeting
- **WHEN** a reader checks `docs/reference/cli.md` for gateway targeting rules
- **THEN** the page explains that `--pair-port` remains supported with `--agent-id` or `--agent-name`
- **AND THEN** the page explains that `--pair-port` belongs to `agents single` and is not exposed by `agents self`

#### Scenario: Gateway CLI reference distinguishes pair-authority port from gateway listener port
- **WHEN** a reader opens `docs/reference/cli/agents-gateway.md`
- **THEN** the page explains that `--pair-port` selects the Houmao pair authority
- **AND THEN** the page does not imply that `--pair-port` controls the live gateway listener port

### Requirement: CLI reference documents the top-level project agents presets surface

The `houmao-mgr` CLI reference SHALL document the canonical low-level recipe surface and the compatibility preset alias as one resource family.

At minimum, that coverage SHALL:

- list `internals native-agent recipes list|get|add|set|remove` as the canonical low-level source-recipe administration surface,
- list `project agents presets list|get|add|set|remove` as the compatibility alias for the same named recipe resources,
- describe recipe files as living under `agents/presets/<name>.yaml`,
- list `internals native-agent launch-dossiers list|get|add|set|remove` as the canonical low-level explicit-launch-profile administration surface,
- describe explicit launch-profile files as living under `agents/launch-profiles/<name>.yaml`,
- explain that `internals native-agent roles` is prompt-only role management,
- state that `internals native-agent roles scaffold` is not part of the supported low-level CLI.

The CLI reference SHALL extend the `houmao-mgr project` command-shape tree so that `project agents` lists `roles`, `recipes`, `presets`, `launch-profiles`, and `tools <tool>`, and so that `project` lists `specialist`, `profile`, and `instance`.

The CLI reference SHALL document `houmao-mgr project profile create|list|get|remove` as the easy-lane reusable specialist-backed birth-time launch-profile administration surface, and SHALL document `houmao-mgr project agents launch --profile <name>` as the project-profile-backed instance launch path with the `--profile`/`--specialist` mutual exclusion rule.

The CLI reference SHALL document `houmao-mgr project agents launch --profile <name>` as the project-profile-backed managed launch path, and SHALL document the `--profile`/`--specialist` mutual exclusion rule.

The CLI reference SHALL describe the launch-time effective-input precedence as: source recipe defaults → launch-profile defaults → direct CLI overrides, and SHALL state that direct CLI overrides such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir` do not rewrite the stored launch profile.

The CLI reference SHALL state that launch-profile-backed birth is project-scoped through `project agents launch --profile`, while low-level explicit launch-dossier authoring remains under `internals native-agent launch-dossiers`.

The CLI reference SHALL link to `docs/getting-started/launch-profiles.md` for the shared conceptual model rather than restating that model on the CLI reference page itself.

#### Scenario: Reader sees canonical recipes and the compatibility preset alias in the project agents reference

- **WHEN** a reader looks up `houmao-mgr project agents` in the CLI reference
- **THEN** the page documents `internals native-agent recipes list|get|add|set|remove`
- **AND THEN** the page documents `project agents presets list|get|add|set|remove` as the compatibility alias for the same files under `agents/presets/<name>.yaml`
- **AND THEN** it does not present `roles presets ...` or `roles scaffold` as the supported surface

#### Scenario: Reader sees the explicit launch-profile surface in the project agents reference

- **WHEN** a reader looks up `houmao-mgr project agents` in the CLI reference
- **THEN** the page documents `internals native-agent launch-dossiers list|get|add|set|remove` as the canonical low-level explicit-launch-profile surface
- **AND THEN** the page describes those files as living under `agents/launch-profiles/<name>.yaml`

#### Scenario: Reader sees the project profile surface in the project reference

- **WHEN** a reader looks up `houmao-mgr project` in the CLI reference
- **THEN** the page documents `project profile create|list|get|remove`
- **AND THEN** the page documents `project agents launch --profile <name>`
- **AND THEN** the page documents the `--profile`/`--specialist` mutual exclusion rule on `instance launch`

#### Scenario: Reader sees project profile launch documented with its precedence rules

- **WHEN** a reader looks up `houmao-mgr project agents launch` in the CLI reference
- **THEN** the page documents `--profile <name>` as the project-profile-backed launch input
- **AND THEN** the page documents the `--profile`/`--specialist` mutual exclusion rule
- **AND THEN** the page documents the precedence order as recipe defaults, then launch-profile defaults, then direct CLI overrides
- **AND THEN** the page states that direct CLI overrides such as `--agent-name`, `--auth`, and `--workdir` do not rewrite the stored launch profile

#### Scenario: Reader sees the project command-shape tree extended for the new subtrees

- **WHEN** a reader checks the `Command shape` overview in the CLI reference
- **THEN** `project agents` lists `roles`, `recipes`, `presets`, `launch-profiles`, and `tools <tool>`
- **AND THEN** `project` lists `specialist`, `profile`, and `instance`

### Requirement: Easy-specialist launch options table includes mail-account-dir

The `docs/getting-started/easy-specialists.md` options table for `project agents launch` SHALL include the `--mail-account-dir` option with its default (None) and its description as an optional private filesystem mailbox directory to symlink into the shared root.

#### Scenario: Reader finds mail-account-dir in the instance launch table

- **WHEN** a reader checks the options table for `project agents launch` in `easy-specialists.md`
- **THEN** the table includes a row for `--mail-account-dir` with default `None`
- **AND THEN** the description explains it is an optional private filesystem mailbox directory to symlink into the shared root

### Requirement: CLI reference documents managed-header controls on launch and launch-profile surfaces
The `houmao-mgr` CLI reference SHALL document the managed-header flags on the relevant launch and launch-profile commands.

At minimum, that coverage SHALL include:
- `houmao-mgr project agents launch --managed-header|--no-managed-header`
- `houmao-mgr internals native-agent launch-dossiers add --managed-header|--no-managed-header`
- `houmao-mgr internals native-agent launch-dossiers set --managed-header|--no-managed-header|--clear-managed-header`
- `houmao-mgr project profile create --managed-header|--no-managed-header`
- `houmao-mgr project agents launch --managed-header|--no-managed-header`

The CLI reference SHALL explain that:
- launch-time managed-header flags are mutually exclusive,
- direct launch override wins over stored launch-profile policy,
- clearing stored launch-profile policy returns that field to inherit behavior,
- omitted launch-time and launch-profile policy falls back to the default enabled managed-header behavior.

#### Scenario: Reader can find the managed-header flags in the CLI reference
- **WHEN** a reader looks up `houmao-mgr project agents launch`, `internals native-agent launch-dossiers`, or the relevant `project` commands
- **THEN** the CLI reference documents the managed-header flags and their meaning
- **AND THEN** the page does not require the reader to infer the new behavior from source code or changelog text

#### Scenario: Reader understands precedence and clear semantics from the CLI reference
- **WHEN** a reader checks the option notes for managed-header controls
- **THEN** the CLI reference explains direct-override precedence over stored profile policy
- **AND THEN** it explains that `--clear-managed-header` returns the stored profile field to inherit behavior

### Requirement: CLI reference removes retired `--yolo` launch option from all pages

The CLI reference SHALL NOT present `--yolo` as a supported option on `houmao-mgr project agents launch` or any other live launch surface. Any remaining `--yolo` references in `docs/reference/cli/houmao-mgr.md`, `docs/reference/cli/agents-gateway.md`, `docs/reference/cli/system-skills.md`, or other CLI reference pages SHALL be removed during this resync pass.

The CLI reference SHALL state that prompt-mode posture is now controlled exclusively through `launch.prompt_mode` in stored profiles (`unattended` or `as_is`) and the corresponding launch-profile flags, not through a separate `--yolo` toggle.

#### Scenario: Reader does not see `--yolo` as a current option in CLI reference

- **WHEN** a reader greps the CLI reference pages for `--yolo`
- **THEN** zero matches appear as supported options on live launch commands
- **AND THEN** any remaining mention is in an explicit "removed in 0.3.x" or migration-note context

#### Scenario: Reader learns the current way to control prompt-mode posture

- **WHEN** a reader looks up how to launch an agent without provider startup prompts
- **THEN** the CLI reference points the reader at `launch.prompt_mode: unattended` in stored profiles or the equivalent launch-profile flags
- **AND THEN** the reference does not present `--yolo` as the way to achieve that posture

### Requirement: CLI reference documents the unified `--model` selection on launch surfaces

The `houmao-mgr` CLI reference SHALL document `--model` as a unified model-selection flag on the relevant managed launch and launch-profile commands.

At minimum, that coverage SHALL include the launch surfaces that accept model selection directly (`houmao-mgr project specialist create`, `houmao-mgr project agents launch`, and the corresponding `internals native-agent launch-dossiers` administration commands when those commands accept stored model defaults).

That coverage SHALL describe `--model` as a tool-agnostic selector that resolves to the appropriate per-tool model identifier through the supported provider mapping, and SHALL state that `--model` does not bypass tool authentication or provider configuration.

That coverage SHALL link to the underlying tool-specific model identifiers documented in the relevant tool reference rather than restating every supported model name on the CLI reference page.

#### Scenario: Reader finds the unified `--model` flag on the launch surfaces

- **WHEN** a reader looks up `project agents launch`
- **THEN** the CLI reference documents `--model` as a current option
- **AND THEN** the page explains that `--model` is a tool-agnostic selector resolved through the provider mapping

#### Scenario: Reader understands that `--model` is not an auth or provider override

- **WHEN** a reader looks up the `--model` flag
- **THEN** the CLI reference states that `--model` does not bypass tool authentication or provider configuration

### Requirement: CLI reference resync against current Click decorators for stale `agents` and `admin` pages

The CLI reference pages `docs/reference/cli/agents-mailbox.md`, `docs/reference/cli/agents-turn.md`, `docs/reference/cli/admin-cleanup.md`, and `docs/reference/cli/houmao-server.md` SHALL be reverified against the current Click decorators in `src/houmao/srv_ctrl/commands/` (and `src/houmao/server/commands/` for the server page) and updated to match the live CLI shape as of this change.

For each of those pages:

- the documented subcommands SHALL match the live Click groups,
- the option tables SHALL list every flag exposed by the current decorators with the current default values,
- removed or renamed flags from the post-`2026-04-04` feature commits SHALL be removed or renamed in the docs accordingly,
- existing prose that remains accurate SHALL be preserved.

#### Scenario: agents-mailbox option tables match current Click decorators

- **WHEN** a reader opens `docs/reference/cli/agents-mailbox.md`
- **THEN** every option in the option tables corresponds to a current Click decorator in `srv_ctrl/commands/agents/mailbox.py`
- **AND THEN** no removed or renamed option remains in the page

#### Scenario: agents-turn page reflects current submit/inspect commands

- **WHEN** a reader opens `docs/reference/cli/agents-turn.md`
- **THEN** the documented subcommands match the live Click groups in `srv_ctrl/commands/agents/turn.py`
- **AND THEN** the option tables match current decorators

#### Scenario: admin-cleanup page reflects current registry and runtime commands

- **WHEN** a reader opens `docs/reference/cli/admin-cleanup.md`
- **THEN** the documented subcommands match the live Click groups in `srv_ctrl/commands/admin.py`
- **AND THEN** the option tables match current decorators

#### Scenario: houmao-server page reflects current server commands

- **WHEN** a reader opens `docs/reference/cli/houmao-server.md`
- **THEN** the documented subcommands match the live Click groups in `src/houmao/server/commands/`
- **AND THEN** the option tables match current decorators

### Requirement: CLI reference cross-links the managed prompt header reference page

The `houmao-mgr` CLI reference and the relevant launch-surface coverage in `docs/reference/cli/houmao-mgr.md` SHALL link to the managed prompt header reference page (`docs/reference/run-phase/managed-prompt-header.md`) wherever they document `--managed-header`, `--no-managed-header`, or related stored launch-profile policy flags.

The link SHALL be a direct cross-reference, not a tooltip or footnote, so a reader looking up the flag from the CLI reference can navigate in one click to the conceptual page that explains what the header contains.

#### Scenario: Reader can navigate from `--managed-header` flag coverage to the conceptual page

- **WHEN** a reader looks up `--managed-header` or `--no-managed-header` on `project agents launch` in the CLI reference
- **THEN** the page contains a direct link to `docs/reference/run-phase/managed-prompt-header.md`
- **AND THEN** the link is presented inline with the flag coverage rather than only at the bottom of the page

### Requirement: CLI reference cross-links the system-skills overview guide

The CLI reference page `docs/reference/cli/system-skills.md` SHALL link to the new getting-started guide `docs/getting-started/system-skills-overview.md` from its introduction so that readers reaching the reference page have a single click into the narrative tour.

#### Scenario: Reader can navigate from system-skills CLI reference to the narrative overview

- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the introduction or top section of the page contains a link to `docs/getting-started/system-skills-overview.md`
- **AND THEN** the link is presented as a "see also" or "narrative overview" pointer rather than buried in the bottom of the page

### Requirement: CLI reference documents headless execution overrides on all supported prompt surfaces

`docs/reference/cli/houmao-mgr.md` (and its child reference pages for scoped `agents single/self turn` and `agents single/self gateway`) SHALL document the request-scoped headless execution overrides on every supported prompt submission CLI surface.

At minimum the coverage SHALL include:

- `houmao-mgr agents single ... prompt` and `houmao-mgr agents self prompt`
- `houmao-mgr agents single ... turn submit` and `houmao-mgr agents self turn submit`
- `houmao-mgr agents single ... gateway prompt` and `houmao-mgr agents self gateway prompt`

For each of those three surfaces the reference SHALL document:

- `--model TEXT` as a request-scoped headless execution model override,
- `--reasoning-level INTEGER` as a tool/model-specific reasoning preset index rather than as a normalized portable `1..10` knob,
- that the interpretation of `--reasoning-level` depends on the resolved tool/model ladder and that positive overflow saturates to the highest maintained Houmao preset for that ladder,
- that the overrides apply to exactly the submitted prompt, turn, or gateway request and do not mutate launch profiles, recipes, specialists, manifests, stored project profiles, or any other live session defaults,
- that the overrides are rejected clearly when the resolved target is a TUI-backed prompt route rather than silently dropped,
- that partial overrides (for example supplying `--reasoning-level` without `--model`) merge with launch-resolved model defaults through the shared headless resolution helper rather than resetting fields that were not explicitly overridden,
- that Gemini reasoning levels are Houmao-documented presets which may map to multiple native Gemini settings together,
- that operators who need finer native control should omit Houmao `--reasoning-level` and manage native tool config or env directly.

#### Scenario: Reader finds headless overrides on scoped agents prompt
- **WHEN** a reader opens the scoped `agents single ... prompt` or `agents self prompt` coverage inside `docs/reference/cli/houmao-mgr.md`
- **THEN** the page documents `--model` and `--reasoning-level` as supported options
- **AND THEN** the page states that those overrides apply to exactly the submitted prompt and never rewrite persistent launch-resolved state

#### Scenario: Reader finds headless overrides on scoped agents turn submit
- **WHEN** a reader opens the scoped `agents single ... turn submit` or `agents self turn submit` coverage
- **THEN** the page documents `--model` and `--reasoning-level` as request-scoped overrides
- **AND THEN** the page explains that those overrides apply only to the submitted turn

#### Scenario: Reader finds headless overrides on scoped agents gateway prompt
- **WHEN** a reader opens the scoped `agents single ... gateway prompt` or `agents self gateway prompt` coverage
- **THEN** the page documents `--model` and `--reasoning-level` as request-scoped overrides
- **AND THEN** the page explains that the overrides apply to exactly the addressed gateway prompt submission, including when that submission is queued through `submit_prompt`

#### Scenario: Reader understands TUI-target rejection
- **WHEN** a reader looks up any of the three supported prompt surfaces
- **THEN** the reference states that supplying `--model` or `--reasoning-level` for a TUI-backed target results in a clear failure rather than a silent drop
- **AND THEN** the reference does not suggest that TUI-backed sessions can be retargeted to a different model through these flags

#### Scenario: Reader finds Gemini preset guidance and native-control escape hatch
- **WHEN** a reader looks up reasoning-level documentation for Gemini-backed launch or prompt submission
- **THEN** the reference explains that Gemini reasoning levels are Houmao-maintained presets that may map to multiple native Gemini settings together
- **AND THEN** the reference explains that operators needing finer Gemini-native control should omit Houmao reasoning-level and manage native config or env directly

### Requirement: CLI reference documents launch-profile editing controls
The `houmao-mgr` CLI reference SHALL document patch and replacement controls for reusable launch profiles.

For `project profile`, the reference SHALL list `create`, `list`, `get`, `set`, and `remove`, and SHALL document `set` as the patch command that preserves unspecified stored fields.

For `project profile create`, the reference SHALL document `--yes` as the non-interactive confirmation for replacing an existing same-lane project profile, and SHALL state that replacement clears omitted optional fields.

For `internals native-agent launch-dossiers add`, the reference SHALL document `--yes` as the non-interactive confirmation for replacing an existing same-lane explicit launch profile, and SHALL state that `launch-profiles set` remains the patch command.

The reference SHALL state that replacement does not cross project-profile and explicit-launch-profile lanes.

#### Scenario: Reader finds project-profile set in CLI reference
- **WHEN** a reader looks up `houmao-mgr project profile`
- **THEN** the CLI reference lists `set` alongside `create`, `list`, `get`, and `remove`
- **AND THEN** the reference explains that `set` mutates stored future launch defaults rather than one running instance

#### Scenario: Reader finds same-lane replacement guidance
- **WHEN** a reader looks up same-name reusable profile creation
- **THEN** the CLI reference explains when to use `--yes` for same-lane replacement
- **AND THEN** it distinguishes replacement from patching through `set`

### Requirement: CLI reference documents managed-header section flags
The `houmao-mgr` CLI reference SHALL document managed-header section flags on every CLI surface that supports them.

At minimum, the CLI reference SHALL document:

- `--managed-header-section SECTION=STATE` on `houmao-mgr project agents launch`,
- `--managed-header-section SECTION=STATE` on `houmao-mgr internals native-agent launch-dossiers add`,
- `--managed-header-section SECTION=STATE`, `--clear-managed-header-section SECTION`, and `--clear-managed-header-sections` on `houmao-mgr internals native-agent launch-dossiers set`,
- `--managed-header-section SECTION=STATE` on `houmao-mgr project profile create`,
- `--managed-header-section SECTION=STATE`, `--clear-managed-header-section SECTION`, and `--clear-managed-header-sections` on `houmao-mgr project profile set`,
- `--managed-header-section SECTION=STATE` on `houmao-mgr project agents launch`.

The CLI reference SHALL list supported section names and states, and SHALL state each section's default, including that `task-reminder` and `mail-ack` default to disabled unless explicitly enabled.

#### Scenario: Reader finds one-shot launch section flags
- **WHEN** a reader opens the CLI reference for `houmao-mgr project agents launch`
- **THEN** the reference documents `--managed-header-section SECTION=STATE`
- **AND THEN** the reference describes it as a one-shot launch override that does not rewrite stored launch-profile state

#### Scenario: Reader finds stored launch-profile section flags
- **WHEN** a reader opens the CLI reference for project launch-profile or project-profile create/set commands
- **THEN** the reference documents `--managed-header-section SECTION=STATE`
- **AND THEN** the reference documents the clear flags available on set commands

#### Scenario: Reader sees supported section vocabulary
- **WHEN** a reader looks at any managed-header section flag description
- **THEN** the reference lists `identity`, `houmao-runtime-guidance`, `automation-notice`, `task-reminder`, and `mail-ack` as supported sections
- **AND THEN** the reference lists `enabled` and `disabled` as supported states
- **AND THEN** the reference states that `task-reminder` and `mail-ack` default to disabled

### Requirement: CLI reference documents revised scoped `agents ... mail` lifecycle commands
When the CLI reference documents scoped `agents single ... mail` and `agents self mail`, that coverage SHALL include the current subcommands `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`.

That coverage SHALL explain:

- the selector rules for explicit targeting versus current-session targeting inside the owning managed tmux session,
- the structured `resolve-live` result contract for current mailbox discovery, including the returned mailbox binding and optional `gateway.base_url`,
- that mailbox-specific shell export is not part of the supported `resolve-live` contract,
- the difference between listing, peeking, and reading mail,
- that reply or acknowledgement marks a message answered but does not close it,
- that archive is the normal completion action for processed mail,
- the authority-aware result semantics that distinguish verified execution from non-authoritative TUI submission fallback.

The CLI reference SHALL NOT present `check` or `mark-read` as the current mailbox lifecycle workflow for processed mail after this change.

#### Scenario: Reader can find archive and move commands
- **WHEN** a reader looks up `houmao-mgr agents single ... mail` or `houmao-mgr agents self mail`
- **THEN** the CLI reference documents `archive` and `move` as supported mailbox lifecycle commands
- **AND THEN** the reader can tell that archive is the common processed-mail completion command

#### Scenario: Reader understands peek versus read
- **WHEN** a reader looks up mailbox message inspection commands
- **THEN** the CLI reference explains that `peek` does not mark a message read
- **AND THEN** it explains that `read` returns the message and marks it read

### Requirement: CLI reference documents gateway mail-notifier mode
The CLI reference page for scoped `houmao-mgr agents single ... gateway` and `houmao-mgr agents self gateway` SHALL document the mail-notifier notification mode option on `mail-notifier enable`.

That documentation SHALL list supported mode values `any_inbox` and `unread_only`, SHALL state that omitted mode defaults to `any_inbox`, and SHALL explain that `unread_only` only wakes for unread unarchived inbox mail.

#### Scenario: Reader finds mail-notifier mode option
- **WHEN** a reader opens the scoped `agents single ... gateway mail-notifier enable` or `agents self gateway mail-notifier enable` CLI reference
- **THEN** the option table documents the notifier mode option and its allowed values
- **AND THEN** the prose states that `any_inbox` is the default

#### Scenario: Reader understands unread-only trade-off
- **WHEN** a reader studies the `unread_only` mode documentation
- **THEN** the CLI reference explains that only unread unarchived inbox mail triggers notifications in that mode
- **AND THEN** it does not imply that read-but-unarchived mail will continue to wake the agent in `unread_only` mode

### Requirement: CLI reference hides compatibility-profile bootstrap
The CLI reference SHALL NOT document `--with-compatibility-profiles` as an option for `houmao-mgr project init`.

The CLI reference SHALL NOT present `.houmao/agents/compatibility-profiles/` as a supported project-layout directory, bootstrap result, optional project-init workflow, or operator-authored compatibility metadata root.

If CLI reference content mentions internal CAO compatibility elsewhere, that content SHALL remain scoped to the relevant legacy or compatibility runtime surface and SHALL NOT direct operators to author or pre-create compatibility profile files.

#### Scenario: Reader sees no compatibility-profile project-init option
- **WHEN** a reader opens CLI reference coverage for `houmao-mgr project init`
- **THEN** the reference does not list `--with-compatibility-profiles`
- **AND THEN** the reference does not include an example that creates `.houmao/agents/compatibility-profiles/`

#### Scenario: Reader sees no compatibility-profile project layout guidance
- **WHEN** a reader scans CLI reference project-layout notes
- **THEN** the reference does not present `.houmao/agents/compatibility-profiles/` as a maintained local project directory

### Requirement: CLI reference explains component-scoped memo seed policies
The `houmao-mgr` CLI reference SHALL explain that launch-profile memo seeds do not expose a memo seed policy option.

The CLI reference SHALL explain that memo seed source options replace only the managed-memory components represented by the supplied source.

When the reference documents `--memo-seed-text` or `--memo-seed-file`, it SHALL state that profile-backed launch replaces `houmao-memo.md` without clearing memory pages.

When the reference documents `--memo-seed-dir`, it SHALL state that a directory seed replaces `houmao-memo.md` only when `houmao-memo.md` is present and replaces pages only when `pages/` is present.

When the reference documents `--clear-memo-seed`, it SHALL distinguish removing stored seed configuration from storing an empty memo seed.

#### Scenario: Reader distinguishes empty memo seed from clearing seed config
- **WHEN** a reader looks up memo seed flags for launch profiles or project profiles
- **THEN** the CLI reference states that `--clear-memo-seed` removes stored seed configuration
- **AND THEN** the CLI reference states that `--memo-seed-text ''` stores an intentional empty memo seed
- **AND THEN** the CLI reference does not document `--memo-seed-policy`

#### Scenario: Reader sees memo-only seed preserves pages
- **WHEN** a reader looks up `--memo-seed-text`
- **THEN** the CLI reference states that the launch replaces `houmao-memo.md`
- **AND THEN** it does not state that pages are cleared for memo-only seeds

### Requirement: CLI reference documents relaunch chat-session selection
The CLI reference SHALL document the `houmao-mgr agents single --agent-id <id> relaunch` and `houmao-mgr agents single --agent-name <name> relaunch` chat-session selectors.

That documentation SHALL include:

- supported modes `new`, `tool_last_or_new`, and `exact`,
- the provider-native id requirement for `exact`,
- default fresh-chat behavior when the selector is omitted,
- examples for current-session active refresh through `agents self relaunch` and selected-agent relaunch through explicit `--agent-id` or `--agent-name`,
- a note that native headless relaunch applies the selector on the next managed prompt.

The CLI reference SHALL NOT present relaunch continuation as a build-time launch option.

#### Scenario: Reader finds latest-chat relaunch example
- **WHEN** a reader looks up `houmao-mgr agents single ... relaunch`
- **THEN** the CLI reference includes an example that relaunches a managed agent with relaunch chat-session mode `tool_last_or_new`
- **AND THEN** the example uses the supported Houmao relaunch command rather than a raw provider CLI command

#### Scenario: Reader sees exact id validation
- **WHEN** a reader looks up relaunch chat-session mode `exact`
- **THEN** the CLI reference states that a provider-native chat-session id is required
- **AND THEN** it does not imply that Houmao can always infer that id for TUI sessions

#### Scenario: Reader understands headless relaunch timing
- **WHEN** a reader looks up relaunch chat-session selection for a native headless managed agent
- **THEN** the CLI reference states that the relaunch command records the selector for the next managed prompt
- **AND THEN** it does not imply that relaunch itself sends a prompt

### Requirement: CLI reference documents degraded and stale recovery paths

The CLI reference SHALL document degraded and stale recovery behavior in the `agents single ... stop` and `agents single ... relaunch` command descriptions. The descriptions SHALL state that these commands probe the target tmux session before acting and route through recovery helpers when the session is degraded or stale. The descriptions SHALL link to the dedicated degraded-stale recovery reference page.

#### Scenario: Reader discovers recovery from CLI reference

- **WHEN** a reader reads the `agents single ... stop` or `agents single ... relaunch` CLI description
- **THEN** they see mention of the degraded/stale recovery path and a link to the dedicated recovery page

### Requirement: CLI reference documents cleanup purge-registry flag

The CLI reference SHALL document the `agents single ... cleanup session --purge-registry` flag in the cleanup command family. The description SHALL explain that this flag deletes the lifecycle record entirely (rather than retiring it) and is intended for confirmed broken active local authority after tmux inspection.

#### Scenario: Reader understands purge-registry from CLI reference

- **WHEN** a reader reads the `agents single ... cleanup session` CLI description
- **THEN** they see `--purge-registry` documented with its destructive semantics and the condition that it requires confirmed broken authority

### Requirement: CLI reference documents external managed-agent imports
The CLI reference SHALL document the `houmao-mgr agents external` command family for registering and managing communication-only external Houmao agents.

At minimum, the reference SHALL cover:
- `agents external register`,
- `agents external list`,
- `agents external get`,
- `agents external verify`,
- `agents external remove`,
- the required registration inputs `--name`, `--api-base-url`, and `--agent-ref`,
- gateway expectation flags,
- local selector behavior after registration,
- the distinction between local lifecycle-managed agents and external communication-only imports.

The CLI reference SHALL identify which normal `houmao-mgr agents` commands are supported for external targets and which lifecycle or raw local-control commands are rejected.

The CLI reference SHALL include security guidance stating that remote passive-server URLs should be exposed only through a trusted channel such as SSH forwarding, VPN, Tailscale, or a secured reverse proxy until an authenticated remote transport is available.

#### Scenario: Reader can register a remote Houmao agent from CLI docs
- **WHEN** a reader looks up `houmao-mgr agents external`
- **THEN** the CLI reference shows the registration command form with `--name`, `--api-base-url`, and `--agent-ref`
- **AND THEN** it explains that the remote URL must be a reachable maintained `houmao-passive-server`

#### Scenario: Reader sees supported external target operations
- **WHEN** a reader checks external-agent command support in the CLI reference
- **THEN** the page lists communication-safe commands such as list, state, prompt, interrupt, gateway status, gateway prompt, and supported pair-backed mail operations
- **AND THEN** it lists rejected local lifecycle or raw local-control operations such as stop, relaunch, cleanup, gateway attach, gateway detach, and gateway send-keys

#### Scenario: Reader sees secure exposure guidance
- **WHEN** a reader copies an example using `--api-base-url`
- **THEN** the surrounding documentation warns against exposing an unauthenticated passive-server on a public network
- **AND THEN** it recommends trusted-channel deployment options for remote access

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

### Requirement: CLI reference points Kimi automation at unattended prompt mode
The CLI reference SHALL document `launch.prompt_mode: unattended` and the corresponding project/profile prompt-mode flags as the supported Houmao-facing way to run Kimi Code without permission dialogs or user questions.

The CLI reference SHALL NOT present Kimi `--yolo` as a current Houmao launch option for achieving unattended behavior.

The CLI reference MAY mention Kimi provider-native `--auto` only as implementation background or low-level provider behavior, not as the recommended Houmao managed launch control.

#### Scenario: Reader finds supported Kimi no-question launch control
- **WHEN** a reader looks up how to run a Kimi managed agent automatically
- **THEN** the CLI reference points them to `launch.prompt_mode: unattended` or the matching project/profile prompt-mode CLI controls
- **AND THEN** it does not instruct them to pass `--yolo`

#### Scenario: Reader does not need raw Kimi flags for managed launch
- **WHEN** a reader looks up Kimi project specialist or project profile launch options
- **THEN** the reference describes prompt mode as the managed automation control
- **AND THEN** it does not require raw launch overrides with Kimi `--auto` for ordinary managed unattended launch

### Requirement: CLI reference documents gateway prompt admission policies

The maintained `houmao-mgr` CLI reference SHALL document `--admission-policy ready-only|if-no-pending|always` for scoped `agents single ... gateway prompt` and `agents self gateway prompt` commands.

The reference SHALL explain the readiness and pending-input condition for each value, the conservative treatment of `pending_input=unknown`, the observational behavior when multiple submissions occur before a TUI repaint, and the TUI-only scope of non-default policies.

The reference SHALL remove `--force` from current syntax, option tables, and examples and SHALL NOT present it as an alias or migration shim.

#### Scenario: Reader can choose the policy from the CLI reference

- **WHEN** a reader opens the scoped gateway prompt command reference
- **THEN** the option table defines ready-only, if-no-pending, and always in terms of tracked readiness and provider-native pending input
- **AND THEN** the examples show the current `--admission-policy` syntax

#### Scenario: Reference explains observational concurrency

- **WHEN** a reader looks up whether if-no-pending reserves an empty queue slot
- **THEN** the CLI reference states that each call evaluates the latest observation independently
- **AND THEN** it explains that two calls may both submit before the provider TUI repaints

#### Scenario: Removed force option is absent from current docs

- **WHEN** a reader reviews gateway prompt syntax after the breaking change
- **THEN** current command tables and examples do not include `--force`
- **AND THEN** no documentation claims that a compatibility alias remains

### Requirement: System-skills reference documents portable release metadata
The CLI reference SHALL explain that each of the six standalone public `SKILL.md` roots declares `houmao_version` equal to its Houmao release. It SHALL explain that shared children inherit the shared root version and do not declare independent values.

The reference SHALL distinguish installed frontmatter version, config `houmao_version`, and content digest evidence.

#### Scenario: Reader inspects shared routines
- **WHEN** a reader asks how the sixteen shared children are versioned
- **THEN** the reference identifies `houmao-shared-routines/SKILL.md` as their version authority
- **AND THEN** it does not advertise per-child release versions

### Requirement: System-skills reference documents doctor usage
The CLI reference SHALL document doctor with explicit tool-home examples, managed-agent id and name examples, repeatable pack selection, agent-pack default, plain output, structured output, and exit codes.

It SHALL explain that doctor can inspect configless copy or Skills CLI installations and that managed-agent name resolution must be unique.

#### Scenario: Reader checks one managed agent
- **WHEN** a reader wants to diagnose one known managed agent
- **THEN** the reference shows the authoritative agent-id form
- **AND THEN** it explains how doctor resolves the persistent home

#### Scenario: Reader checks an external copy
- **WHEN** a reader installed the static agent roots without `houmao-mgr`
- **THEN** the reference shows explicit `--tool`, `--home`, and `--pack agent`
- **AND THEN** it states that a missing config does not prevent version diagnosis

### Requirement: Documentation preserves the diagnostic boundary
The reference SHALL state that `houmao_version` equality is checked only by doctor. It SHALL NOT claim that install, status, upgrade, managed launch, join, runtime authorization, or skill invocation rejects mismatched versions.

Doctor documentation SHALL describe it as read only and SHALL direct repairs to explicit install or upgrade commands rather than implying automatic mutation.

#### Scenario: Doctor reports an old release
- **WHEN** a reader receives a version mismatch
- **THEN** the reference explains that the result is diagnostic
- **AND THEN** it offers an explicit upgrade or reinstall as a separate operator decision

### Requirement: System-skills reference documents minimal skill config
The system-skills CLI reference SHALL document `<tool-home>/.houmao/system-skills/<tool>/houmao-skill-config.json` as the sole manager ownership configuration. It SHALL enumerate the exact four top-level fields and exact four fields in each installed-skill record, explain derived pack selection, and distinguish config `houmao_version`, installed frontmatter version, and content digest evidence.

The reference SHALL use config terminology throughout lifecycle commands and output examples. It SHALL NOT describe a current receipt path or receipt schema.

#### Scenario: Reader inspects ownership state
- **WHEN** a reader wants to understand what Houmao installed
- **THEN** the reference identifies the exact skill-config path and minimal field contract
- **AND THEN** it explains how owner sets preserve shared roots across partial pack uninstall

### Requirement: System-skills reference documents the breaking reinstall boundary
The system-skills reference SHALL state that the current release does not read, migrate, delete, or report `receipt.json`. It SHALL direct users to uninstall with the previous release or remove the old system-skill projections and state before reinstalling.

The reference SHALL continue to explain that doctor can diagnose complete configless copy-paste and Skills CLI installations directly.

#### Scenario: Existing user upgrades from receipt state
- **WHEN** a reader has a receipt-based installation
- **THEN** the reference gives the clean removal and reinstall requirement
- **AND THEN** it does not promise automatic migration or overwrite of old projected roots

### Requirement: CLI reference documents system-skill pack lifecycle
`docs/reference/cli/system-skills.md` SHALL document `list`, `install`, `status`, `doctor`, `upgrade`, and `uninstall` with repeatable `--pack admin|agent`, supported tool and home resolution, copy and explicit symlink projection, plain output, and root `--print-json` output.

The reference SHALL explain CLI-default admin selection, managed-default agent selection, complete-pack atomicity, config ownership, integrity states, and transaction rollback. It SHALL NOT document `--set` or low-level `--skill` as current manager selectors.

#### Scenario: Reader looks up external installation
- **WHEN** a reader opens the system-skills CLI reference
- **THEN** they find a complete admin-pack install example and effective-home rules
- **AND THEN** they understand that omission selects the admin pack

### Requirement: CLI reference documents public roles and actor entrypoints
The reference SHALL list all six standalone roots and SHALL distinguish the three actor-facing roots from shared routines and the two direct loop roots.

It SHALL explain the welcome mutation boundary, admin explicit-target posture, agent self-identity verification, managed joined-session actor transition, explicit shared and loop activation, and the absence of an agent welcome.

#### Scenario: Reader chooses between admin and agent entrypoints
- **WHEN** a reader needs to perform an operation from a human-operated home or managed home
- **THEN** the reference identifies the correct actor entrypoint and actor semantics
- **AND THEN** it does not suggest that prompt wording can switch the active actor

### Requirement: CLI reference provides an actor-qualified shared route map
The reference SHALL map every parent-scoped shared routine to eligible actor entrypoints, route names, major `houmao-mgr` command families, and actor-specific target behavior.

Parent-qualified designators SHALL be labeled as route traces. Copyable prompts SHALL begin with an actor entrypoint or the explicit advanced shared-routines root. The reference SHALL identify old top-level routine names only in migration guidance.

#### Scenario: Reader finds credential-management commands
- **WHEN** a reader searches for credential-management skill guidance
- **THEN** the reference points to the admin entrypoint's credential route and maintained CLI families
- **AND THEN** it does not present `houmao-credential-mgr` as a top-level installed skill

### Requirement: CLI reference documents clean reinstall and config-owned removal
The reference SHALL explain status classifications, safe legacy digest or symlink detection, preserved modified conflicts, config-owned upgrade and uninstall, static projection paths, and host refresh requirements.

It SHALL state that the current lifecycle ignores old `receipt.json` state, does not silently overwrite old untracked roots, and requires a clean reinstall before those roots can become config-owned.

#### Scenario: Reader has a modified legacy skill directory
- **WHEN** a reader follows migration guidance for an old home with modified content
- **THEN** the reference tells them to preserve and review the conflict
- **AND THEN** it provides an explicit cleanup and reinstall path before retrying

### Requirement: CLI reference retains supported provider boundaries at pack level
The reference SHALL document pack projection for Claude, Codex, Copilot, Kimi, and universal targets, including maintained Kimi reachability caveats.

It SHALL state that Gemini is not a supported system-skill projection target and that `houmao-auto-system-prompt` remains separate from pack lifecycle commands.

#### Scenario: Reader checks Copilot or Gemini support
- **WHEN** a reader compares system-skill targets
- **THEN** Copilot is identified as a pack projection target rather than a launch backend
- **AND THEN** Gemini is not presented as a supported pack target

### Requirement: System-skills CLI reference documents static pack membership
The CLI reference SHALL list all standalone members of the admin and agent packs, identify shared ownership of `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite`, and distinguish the sixteen shared children from installable roots.

It SHALL NOT describe protected mounts, audience-specific composed route files, or materialized entrypoint trees as current behavior.

#### Scenario: Reader checks the agent pack
- **WHEN** a reader opens the system-skills pack table
- **THEN** the agent pack contains agent entrypoint, shared routines, pro loop, and lite loop
- **AND THEN** all four appear as top-level static destinations

### Requirement: System-skills CLI reference documents shared-owner lifecycle behavior
The CLI reference SHALL explain install, status, upgrade, and uninstall behavior for overlapping pack members. It SHALL state that uninstall removes a shared projection only after its last owning pack is removed.

The reference SHALL describe the new config as the sole manager ownership evidence and SHALL explain that old receipt-era roots require a clean reinstall rather than automatic migration.

#### Scenario: Reader plans to remove one of two installed packs
- **WHEN** both packs own shared members
- **THEN** the reference explains which exclusive entrypoint is removed
- **AND THEN** it explains why shared routines and loops remain for the other pack

### Requirement: CLI reference documents standard external skill installation
The system-skills reference SHALL link to the public static source collection and show that users may install it with normal Skills CLI or copy-paste workflows.

It SHALL explain that external standard installation has no Houmao skill config and requires explicit sibling selection, while `houmao-mgr system-skills` provides dependency-aware pack lifecycle management.

#### Scenario: Reader compares manager and Skills CLI
- **WHEN** a reader chooses an installation method
- **THEN** the reference distinguishes config ownership and automatic pack closure from independent skill selection
- **AND THEN** it provides the complete sibling list needed by the chosen actor entrypoint

### Requirement: CLI reference documents direct public invocation surfaces
The reference SHALL document normal admin and agent entrypoint forms, direct shared-routines advanced invocation, direct pro and lite invocation, and the optional managed-self qualifier for direct shared or loop calls.

It SHALL describe shared children with parent-qualified object notation and SHALL not advertise their old top-level `$houmao-<routine>` forms as current standalone triggers.

#### Scenario: Reader invokes a loop manually
- **WHEN** a reader chooses the pro loop skill
- **THEN** the reference shows `$houmao-agent-loop-pro <operation>`
- **AND THEN** it preserves the explicit manual activation boundary and `<loop-dir>` input rules
