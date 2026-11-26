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
- **THEN** the page explains that `agents global` is for zero-or-many local managed-agent operations, `agents single` is for exactly one explicitly selected local managed agent, and `agents self` is for the one local managed agent held by the caller's current tmux session
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

### Requirement: Managed-launch CLI reference documents `--workdir` and source-project pinning
Managed launch references SHALL document `--workdir` as the public runtime working-directory option where supported.

#### Scenario: Reader Sets a Runtime Working Directory
- **WHEN** a reader looks up `houmao-mgr project agents launch`
- **THEN** the reference explains that `--workdir` sets the agent's runtime working directory while preserving source-project resolution
- **AND THEN** if omitted, launch uses the invocation directory
- **AND THEN** for `project agents launch`, the selected easy-project overlay and specialist source remain authoritative even when `--workdir` points elsewhere
- **AND THEN** the launch reference omits `--working-directory` as a supported flag

#### Scenario: Reader sees `--workdir` on the managed launch surfaces
- **WHEN** a reader opens the CLI reference for `houmao-mgr project agents launch`
- **THEN** the documented runtime-cwd flag is `--workdir`
- **AND THEN** the reference does not describe `--working-directory` as the current launch flag

#### Scenario: Reader understands source-project pinning for managed launch
- **WHEN** a reader looks up `houmao-mgr project agents launch --workdir`
- **THEN** the reference explains that `--workdir` changes the launched agent cwd
- **AND THEN** it explains that source overlay/runtime/jobs resolution remains pinned to the launch source project when one exists

#### Scenario: Reader understands easy launch keeps the selected overlay even with external workdir
- **WHEN** a reader looks up `houmao-mgr project agents launch --workdir`
- **THEN** the reference explains that the selected project overlay and specialist source remain authoritative
- **AND THEN** it explains that `--workdir` only changes the launched agent cwd

### Requirement: CLI reference documents agents scoped migration examples
The CLI reference SHALL map removed ambiguous `houmao-mgr agents` paths to maintained scoped commands in migration examples where a replacement exists.

#### Scenario: Reader Migrates Registry and Explicit Targets
- **WHEN** a reader migrates listing or commands with an explicit agent selector
- **THEN** the examples map `houmao-mgr agents list` to `houmao-mgr agents global list`
- **AND THEN** they map `houmao-mgr agents stop --agent-id <id>` to `houmao-mgr agents single --agent-id <id> stop` and `houmao-mgr agents prompt --agent-name <name>` to `houmao-mgr agents single --agent-name <name> prompt`
- **AND THEN** they map `houmao-mgr agents gateway prompt --agent-id <id>` to `houmao-mgr agents single --agent-id <id> gateway prompt`
- **AND THEN** they show `houmao-mgr agents external register ...` as the direct external-reference path and `houmao-mgr project [--project-dir <dir>] agents launch --profile <name>` for project-profile launches

#### Scenario: Reader Migrates Current-Session Commands
- **WHEN** a reader migrates an implicit current-session command
- **THEN** the examples map `houmao-mgr agents prompt --prompt <text>` to `houmao-mgr agents self prompt --prompt <text>`, `houmao-mgr agents interrupt` to `houmao-mgr agents self interrupt`, and `houmao-mgr agents relaunch` to `houmao-mgr agents self relaunch`
- **AND THEN** they map `houmao-mgr agents gateway prompt` to `houmao-mgr agents self gateway prompt` and `houmao-mgr agents mail read --message-ref <ref>` to `houmao-mgr agents self mail read --message-ref <ref>`

#### Scenario: Reader sees migration table for scoped agents commands
- **WHEN** a reader opens the managed-agent CLI reference after the scoped split
- **THEN** the page includes examples mapping old ambiguous command paths to `agents global`, `agents single`, `agents self`, `agents external`, or `project agents`
- **AND THEN** current-session examples use `agents self` rather than `--current-session`

#### Scenario: Reader Upgrades With a Joined Session
- **WHEN** a reader previously used `houmao-mgr agents self join`
- **THEN** the reference identifies TUI and headless adoption as retired and points to managed project launch for a new agent
- **AND THEN** it advises winding down the existing Houmao management and its gateway with the release that owns the joined session before upgrading
- **AND THEN** it explains that the upgrade preserves the manually started process and its files

### Requirement: Documentation preserves the diagnostic boundary
The reference SHALL state that `houmao_version` equality is checked only by doctor. It SHALL NOT claim that install, status, upgrade, managed launch, runtime authorization, or skill invocation rejects mismatched versions.

Doctor documentation SHALL describe it as read only and SHALL direct repairs to explicit install or upgrade commands rather than implying automatic mutation.

#### Scenario: Doctor reports an old release
- **WHEN** a reader receives a version mismatch
- **THEN** the reference explains that the result is diagnostic
- **AND THEN** it offers an explicit upgrade or reinstall as a separate operator decision

### Requirement: CLI reference documents public roles and actor entrypoints
The reference SHALL list all six standalone roots and SHALL distinguish the three actor-facing roots from shared routines and the two direct loop roots.

It SHALL explain the welcome mutation boundary, admin explicit-target posture, agent self-identity verification, explicit shared and loop activation, and the absence of an agent welcome.

#### Scenario: Reader chooses between admin and agent entrypoints
- **WHEN** a reader needs to perform an operation from a human-operated home or managed home
- **THEN** the reference identifies the correct actor entrypoint and actor semantics
- **AND THEN** it does not suggest that prompt wording can switch the active actor
