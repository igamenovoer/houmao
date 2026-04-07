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

The comparison table SHALL list the correct default ports: 9891 for `houmao-passive-server` and 9889 for `houmao-server`.

#### Scenario: Reader understands passive vs active server difference

- **WHEN** a reader compares passive-server and houmao-server pages
- **THEN** they understand that passive-server is stateless/registry-driven with no CAO dependency, while houmao-server is the CAO-compatible path

#### Scenario: Comparison table shows correct default ports

- **WHEN** a reader checks the comparison table in houmao-passive-server.md
- **THEN** the default port for `houmao-passive-server` is listed as 9891
- **AND THEN** the default port for `houmao-server` is listed as 9889

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

### Requirement: CLI reference distinguishes Claude credential inputs from the optional state template
The `houmao-mgr` CLI reference SHALL describe Claude credential-providing inputs separately from the optional Claude state-template input on both:

- `project agents tools claude auth ...`
- `project easy specialist create --tool claude`

When the reference documents Claude-specific flags, it SHALL make clear that `claude_state.template.json` or `--claude-state-template-file` is optional runtime bootstrap state and not itself a credential-providing method.

#### Scenario: Reader sees the Claude state template documented separately in the CLI reference
- **WHEN** a reader looks up the Claude project-auth or easy-specialist options in `docs/reference/cli/houmao-mgr.md`
- **THEN** the page distinguishes credential-providing Claude inputs from the optional state-template input
- **AND THEN** it does not present the state-template input as one of the ways to authenticate Claude

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

### Requirement: System-skills reference documents the renamed specialist-management skill
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe the current project-easy packaged skill as `houmao-manage-specialist`.

That page SHALL describe the packaged skill as the Houmao-owned specialist-management entry point for `project easy specialist create|list|get|remove` plus specialist-scoped `project easy instance launch|stop`.

The page SHALL describe the top-level packaged skill page as an index/router and SHALL state that further agent management after those specialist-scoped runtime actions goes to `houmao-manage-agent-instance`.

The page SHALL NOT continue to describe `houmao-create-specialist` as the active packaged project-easy skill.

#### Scenario: Reader sees the renamed packaged skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-manage-specialist` as the packaged project-easy skill
- **AND THEN** it describes that skill as covering `create`, `list`, `get`, `remove`, `launch`, and `stop`

#### Scenario: Reader does not see the stale create-only packaged skill name
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page does not present `houmao-create-specialist` as the current packaged specialist-management skill
- **AND THEN** it explains that follow-up live-agent management after specialist launch or stop belongs to `houmao-manage-agent-instance`

### Requirement: System-skills reference documents the packaged agent-instance lifecycle skill and its boundary
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-manage-agent-instance` as a packaged Houmao-owned system skill.

That page SHALL describe the packaged skill as the Houmao-owned entry point for managed-agent instance lifecycle guidance across:

- `agents launch`
- `project easy instance launch`
- `agents join`
- `agents list`
- `agents stop`
- `agents cleanup session|logs`

That page SHALL explain that `houmao-manage-agent-instance` remains the canonical lifecycle skill while `houmao-agent-messaging` becomes the canonical ordinary communication/control and mailbox-routing skill for already-running managed agents, `houmao-agent-email-comms` remains the ordinary mailbox operations skill, and `houmao-agent-gateway` becomes the canonical gateway-specific skill.

That page SHALL explain that mailbox surfaces, prompting, mailbox routing, ordinary mailbox operations, gateway-only services, reset-context guidance, and specialist CRUD remain outside the packaged `houmao-manage-agent-instance` skill scope.

That page SHALL describe the CLI-default system-skill install selection as including the packaged specialist-management, credential-management, agent-definition, agent-instance, agent-messaging, and agent-gateway skills.

That page SHALL explain that managed launch and managed join auto-install the messaging and gateway skills but do not auto-install the separate lifecycle-only `houmao-manage-agent-instance` skill.

#### Scenario: Reader sees the packaged lifecycle skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-manage-agent-instance` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering managed-agent instance lifecycle rather than gateway or messaging guidance

#### Scenario: Reader sees the boundary between lifecycle, messaging, and gateway skills
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page distinguishes `houmao-manage-agent-instance` from `houmao-agent-messaging` and `houmao-agent-gateway`
- **AND THEN** it explains that prompting and mailbox routing belong to messaging, ordinary mailbox operations belong to the mailbox skill family, and gateway lifecycle, discovery, and gateway-only services belong to the gateway skill

#### Scenario: Reader sees the updated default install behavior
- **WHEN** a reader checks the install-selection behavior in `docs/reference/cli/system-skills.md`
- **THEN** the page explains that CLI-default installation includes lifecycle, messaging, and gateway skills
- **AND THEN** it explains that managed launch and managed join auto-install the messaging and gateway skills without auto-installing the lifecycle-only skill

### Requirement: System-skills reference documents the packaged agent-messaging skill and its communication-path boundary
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-agent-messaging` as a packaged Houmao-owned system skill.

That page SHALL describe the packaged skill as the Houmao-owned entry point for communicating with already-running managed agents across:

- `agents prompt`
- `agents interrupt`
- `agents gateway prompt|interrupt`
- `agents gateway send-keys`
- `agents gateway tui state|history|note-prompt`
- `agents mail resolve-live`

That page SHALL explain that the packaged skill routes by communication intent and not by one hardcoded transport path.

That page SHALL explain that ordinary prompting should prefer the managed-agent seam, that mailbox discovery and mailbox routing begin from `agents mail resolve-live`, and that ordinary mailbox operations belong to `houmao-agent-email-comms` while notifier-round mailbox workflow belongs to `houmao-process-emails-via-gateway`.

That page SHALL explain that gateway lifecycle, current-session discovery, notifier control, and wakeup guidance belong to `houmao-agent-gateway`.

That page SHALL explain that transport-specific mailbox behavior remains in the mailbox skill family rather than in `houmao-agent-messaging`.

#### Scenario: Reader sees the packaged messaging skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-agent-messaging` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering managed-agent communication and mailbox routing rather than lifecycle or gateway-control-plane ownership

#### Scenario: Reader sees the communication-path boundary
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page explains the distinction between synchronous prompt turns, queued gateway requests, raw `send-keys`, mailbox handoff, ordinary mailbox operations in the mailbox skills, and the separate gateway skill's lifecycle or reminder services
- **AND THEN** it does not imply that those paths are interchangeable shortcuts

### Requirement: Managed-launch CLI reference documents `--workdir` and source-project pinning
The CLI reference pages that document `houmao-mgr agents launch`, `houmao-mgr agents join`, and `houmao-mgr project easy instance launch` SHALL describe `--workdir` as the current public runtime-cwd flag.

That coverage SHALL describe the default behavior as using the invocation cwd for launch-time runtime workdir and tmux-pane current path for join-time adopted workdir when `--workdir` is omitted.

That coverage SHALL explain that `--workdir` sets the launched or adopted agent cwd and does not retarget launch source project resolution.

For `agents launch`, that coverage SHALL explain that when launch originates from a Houmao project, source overlay selection and overlay-local runtime/jobs roots remain pinned to that source project rather than following `--workdir`.

For `project easy instance launch`, that coverage SHALL explain that the selected easy-project overlay and specialist source remain authoritative even when `--workdir` points somewhere else.

That coverage SHALL NOT present `--working-directory` as part of the current public CLI for `agents join`.

#### Scenario: Reader sees `--workdir` on the managed launch surfaces
- **WHEN** a reader opens the CLI reference for `houmao-mgr agents launch`, `houmao-mgr agents join`, or `houmao-mgr project easy instance launch`
- **THEN** the documented runtime-cwd flag is `--workdir`
- **AND THEN** the reference does not describe `--working-directory` as the current join flag

#### Scenario: Reader understands source-project pinning for managed launch
- **WHEN** a reader looks up `houmao-mgr agents launch --workdir`
- **THEN** the reference explains that `--workdir` changes the launched agent cwd
- **AND THEN** it explains that source overlay/runtime/jobs resolution remains pinned to the launch source project when one exists

#### Scenario: Reader understands easy launch keeps the selected overlay even with external workdir
- **WHEN** a reader looks up `houmao-mgr project easy instance launch --workdir`
- **THEN** the reference explains that the selected project overlay and specialist source remain authoritative
- **AND THEN** it explains that `--workdir` only changes the launched agent cwd

### Requirement: System-skills reference documents effective-home resolution and omitted-selection defaults
The CLI reference pages `docs/reference/cli/system-skills.md` and `docs/reference/cli/houmao-mgr.md` SHALL describe `houmao-mgr system-skills install` and `houmao-mgr system-skills status` as requiring `--tool` and accepting an optional `--home`.

That coverage SHALL document effective-home resolution with this precedence:

1. explicit `--home`
2. tool-native home env var
3. project-scoped default home

That coverage SHALL document the tool-native home env vars:

- Claude: `CLAUDE_CONFIG_DIR`
- Codex: `CODEX_HOME`
- Gemini: `GEMINI_CLI_HOME`

That coverage SHALL document the project-scoped default homes:

- Claude: `<cwd>/.claude`
- Codex: `<cwd>/.codex`
- Gemini: `<cwd>`

That coverage SHALL state that omitting both `--set` and `--skill` resolves the packaged CLI-default set list.

That coverage SHALL NOT present `--default` as part of the current public `system-skills install` surface.

That coverage SHALL explain that the default Gemini home root is `<cwd>`, which yields Houmao-owned skill projection under `<cwd>/.gemini/skills/`.

#### Scenario: Reader sees the effective-home precedence in the system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page documents `--home` as optional for `install` and `status`
- **AND THEN** it explains the precedence order of explicit `--home`, tool-native env redirection, and project-scoped default home

#### Scenario: Reader sees the Gemini project-root default home clearly
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page explains that Gemini defaults to `<cwd>` rather than `<cwd>/.gemini`
- **AND THEN** it explains that omitted-home Gemini installs project skills under `<cwd>/.gemini/skills/`

#### Scenario: Reader does not see the removed default flag in current reference docs
- **WHEN** a reader opens `docs/reference/cli/system-skills.md` or `docs/reference/cli/houmao-mgr.md`
- **THEN** the current command shape does not present `--default` as a supported `system-skills install` option
- **AND THEN** the reference explains that omitting both `--set` and `--skill` is the supported way to request CLI-default selection

### Requirement: CLI reference documents tmux-session targeting for `agents gateway`
The CLI reference pages `docs/reference/cli/agents-gateway.md` and `docs/reference/cli.md` SHALL document `--target-tmux-session <tmux-session-name>` as an explicit selector for single-target `houmao-mgr agents gateway ...` commands.

That documentation SHALL describe the selector as mutually exclusive with `--agent-id`, `--agent-name`, and `--current-session`. It SHALL also document `--pair-port` as the pair-authority override name for explicit `--agent-id` and `--agent-name` targeting.

The docs SHALL state that `--pair-port` is unsupported with tmux-session targeting because the command follows the addressed session's manifest-declared authority after local resolution. They SHALL also explain that `--pair-port` is not the same thing as a gateway listener port override such as lower-level `--gateway-port`.

The `agents-gateway` reference SHALL distinguish outside-tmux `--target-tmux-session` targeting from inside-tmux current-session targeting and SHALL explain when each mode is appropriate.

#### Scenario: CLI reference page lists the tmux-session selector and targeting boundary
- **WHEN** a reader opens `docs/reference/cli/agents-gateway.md`
- **THEN** the option tables include `--target-tmux-session`
- **AND THEN** the page explains that `--target-tmux-session` is for explicit outside-tmux targeting while `--current-session` is for the owning tmux session

#### Scenario: Top-level CLI guidance explains the port rule for tmux-session targeting
- **WHEN** a reader checks `docs/reference/cli.md` for gateway targeting rules
- **THEN** the page explains that `--pair-port` remains supported with `--agent-id` or `--agent-name`
- **AND THEN** the page explains that `--pair-port` is rejected with `--target-tmux-session` because tmux-session targeting follows manifest-declared authority

#### Scenario: Gateway CLI reference distinguishes pair-authority port from gateway listener port
- **WHEN** a reader opens `docs/reference/cli/agents-gateway.md`
- **THEN** the page explains that `--pair-port` selects the Houmao pair authority
- **AND THEN** the page does not imply that `--pair-port` controls the live gateway listener port

### Requirement: CLI reference documents the top-level project agents presets surface

The `houmao-mgr` CLI reference SHALL document the canonical low-level recipe surface and the compatibility preset alias as one resource family.

At minimum, that coverage SHALL:

- list `project agents recipes list|get|add|set|remove` as the canonical low-level source-recipe administration surface,
- list `project agents presets list|get|add|set|remove` as the compatibility alias for the same named recipe resources,
- describe recipe files as living under `agents/presets/<name>.yaml`,
- list `project agents launch-profiles list|get|add|set|remove` as the canonical low-level explicit-launch-profile administration surface,
- describe explicit launch-profile files as living under `agents/launch-profiles/<name>.yaml`,
- explain that `project agents roles` is prompt-only role management,
- state that `project agents roles scaffold` is not part of the supported low-level CLI.

The CLI reference SHALL extend the `houmao-mgr project` command-shape tree so that `project agents` lists `roles`, `recipes`, `presets`, `launch-profiles`, and `tools <tool>`, and so that `project easy` lists `specialist`, `profile`, and `instance`.

The CLI reference SHALL document `houmao-mgr project easy profile create|list|get|remove` as the easy-lane reusable specialist-backed birth-time launch-profile administration surface, and SHALL document `houmao-mgr project easy instance launch --profile <name>` as the easy-profile-backed instance launch path with the `--profile`/`--specialist` mutual exclusion rule.

The CLI reference SHALL document `houmao-mgr agents launch --launch-profile <name>` as the explicit-launch-profile-backed managed launch path, and SHALL document the `--launch-profile`/`--agents` mutual exclusion rule. The reference SHALL state that the effective provider defaults from the resolved profile source when that source already determines one tool family, and that supplying `--provider` together with `--launch-profile` is accepted only when it matches the resolved source.

The CLI reference SHALL describe the launch-time effective-input precedence as: source recipe defaults → launch-profile defaults → direct CLI overrides, and SHALL state that direct CLI overrides such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir` do not rewrite the stored launch profile.

The CLI reference SHALL state that the launch-profile-backed launch resolution applies through the same shared model whether the operator started from an easy profile through `project easy instance launch --profile` or from an explicit launch profile through `agents launch --launch-profile`.

The CLI reference SHALL link to `docs/getting-started/launch-profiles.md` for the shared conceptual model rather than restating that model on the CLI reference page itself.

#### Scenario: Reader sees canonical recipes and the compatibility preset alias in the project agents reference

- **WHEN** a reader looks up `houmao-mgr project agents` in the CLI reference
- **THEN** the page documents `project agents recipes list|get|add|set|remove`
- **AND THEN** the page documents `project agents presets list|get|add|set|remove` as the compatibility alias for the same files under `agents/presets/<name>.yaml`
- **AND THEN** it does not present `roles presets ...` or `roles scaffold` as the supported surface

#### Scenario: Reader sees the explicit launch-profile surface in the project agents reference

- **WHEN** a reader looks up `houmao-mgr project agents` in the CLI reference
- **THEN** the page documents `project agents launch-profiles list|get|add|set|remove` as the canonical low-level explicit-launch-profile surface
- **AND THEN** the page describes those files as living under `agents/launch-profiles/<name>.yaml`

#### Scenario: Reader sees the easy profile surface in the project easy reference

- **WHEN** a reader looks up `houmao-mgr project easy` in the CLI reference
- **THEN** the page documents `project easy profile create|list|get|remove`
- **AND THEN** the page documents `project easy instance launch --profile <name>`
- **AND THEN** the page documents the `--profile`/`--specialist` mutual exclusion rule on `instance launch`

#### Scenario: Reader sees `agents launch --launch-profile` documented with its precedence rules

- **WHEN** a reader looks up `houmao-mgr agents launch` in the CLI reference
- **THEN** the page documents `--launch-profile <name>` as the explicit-launch-profile-backed launch input
- **AND THEN** the page documents the `--launch-profile`/`--agents` mutual exclusion rule
- **AND THEN** the page documents the precedence order as recipe defaults, then launch-profile defaults, then direct CLI overrides
- **AND THEN** the page states that direct CLI overrides such as `--agent-name`, `--auth`, and `--workdir` do not rewrite the stored launch profile

#### Scenario: Reader sees the project command-shape tree extended for the new subtrees

- **WHEN** a reader checks the `Command shape` overview in the CLI reference
- **THEN** `project agents` lists `roles`, `recipes`, `presets`, `launch-profiles`, and `tools <tool>`
- **AND THEN** `project easy` lists `specialist`, `profile`, and `instance`

### Requirement: Easy-specialist launch options table includes mail-account-dir

The `docs/getting-started/easy-specialists.md` options table for `project easy instance launch` SHALL include the `--mail-account-dir` option with its default (None) and its description as an optional private filesystem mailbox directory to symlink into the shared root.

#### Scenario: Reader finds mail-account-dir in the instance launch table

- **WHEN** a reader checks the options table for `project easy instance launch` in `easy-specialists.md`
- **THEN** the table includes a row for `--mail-account-dir` with default `None`
- **AND THEN** the description explains it is an optional private filesystem mailbox directory to symlink into the shared root

### Requirement: System-skills reference documents the packaged agent-gateway skill and its gateway-service boundary
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-agent-gateway` as a packaged Houmao-owned system skill.

That page SHALL describe the packaged skill as the Houmao-owned entry point for gateway-focused work across:

- `agents gateway attach|detach|status`
- `agents gateway mail-notifier status|enable|disable`
- current-session versus explicit managed-agent gateway targeting
- direct live gateway route families such as `/v1/status`, `/v1/wakeups`, and `/v1/mail-notifier` when the exact live `gateway.base_url` is already known from supported discovery

That page SHALL explain that the packaged gateway skill prefers `houmao-mgr agents gateway ...` and managed-agent `/houmao/agents/{agent_ref}/gateway...` routes when those higher-level surfaces exist.

That page SHALL explain that wakeups are direct live-gateway HTTP in the current implementation and remain in-memory state that does not survive gateway restart.

That page SHALL explain that ordinary prompt/mail follow-up remains in `houmao-agent-messaging` and the mailbox skill family rather than in `houmao-agent-gateway`.

#### Scenario: Reader sees the packaged gateway skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-agent-gateway` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering gateway lifecycle, gateway discovery, and gateway-only reminder/control surfaces

#### Scenario: Reader sees the wakeup boundary clearly
- **WHEN** a reader opens the packaged gateway-skill section of `docs/reference/cli/system-skills.md`
- **THEN** the page explains that current wakeup control uses direct live gateway `/v1/wakeups` routes
- **AND THEN** it does not imply that wakeups are durable across gateway restart or already projected through `houmao-mgr agents gateway ...`

### Requirement: CLI reference documents managed-header controls on launch and launch-profile surfaces
The `houmao-mgr` CLI reference SHALL document the managed-header flags on the relevant launch and launch-profile commands.

At minimum, that coverage SHALL include:
- `houmao-mgr agents launch --managed-header|--no-managed-header`
- `houmao-mgr project agents launch-profiles add --managed-header|--no-managed-header`
- `houmao-mgr project agents launch-profiles set --managed-header|--no-managed-header|--clear-managed-header`
- `houmao-mgr project easy profile create --managed-header|--no-managed-header`
- `houmao-mgr project easy instance launch --managed-header|--no-managed-header`

The CLI reference SHALL explain that:
- launch-time managed-header flags are mutually exclusive,
- direct launch override wins over stored launch-profile policy,
- clearing stored launch-profile policy returns that field to inherit behavior,
- omitted launch-time and launch-profile policy falls back to the default enabled managed-header behavior.

#### Scenario: Reader can find the managed-header flags in the CLI reference
- **WHEN** a reader looks up `houmao-mgr agents launch`, `project agents launch-profiles`, or the relevant `project easy` commands
- **THEN** the CLI reference documents the managed-header flags and their meaning
- **AND THEN** the page does not require the reader to infer the new behavior from source code or changelog text

#### Scenario: Reader understands precedence and clear semantics from the CLI reference
- **WHEN** a reader checks the option notes for managed-header controls
- **THEN** the CLI reference explains direct-override precedence over stored profile policy
- **AND THEN** it explains that `--clear-managed-header` returns the stored profile field to inherit behavior

