# Spec Delta

## MODIFIED Requirements

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
- **THEN** the reference explains that `agents self` requires the caller's verified managed runtime
- **AND THEN** `self` operations target the current managed runtime and omit `--agent-id`, `--agent-name`, and `--current-session`
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
- **THEN** the page explains that `agents global` is for zero-or-many local managed-agent operations, `agents single` is for exactly one explicitly selected local managed agent, and `agents self` is for the caller's one verified current managed agent
- **AND THEN** the page explains that `agents external` manages external-agent registry/reference onboarding without local lifecycle authority

#### Scenario: Reader can discover internal brain and credential command families
- **WHEN** a reader looks up `houmao-mgr` command groups in the CLI reference
- **THEN** they find an `internals` section that points to `docs/reference/cli/internals.md`
- **AND THEN** that internals reference documents direct native-agent credentials and brain build commands

#### Scenario: Reader can discover nested managed-agent and project command families
- **WHEN** a reader needs details for `agents global list`, `agents single gateway`, `agents single turn`, `agents single mail`, `agents self relaunch`, `agents self gateway`, `agents self mail`, `agents self turn`, `agents external register`, `project agents`, `project credentials`, `project`, `project mailbox`, or `admin cleanup`
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
- **AND THEN** the reader can see that `agents single mail` uses a group-level explicit selector while `agents self mail` uses the verified current runtime, including supported detached Hermes tools
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

#### Scenario: A Hermes Tool Uses Self Commands Outside Tmux

- **WHEN** a reader looks up `agents self identity` or self mail from a Hermes service or TUI tool
- **THEN** the reference explains that Houmao verifies the tool against its current managed Hermes daemon
- **AND THEN** the reference distinguishes daemon-backed self commands from terminal operations that require a live owning surface

### Requirement: CLI reference documents scoped gateway targeting
The CLI reference SHALL distinguish explicit gateway targets from the current managed session and document the pair-authority override.

#### Scenario: Reader Selects a Gateway Target
- **WHEN** a reader opens `docs/reference/cli/agents-gateway.md` or `docs/reference/cli.md`
- **THEN** the reference shows `houmao-mgr agents single --agent-id <id> gateway ...` and `houmao-mgr agents single --agent-name <name> gateway ...` for explicit targets
- **AND THEN** it defines `--pair-port` as the `agents single` pair-authority override and identifies lower-level `--gateway-port` as controlling the listener
- **AND THEN** the `agents-gateway` page explains explicit selection through `agents single` and verified current-runtime targeting through `agents self`

#### Scenario: CLI reference page lists the tmux-session selector and targeting boundary
- **WHEN** a reader opens `docs/reference/cli/agents-gateway.md`
- **THEN** the option tables and synopsis show `agents single --agent-id <id> gateway ...`, `agents single --agent-name <name> gateway ...`, and `agents self gateway ...`
- **AND THEN** the page explains that `agents single` takes an explicit target and `agents self` uses the verified current runtime, including supported detached Hermes tools

#### Scenario: Top-level CLI guidance explains the port rule for tmux-session targeting
- **WHEN** a reader checks `docs/reference/cli.md` for gateway targeting rules
- **THEN** the page explains that `--pair-port` remains supported with `--agent-id` or `--agent-name`
- **AND THEN** the page explains that `--pair-port` belongs to `agents single` and is not exposed by `agents self`

#### Scenario: Gateway CLI reference distinguishes pair-authority port from gateway listener port
- **WHEN** a reader opens `docs/reference/cli/agents-gateway.md`
- **THEN** the page explains that `--pair-port` selects the Houmao pair authority
- **AND THEN** the page does not imply that `--pair-port` controls the live gateway listener port

### Requirement: CLI reference documents revised scoped `agents ... mail` lifecycle commands

The CLI reference SHALL document scoped mail discovery, processing, completion, and result authority. It SHALL describe lifecycle commands according to the selected mailbox binding's capabilities and the caller's authority. On protected bindings it SHALL direct readers to independently authorized owner archive for successfully processed mail.

#### Scenario: Reader Finds Scoped Mail Commands

- **WHEN** a reader opens the `agents single ... mail` or `agents self mail` reference
- **THEN** the page covers `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive` and identifies the applicable binding and authority for each
- **AND THEN** it explains explicit selection and self selection through the owning managed tmux session or a verified detached Hermes daemon
- **AND THEN** it describes `resolve-live` structured output with a mailbox binding and optional `gateway.base_url`, without mailbox-specific shell exports

#### Scenario: Reader Processes Mail

- **WHEN** a reader follows the current mailbox lifecycle
- **THEN** the page distinguishes listing, peeking, and reading, and explains that replying or acknowledging marks mail answered while leaving it open
- **AND THEN** it describes archive as the completion action through the applicable authorized path and omits `check` and `mark-read` as current lifecycle steps
- **AND THEN** it distinguishes verified execution from non-authoritative TUI submission fallback

#### Scenario: Reader can find archive and move commands

- **WHEN** a reader looks up `houmao-mgr agents single ... mail` or `houmao-mgr agents self mail`
- **THEN** the CLI reference documents `archive` and `move` for bindings and callers that authorize them
- **AND THEN** the reader can tell that successfully processed mail on a protected binding needs independently authorized owner archive through the backend

#### Scenario: Reader understands peek versus read

- **WHEN** a reader looks up mailbox message inspection commands
- **THEN** the CLI reference explains that `peek` leaves read state unchanged
- **AND THEN** it explains that `read` returns the message and marks it read
