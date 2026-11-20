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
The `houmao-mgr` reference SHALL describe the public command tree, scoped agent targeting, and the nested operations supported by the CLI.

#### Scenario: Reader Locates Public Manager Commands
- **WHEN** a reader opens the `houmao-mgr` reference
- **THEN** the page covers `admin`, `agents`, `internals`, `mailbox`, `project`, and `system-skills`, with subcommand summaries drawn from `srv_ctrl/commands/` docstrings, Click decorators, and live help
- **AND THEN** it omits top-level `credentials`, `brains`, and `server` as maintained surfaces
- **AND THEN** it presents `agents` with explicit `global`, `single`, `self`, and `external` scopes and omits unscoped action paths such as `agents launch`, `agents mail`, and `agents gateway`
- **AND THEN** inline coverage or dedicated links make the major nested managed-agent, project, and internal families discoverable
- **AND THEN** project and utility coverage includes `project --project-dir`, `project agents`, `project credentials`, `project`, `project mailbox`, `admin cleanup`, `internals native-agent credentials`, and `internals native-agent brain build`, with a dedicated link to `docs/reference/cli/internals.md` for `internals graph`

#### Scenario: Reader Chooses Global or Selected-Agent Control
- **WHEN** a reader looks up the `global` or `single` scope
- **THEN** the reference lists `agents global list` for registry operations on zero or multiple local agents, without `--agent-id` or `--agent-name`
- **AND THEN** each `single` operation uses the group-level `--agent-id <id>` or `--agent-name <name>` selector, without current-session fallback
- **AND THEN** selected-agent coverage includes `state`, `prompt`, `stop`, `interrupt`, `relaunch`, `turn`, `gateway`, `mail`, `mailbox`, `memory`, and `cleanup`
- **AND THEN** the reference explains that selected-agent relaunch can revive stopped relaunchable records and recover degraded or stale active records where supported

#### Scenario: Reader Chooses Current-Session Control
- **WHEN** a reader looks up `agents self`
- **THEN** the reference explains `self join` adoption of the caller's current tmux session into one local managed-agent identity
- **AND THEN** other `self` operations target the current managed tmux session and omit `--agent-id`, `--agent-name`, and `--current-session`
- **AND THEN** the documented current-session commands include `identity`, `state`, `prompt`, `interrupt`, `relaunch`, `turn`, `gateway`, `mail`, `mailbox`, and `memory`
- **AND THEN** the reference confines `self relaunch` to refreshing the active tmux-backed surface and assigns stopped-record revival and degraded or stale recovery to `single relaunch` with an explicit selector
- **AND THEN** the reference omits `self stop` and `self cleanup` as maintained public paths

#### Scenario: Reader Uses an External Reference
- **WHEN** a reader looks up `agents external`
- **THEN** the reference covers `register`, `list`, `get`, `verify`, and `remove`
- **AND THEN** it explains that these commands store remotely owned or communication-only references in the shared registry and that the local manager has no lifecycle control over them

#### Scenario: Reader Looks up Scoped Mail and Gateway Operations
- **WHEN** a reader looks up managed-agent mail or gateway operations
- **THEN** the reference covers `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive` for scoped mail
- **AND THEN** mail coverage explains `single` and `self` selectors, the structured `resolve-live` mailbox binding and optional `gateway.base_url`, the absence of mailbox shell exports, and how to distinguish verified execution from non-authoritative TUI submission
- **AND THEN** full option tables and descriptions cover maintained single and self paths for `tui state|history|watch|note-prompt`, `mail-notifier status|enable|disable`, and `reminders list|get|create|set|remove`

#### Scenario: Reader Looks up Native Build and Claude Auth Options
- **WHEN** a reader looks up native brain building or Claude specialist credentials
- **THEN** the brain-build table lists live flags including `--preset`, `--setup`, and `--auth` while supported, and omits `--recipe`, `--config-profile`, and `--cred-profile`
- **AND THEN** the Claude specialist path lists `--claude-auth-token`, `--claude-oauth-token`, and `--claude-config-dir`, while `project credentials claude` and `internals native-agent credentials claude` list `--auth-token`, `--oauth-token`, and `--config-dir`
- **AND THEN** the reference confirms that both flag sets have the same credential semantics

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

The `houmao-passive-server` CLI reference SHALL document the maintained registry-driven server and API authority.

#### Scenario: Reader Finds the Maintained Server Path
- **WHEN** a reader opens the passive-server reference
- **THEN** the page describes registry-driven discovery, the serve command, and the API surface from `passive_server/` docstrings
- **AND THEN** it explains how passive-server collects and manages running Houmao agents through supported routes and omits standalone `houmao-server` as a deployment choice
- **AND THEN** any comparison table gives passive-server's default port of 9891 and omits a retained port for standalone `houmao-server`

#### Scenario: Reader understands passive-server is the maintained server path
- **WHEN** a reader opens the passive-server CLI reference
- **THEN** they understand that passive-server is the maintained registry-driven API server
- **AND THEN** the page does not tell the reader to choose standalone `houmao-server` instead for current workflows

#### Scenario: Comparison table shows passive-server default port only
- **WHEN** a reader checks the comparison table in `houmao-passive-server.md`
- **THEN** the default port for `houmao-passive-server` is listed as 9891
- **AND THEN** standalone `houmao-server` is not presented as a retained server binary with a current default port

### Requirement: CLI reference uses `.houmao` ambient resolution and deprecation-only legacy notes
Repo-owned CLI reference pages SHALL describe the current `.houmao` resolution rules and identify retired entrypoints as historical.

#### Scenario: Reader Resolves the Agent Definition Directory
- **WHEN** a reader looks up the active agent-definition directory
- **THEN** the reference starts with `--agent-def-dir`, then checks `HOUMAO_NATIVE_AGENT_ROOT`, the overlay selected by `HOUMAO_PROJECT_OVERLAY_DIR`, and ambient overlay discovery before using `<cwd>/.houmao/agents`
- **AND THEN** it identifies `houmao-config.toml` as the discovery anchor and `agents/` beneath the selected overlay as the compatibility projection for file-tree consumers
- **AND THEN** it omits `<cwd>/.agentsys/agents` as a supported default or fallback

#### Scenario: Reader Selects Ambient Discovery
- **WHEN** a reader looks up `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` or `HOUMAO_PROJECT_OVERLAY_DIR`
- **THEN** the reference identifies `ancestor` as the default lookup of the nearest ancestor `.houmao/houmao-config.toml` and `cwd_only` as lookup restricted to `<cwd>/.houmao/houmao-config.toml`
- **AND THEN** it explains that this mode only affects ambient discovery and that the absolute `HOUMAO_PROJECT_OVERLAY_DIR` override directly selects an overlay for CI and controlled automation

#### Scenario: Reader Encounters a Retired Entrypoint
- **WHEN** the CLI reference mentions `houmao-cli`, standalone `houmao-server`, or `houmao-cao-server`
- **THEN** it confines those names to explicit retirement, historical, removal, or migration context and omits them as active or deprecated-installable workflows

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

The CLI reference SHALL provide complete, handwritten pages for the `houmao-mgr agents` subcommand families.

#### Scenario: Reader Finds Complete Scoped Reference Pages
- **WHEN** a reader opens a dedicated managed-agent reference
- **THEN** `docs/reference/cli/agents-gateway.md` documents all subcommands, including `tui state|history|watch|note-prompt` and `mail-notifier status|enable|disable`, with full option tables
- **AND THEN** `docs/reference/cli/agents-mail.md` documents `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive` with full option tables and usage notes
- **AND THEN** `docs/reference/cli/agents-mailbox.md` documents `register`, `unregister`, and `status` with full option tables
- **AND THEN** `docs/reference/cli/agents-turn.md` documents `submit`, `status`, `events`, `stdout`, and `stderr` with full option tables
- **AND THEN** each page follows `docs/reference/cli/admin-cleanup.md` with brief usage context and examples where useful

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
The CLI reference SHALL document `reminders` as a first-class subgroup for both scoped gateway command paths.

#### Scenario: Reader Finds Reminder Targeting and Ranking
- **WHEN** a reader looks up `agents single ... gateway reminders` or `agents self gateway reminders`
- **THEN** the `agents-gateway` page provides full option tables and usage guidance for `list`, `get`, `create`, `set`, and `remove`
- **AND THEN** it explains selected-agent and current-session targeting, pair-managed authority with `--pair-port`, and direct `/v1/reminders` as the underlying gateway contract
- **AND THEN** it describes numeric ranking and the placement of `--before-all` ahead of the current minimum and `--after-all` after the current maximum

#### Scenario: Reader finds all reminder subcommands from the scoped gateway CLI reference
- **WHEN** a reader opens `docs/reference/cli/agents-gateway.md`
- **THEN** the page documents `reminders list`, `reminders get`, `reminders create`, `reminders set`, and `reminders remove`
- **AND THEN** the reminder subgroup appears alongside the other current scoped gateway operator surfaces rather than as an undocumented exception

#### Scenario: Reader can understand ranking placement flags from the CLI reference
- **WHEN** a reader looks up scoped `houmao-mgr agents single ... gateway reminders create|set` or `houmao-mgr agents self gateway reminders create|set`
- **THEN** the option tables and prose explain `--ranking`, `--before-all`, and `--after-all`
- **AND THEN** the page makes clear that ranking is numeric and that the convenience flags resolve to concrete numeric positions relative to the live reminder set

### Requirement: houmao-passive-server reference rewritten with operational depth

The `houmao-passive-server` CLI reference SHALL explain how to deploy, configure, and use the shared-registry server.

#### Scenario: Reader Deploys Passive-Server
- **WHEN** a reader opens `docs/reference/cli/houmao-passive-server.md` to set up distributed coordination
- **THEN** the page describes when to use the maintained server API, registry-driven discovery and observation, REST route families and capabilities, and supported `houmao-mgr` pair-authority options
- **AND THEN** it describes passive-server as a global service over the shared registry and states that `serve` can start independently of a project overlay
- **AND THEN** it covers every current `serve` option, including runtime-root and registry-root resolution via `--runtime-root`, `--registry-root`, `HOUMAO_GLOBAL_RUNTIME_DIR`, `HOUMAO_GLOBAL_REGISTRY_DIR`, and global defaults
- **AND THEN** it omits standalone `houmao-server` as a maintained deployment choice

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
The `houmao-mgr` CLI reference SHALL distinguish Claude credential inputs from optional runtime bootstrap state.

#### Scenario: Reader Separates Authentication and State
- **WHEN** a reader looks up Claude flags for `project credentials claude`, `internals native-agent credentials claude ... --native-agent-root <path>`, or `project specialist create --tool claude`
- **THEN** the page identifies credential-providing inputs separately from optional bootstrap state in `claude_state.template.json` or `--claude-state-template-file`

#### Scenario: Reader sees the Claude state template documented separately in the CLI reference
- **WHEN** a reader looks up the Claude credential-management or easy-specialist options in `docs/reference/cli/houmao-mgr.md`
- **THEN** the page distinguishes credential-providing Claude inputs from the optional state-template input
- **AND THEN** it does not present the state-template input as one of the ways to authenticate Claude

### Requirement: CLI reference documents specialist editing controls
The `houmao-mgr` CLI reference SHALL document how operators patch and replace reusable specialists.

#### Scenario: Reader Edits a Reusable Specialist
- **WHEN** a reader looks up the `project specialist` commands
- **THEN** the reference lists `create`, `list`, `get`, `set`, and `remove`
- **AND THEN** it describes `set` as a patch that preserves unspecified stored fields and applies the updated source only to future launches
- **AND THEN** it explains that `create --yes` confirms same-name replacement non-interactively, using create semantics that may clear omitted optional fields

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
Launch and join references SHALL document `--workdir` as the public runtime working-directory option where supported.

#### Scenario: Reader Sets a Runtime Working Directory
- **WHEN** a reader looks up `houmao-mgr project agents launch` or `houmao-mgr agents self join`
- **THEN** the reference explains that `--workdir` sets the agent's runtime working directory while preserving source-project resolution
- **AND THEN** if omitted, launch uses the invocation directory and join uses the tmux pane's current directory
- **AND THEN** for `project agents launch`, the selected easy-project overlay and specialist source remain authoritative even when `--workdir` points elsewhere
- **AND THEN** the join reference omits `--working-directory` as a supported flag

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
The CLI reference SHALL distinguish explicit gateway targets from the current managed session and document the pair-authority override.

#### Scenario: Reader Selects a Gateway Target
- **WHEN** a reader opens `docs/reference/cli/agents-gateway.md` or `docs/reference/cli.md`
- **THEN** the reference shows `houmao-mgr agents single --agent-id <id> gateway ...` and `houmao-mgr agents single --agent-name <name> gateway ...` for explicit targets
- **AND THEN** it defines `--pair-port` as the `agents single` pair-authority override and identifies lower-level `--gateway-port` as controlling the listener
- **AND THEN** the `agents-gateway` page explains outside-tmux selection through `agents single` and inside-tmux targeting through `agents self`

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

The manager reference SHALL document canonical recipes and their preset alias, plus the project-profile and explicit launch-dossier surfaces.

#### Scenario: Reader Locates Recipe, Role, and Dossier Commands
- **WHEN** a reader prepares a recipe, role, or explicit launch profile
- **THEN** the reference lists `internals native-agent recipes list|get|add|set|remove` as canonical and `project agents presets list|get|add|set|remove` as an alias for the same resources in `agents/presets/<name>.yaml`
- **AND THEN** it lists `internals native-agent launch-dossiers list|get|add|set|remove` as the canonical explicit launch-profile surface for `agents/launch-profiles/<name>.yaml`
- **AND THEN** it describes `internals native-agent roles` as prompt-only role management and omits `roles scaffold` as a supported command

#### Scenario: Reader Locates Project Profiles and Launch Commands
- **WHEN** a reader works from a specialist-backed profile
- **THEN** the reference lists `project profile create|list|get|remove` for reusable birth-time launch profiles
- **AND THEN** it shows project-scoped birth through `project agents launch --profile <name>` and explains that `--profile` and `--specialist` are mutually exclusive
- **AND THEN** it applies source recipe defaults, then launch-profile defaults, then direct CLI overrides, and explains that overrides such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir` apply only to that launch
- **AND THEN** it identifies the separate low-level `internals native-agent launch-dossiers` authoring surface and links to `docs/getting-started/launch-profiles.md` for the shared model

#### Scenario: Reader Checks the Expected Project Tree
- **WHEN** a reader checks the `houmao-mgr project` overview
- **THEN** the command shape lists `roles`, `recipes`, `presets`, `launch-profiles`, and `tools <tool>` under `project agents` and `specialist`, `profile`, and `instance` under `project`

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
The manager reference SHALL document the managed-header controls and their precedence on supported launch and profile commands.

#### Scenario: Reader Chooses or Clears the Managed Header
- **WHEN** a reader looks up managed-header options
- **THEN** the reference lists `--managed-header` and `--no-managed-header` on `project agents launch`, `internals native-agent launch-dossiers add`, `internals native-agent launch-dossiers set`, and `project profile create`
- **AND THEN** it includes `--clear-managed-header` on `internals native-agent launch-dossiers set`
- **AND THEN** it explains mutually exclusive direct launch flags, direct override precedence over stored policy, restoration of inheritance when stored policy is cleared, and the default enabled behavior when no launch or profile policy is supplied

#### Scenario: Reader can find the managed-header flags in the CLI reference
- **WHEN** a reader looks up `houmao-mgr project agents launch`, `internals native-agent launch-dossiers`, or the relevant `project` commands
- **THEN** the CLI reference documents the managed-header flags and their meaning
- **AND THEN** the page does not require the reader to infer the new behavior from source code or changelog text

#### Scenario: Reader understands precedence and clear semantics from the CLI reference
- **WHEN** a reader checks the option notes for managed-header controls
- **THEN** the CLI reference explains direct-override precedence over stored profile policy
- **AND THEN** it explains that `--clear-managed-header` returns the stored profile field to inherit behavior

### Requirement: CLI reference removes retired `--yolo` launch option from all pages

Current launch references SHALL use only stored `launch.prompt_mode` and the corresponding profile flags for prompt posture.

#### Scenario: Reader Looks up Current Prompt Posture
- **WHEN** a reader checks launch controls in `docs/reference/cli/houmao-mgr.md`, `docs/reference/cli/agents-gateway.md`, `docs/reference/cli/system-skills.md`, or another CLI reference page
- **THEN** the page describes supported profile values `unattended` and `as_is` and their flags
- **AND THEN** the page omits `--yolo` from launch options and removes remaining references to it

#### Scenario: Reader does not see `--yolo` as a current option in CLI reference

- **WHEN** a reader greps the CLI reference pages for `--yolo`
- **THEN** zero matches appear as supported options on live launch commands
- **AND THEN** any remaining mention is in an explicit "removed in 0.3.x" or migration-note context

#### Scenario: Reader learns the current way to control prompt-mode posture

- **WHEN** a reader looks up how to launch an agent without provider startup prompts
- **THEN** the CLI reference points the reader at `launch.prompt_mode: unattended` in stored profiles or the equivalent launch-profile flags
- **AND THEN** the reference does not present `--yolo` as the way to achieve that posture

### Requirement: CLI reference documents the unified `--model` selection on launch surfaces

The manager reference SHALL document `--model` as the unified selector for managed launch and launch-profile defaults.

#### Scenario: Reader Selects a Launch Model
- **WHEN** a reader looks up model selection
- **THEN** the reference covers `project specialist create`, `project agents launch`, and `internals native-agent launch-dossiers` commands that accept stored model defaults
- **AND THEN** it explains that the tool-agnostic selector maps to the appropriate per-tool identifier and still requires tool authentication and provider configuration
- **AND THEN** it uses the relevant tool reference link as the source of tool-specific model identifiers

#### Scenario: Reader finds the unified `--model` flag on the launch surfaces

- **WHEN** a reader looks up `project agents launch`
- **THEN** the CLI reference documents `--model` as a current option
- **AND THEN** the page explains that `--model` is a tool-agnostic selector resolved through the provider mapping

#### Scenario: Reader understands that `--model` is not an auth or provider override

- **WHEN** a reader looks up the `--model` flag
- **THEN** the CLI reference states that `--model` does not bypass tool authentication or provider configuration

### Requirement: CLI reference resync against current Click decorators for stale `agents` and `admin` pages

The managed-agent, admin cleanup, and server CLI references SHALL match the current Click command definitions.

#### Scenario: Reader Finds Correct Command and Option Tables
- **WHEN** the CLI reference sync updates `agents-mailbox.md`, `agents-turn.md`, `admin-cleanup.md`, or `houmao-server.md` under `docs/reference/cli/`
- **THEN** subcommands and all option names and defaults match the decorators in `src/houmao/srv_ctrl/commands/` and, for the server page, `src/houmao/server/commands/`
- **AND THEN** the pages account for removed or renamed flags from feature commits after `2026-04-04` and preserve accurate prose

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

The manager and launch-surface references SHALL link directly to the managed prompt header reference from supported header controls.

#### Scenario: Reader Opens the Header Reference From a Flag
- **WHEN** a reader studies `--managed-header`, `--no-managed-header`, or a related stored launch-profile policy flag in `docs/reference/cli/houmao-mgr.md`
- **THEN** the page links directly to `docs/reference/run-phase/managed-prompt-header.md` to explain what the header contains, without requiring a tooltip or footnote

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

The manager and scoped turn and gateway references SHALL document request-scoped headless model and reasoning overrides on every supported prompt surface.

#### Scenario: Reader Finds Headless Overrides
- **WHEN** a reader opens `docs/reference/cli/houmao-mgr.md` or its scoped turn and gateway child pages
- **THEN** the reference covers both `agents single` and `agents self` paths for `prompt`, `turn submit`, and `gateway prompt`
- **AND THEN** each path documents `--model TEXT` for a headless model override and `--reasoning-level INTEGER` as a preset index for the selected tool and model
- **AND THEN** the options affect exactly the submitted request, with no mutation of launch profiles, recipes, specialists, manifests, stored project profiles, or live session defaults
- **AND THEN** the reference describes explicit rejection for TUI-backed prompt routes

#### Scenario: Reader Interprets a Reasoning Preset
- **WHEN** a reader chooses a reasoning level or supplies only part of an override
- **THEN** the reference explains that each resolved tool and model has its own preset ladder, with positive overflow saturating to its highest maintained Houmao preset
- **AND THEN** partial overrides merge with launch-resolved defaults through the shared headless resolution helper and preserve unspecified fields
- **AND THEN** Gemini presets may set multiple native values together
- **AND THEN** the reference directs readers who need finer native control to omit `--reasoning-level` and use the native tool's config or environment

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

#### Scenario: Reader Edits a Project Profile or Launch Dossier
- **WHEN** a reader edits a stored launch profile
- **THEN** the `project profile` reference lists `create`, `list`, `get`, `set`, and `remove`, with `set` patching supplied fields and preserving unspecified fields
- **AND THEN** `project profile create --yes` confirms same-lane replacement non-interactively and clears omitted optional fields
- **AND THEN** `internals native-agent launch-dossiers add --yes` confirms same-lane explicit profile replacement non-interactively, and `launch-profiles set` patches that resource
- **AND THEN** replacement stays within the project-profile or explicit-launch-profile lane

#### Scenario: Reader finds project-profile set in CLI reference
- **WHEN** a reader looks up `houmao-mgr project profile`
- **THEN** the CLI reference lists `set` alongside `create`, `list`, `get`, and `remove`
- **AND THEN** the reference explains that `set` mutates stored future launch defaults rather than one running instance

#### Scenario: Reader finds same-lane replacement guidance
- **WHEN** a reader looks up same-name reusable profile creation
- **THEN** the CLI reference explains when to use `--yes` for same-lane replacement
- **AND THEN** it distinguishes replacement from patching through `set`

### Requirement: CLI reference documents managed-header section flags
The manager reference SHALL document managed-header section options on each supported command, with accepted values and defaults.

#### Scenario: Reader Sets or Clears Header Sections
- **WHEN** a reader looks up section flags
- **THEN** the reference covers `--managed-header-section SECTION=STATE` on `project agents launch`, `internals native-agent launch-dossiers add|set`, and `project profile create|set`
- **AND THEN** it covers `--clear-managed-header-section SECTION` and `--clear-managed-header-sections` on `internals native-agent launch-dossiers set` and `project profile set`
- **AND THEN** it lists supported sections, states, and per-section defaults, including disabled defaults for `task-reminder` and `mail-ack` unless explicitly enabled

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
The CLI reference SHALL document scoped mail discovery, processing, completion, and result authority.

#### Scenario: Reader Finds Scoped Mail Commands
- **WHEN** a reader opens the `agents single ... mail` or `agents self mail` reference
- **THEN** the page covers `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`
- **AND THEN** it explains explicit selection and current-session selection inside the owning managed tmux session
- **AND THEN** it describes `resolve-live` structured output with a mailbox binding and optional `gateway.base_url`, without mailbox-specific shell exports

#### Scenario: Reader Processes Mail
- **WHEN** a reader follows the current mailbox lifecycle
- **THEN** the page distinguishes listing, peeking, and reading, and explains that replying or acknowledging marks mail answered while leaving it open
- **AND THEN** it describes archive as the normal completion action and omits `check` and `mark-read` as current lifecycle steps
- **AND THEN** it distinguishes verified execution from non-authoritative TUI submission fallback

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
The CLI reference SHALL document project bootstrap and reserve internal CAO compatibility guidance for the legacy runtime surface.

#### Scenario: Reader Initializes a Project
- **WHEN** a reader looks up `houmao-mgr project init`
- **THEN** the reference omits `--with-compatibility-profiles` as an option
- **AND THEN** it omits `.houmao/agents/compatibility-profiles/` as a supported project-layout directory, bootstrap result, optional init workflow, or operator-authored metadata root

#### Scenario: Reader Encounters CAO Compatibility Notes
- **WHEN** the CLI reference mentions internal CAO compatibility
- **THEN** it keeps the notes within the relevant legacy or compatibility runtime surface and gives operators no instructions to author or pre-create compatibility profile files

#### Scenario: Reader sees no compatibility-profile project-init option
- **WHEN** a reader opens CLI reference coverage for `houmao-mgr project init`
- **THEN** the reference does not list `--with-compatibility-profiles`
- **AND THEN** the reference does not include an example that creates `.houmao/agents/compatibility-profiles/`

#### Scenario: Reader sees no compatibility-profile project layout guidance
- **WHEN** a reader scans CLI reference project-layout notes
- **THEN** the reference does not present `.houmao/agents/compatibility-profiles/` as a maintained local project directory

### Requirement: CLI reference explains component-scoped memo seed policies
The manager reference SHALL explain which memory components each launch-profile memo seed replaces.

#### Scenario: Reader Chooses a Memo Seed Source
- **WHEN** a reader consults the memo seed options
- **THEN** the reference explains that launch-profile sources replace only the managed-memory components they supply and expose no separate policy option
- **AND THEN** `--memo-seed-text` and `--memo-seed-file` replace `houmao-memo.md` and preserve memory pages
- **AND THEN** `--memo-seed-dir` replaces the memo only when `houmao-memo.md` is present and replaces pages only when `pages/` is present
- **AND THEN** the reference distinguishes `--clear-memo-seed` removal of stored configuration from storage of an empty seed

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
The CLI reference SHALL document how to choose a provider chat session at relaunch.

#### Scenario: Reader Chooses a Chat Session at Relaunch
- **WHEN** a reader checks selected-agent chat-session flags
- **THEN** the reference documents both `agents single --agent-id <id> relaunch` and `agents single --agent-name <name> relaunch`, with selector modes `new`, `tool_last_or_new`, and `exact`
- **AND THEN** it explains the provider-native ID requirement for `exact` and the default fresh chat when no selector is supplied
- **AND THEN** it gives current-session active refresh examples through `agents self relaunch` and selected-agent examples using either explicit selector
- **AND THEN** it explains that native headless relaunch applies the selector to the next managed prompt, with continuation available as relaunch behavior only

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
The CLI reference SHALL document registering and using communication-only agents through `houmao-mgr agents external`.

#### Scenario: Reader Registers and Targets an External Agent
- **WHEN** a reader looks up external managed-agent imports
- **THEN** the reference covers `register`, `list`, `get`, `verify`, and `remove`
- **AND THEN** it lists required registration flags `--name`, `--api-base-url`, and `--agent-ref`, gateway expectation flags, and local selector behavior
- **AND THEN** it distinguishes imported communication-only agents from local lifecycle-managed agents and identifies supported normal commands and rejected lifecycle or raw local-control commands

#### Scenario: Reader Exposes a Remote Passive-Server URL
- **WHEN** a reader sets up remote connectivity for an external agent
- **THEN** the reference limits exposure to trusted channels such as SSH forwarding, VPN, Tailscale, or a secured reverse proxy until authenticated remote transport is available

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
The CLI reference SHALL map removed ambiguous `houmao-mgr agents` paths to maintained scoped commands in migration examples.

#### Scenario: Reader Migrates Registry and Explicit Targets
- **WHEN** a reader migrates listing or commands with an explicit agent selector
- **THEN** the examples map `houmao-mgr agents list` to `houmao-mgr agents global list`
- **AND THEN** they map `houmao-mgr agents stop --agent-id <id>` to `houmao-mgr agents single --agent-id <id> stop` and `houmao-mgr agents prompt --agent-name <name>` to `houmao-mgr agents single --agent-name <name> prompt`
- **AND THEN** they map `houmao-mgr agents gateway prompt --agent-id <id>` to `houmao-mgr agents single --agent-id <id> gateway prompt`
- **AND THEN** they show `houmao-mgr agents external register ...` as the direct external-reference path and `houmao-mgr project [--project-dir <dir>] agents launch --profile <name>` for project-profile launches

#### Scenario: Reader Migrates Current-Session Commands
- **WHEN** a reader migrates an adoption or implicit current-session command
- **THEN** the examples map `houmao-mgr agents join --agent-name <name>` to `houmao-mgr agents self join --agent-name <name>`
- **AND THEN** they map `houmao-mgr agents prompt --prompt <text>` to `houmao-mgr agents self prompt --prompt <text>`, `houmao-mgr agents interrupt` to `houmao-mgr agents self interrupt`, and `houmao-mgr agents relaunch` to `houmao-mgr agents self relaunch`
- **AND THEN** they map `houmao-mgr agents gateway prompt` to `houmao-mgr agents self gateway prompt` and `houmao-mgr agents mail read --message-ref <ref>` to `houmao-mgr agents self mail read --message-ref <ref>`

#### Scenario: Reader sees migration table for scoped agents commands
- **WHEN** a reader opens the managed-agent CLI reference after the scoped split
- **THEN** the page includes examples mapping old ambiguous command paths to `agents global`, `agents single`, `agents self`, `agents external`, or `project agents`
- **AND THEN** current-session examples use `agents self` rather than `--current-session`

### Requirement: CLI reference points Kimi automation at unattended prompt mode
The CLI reference SHALL document unattended prompt mode as the managed Kimi automation control.

#### Scenario: Reader Automates Kimi Code
- **WHEN** a reader looks up how to run Kimi without permission dialogs or user questions
- **THEN** the reference points to `launch.prompt_mode: unattended` and the corresponding project and profile flags
- **AND THEN** it omits `--yolo` as a current Houmao launch option
- **AND THEN** any mention of native `--auto` appears only as implementation background or low-level provider behavior

#### Scenario: Reader finds supported Kimi no-question launch control
- **WHEN** a reader looks up how to run a Kimi managed agent automatically
- **THEN** the CLI reference points them to `launch.prompt_mode: unattended` or the matching project/profile prompt-mode CLI controls
- **AND THEN** it does not instruct them to pass `--yolo`

#### Scenario: Reader does not need raw Kimi flags for managed launch
- **WHEN** a reader looks up Kimi project specialist or project profile launch options
- **THEN** the reference describes prompt mode as the managed automation control
- **AND THEN** it does not require raw launch overrides with Kimi `--auto` for ordinary managed unattended launch

### Requirement: CLI reference documents gateway prompt admission policies

The manager reference SHALL document the supported admission policies for both scoped gateway prompt paths.

#### Scenario: Reader Selects a Gateway Admission Policy
- **WHEN** a reader consults `agents single ... gateway prompt` or `agents self gateway prompt`
- **THEN** the reference lists `--admission-policy ready-only|if-no-pending|always` and explains the readiness and pending-input rules for each value
- **AND THEN** it describes conservative handling of `pending_input=unknown`, observational behavior during concurrent submissions before a TUI repaint, and the TUI-only scope of non-default policies
- **AND THEN** it omits `--force` from syntax, option tables, examples, aliases, and migration shims

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
The system-skills CLI reference SHALL document the manager ownership config and the evidence used to evaluate it.

#### Scenario: Reader Inspects System-Skill Ownership
- **WHEN** a reader checks system-skill storage or lifecycle output
- **THEN** the reference identifies `<tool-home>/.houmao/system-skills/<tool>/houmao-skill-config.json` as the sole ownership config, with the exact four top-level fields and four per-skill fields
- **AND THEN** it explains derived pack selection and distinguishes the config `houmao_version`, installed frontmatter version, and content digest
- **AND THEN** lifecycle commands and output examples use config terminology and omit a current receipt path or schema

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
The system-skills CLI reference SHALL document supported pack operations and the manager's ownership and integrity rules.

#### Scenario: Reader Manages Skill Packs
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page covers `list`, `install`, `status`, `doctor`, `upgrade`, and `uninstall`, with repeatable `--pack admin|agent`, tool and home resolution, copy and explicit symlink projection, and plain and root `--print-json` output
- **AND THEN** it explains CLI-default admin selection, managed-default agent selection, complete-pack atomicity, config ownership, integrity states, and rollback
- **AND THEN** it omits `--set` and low-level `--skill` as current manager selectors

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
The reference SHALL document pack projection for Claude, Codex, Copilot, Kimi, and universal targets, including the Kimi 2.1.1 managed-launch floor and absence of an upper version limit.

It SHALL state that Gemini is not a supported system-skill projection target and that provider-native role-prompt files are not system-skill pack members or lifecycle targets. The CLI reference SHALL not document `houmao-auto-system-prompt` or `houmao-mgr agents self system-prompt show` as current surfaces.

#### Scenario: Reader checks Copilot or Gemini support
- **WHEN** a reader compares system-skill targets
- **THEN** Copilot is identified as a pack projection target rather than a launch backend
- **AND THEN** Gemini is not presented as a supported pack target

#### Scenario: Reader checks Kimi role-prompt ownership
- **WHEN** a reader compares Kimi system-skill packs with managed role injection
- **THEN** the reference places native `SYSTEM.md` under brain construction and provenance
- **AND THEN** it exposes no auto-skill install unit or self-prompt retrieval command

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
The system-skills reference SHALL explain standard external installation and its relationship to manager-owned packs.

#### Scenario: Reader Installs Public Skills Externally
- **WHEN** a reader chooses standard Skills CLI or copy-paste installation
- **THEN** the reference links to the dedicated public `houmao-skills` repository and shows its root-level static collection
- **AND THEN** it identifies the unqualified URL as tracking the latest stable release and a matching Houmao Git tag as selecting a specific released version
- **AND THEN** it explains that standard external installation uses explicit sibling selection and no Houmao skill config, while `houmao-mgr system-skills` provides dependency-aware pack lifecycle management

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

### Requirement: The manager reference introduces the operator manual

The `houmao-mgr` reference SHALL list `manual` as a public command group, show how to open the index, a catalog, and a page, and describe its role as offline operating guidance for agents using the manager directly.

#### Scenario: A CLI reference reader finds workflow guidance

- **WHEN** a reader opens the manager CLI reference
- **THEN** the reference shows `houmao-mgr manual`, `houmao-mgr manual start`, and `houmao-mgr manual start first-agent`
- **AND THEN** it directs readers to the packaged manual for workflow decisions and to command help for command syntax
