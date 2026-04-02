## Purpose
Define expected runtime behaviors for brain launch session orchestration,
CLI session control, backend continuity, and CAO/tmux integrations.
## Requirements
### Requirement: Launch plan composition from `{brain, role}`
The system SHALL compose a tool launch plan from a resolved brain manifest and a role package.

#### Scenario: Compose a launch plan
- **WHEN** a developer provides a resolved brain manifest (tool, home path, launch contract) and a role identifier
- **THEN** the system produces a launch plan that includes the tool executable/args, the tool home selector (env var/flag), and the role injection strategy

### Requirement: Non-CAO interactive sessions with backend-defined continuity
The system SHALL support a non-CAO interactive mode where callers can send multiple prompts across one logical session, even when backend process lifecycle differs by tool.

#### Scenario: Interactive session processes multiple turns
- **WHEN** a developer starts a non-CAO interactive session for a supported tool backend
- **THEN** they can send multiple prompts over time and receive corresponding replies within one logical session
- **AND THEN** backends without a stable long-lived programmatic protocol MAY restart the CLI process between turns if continuity is preserved via persisted resume identity (for example `session_id`)

### Requirement: Headless Claude/Gemini/Codex sessions are tmux-backed and inspectable
The runtime SHALL publish `HOUMAO_MANIFEST_PATH=<absolute manifest path>` into the tmux session environment so that name-based `--agent-identity` resolution can locate the persisted session manifest.

#### Scenario: Started headless tmux session publishes the HOUMAO manifest pointer
- **WHEN** the runtime starts a tmux-backed headless session
- **THEN** the tmux session environment contains `HOUMAO_MANIFEST_PATH` pointing at the persisted session manifest JSON

### Requirement: Codex headless backend uses `codex exec --json` and resumes via thread id
For Codex, the runtime SHALL support a non-CAO interactive backend using repeated Codex CLI invocations that emit machine-readable JSONL output and provide a stable resume identifier.

The runtime SHALL:
- start a new Codex headless session using `codex exec --json`, and
- persist the returned Codex thread/session identifier, and
- resume subsequent turns using `codex exec --json resume <thread_id>`.

#### Scenario: First Codex headless turn persists a resume identifier
- **WHEN** a developer starts a Codex headless session and sends a first prompt
- **THEN** the runtime invokes Codex headless execution using `codex exec --json`
- **AND THEN** the runtime extracts the Codex thread/session identifier from machine-readable output and persists it in the session manifest

#### Scenario: Subsequent Codex headless turns use `codex exec --json resume <thread_id>`
- **WHEN** a developer sends a follow-up prompt to a resumed Codex headless session
- **AND WHEN** the session manifest contains a persisted Codex thread/session identifier
- **THEN** the runtime invokes Codex using `codex exec --json resume <thread_id>`
- **AND THEN** the reply is produced within the same logical Codex session context

### Requirement: Default non-CAO Codex backend is resumable headless CLI turns
When tool selection is `codex` and the caller does not explicitly request CAO, the runtime SHALL default to a resumable headless CLI backend rather than a long-lived server mode.

#### Scenario: Starting Codex without backend override selects headless backend
- **WHEN** a developer starts a Codex session without specifying a backend override
- **AND WHEN** the session is not CAO-backed
- **THEN** the runtime selects the Codex headless CLI backend as the default execution mode

### Requirement: Headless stop preserves tmux by default with explicit cleanup path
For tmux-backed headless sessions, `stop-session` SHALL preserve the tmux session by default for inspectability/debugging.

The runtime SHALL provide an explicit force-cleanup path that terminates the tmux session for automation/CI workflows.

#### Scenario: Default stop keeps tmux session
- **WHEN** a developer stops a tmux-backed headless session using default stop behavior
- **THEN** runtime session control is stopped
- **AND THEN** the tmux session remains available for inspection/attach

#### Scenario: Explicit force-cleanup stop removes tmux session
- **WHEN** a developer or automation pipeline invokes stop with explicit force-cleanup
- **THEN** runtime stops session control
- **AND THEN** the corresponding tmux session is terminated

### Requirement: Deprecated standalone build and start entrypoints use config-first `.houmao` agent-definition resolution
Deprecated standalone build/start entrypoints SHALL resolve agent-definition roots with this precedence:
1. explicit CLI `--agent-def-dir`
2. `HOUMAO_AGENT_DEF_DIR`
3. nearest ancestor `.houmao/houmao-config.toml`
4. default `<cwd>/.houmao/agents`

#### Scenario: Env-var override wins for deprecated standalone build/start entrypoints
- **WHEN** `HOUMAO_AGENT_DEF_DIR=/tmp/agents`
- **AND WHEN** no explicit CLI `--agent-def-dir` is supplied
- **THEN** the effective agent-definition root is `/tmp/agents`

### Requirement: `codex_app_server` remains explicit opt-in during one deprecation window
During this change's deprecation window, the runtime SHALL:
- use `codex_headless` as the default non-CAO Codex backend, and
- continue honoring explicit `codex_app_server` backend override requests.

Removal of `codex_app_server` is deferred to a follow-up change after documented sunset criteria are met.

#### Scenario: Explicit legacy override remains functional during deprecation window
- **WHEN** a developer explicitly requests `backend=codex_app_server`
- **THEN** the runtime starts Codex using `codex_app_server` behavior during the deprecation window
- **AND THEN** this does not change the default backend selection for unspecified non-CAO Codex sessions

### Requirement: Claude headless backend via `claude -p` + `--resume`
For Claude, the system SHALL support a non-CAO interactive backend using repeated headless CLI invocations with machine-readable output and session resume.

#### Scenario: Start Claude headless session and continue with `session_id`
- **WHEN** a developer starts a Claude session in headless mode and sends a first prompt using a constructed brain home
- **THEN** the system captures the returned Claude `session_id` and persists it in the session manifest
- **AND THEN** the system sends subsequent prompts with `--resume <session_id>` and receives replies in the same logical session

### Requirement: Gemini headless backend via `gemini -p` + `--resume`
For Gemini, the system SHALL support a non-CAO interactive backend using repeated headless CLI invocations with machine-readable output and session resume.

#### Scenario: Start Gemini headless session and continue with `session_id`
- **WHEN** a developer starts a Gemini session in headless mode and sends a first prompt using a constructed brain home
- **THEN** the system captures the returned Gemini `session_id` and persists it in the session manifest
- **AND THEN** the system sends subsequent prompts with `--resume <session_id>` and receives replies in the same logical session
- **AND THEN** resume uses the same working directory/project context recorded in the session manifest

### Requirement: Role prompt applied before first user turn
The system SHALL apply the selected role package as the initial tool instructions before the first user prompt is processed when the role package contains prompt content.

When the selected role package intentionally contains an empty system prompt, launch SHALL remain valid and the runtime SHALL treat that role as having no startup prompt content.

#### Scenario: Role is injected on session start
- **WHEN** a session is started with role `R` whose `system-prompt.md` contains prompt content
- **THEN** the tool is initialized with `R` as initial instructions using a tool-supported mechanism when available
- **AND THEN** if the tool lacks a native mechanism, the system sends `R` as a clearly delimited bootstrap message before the first user prompt

#### Scenario: Empty role prompt skips startup injection
- **WHEN** a session is started with role `R` whose `system-prompt.md` is intentionally empty
- **THEN** session startup remains valid
- **AND THEN** the runtime does not pass empty native developer instructions, empty appended system-prompt arguments, or an empty bootstrap message to the provider

#### Scenario: Role bootstrap is not replayed on resumed headless turns
- **WHEN** a headless session has already applied role `R` during bootstrap
- **AND WHEN** a developer sends a follow-up prompt using the persisted resume identity
- **THEN** the system does not replay role bootstrap content unless the caller explicitly starts a new session

### Requirement: Optional CAO backend via REST boundary
The system SHALL optionally support CAO-compatible session control through a REST boundary without requiring the core runtime to depend on CAO internals.

For supported operator workflows after this change, that CAO-compatible control SHALL be reached through the Houmao-owned pair authority rather than through public `houmao-cli` flows that create or control standalone `cao_rest` sessions.

The runtime MAY retain internal CAO-compatible adapter code for parity, debugging, or transition purposes, but public runtime-management CLI entrypoints that would create or control standalone CAO-backed sessions SHALL fail fast with explicit migration guidance to `houmao-server` and `houmao-mgr`.

That public deprecation guard SHALL reject deprecated `backend="cao_rest"` operator selections at the CLI entrypoint layer before standalone runtime-session construction begins.

For supported loopback compatibility authorities (`http://localhost:<port>`,
`http://127.0.0.1:<port>` with explicit ports), runtime-owned HTTP communication SHALL bypass ambient proxy environment variables by default by ensuring loopback entries exist in `NO_PROXY` and `no_proxy`.

When `HOUMAO_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY` or `no_proxy` and will respect caller-provided values.

When the runtime uses a pair-backed compatibility authority internally, it SHALL pass the resolved working directory through to that authority as launch input and SHALL NOT impose a repo-owned validation rule that requires the workdir to live under the user home tree, the tool home, or a deprecated launcher home.

#### Scenario: Deprecated raw CAO-backed runtime start fails with migration guidance
- **WHEN** a developer invokes `houmao-cli` in a way that would start a standalone `cao_rest` session
- **THEN** the command exits non-zero with explicit guidance to use `houmao-server` and `houmao-mgr`
- **AND THEN** it does not create a new standalone CAO-backed session as a supported operator workflow

#### Scenario: CLI rejects deprecated backend selection before runtime construction
- **WHEN** a developer runs `houmao-cli start-session --backend cao_rest ...`
- **THEN** the CLI rejects that request with migration guidance before constructing a standalone `CaoRestSession`
- **AND THEN** internal parity or debugging code paths are not implied to be removed by that public CLI rejection

#### Scenario: Deprecated raw CAO-backed runtime control fails with migration guidance
- **WHEN** a developer invokes a runtime-management CLI command that would send input to, interrupt, or stop a standalone `cao_rest` session through the deprecated public path
- **THEN** the command exits non-zero with explicit guidance to move to the supported pair
- **AND THEN** it does not silently fall back to mutating standalone CAO state behind the user's back

#### Scenario: Loopback pair-compatible communication bypasses caller proxy env by default
- **WHEN** a developer starts or resumes a pair-backed compatibility session using loopback authority `http://127.0.0.1:9990`
- **AND WHEN** caller environment includes `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`
- **THEN** runtime-owned HTTP communication to that loopback compatibility authority bypasses those proxy endpoints by default

### Requirement: Mailbox enablement is resolved before session start and persisted for resume
The runtime SHALL enable mailbox support through declarative recipe configuration and MAY allow explicit `start-session` CLI overrides for transport-specific ad hoc sessions.

The runtime SHALL resolve one effective mailbox configuration before building the launch plan, SHALL persist that resolved mailbox configuration in the session manifest, and SHALL restore it when resuming the session.

The resolved mailbox configuration SHALL preserve transport-specific binding data appropriate to the selected transport, and it SHALL use transport-specific binding shapes rather than one filesystem-shaped mailbox record with optional extras.

For filesystem sessions, that resolved configuration MAY include a filesystem mailbox root and registration-derived filesystem bindings.

For `stalwart` sessions, that resolved configuration SHALL include the mailbox transport identity, mailbox principal identity, mailbox address, and a transport-safe JMAP endpoint plus secret-free `credential_ref` metadata needed to restore the same mailbox binding and construct the same gateway mailbox adapter later without persisting inline secrets in the manifest payload.

#### Scenario: Recipe configuration enables filesystem mailbox support
- **WHEN** a developer starts an agent session whose resolved recipe enables filesystem mailbox support
- **THEN** the runtime resolves that mailbox configuration before building the launch plan
- **AND THEN** the resolved session uses that mailbox transport and principal binding for subsequent mailbox-aware runtime work

#### Scenario: Recipe configuration enables Stalwart mailbox support
- **WHEN** a developer starts an agent session whose resolved recipe enables `stalwart` mailbox support
- **THEN** the runtime resolves that mailbox configuration before building the launch plan
- **AND THEN** the resolved session uses that mailbox transport and principal binding for subsequent mailbox-aware runtime work

#### Scenario: Start session CLI overrides mailbox transport-specific settings
- **WHEN** a developer starts an agent session with explicit mailbox CLI overrides such as transport or transport-specific mailbox location or endpoint settings
- **THEN** the runtime applies those overrides to the effective mailbox configuration for that session
- **AND THEN** the resulting session manifest records the overridden mailbox transport and transport-safe mailbox bindings rather than forcing resume to re-derive them from recipe defaults

#### Scenario: Resume restores persisted filesystem mailbox bindings
- **WHEN** a developer resumes a previously started mailbox-enabled session
- **THEN** the runtime restores the mailbox transport, principal binding, and transport-specific mailbox bindings from the persisted session manifest
- **AND THEN** runtime mailbox commands for that resumed session preserve the same sender principal and mailbox root unless an explicit refresh changes them later

#### Scenario: Resume restores persisted Stalwart mailbox bindings
- **WHEN** a developer resumes a previously started `stalwart` mailbox-enabled session
- **THEN** the runtime restores the mailbox transport, principal binding, mailbox address, and transport-safe mailbox binding metadata from the persisted session manifest
- **AND THEN** runtime mailbox commands for that resumed session preserve the same sender principal and Stalwart mailbox identity unless an explicit refresh changes them later

### Requirement: Filesystem mailbox startup can target either the shared-root mailbox path or an explicit private mailbox directory
When no explicit filesystem mailbox content root override is supplied and `HOUMAO_GLOBAL_MAILBOX_DIR` is set to an absolute directory path, the runtime SHALL derive the effective Houmao mailbox root from that env-var override before persisting or resolving filesystem mailbox state for that session.

#### Scenario: Mailbox env override relocates the shared-root mailbox path
- **WHEN** `HOUMAO_GLOBAL_MAILBOX_DIR` is set to `/tmp/houmao-mailbox`
- **AND WHEN** a filesystem-backed mailbox session has no more specific explicit mailbox-root override
- **THEN** the runtime resolves the effective shared mailbox root from `/tmp/houmao-mailbox`

### Requirement: Mailbox-enabled runtime sessions project mailbox system skills and persist manifest-backed mailbox bindings
When mailbox support is enabled for a started session, the runtime SHALL project the platform-owned mailbox system skills into the active agent skillset through a discoverable tool-native mailbox skill surface and SHALL persist one transport-specific mailbox binding for that session in the session manifest.

When the selected transport is `filesystem`, the runtime SHALL derive and persist the effective filesystem mailbox content root and the mailbox identity needed to resolve current filesystem mailbox state for that session.

When the selected transport is `stalwart`, the runtime SHALL persist the real-mail mailbox binding metadata needed for later mailbox work and SHALL NOT synthesize filesystem-only mailbox path metadata that does not belong to that transport.

Those persisted Stalwart runtime bindings SHALL expose only secret-free transport metadata, with any session-local credential material derived later from persisted references rather than embedded inline in the session manifest.

When no explicit filesystem mailbox content root override is supplied, the runtime SHALL derive the effective filesystem mailbox content root from the independent Houmao mailbox root rather than from the effective runtime root.

When no explicit filesystem mailbox content root override is supplied and `HOUMAO_GLOBAL_MAILBOX_DIR` is set to an absolute directory path, the runtime SHALL derive the effective Houmao mailbox root from that env-var override before persisting or resolving filesystem mailbox state for that session.

When current filesystem mailbox resolution depends on the session address having an active mailbox registration, the runtime SHALL bootstrap or confirm that session's mailbox registration before persisting the durable mailbox binding or serving manager-owned current-mailbox resolution for `start-session`.

The runtime SHALL satisfy that registration-dependent mailbox contract through bootstrap ordering rather than by synthesizing fallback mailbox paths when the active registration is missing.

For Claude sessions, the discoverable tool-native mailbox skill surface SHALL use Claude-native top-level Houmao skill directories under the active isolated Claude skill root rather than a `mailbox/` namespace subtree.

For Claude sessions, the isolated Claude skill root SHALL remain part of the runtime-owned `CLAUDE_CONFIG_DIR` rather than being rebound to the launched workdir's `.claude/` directory.

For non-Claude sessions, the discoverable tool-native mailbox skill surface MAY continue to use the existing visible mailbox namespace subtree when that remains the active contract for that tool.

#### Scenario: Start Claude session projects mailbox system skills with a filesystem mailbox binding
- **WHEN** a developer starts a Claude session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the Claude active skill destination through top-level Houmao-owned skill directories
- **AND THEN** the runtime persists one filesystem mailbox binding for that session in the session manifest
- **AND THEN** later mailbox discovery can derive the effective mailbox content root for that session from that persisted binding

#### Scenario: Start Claude session keeps runtime-owned state out of project-local `.claude`
- **WHEN** a developer starts a Claude session with mailbox support enabled for workdir `<workdir>`
- **THEN** the runtime uses an isolated runtime-owned `CLAUDE_CONFIG_DIR` for Houmao-managed Claude state
- **AND THEN** runtime-owned mailbox skill projection does not require setting `CLAUDE_CONFIG_DIR` to `<workdir>/.claude`
- **AND THEN** the runtime does not depend on projecting Houmao mailbox skills into the user repo's `.claude/skills/` tree

#### Scenario: Start Claude session projects mailbox system skills with a Stalwart mailbox binding
- **WHEN** a developer starts a Claude session with `stalwart` mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the Claude active skill destination through top-level Houmao-owned skill directories
- **AND THEN** the runtime persists one secret-free `stalwart` mailbox binding for that session in the session manifest
- **AND THEN** the runtime does not persist filesystem mailbox root or mailbox-path metadata for that Stalwart session

#### Scenario: Start non-Claude session projects mailbox system skills through its current visible mailbox namespace
- **WHEN** a developer starts a non-Claude agent session with mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the tool adapter's active skill destination through the current visible mailbox namespace for that tool
- **AND THEN** the runtime persists the transport-appropriate mailbox binding for that session in the session manifest

#### Scenario: Start session defaults the filesystem mailbox root from the Houmao mailbox root
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from the Houmao mailbox root default
- **AND THEN** the persisted session mailbox binding reflects that derived default path

#### Scenario: Mailbox-root env-var override redirects the effective mailbox root
- **WHEN** `HOUMAO_GLOBAL_MAILBOX_DIR` is set to `/tmp/houmao-mailbox`
- **AND WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from `/tmp/houmao-mailbox`
- **AND THEN** the persisted session mailbox binding reflects that derived path

#### Scenario: Second mailbox-enabled session joins an initialized shared mailbox root without manual pre-registration
- **WHEN** one mailbox-enabled session has already initialized and registered itself into a shared filesystem mailbox root
- **AND WHEN** a second mailbox-enabled session starts against that same shared mailbox root with its own mailbox address
- **THEN** the runtime bootstraps or confirms the second session's mailbox registration before persisting registration-dependent filesystem mailbox state for that session
- **AND THEN** the second `start-session` succeeds without requiring manual mailbox pre-registration outside the runtime startup path

### Requirement: Runtime CLI exposes top-level agent-mediated mailbox operations for resumed sessions
The runtime CLI SHALL expose a top-level `mail` command surface for resumed mailbox-enabled sessions.

That `mail` command surface SHALL support at minimum the operations `check`, `send`, and `reply`, and SHALL target an existing live session through the same agent-identity or session-manifest resolution model used by other runtime session-control commands.

#### Scenario: Mail check targets a resumed mailbox-enabled session
- **WHEN** a developer invokes the runtime `mail check` command against a resumed mailbox-enabled session
- **THEN** the runtime resolves that target session through the normal runtime session-identity resolution path
- **AND THEN** the runtime asks that live agent session to perform one mailbox-check operation for its bound mailbox principal

#### Scenario: Mail send targets a resumed mailbox-enabled session
- **WHEN** a developer invokes the runtime `mail send` command against a resumed mailbox-enabled session with recipients and message content
- **THEN** the runtime asks that live agent session to compose and deliver one new mailbox message through its configured mailbox transport
- **AND THEN** the resulting mailbox operation preserves the sender principal bound to that session rather than allowing the operator to spoof an arbitrary sender principal

#### Scenario: Mail reply preserves existing thread ancestry
- **WHEN** a developer invokes the runtime `mail reply` command against a resumed mailbox-enabled session for an existing message
- **THEN** the runtime asks that live agent session to reply through the mailbox protocol rather than starting an unrelated new root message
- **AND THEN** the reply preserves the existing `thread_id`, `in_reply_to`, and `references` semantics for that thread

### Requirement: Runtime mail commands keep one operator surface while allowing gateway-backed shared mailbox interaction
The runtime SHALL preserve the current operator-facing `mail check`, `mail send`, and `mail reply` command surface across filesystem and `stalwart` sessions.

When the runtime owns mailbox execution directly, including manager-owned direct execution or gateway-backed execution, it SHALL return authoritative mailbox success or failure for the requested operation.

When the runtime executes a mailbox operation by submitting a request through a live TUI session, it SHALL treat the command outcome as non-authoritative request lifecycle state rather than mailbox success or failure recovered from exact transcript parsing.

The runtime SHALL still translate TUI-mediated `mail` invocations into a runtime-owned mailbox prompt delivered through the existing prompt-turn control path rather than directly manipulating mailbox files or mailbox SQLite state itself.

That mailbox prompt SHALL explicitly tell the agent which discoverable projected mailbox system skill to use for the mailbox operation and SHALL append structured mailbox metadata needed for the mailbox operation.

For the current mailbox skill contract, that prompt SHALL identify the stable transport-specific mailbox skill name together with the primary visible mailbox skill path under the active skill destination.

The runtime SHALL NOT mention or rely on a hidden `.system/mailbox/...` mailbox path in that prompt.

The mailbox prompt and projected mailbox system skill SHALL prefer a live gateway mailbox facade when that facade is available for the addressed session.

When no live gateway mailbox facade is available, the runtime MAY continue to rely on the direct session-mediated mailbox path appropriate to the selected transport.

The mailbox prompt SHALL follow gateway-aware transport expectations:

- filesystem prompts SHALL continue to instruct the agent to follow filesystem mailbox rules and helper boundaries when those are required for that transport,
- `stalwart` prompts SHALL direct the agent to use the shared gateway mailbox facade when available or Stalwart-backed mailbox bindings when not, without inheriting filesystem-only `rules/` or managed-script instructions.

The runtime-owned prompt-construction path SHALL dispatch by transport and gateway availability rather than assuming filesystem-only mailbox instructions for every mailbox-enabled session.

For TUI-mediated mailbox commands, exact sentinel-delimited structured result parsing SHALL NOT be the correctness boundary for command completion.

For TUI-mediated mailbox commands, shadow parsing and transcript recovery MAY be used for:

- submit-ready versus busy state tracking,
- request-submission confirmation,
- optional preview,
- diagnostics.

For TUI-mediated mailbox commands, the runtime SHALL NOT require exactly one parseable mailbox-result payload for the active request in order to return a non-authoritative submitted or rejected outcome.

If a parseable active-request sentinel payload is recovered in TUI-mediated mode, the runtime MAY surface it as optional diagnostic or preview data. It SHALL NOT be required for the command to return.

For `shadow_only` mailbox commands, prompt-echo mentions of `HOUMAO_MAIL_RESULT_BEGIN` and `HOUMAO_MAIL_RESULT_END` inside ordinary prose, echoed mailbox request content, or echoed response-contract metadata SHALL NOT be treated as authoritative mailbox-result evidence.

For `shadow_only` mailbox commands, mailbox correctness SHALL not depend on `dialog_projection.dialog_text` being an exact recovered reply transcript.

#### Scenario: Verified direct execution returns authoritative mailbox result
- **WHEN** a developer invokes a runtime `mail` command for a mailbox-enabled session
- **AND WHEN** the runtime owns the mailbox execution path directly
- **THEN** the runtime returns authoritative mailbox success or failure for that operation
- **AND THEN** the command result reflects protocol-owned or manager-owned mailbox truth rather than transcript recovery

#### Scenario: TUI-mediated mail send returns non-authoritative submitted state
- **WHEN** a developer invokes `mail send` for a mailbox-enabled session
- **AND WHEN** the execution path is prompt submission into a live TUI session
- **THEN** the runtime returns request lifecycle state such as submitted, rejected, interrupted, busy, or TUI error
- **AND THEN** the runtime does not require exact structured mailbox-result parsing to complete the command

#### Scenario: TUI preview data does not redefine mailbox truth
- **WHEN** a mailbox-enabled TUI session emits a parseable sentinel-delimited JSON result or other mailbox-related preview text
- **THEN** the runtime MAY surface that data as optional preview or diagnostics
- **AND THEN** the authoritative outcome contract for the command remains based on execution authority rather than preview transcript recovery

#### Scenario: Mail command fails fast when session cannot accept a new turn
- **WHEN** a developer invokes a runtime `mail` command for a session that is already busy or otherwise cannot safely accept a new prompt turn
- **THEN** the runtime returns an explicit mailbox-command error
- **AND THEN** it does not silently queue hidden mailbox work for later execution

### Requirement: Runtime mail send and reply commands require full recipient addresses and explicit body inputs
Runtime mail send and reply commands SHALL require full mailbox addresses in the active Houmao namespace rather than loose agent-name shortcuts.

#### Scenario: Runtime mail send accepts full HOUMAO mailbox addresses
- **WHEN** a developer invokes `mail send` for a resumed mailbox-enabled session with `--to HOUMAO-bob@agents.localhost` and `--body-content`
- **THEN** the command accepts that address as a valid full recipient address

### Requirement: Runtime mailbox prompt payloads carry explicit content and address data without instruction fields
When the runtime translates `mail send` or `mail reply` into a runtime-owned mailbox prompt for a live session, the structured mailbox request payload SHALL carry explicit address and body data rather than an instruction asking the agent to improvise the final message.

For `mail send`, the structured request payload SHALL include full mailbox addresses for recipients and explicit Markdown body content.

For `mail reply`, the structured request payload SHALL include the target `message_id` plus explicit Markdown body content.

The structured request payload for `send` and `reply` SHALL NOT include an `instruction` field.

#### Scenario: Mail send payload carries explicit recipient addresses and body content
- **WHEN** the runtime prepares a `mail send` prompt request for a mailbox-enabled session
- **THEN** the structured mailbox request payload contains explicit full-form recipient addresses and explicit body content
- **AND THEN** that payload does not include an `instruction` field for content generation

#### Scenario: Mail reply payload carries explicit reply body and target message id
- **WHEN** the runtime prepares a `mail reply` prompt request for a mailbox-enabled session
- **THEN** the structured mailbox request payload contains the target `message_id` and explicit body content for the reply
- **AND THEN** that payload does not depend on free-form instruction text to determine the reply content

### Requirement: Runtime filesystem mailbox resolution follows the active mailbox registration path
When the runtime resolves current mailbox state for a filesystem-backed session, it SHALL derive registration-dependent filesystem paths from the active mailbox registration for the session's bound mailbox address rather than by reconstructing a mailbox path from `principal_id`.

At minimum, the manager-owned current-mailbox resolution path SHALL report the active inbox path for the session's bound mailbox address when that address has an active registration.

If runtime bootstrap or later current-mailbox resolution can detect that the target mailbox root still uses the unsupported principal-keyed layout from the earlier implementation, it SHALL fail explicitly and direct the operator to delete and re-bootstrap that mailbox root.

#### Scenario: Current mailbox resolution reports the active address-based inbox path
- **WHEN** the runtime resolves current mailbox state for a filesystem-backed session whose active registration is `AGENTSYS-research@agents.localhost`
- **THEN** the resolved inbox path points at the inbox for that active registration
- **AND THEN** the runtime does not derive that path by concatenating `mailboxes/<principal_id>/inbox`

#### Scenario: Updated registration changes derived filesystem mailbox paths
- **WHEN** the runtime resolves current mailbox state for an active filesystem-backed session after the active mailbox registration changes for the bound address
- **THEN** the resolved filesystem mailbox paths follow the current active registration for that address
- **AND THEN** subsequent runtime-controlled mailbox work uses the refreshed derived path set

#### Scenario: Unsupported stale mailbox root fails current mailbox resolution explicitly
- **WHEN** the runtime attempts to bootstrap or resolve current filesystem mailbox state against a stale principal-keyed mailbox root from the earlier implementation
- **THEN** the runtime fails explicitly
- **AND THEN** the error tells the operator to delete and re-bootstrap the mailbox root rather than silently deriving incorrect paths

### Requirement: Runtime-generated CAO agent profiles from roles
When using CAO, the system SHALL generate CAO agent profiles at runtime from repo role packages rather than requiring committed/static CAO profile files.

The generated profile system prompt SHALL be derived from `agents/roles/<R>/system-prompt.md`, including the empty-string case for promptless roles.

#### Scenario: Generate and install a CAO profile for a role
- **WHEN** a developer launches a CAO-backed session with role `R`
- **THEN** the system generates an agent profile whose system prompt is derived from `agents/roles/<R>/system-prompt.md`
- **AND THEN** the CAO terminal launch references that generated profile by name

#### Scenario: Promptless role stays valid for CAO profile generation
- **WHEN** a developer launches a CAO-backed session with role `R` whose `system-prompt.md` is intentionally empty
- **THEN** the generated profile uses an empty system prompt
- **AND THEN** launch remains valid rather than failing role validation

### Requirement: Credential env var allowlist enforcement at launch
The system SHALL apply only allowlisted credential environment variables at launch time, as defined by the selected tool adapter and auth bundle.

#### Scenario: Disallowed env vars are ignored
- **WHEN** the credential env file contains both allowlisted and non-allowlisted keys
- **THEN** only allowlisted keys are applied to the tool process environment
- **AND THEN** non-allowlisted keys are not applied

### Requirement: Claude model selection env vars are propagated to launched sessions
For Claude Code launches, the system SHALL preserve Claude Code model-selection
environment variables in the tool process environment for both:

- `backend=claude_headless` (subprocess launches)
- `backend=cao_rest` (tmux-isolated CAO-backed launches)

At minimum, the system SHALL support `ANTHROPIC_MODEL` for selecting the
effective model, and SHALL allow pinning alias resolution via:

- `ANTHROPIC_DEFAULT_OPUS_MODEL`
- `ANTHROPIC_DEFAULT_SONNET_MODEL`
- `ANTHROPIC_DEFAULT_HAIKU_MODEL`

The system SHALL additionally support:

- `CLAUDE_CODE_SUBAGENT_MODEL`
- `ANTHROPIC_SMALL_FAST_MODEL` (when unset, the system SHALL NOT synthesize it and Claude Code defaults apply)

#### Scenario: CAO-backed session inherits caller model env vars
- **WHEN** a developer starts a CAO-backed Claude session with `ANTHROPIC_MODEL` set in the caller environment
- **THEN** the created tmux session environment SHALL include `ANTHROPIC_MODEL` with the same value
- **AND THEN** if the caller environment defines `CLAUDE_CODE_SUBAGENT_MODEL`, the created tmux session environment SHALL include `CLAUDE_CODE_SUBAGENT_MODEL` with the same value
- **AND THEN** if the caller environment defines `ANTHROPIC_SMALL_FAST_MODEL`, the created tmux session environment SHALL include `ANTHROPIC_SMALL_FAST_MODEL` with the same value

#### Scenario: Headless session includes allowlisted model env vars from auth bundle
- **WHEN** a developer starts a Claude headless session and the selected auth bundle env file defines `ANTHROPIC_MODEL` (and/or `ANTHROPIC_SMALL_FAST_MODEL` and/or `CLAUDE_CODE_SUBAGENT_MODEL` and/or one of the `ANTHROPIC_DEFAULT_*_MODEL` pinning vars)
- **THEN** the headless Claude subprocess environment SHALL include the corresponding model-selection env var(s)

### Requirement: Auth bundle sharing is permitted
The system SHALL allow launching multiple sessions that reference the same auth bundle.

#### Scenario: Launch does not require exclusive auth ownership
- **WHEN** a developer launches two sessions selecting the same auth bundle name
- **THEN** both launches can proceed without requiring an exclusive lock

### Requirement: Interactive sessions provide streaming output and support interruption
The system SHALL support streaming output/events for interactive sessions, and SHALL support interrupting or terminating in-flight backend work.

#### Scenario: Stream events and interrupt an in-flight request
- **WHEN** a developer sends a prompt to an interactive session
- **THEN** the system emits streaming output/events while the backend is processing
- **AND WHEN** the developer requests interruption/termination before completion
- **THEN** the system attempts a best-effort interrupt and, if needed, terminates the underlying backend session/process
- **AND THEN** the session reports an `interrupted`/`terminated` outcome (or an error if interruption fails)

### Requirement: Persist a session manifest JSON
The system SHALL persist a session manifest JSON (session handle) alongside the brain manifest for audit, resume, stop, gateway attach authority, and tmux-backed relaunch authority.

For tmux-backed sessions, that manifest SHALL persist normalized session authority that includes at minimum:

- runtime-owned session identity and paths
- authoritative `agent_id` and canonical `agent_name`
- persisted tmux session identity
- agent process pid when a live agent worker process currently exists
- secret-free agent relaunch authority needed for later gateway-managed or CLI-managed relaunch
- the backend-specific attach authority needed for later gateway attach
- the backend-specific runtime control authority needed for later resumed control

For native headless tmux-backed sessions, that manifest SHALL additionally persist enough authority for the gateway or resumed controller to relaunch future headless turns from manifest-owned state even when no live worker process currently exists.

For tmux-backed supported surfaces, the manifest SHALL be the stable authority for later gateway attach and runtime control rather than relying on `gateway_manifest.json`, `attach.json`, or duplicated legacy `backend_state` blobs.

#### Scenario: Start session writes a manifest with normalized session authority
- **WHEN** a developer starts a tmux-backed runtime-owned session
- **THEN** the system writes a session manifest JSON that records backend type, canonical session authority, persisted tmux session identity, and the attach or control fields required for later resume and gateway attach
- **AND THEN** that manifest includes secret-free relaunch posture plus the live agent process pid when one exists as part of runtime-owned session truth

#### Scenario: Native headless manifest remains attachable between turns
- **WHEN** a developer starts or resumes a native headless tmux-backed session
- **AND WHEN** no live headless worker process is currently running because the prior turn already completed
- **THEN** the persisted manifest still contains the authority needed for later gateway attach and future turn relaunch
- **AND THEN** a missing live `agent_pid` does not invalidate that manifest

#### Scenario: Resume tmux-backed session uses manifest authority rather than gateway bootstrap publication
- **WHEN** a developer resumes a tmux-backed session from a persisted session manifest
- **THEN** the system uses the manifest's persisted attach or control authority as the source of truth for resumed control
- **AND THEN** it does not require `gateway_manifest.json` or `attach.json` to remain authoritative for the resumed operation

### Requirement: Runtime defaults new build and session state to the Houmao runtime root
The runtime SHALL default new build and session state to the effective project-aware runtime root when local command flows operate in project context.

When a maintained local build or launch flow has an active project overlay and no stronger runtime-root override exists, the effective runtime root SHALL be `<active-overlay>/runtime`.

When an explicit runtime-root override exists, that explicit override SHALL win.
When no active project overlay exists for the flow and the command requires local Houmao-owned state, the command SHALL ensure `<cwd>/.houmao` exists and use `<cwd>/.houmao/runtime` as the resulting default runtime root unless a stronger override applies.

Registry publication remains separate and SHALL continue to use the shared registry root rather than nesting registry state under the runtime root.

#### Scenario: Project-context build uses overlay-local runtime root
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** a maintained local brain build or runtime launch runs without a stronger runtime-root override
- **THEN** the effective runtime root is `/repo/.houmao/runtime`
- **AND THEN** generated homes, manifests, and session envelopes are written under that overlay-local runtime root

#### Scenario: Explicit runtime-root override still wins over project-aware defaulting
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** a maintained local build or launch flow is given explicit runtime-root override `/tmp/custom-runtime`
- **THEN** the effective runtime root is `/tmp/custom-runtime`
- **AND THEN** the overlay-local runtime default is not used for that operation

### Requirement: Runtime materializes canonical agent name and authoritative `agent_id` for system-owned association
Runtime-owned session start SHALL materialize canonical agent names in `HOUMAO-<name>` form and SHALL derive the initial authoritative `agent_id` from that canonical name when no explicit or previously persisted `agent_id` exists.

The initial authoritative id SHALL be the full lowercase `md5("HOUMAO-<name>").hexdigest()` value.

#### Scenario: Runtime bootstraps agent identity from the HOUMAO canonical name
- **WHEN** a developer starts a runtime-owned session with canonical agent name `HOUMAO-gpu`
- **THEN** the runtime materializes the full lowercase `md5("HOUMAO-gpu").hexdigest()` value as the session's initial authoritative `agent_id`

### Requirement: Tmux session names are unique live-session handles rather than authoritative agent names
For tmux-backed runtime sessions, the runtime SHALL treat the tmux session name as a unique handle for one live session rather than as the source of truth for canonical agent name or authoritative `agent_id`.

The runtime SHALL choose and persist the tmux session name explicitly for each started tmux-backed session rather than relying on tmux collision auto-renaming as an identity mechanism.

Persisted runtime metadata for a tmux-backed session SHALL record at minimum:
- canonical agent name,
- authoritative `agent_id`,
- the actual tmux session name used for that live session.

The session-manifest schema for this capability SHALL also expose that actual tmux session name as a first-class top-level manifest field rather than only as backend-specific state.

When runtime-controlled logic needs to recover the true canonical agent name or authoritative `agent_id` for a tmux-backed live session, it SHALL read persisted manifest metadata or shared-registry publication rather than inferring that identity from the tmux session name alone.

#### Scenario: Tmux-backed start persists the actual tmux session name separately from canonical agent name
- **WHEN** the runtime starts a tmux-backed session for canonical agent name `AGENTSYS-gpu`
- **AND WHEN** the runtime chooses live tmux session name `houmao-session-abc123`
- **THEN** persisted runtime metadata records canonical agent name `AGENTSYS-gpu`
- **AND THEN** that same metadata also records tmux session name `houmao-session-abc123` as a distinct live-session handle

#### Scenario: Runtime learns true agent identity from manifest or registry rather than from tmux session name
- **WHEN** runtime-controlled logic needs to inspect tmux-backed live session `houmao-session-abc123`
- **THEN** it reads persisted manifest metadata or shared-registry publication to recover canonical agent name and authoritative `agent_id`
- **AND THEN** it does not assume the tmux session name itself equals the canonical agent name

### Requirement: Runtime creates and reuses a per-agent job dir for each started session
For maintained local launch flows operating in project context, the runtime SHALL derive the default per-agent job dir from the active project overlay as:

- `<active-overlay>/jobs/<session-id>/`

When an explicit jobs-root override exists, that explicit override SHALL win.
When `HOUMAO_LOCAL_JOBS_DIR` is set and no stronger explicit jobs-root override exists, that env-var override SHALL win.
Maintained local launch boundaries SHALL resolve the effective jobs root before session startup and pass an explicit jobs-root or already resolved job dir into that startup path rather than relying on the caller's working directory as the implicit jobs anchor.

The runtime SHALL persist the resolved job dir in the session manifest and publish it to the launched session environment as `HOUMAO_JOB_DIR`.

#### Scenario: Project-context session derives its job dir under the overlay
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** the runtime starts a session with generated session id `session-20260314-120000Z-abcd1234`
- **AND WHEN** no stronger jobs-root override exists
- **THEN** the effective job dir is `/repo/.houmao/jobs/session-20260314-120000Z-abcd1234/`
- **AND THEN** the session manifest records that resolved path as `job_dir`

#### Scenario: Jobs env override still relocates the per-session job dir
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** `HOUMAO_LOCAL_JOBS_DIR=/tmp/houmao-jobs`
- **AND WHEN** the runtime starts a session with generated session id `session-20260314-120000Z-abcd1234`
- **THEN** the effective job dir is `/tmp/houmao-jobs/session-20260314-120000Z-abcd1234/`
- **AND THEN** the overlay-local jobs default is not used for that session

#### Scenario: Project-aware launch resolves jobs placement before session startup
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator starts a maintained local launch flow from working directory `/repo/subdir`
- **AND WHEN** no stronger jobs-root override exists
- **THEN** the launch boundary passes `/repo/.houmao/jobs` or the fully resolved `/repo/.houmao/jobs/<session-id>/` into session startup
- **AND THEN** the session does not derive its default job dir from `/repo/subdir/.houmao/jobs`

### Requirement: Runtime-generated manifests/configs are schema-validated
The system SHALL schema-validate all runtime-generated structured manifest/config artifacts on write and on read/load.

#### Scenario: Generated artifact fails schema validation on write
- **WHEN** the runtime is about to persist a generated structured artifact whose payload does not match its declared schema
- **THEN** the write is rejected
- **AND THEN** the runtime returns a validation error that identifies the failing field path and reason

#### Scenario: Persisted artifact fails schema validation on read/resume
- **WHEN** the runtime loads an existing manifest/config artifact for resume or control operations
- **AND WHEN** the artifact fails schema validation
- **THEN** the runtime rejects the operation with an explicit schema-validation error instead of proceeding with undefined behavior

### Requirement: JSON Schema assets live in `src/` runtime package
The system SHALL keep JSON Schema files for runtime-generated structured artifacts inside the runtime package under `src/houmao/.../schemas/`.

#### Scenario: Session manifest schema is versioned and discoverable
- **WHEN** developers inspect the runtime package source
- **THEN** they can find versioned JSON Schema files (for example `session_manifest.v3.schema.json`) under the runtime package `schemas/` directory
- **AND THEN** generated artifacts include schema version information that selects the matching schema for validation

### Requirement: CAO parsing mode is explicit and constrained
For CAO-backed sessions, the system SHALL resolve a parsing mode at session start from configuration.

Allowed values are exactly:
- `cao_only`
- `shadow_only`

The selected mode SHALL be persisted in session runtime state so resumed operations use the same parsing mode.

`cao_only` SHALL remain the generic CAO-native mode for CAO-backed sessions.
`shadow_only` SHALL be used only for tools that have a runtime-owned shadow parser family.
The runtime SHALL define one explicit shadow-parser-support capability contract for this purpose, and that contract SHALL be shared by parsing-mode validation and backend parser-stack selection rather than inferred indirectly from unrelated defaults.

Default mapping SHALL be:
- `tool=claude` -> `shadow_only`
- `tool=codex` -> `shadow_only`

#### Scenario: Session start resolves parsing mode from tool default (Claude)
- **WHEN** a caller starts a CAO-backed session without explicitly specifying parsing mode
- **AND WHEN** the tool is `claude`
- **THEN** the resolved parsing mode is `shadow_only`

#### Scenario: Session start resolves parsing mode from tool default (Codex)
- **WHEN** a caller starts a CAO-backed session without explicitly specifying parsing mode
- **AND WHEN** the tool is `codex`
- **THEN** the resolved parsing mode is `shadow_only`

#### Scenario: Session start accepts explicit `cao_only`
- **WHEN** a caller starts a CAO-backed session and explicitly specifies `parsing_mode=cao_only`
- **THEN** the resolved parsing mode is `cao_only`

#### Scenario: Session start fails when parsing mode cannot be resolved
- **WHEN** a caller starts a CAO-backed session and configuration does not provide an explicit parsing mode or a valid tool default
- **THEN** the system rejects the start request with an explicit validation error

#### Scenario: Unknown parsing mode is rejected
- **WHEN** a caller requests a parsing mode other than `cao_only` or `shadow_only`
- **THEN** the system rejects the request with an explicit unsupported-mode error

#### Scenario: `shadow_only` is rejected when no runtime shadow parser exists
- **WHEN** a caller requests `parsing_mode=shadow_only` for a CAO-backed tool that does not have a runtime-owned shadow parser family
- **THEN** the system rejects the request with an explicit unsupported-mode error

### Requirement: Repo-owned CAO workflows for supported shadow tools follow the shadow-first contract
For CAO-backed tools that have a runtime-owned shadow parser family, repo-owned workflows, demos, and maintainer-facing helper surfaces SHALL treat `shadow_only` as the normal parsing posture.

Such surfaces MAY rely on the existing per-tool parsing-mode default or request `shadow_only` explicitly, but SHALL NOT pin `cao_only` as their normal default unless the workflow exists specifically to exercise or debug the CAO-native path.

When one such shadow-first workflow needs text beyond completion status, it SHALL use structured shadow payloads, explicit schema/sentinel outputs, side-effect verification, or clearly labeled best-effort shadow extraction rather than assuming the final runtime `done.message` contains the exact agent reply text.

#### Scenario: Repo-owned CAO helper workflow relies on the supported tool default
- **WHEN** a repo-owned workflow starts a CAO-backed Claude or Codex session without an explicit parsing-mode override
- **THEN** the workflow runs under the runtime-resolved `shadow_only` default for that supported tool
- **AND THEN** the workflow does not introduce an unnecessary `cao_only` override just to preserve older answer-text assumptions

#### Scenario: Shadow-first workflow needs text evidence beyond neutral completion message
- **WHEN** a repo-owned CAO workflow for Claude or Codex needs text evidence from a successful `shadow_only` turn
- **THEN** it does not treat the final runtime `done.message` as the authoritative reply text
- **AND THEN** it uses structured shadow payloads, explicit schema/sentinel outputs, side-effect checks, or clearly labeled best-effort shadow extraction instead

#### Scenario: CAO-native troubleshooting remains an explicit exception
- **WHEN** a maintainer runs a dedicated troubleshooting or CAO-native coverage path for a supported tool
- **THEN** that path may still request `parsing_mode=cao_only`
- **AND THEN** the exception is explicit rather than being presented as the normal default posture

### Requirement: Codex runtime launch applies non-interactive home bootstrap
For Codex launches, the runtime SHALL apply a runtime-owned bootstrap step to the generated Codex home configuration before starting the tool for:
- `backend=codex_headless`
- `backend=codex_app_server`
- `backend=cao_rest`

Bootstrap behavior SHALL include:
- ensuring launch-context trust is recorded for the active workspace target in Codex project config, and
- seeding required notice state needed to avoid interactive onboarding/warning prompts for the selected policy profile, and
- applying configured non-interactive launch flags needed to reduce interactive startup prompts (including `approval_policy` / `sandbox_mode` only when explicitly present in the selected Codex setup bundle; the runtime SHALL NOT hardcode new approval/sandbox defaults).

#### Scenario: CAO Codex launch seeds trust for launch workspace
- **WHEN** a Codex CAO-backed session is started with a resolved working directory
- **THEN** runtime bootstrap writes/updates Codex runtime-home config so the launch workspace trust decision is pre-seeded before terminal start

#### Scenario: Codex headless launch uses the same bootstrap contract
- **WHEN** a Codex headless session is started from a generated brain home
- **THEN** runtime applies the same Codex bootstrap contract before the first headless CLI turn

### Requirement: CAO shadow polling supports configurable unknown-to-stalled policy
For CAO sessions in `parsing_mode=shadow_only`, the runtime SHALL support a configurable shadow stall policy with at least:
- `unknown_to_stalled_timeout_seconds`
- `stalled_is_terminal`

When unset, `unknown_to_stalled_timeout_seconds` SHALL default to 30 seconds.

The same `unknown_to_stalled_timeout_seconds` value applies to both:
- readiness wait before prompt submission, and
- completion wait during turn execution.

For the corrected two-axis shadow surface model, the unknown-to-stalled timer SHALL treat a surface as "unknown for stall purposes" only when either:

- `availability = unknown`, or
- `availability = supported` and `business_state = unknown`

`input_mode = unknown` by itself SHALL keep the surface non-ready, but SHALL NOT trigger the unknown-to-stalled timer when `business_state` remains known.

The unknown-to-stalled timeout SHALL measure inter-observation gaps rather than wall-clock elapsed time from a fixed start timestamp. When polling intervals vary (slow network, slow CAO), the effective timeout SHALL scale proportionally to the number of actual observations rather than firing after a fixed wall-clock duration that may contain fewer observations than intended.

Any known observation SHALL cancel a pending unknown-to-stalled timeout and reset unknown/stalled tracking. The runtime SHALL NOT enter `stalled` unless the current continuous unknown run reaches the configured threshold.

#### Scenario: Unknown business state reaches stalled threshold
- **WHEN** shadow polling remains on a supported surface with `business_state = unknown`
- **AND WHEN** the continuous inter-observation gap on unknown surfaces reaches `unknown_to_stalled_timeout_seconds`
- **THEN** runtime marks the shadow lifecycle state as `stalled`

#### Scenario: Unknown input mode alone does not enter stalled
- **WHEN** shadow polling remains on a supported surface with a known `business_state`
- **AND WHEN** only `input_mode = unknown`
- **THEN** runtime keeps the surface non-ready
- **AND THEN** it does not enter `stalled` solely because the input mode is unknown

#### Scenario: Slow polling extends effective stall wait
- **WHEN** shadow polling intervals are slower than normal (e.g., due to network latency or CAO load)
- **AND WHEN** the surface remains unknown across those slow polls
- **THEN** the stall timeout fires after the configured duration of continuous unknown observations
- **AND THEN** the effective wall-clock wait is longer than it would be under normal polling intervals

#### Scenario: Known observation cancels pending stall timeout
- **WHEN** shadow polling emits unknown-for-stall observations
- **AND WHEN** a later observation returns to a known surface before the stall threshold is reached
- **THEN** runtime cancels the pending unknown-to-stalled timeout
- **AND THEN** it does not emit `stalled` unless a later continuous unknown run reaches the threshold

### Requirement: Runtime emits stalled lifecycle anomaly codes
For CAO sessions in `parsing_mode=shadow_only`, runtime SHALL emit dedicated anomaly codes for stalled lifecycle transitions:
- `stalled_entered` when transitioning from `unknown` to `stalled`
- `stalled_recovered` when transitioning from `stalled` back to a known status

Emitted anomalies SHALL include phase context (`readiness` vs `completion`) and elapsed duration context.

#### Scenario: Emit `stalled_entered` anomaly with phase context
- **WHEN** a CAO-backed session is running in `parsing_mode=shadow_only`
- **AND WHEN** shadow polling transitions from `unknown` to `stalled` during readiness or completion
- **THEN** runtime emits a `stalled_entered` anomaly
- **AND THEN** the anomaly includes phase context (`readiness` or `completion`) and elapsed duration context

#### Scenario: Emit `stalled_recovered` anomaly when status becomes known again
- **WHEN** a CAO-backed session is running in `parsing_mode=shadow_only`
- **AND WHEN** shadow polling has entered `stalled` and later transitions back to a known status
- **THEN** runtime emits a `stalled_recovered` anomaly
- **AND THEN** the anomaly includes phase context (`readiness` or `completion`) and elapsed duration context

### Requirement: Stalled handling is configurable between terminal and recoverable modes
The runtime SHALL support both terminal and non-terminal stalled handling.

#### Scenario: Stalled is terminal
- **WHEN** `stalled_is_terminal=true`
- **AND WHEN** runtime reaches `stalled`
- **THEN** the turn fails immediately with an explicit stalled-state error and diagnostics excerpt

#### Scenario: Stalled is non-terminal and can recover
- **WHEN** `stalled_is_terminal=false`
- **AND WHEN** runtime reaches `stalled`
- **THEN** runtime continues periodic polling instead of immediate failure
- **AND THEN** if later output becomes classifiable, runtime resumes known-state flow from that snapshot

### Requirement: CAO backend sends input only when terminal is ready and does not use inbox
When using the CAO backend, the system SHALL only send terminal input when the target terminal is ready for the selected parsing mode, SHALL not use CAO inbox messaging, and SHALL fetch or derive output only after request completion for the same mode.

Mode-specific readiness and completion behavior SHALL be:
- `cao_only`: readiness and completion from CAO terminal status (`idle|completed`) and answer retrieval from CAO `output?mode=last`.
- `shadow_only`: readiness from runtime shadow surface assessment derived from CAO `output?mode=full`, with generic lifecycle completion determined by runtime predicates over `availability`, `business_state`, `input_mode`, and post-submit progress evidence. Runtime-owned commands with explicit machine-critical output contracts MAY require additional caller-owned terminal evidence over post-submit shadow text before the turn result is surfaced.

For `shadow_only`, the runtime SHALL treat a surface as submit-ready only when all of the following are true:

- `availability = supported`
- `business_state = idle`
- `input_mode = freeform`

For `shadow_only`, the runtime SHALL surface projected dialog data derived from `output?mode=full` and SHALL NOT require parser-owned prompt-associated answer extraction to complete the turn.
For `shadow_only`, generic success terminality SHALL require a return to the submit-ready surface plus previously-seen post-submit activity from either:
- normalized shadow-text change observed after submit, or
- post-submit observation of `business_state = working`.

That candidate-complete surface SHALL then remain stable for `completion_stability_seconds` before generic shadow completion is emitted. State changes during that stability window SHALL reset the pending completion window.

This generic completion gate intentionally uses full `submit_ready`, not merely "the surface looks typeable again." A `shadow_only` turn SHALL NOT complete while `business_state = working`, even when `input_mode = freeform`.

For `shadow_only`, runtime-owned mailbox commands that require sentinel-delimited results SHALL treat that generic success terminality as provisional only. Those commands SHALL continue polling post-submit shadow text until the mailbox contract is satisfied or the bounded turn failure policy fires.
For `shadow_only`, readiness SHALL follow the currently active input surface rather than any historical slash-command line still visible in earlier scrollback. Completed slash-command or model-switch output that remains in the projected dialog SHALL NOT keep a later recovered normal prompt in a non-ready state.
For `shadow_only`, an active modal surface such as slash-command SHALL remain non-ready until the provider returns to a freeform prompt, but SHALL NOT be treated as an operator-blocked failure solely because it is modal.
For `shadow_only`, a surface with `business_state = awaiting_operator` SHALL be treated as blocked and SHALL fail the active turn with explicit blocked-surface diagnostics.
For `shadow_only`, a surface with `business_state = working` and `input_mode = freeform` SHALL remain in progress and SHALL NOT be treated as submit-ready or complete merely because typing is possible.

The runtime SHALL NOT mix parser families in one turn. If a mode-specific parser/projection step fails, the turn SHALL fail without invoking the other mode in the same turn.
The runtime SHALL NOT perform an automatic retry under the other parser mode after a mode-specific failure.

#### Scenario: `cao_only` waits for CAO status and uses `mode=last`
- **WHEN** a developer sends a prompt via a CAO-backed session with `parsing_mode=cao_only` while the terminal is `processing`
- **THEN** the system polls CAO terminal status until it becomes `idle|completed` (or timeout)
- **AND THEN** the system sends direct terminal input
- **AND THEN** the system waits for completion using CAO status and fetches answer text from `output?mode=last`

#### Scenario: `shadow_only` waits for derived submit-ready surface and returns projected dialog
- **WHEN** a developer sends a prompt via a CAO-backed session with `parsing_mode=shadow_only`
- **THEN** the system polls `output?mode=full` and computes runtime shadow readiness and completion from provider surface assessment plus runtime turn-monitor logic
- **AND THEN** the system sends direct terminal input only after the derived submit-ready surface is observed
- **AND THEN** after turn completion the system surfaces projected dialog data and state or provenance metadata derived from `mode=full`

#### Scenario: `shadow_only` mailbox commands wait for stronger command-owned terminal evidence
- **WHEN** a `shadow_only` CAO-backed mailbox turn returns to the submit-ready surface with post-submit progress evidence
- **AND WHEN** the required mailbox sentinel-delimited result for the active request is not yet visible in post-submit shadow text
- **THEN** the runtime treats generic shadow completion as provisional and keeps polling
- **AND THEN** the command does not surface success or a missing-sentinel parse failure until the mailbox contract is satisfied or the turn fails under the existing bounded policy

#### Scenario: Historical slash-command output does not block recovered shadow readiness
- **WHEN** a developer previously used a slash command or manual model switch in a CAO-backed session
- **AND WHEN** that slash-command echo or result is still visible in `output?mode=full`
- **AND WHEN** the current provider surface has already returned to `availability = supported`, `business_state = idle`, and `input_mode = freeform`
- **THEN** the runtime treats the session as shadow-ready
- **AND THEN** it sends the next direct terminal input instead of waiting for a different surface classification

#### Scenario: Active slash-command surface remains non-ready without becoming blocked
- **WHEN** a `shadow_only` CAO-backed session is still showing an active slash-command surface
- **AND WHEN** the provider classifies that surface as `business_state = idle` and `input_mode = modal`
- **THEN** the runtime does not submit the next prompt
- **AND THEN** it continues waiting for a freeform prompt instead of failing the turn as operator-blocked

#### Scenario: Working but typeable surface remains in progress
- **WHEN** a post-submit `shadow_only` observation shows `business_state = working` and `input_mode = freeform`
- **THEN** the runtime keeps the turn in an in-progress lifecycle path
- **AND THEN** it does not complete the turn merely because freeform typing is possible

#### Scenario: Operator-blocked surface fails explicitly
- **WHEN** a `shadow_only` CAO-backed turn observes a surface with `business_state = awaiting_operator`
- **THEN** the runtime fails the turn with an explicit blocked-surface error
- **AND THEN** the failure includes provider-specific diagnostics when an excerpt is available

#### Scenario: `shadow_only` does not complete on submit-ready surface alone when no post-submit evidence exists
- **WHEN** a `shadow_only` turn returns to the derived submit-ready surface
- **AND WHEN** the runtime has not observed post-submit `business_state = working`
- **AND WHEN** normalized shadow text has not changed since submit
- **THEN** the runtime does not mark the turn complete yet
- **AND THEN** it continues monitoring or fails according to turn-monitor timeout or stall policy

#### Scenario: No in-turn parser mixing on failure
- **WHEN** mode-specific projection or state-evaluation fails during a CAO-backed turn
- **THEN** the system returns a mode-specific error
- **AND THEN** the system does not fall back to the other parser mode within the same turn

#### Scenario: No cross-mode automatic retry after failure
- **WHEN** a CAO-backed turn fails in `parsing_mode=shadow_only` or `parsing_mode=cao_only`
- **THEN** the system reports the mode-specific failure
- **AND THEN** the system does not automatically retry the turn under the other parser mode

### Requirement: Shadow TurnMonitor evaluates two-axis surfaces in deterministic priority order
For CAO sessions in `parsing_mode=shadow_only`, runtime SHALL feed each parsed observation into a stateful turn monitor that preserves post-submit progress evidence across observations.

At minimum, the readiness path SHALL evaluate each observation in this priority order:

1. `availability in {unsupported, disconnected}` -> fail
2. `business_state = awaiting_operator` -> blocked outcome
3. unknown-for-stall surface -> unknown or stalled path
4. otherwise remain in readiness waiting, and submit only when `submit_ready`

At minimum, the completion path SHALL evaluate each observation in this priority order:

1. update progress evidence from normalized shadow text change derived from `DialogProjection.normalized_text` and `business_state = working`
2. `availability in {unsupported, disconnected}` -> fail
3. `business_state = awaiting_operator` -> blocked outcome
4. unknown-for-stall surface -> unknown or stalled path
5. `business_state = working` -> keep `in_progress` regardless of `input_mode`
6. `submit_ready` plus previously-seen progress evidence plus completion stability window elapsed -> complete
7. otherwise remain in a post-submit waiting state

The turn monitor SHALL be implemented as ReactiveX pipelines using `reactivex` operators for temporal logic rather than hand-rolled mutable fields and manual timestamp arithmetic.
The turn monitor's temporal operators SHALL consume the full classified-state stream so non-target observations can cancel pending stall and completion timers instead of being hidden behind filtered sub-streams.

#### Scenario: Working modal surface remains in progress during completion
- **WHEN** a post-submit `shadow_only` observation shows `availability = supported`, `business_state = working`, and `input_mode = modal`
- **THEN** the runtime keeps the turn in an in-progress lifecycle path
- **AND THEN** it does not complete the turn or treat the modal input mode as a blocked outcome by itself

#### Scenario: Awaiting-operator surface is evaluated before ready or complete
- **WHEN** a `shadow_only` observation shows `business_state = awaiting_operator`
- **THEN** the runtime routes the observation to a blocked-surface outcome before considering ready or completion gating
- **AND THEN** it does not treat that observation as submit-ready or completed

### Requirement: Shadow completion requires stability window before declaring turn complete
For CAO sessions in `parsing_mode=shadow_only`, the runtime SHALL accept a configurable stability window (`completion_stability_seconds`) from the CAO shadow policy config surface and SHALL NOT declare a turn complete on a single idle observation after post-submit activity. Instead, the runtime SHALL require `completion_stability_seconds` of continuous idle observations with no state changes before emitting a completion event.

When unset, `completion_stability_seconds` SHALL default to 1.0 second.

Each new state change (`DialogProjection.normalized_text` change after pipeline normalization, `business_state` transition) observed during the stability window SHALL reset the stability timer.

The stability window applies only to generic shadow completion. Caller-owned completion observers (e.g., mailbox sentinel detection) that find a definitive result MAY bypass the stability window and complete immediately.

#### Scenario: Transient idle flicker does not trigger false completion
- **WHEN** a post-submit `shadow_only` observation shows `submit_ready` after previously observing `working`
- **AND WHEN** a subsequent observation within `completion_stability_seconds` shows `business_state = working` again
- **THEN** the runtime resets the stability timer and does not declare the turn complete
- **AND THEN** the runtime continues monitoring for sustained idle

#### Scenario: Sustained idle after activity triggers completion
- **WHEN** a post-submit `shadow_only` observation shows `submit_ready` after previously observing `working`
- **AND WHEN** no further state changes occur for `completion_stability_seconds`
- **THEN** the runtime declares the turn complete

#### Scenario: Normalized shadow text change resets stability window
- **WHEN** a post-submit `shadow_only` observation shows `submit_ready` after previously observing `working`
- **AND WHEN** the normalized shadow text changes again before `completion_stability_seconds` elapses
- **THEN** the runtime resets the stability timer
- **AND THEN** it continues monitoring for a fresh sustained-idle window

#### Scenario: Mailbox observer bypasses stability window on definitive result
- **WHEN** a `shadow_only` mailbox turn's completion observer detects a valid sentinel-delimited result in post-submit shadow text
- **THEN** the runtime completes the turn immediately with that result
- **AND THEN** the generic stability window does not delay the mailbox result

### Requirement: Shadow turn monitor supports deterministic time-based testing
The shadow turn monitor's temporal logic SHALL be testable with deterministic virtual-time scheduling. Unit tests SHALL be able to advance time precisely, verify debounce windows, timeout thresholds, and observation sequences without real sleeps or wall-clock timing dependencies.

#### Scenario: Unit test verifies debounce window with virtual time
- **WHEN** a test creates a shadow completion pipeline with a `TestScheduler`
- **AND WHEN** the test advances virtual time past the stability window after emitting an idle observation
- **THEN** the pipeline emits a completion event at the expected virtual timestamp

#### Scenario: Unit test verifies stall timeout with virtual time
- **WHEN** a test creates a shadow readiness pipeline with a `TestScheduler`
- **AND WHEN** the test emits unknown observations and advances virtual time past the stall threshold
- **THEN** the pipeline emits a stalled event at the expected virtual timestamp

### Requirement: Shadow runtime distinguishes operator-blocked surfaces from modal non-ready surfaces
For CAO sessions in `parsing_mode=shadow_only`, runtime SHALL distinguish between surfaces that are blocked on operator action and surfaces that are merely modal or otherwise not yet freeform-ready.

At minimum:

- `business_state = awaiting_operator` SHALL be treated as a blocked-surface outcome,
- `business_state = idle` with `input_mode = modal` SHALL remain non-ready without becoming a blocked-surface error by itself, and
- `business_state = working` with `input_mode = freeform` SHALL remain in progress instead of being treated as ready.

#### Scenario: Modal slash-command surface keeps waiting instead of failing
- **WHEN** a `shadow_only` readiness check observes `business_state = idle` and `input_mode = modal`
- **THEN** the runtime keeps waiting for readiness
- **AND THEN** it does not fail the session as blocked solely because the input mode is modal

#### Scenario: Awaiting-operator surface becomes a blocked outcome
- **WHEN** a `shadow_only` observation shows `business_state = awaiting_operator`
- **THEN** the runtime reports a blocked-surface outcome
- **AND THEN** it does not treat that surface as either ready or completed

### Requirement: Shared post-processing provides a stable runtime contract in both modes
For CAO-backed turns in both `parsing_mode=cao_only` and `parsing_mode=shadow_only`, the runtime SHALL apply a shared, parser-agnostic post-processing step after mode-specific gating/output handling.

This shared post-processing step SHALL NOT sanitize/rewrite `cao_only` extracted answer text. It SHALL canonicalize status/provenance into runtime-stable values for downstream consumers and record/log raw backend values for diagnostics.

For `shadow_only`, shared post-processing SHALL distinguish projected dialog content from any caller-owned answer association logic, SHALL expose first-class `dialog_projection` and `surface_assessment` payload fields, and SHALL NOT label projected dialog as the authoritative final answer for the current prompt by default.
For `shadow_only`, the surfaced `dialog_projection` SHALL remain a best-effort text projection that is suitable for operator inspection and caller-owned best-effort extraction. Lifecycle change evidence MAY instead use normalized shadow text derived from the same parser output, and projected dialog SHALL NOT be represented as an exact recovered reply transcript.
For `shadow_only`, downstream machine-critical parsing SHALL rely on explicit schema-shaped output contracts or caller-owned extraction rules over the available text surfaces rather than on projection fidelity alone.
For `shadow_only`, shared post-processing SHALL NOT preserve `output_text` as a compatibility alias to projected dialog.
If raw CAO `tail` text is retained for debugging, it SHALL remain in diagnostics or internal-only fields and SHALL NOT become a first-class caller-facing shadow result field.

#### Scenario: Shared post-processing runs regardless of parsing mode
- **WHEN** a CAO-backed turn completes in `parsing_mode=cao_only` or `parsing_mode=shadow_only`
- **THEN** shared post-processing is applied before the result is surfaced to the caller

#### Scenario: `shadow_only` payload distinguishes projection from authoritative answer
- **WHEN** a CAO-backed `shadow_only` turn completes
- **THEN** the surfaced runtime payload includes projected dialog/provenance data and surface-assessment data as first-class fields
- **AND THEN** the payload does not include a shadow-mode `output_text` compatibility alias
- **AND THEN** any retained raw tail debugging data remains outside the primary caller-facing result surface
- **AND THEN** the runtime does not represent that projection as the authoritative final answer or as an exact recovered reply transcript for the submitted prompt

#### Scenario: Machine-critical shadow consumer uses explicit extraction contract
- **WHEN** a downstream caller needs reliable machine-readable data from a `shadow_only` result
- **THEN** the runtime exposes the best-effort projection surfaces without claiming exact reply extraction
- **AND THEN** the caller uses an explicit schema-shaped contract or caller-owned extractor to recover the needed payload

### Requirement: CAO profiles are unique per session
When using CAO, the system SHALL generate an agent profile file that is unique per session (append-only) and does not overwrite a stable per-role profile file.

#### Scenario: Two CAO sessions with the same role generate distinct profile names
- **WHEN** a developer launches two CAO-backed sessions with the same role `R`
- **THEN** the system generates two distinct CAO profile names (e.g., `<role_name>_<timestamp>_<uuid4hex>`) and writes two distinct profile files

### Requirement: Runtime CLI uses `--agent-identity` for session control and drops `--session-manifest`
The system SHALL expose a `--agent-identity <name|manifest-path>` argument on runtime CLI commands that control an existing session (at minimum `send-prompt` and `stop-session`).

The system SHALL NOT accept `--session-manifest` on those commands.

#### Scenario: `send-prompt` targets a session via `--agent-identity`
- **WHEN** a developer runs the `send-prompt` CLI command with `--agent-identity <identity>`
- **THEN** the runtime resolves `<identity>` to a session manifest and sends the prompt to that session

#### Scenario: `stop-session` targets a session via `--agent-identity`
- **WHEN** a developer runs the `stop-session` CLI command with `--agent-identity <identity>`
- **THEN** the runtime resolves `<identity>` to a session manifest and stops that session

#### Scenario: Legacy `--session-manifest` is rejected
- **WHEN** a developer invokes `send-prompt` or `stop-session` with `--session-manifest`
- **THEN** the CLI rejects the invocation with an explicit argument validation error

### Requirement: CAO session start supports a human agent identity name and persists the actual tmux session name
When starting a CAO-backed session, the system SHALL allow the caller to provide an agent identity name via `start-session --agent-identity <name>` (name-only for CAO in this change).
For CAO-backed sessions, the system SHALL persist the canonical `AGENTSYS-...` identity separately from the actual tmux session name used for the live session.

If the caller does not provide a name, the system SHALL generate a short, easy-to-type name derived from the tool and role/blueprint identity, and SHALL add a conflict-avoiding suffix when needed.

#### Scenario: Start CAO session with an explicit name persists the canonical identity
- **WHEN** a developer starts a CAO-backed session with `start-session --agent-identity gpu`
- **THEN** the persisted canonical agent identity for the session is `AGENTSYS-gpu`
- **AND THEN** the actual tmux session name is persisted separately as the live-session handle

#### Scenario: Start CAO session without a name auto-generates a short identity
- **WHEN** a developer starts a CAO-backed session without providing `--agent-identity`
- **THEN** the runtime selects a short canonical `AGENTSYS-...` identity derived from tool + role/blueprint
- **AND THEN** the selected identity remains distinct from the actual tmux session name used for the live session

### Requirement: CAO session start returns the selected agent identity and tmux session handle
For CAO-backed sessions, the `start-session` CLI output SHALL include the selected canonical agent identity and the persisted actual tmux session name so callers can reuse the identity while retaining the true live-session handle in diagnostics.

#### Scenario: `start-session` output includes the canonical identity and tmux session name
- **WHEN** a developer starts a CAO-backed session
- **THEN** the `start-session` CLI output includes the selected canonical agent identity (for example `AGENTSYS-gpu`)
- **AND THEN** the same output includes the actual persisted tmux session name for that live session

### Requirement: CAO `start-session` output includes resolved parsing mode
For CAO-backed sessions, the `start-session` CLI output SHALL include the resolved `parsing_mode` alongside the canonical agent identity.

#### Scenario: Start-session output includes parsing mode
- **WHEN** a developer starts a CAO-backed session with `parsing_mode=cao_only` or `parsing_mode=shadow_only`
- **THEN** the `start-session` output includes the resolved `parsing_mode`

### Requirement: Parsing mode changes do not alter AGENTSYS identity/addressing contracts
Changing runtime parsing mode SHALL NOT redefine the active Houmao identity or addressing contracts. Parsing-mode differences do not rename canonical agent identities, mailbox addressing, or tmux-published discovery pointers away from the `HOUMAO-*` / `HOUMAO_*` family selected by this change.

#### Scenario: Parsing mode change preserves the HOUMAO namespace contract
- **WHEN** the runtime starts two equivalent sessions that differ only in parsing mode
- **THEN** both sessions persist canonical `HOUMAO-...` identity metadata
- **AND THEN** both sessions publish `HOUMAO_MANIFEST_PATH` and related `HOUMAO_*` discovery variables rather than reverting to `AGENTSYS_*`

### Requirement: Name-addressed tmux-backed session control SHALL recover `agent_def_dir` from session environment
Name-addressed tmux-backed control SHALL prefer the tmux-published `HOUMAO_MANIFEST_PATH` and `HOUMAO_AGENT_DEF_DIR` values when they are present and valid.

#### Scenario: Name-addressed control recovers the agent-definition root from HOUMAO tmux env
- **WHEN** tmux session `HOUMAO-chris` exists
- **AND WHEN** that tmux session publishes valid `HOUMAO_MANIFEST_PATH` and `HOUMAO_AGENT_DEF_DIR` values
- **THEN** name-addressed tmux-backed session control resolves the manifest and effective agent-definition root from those `HOUMAO_*` values

### Requirement: Runtime-launched agent subprocess env injects loopback `NO_PROXY` by default
For supported loopback compatibility base URLs, the runtime SHALL bypass ambient proxy environment variables by default by ensuring loopback entries exist in `NO_PROXY` and `no_proxy`.

When `HOUMAO_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY` or `no_proxy` and will respect caller-provided values.

#### Scenario: Preserve mode does not modify loopback no-proxy entries
- **WHEN** the runtime launches against a supported loopback compatibility base URL
- **AND WHEN** caller environment includes `HOUMAO_PRESERVE_NO_PROXY_ENV=1`
- **THEN** the runtime does not inject or modify `NO_PROXY` or `no_proxy`

### Requirement: Runtime CLI exposes a `send-keys` raw control-input path distinct from prompt submission
The runtime SHALL provide a caller-facing `send-keys` control-input command for resumed CAO-backed tmux sessions that is distinct from `send-prompt`.

The runtime session-control surface SHALL expose the corresponding advanced mixed-input operation as `send_input_ex()`.

The existing `send-prompt` command SHALL retain its current high-level prompt-turn semantics.

The control-input command SHALL:
- require `--agent-identity` and `--sequence`,
- support the global `--escape-special-keys` flag and the existing optional `--agent-def-dir` override pattern,
- accept the mixed sequence grammar defined by `runtime-tmux-control-input`,
- deliver the requested input without automatically pressing `Enter`, and
- return a single `SessionControlResult` with `action="control_input"` after delivery without waiting for prompt completion or advancing prompt-turn state, and
- append one recorder-managed control-input event to the addressed recorder artifacts when an `active` terminal recorder is live for the same tmux-backed session.

#### Scenario: Prompt submission path remains unchanged
- **WHEN** a developer uses `send-prompt` against a resumed CAO-backed session
- **THEN** the runtime continues to use the existing prompt-turn submission path
- **AND THEN** this change does not require callers to switch away from `send-prompt` for ordinary turn submission

#### Scenario: Raw control-input path returns after delivery
- **WHEN** a developer uses the control-input command against a resumed CAO-backed session
- **THEN** the runtime routes the request through `send_input_ex()` and delivers the requested control-input sequence to the live terminal
- **AND THEN** it returns a `SessionControlResult` with `action="control_input"` without waiting for turn completion or output extraction

#### Scenario: `send-keys` uses an explicit CLI contract
- **WHEN** a developer invokes `send-keys --agent-identity my-agent --sequence '/model<[Enter]>'`
- **THEN** the runtime accepts the request without requiring a positional sequence argument
- **AND THEN** it returns one JSON control-action result object rather than streaming prompt-turn events

#### Scenario: Active recorder receives managed control-input events
- **WHEN** a developer invokes `send-keys` for a tmux-backed CAO session that is currently targeted by a live `active` terminal recorder
- **THEN** the runtime still delivers the requested control-input sequence to the live terminal
- **AND THEN** it appends a structured managed control-input event to that recorder's input-event artifacts before returning

### Requirement: CAO raw control input uses manifest-driven tmux target resolution
For CAO-backed sessions resumed by `agent_identity`, the runtime SHALL resolve the tmux target for raw control input from persisted runtime session state and CAO terminal metadata as needed.

The persisted CAO manifest section SHALL treat `tmux_window_name` as an optional field so existing manifests remain valid and newer manifests can reuse the stored window name when available.

The caller SHALL NOT be required to provide raw tmux session names, window names, or window ids.

#### Scenario: Resumed CAO session receives control input by agent identity
- **WHEN** a developer resumes a CAO-backed session using `agent_identity`
- **AND WHEN** they invoke the control-input command with a mixed sequence
- **THEN** the runtime resolves the corresponding tmux target from manifest-backed CAO session state
- **AND THEN** it delivers the requested control-input sequence without requiring the caller to discover raw tmux identifiers manually

#### Scenario: Older manifests remain usable without persisted window metadata
- **WHEN** a developer invokes the control-input command for an older CAO session manifest that does not contain `cao.tmux_window_name`
- **THEN** the runtime falls back to CAO terminal metadata to resolve the live tmux target
- **AND THEN** the older manifest remains valid for control-input use

#### Scenario: Missing tmux target fails explicitly
- **WHEN** a developer invokes the control-input command for a CAO-backed session whose tmux target cannot be resolved from persisted state or CAO terminal metadata
- **THEN** the runtime fails with an explicit target-resolution error
- **AND THEN** the error explains that the live tmux target could not be determined for that session

### Requirement: Raw control input is CAO-scoped in the initial runtime release
The initial runtime control-input command SHALL support tmux-backed `backend=cao_rest` sessions only.

If a caller invokes the control-input command for a different backend, the runtime SHALL fail with an explicit unsupported-backend error instead of silently attempting a different input path.

#### Scenario: Non-CAO backend is rejected for control input
- **WHEN** a developer invokes the control-input command for a resumed `claude_headless`, `codex_headless`, `gemini_headless`, or `codex_app_server` session
- **THEN** the runtime rejects the request with an explicit unsupported-backend error
- **AND THEN** it does not attempt to translate the request into `send-prompt` or another fallback path

### Requirement: CAO session startup fixes "shell-first attach" and prunes the bootstrap window when safe
For CAO-backed session startup (`backend=cao_rest`), when the runtime pre-creates one bootstrap tmux window for env setup and CAO subsequently creates the real agent terminal window, the runtime SHALL best-effort make the CAO terminal window the session's current tmux window and SHALL prune the bootstrap window when it can be safely identified as distinct from the CAO terminal window.

The runtime SHALL record the bootstrap tmux `window_id` immediately after session creation and SHALL use `window_id` targeting, rather than index assumptions, for window selection and pruning.

The runtime SHALL resolve the CAO terminal window id from `terminal.name` using bounded retry to tolerate transient tmux visibility races. If the CAO window cannot be resolved within the bound, startup SHALL still succeed and the runtime SHALL emit a warning diagnostic.

The runtime SHOULD use the `create_terminal(...)` response `terminal.name` as
the CAO tmux window name (no extra `GET /terminals/{id}` is required solely to
obtain the name).

#### Scenario: Successful CAO startup leaves only the agent terminal window (and first attach lands on it)
- **WHEN** a developer starts a CAO-backed session and terminal creation succeeds
- **AND WHEN** the recorded bootstrap window differs from the resolved CAO terminal window
- **THEN** the runtime selects the CAO terminal window as the session's current window
- **AND THEN** the runtime removes the recorded bootstrap window from that tmux session
- **AND THEN** the tmux session remains active with the CAO terminal window

### Requirement: Bootstrap-window pruning is targeted and non-fatal
Bootstrap-window pruning for CAO-backed startup SHALL be best-effort.
The runtime SHALL target only the recorded bootstrap window and SHALL NOT
terminate the resolved CAO terminal window.

#### Scenario: Startup does not fail when bootstrap-window pruning fails
- **WHEN** CAO terminal creation succeeds but bootstrap-window pruning returns an error
- **THEN** `start-session` still succeeds and returns the selected agent identity
- **AND THEN** the runtime selects the CAO terminal window as the session's current window (best-effort)
- **AND THEN** the runtime emits a warning diagnostic describing the prune failure

#### Scenario: Startup warns when CAO terminal window cannot be resolved within the bound
- **WHEN** CAO terminal creation succeeds but the runtime cannot resolve `terminal.name` to a tmux `window_id` within the bounded retry policy
- **THEN** `start-session` still succeeds
- **AND THEN** the runtime emits a warning diagnostic describing the resolution failure

#### Scenario: Runtime skips prune when bootstrap and terminal window are the same
- **WHEN** the recorded bootstrap window resolves to the same tmux window as the CAO terminal
- **THEN** the runtime skips bootstrap-window deletion
- **AND THEN** the CAO terminal remains active for subsequent prompt/stop operations

### Requirement: Runtime-owned tmux sessions may publish gateway attachability independently from a running gateway
The runtime SHALL be able to make a tmux-backed session gateway-capable without requiring a gateway process to already be running.

For runtime-owned tmux-backed sessions, the runtime SHALL publish secret-free gateway attach metadata that later attach flows can use to start a gateway for the live session.

That attachability publication SHALL be additive and SHALL NOT make legacy non-gateway start or resume behavior fail by itself.

Blueprint `gateway.host` and `gateway.port` values SHALL act only as defaults after gateway attach is requested and SHALL NOT make a session gateway-capable or gateway-running by themselves.

In this change, the runtime SHALL publish attach metadata by default for newly started runtime-owned tmux-backed sessions and SHALL re-publish attach metadata on resume whenever attachability can be reconstructed from persisted session state. It SHALL support live gateway attach for every runtime-owned tmux-backed backend whose gateway execution adapter is implemented, including the runtime-owned REST-backed sessions, runtime-owned native headless sessions, and runtime-owned `local_interactive` sessions.

Gateway attach MAY happen later against the already-running tmux-backed session by using the published attach metadata, tmux session environment, and persisted manifest pointer for that session rather than by requiring gateway lifecycle decisions to be baked into the original launch command.

Supplying gateway listener overrides during session startup without a separate attach lifecycle action SHALL fail with an explicit error.

If a caller requests live gateway attach for any backend whose gateway adapter is not yet implemented, the runtime SHALL fail with an explicit unsupported-backend error rather than silently falling back to implicit direct control.

#### Scenario: Blueprint gateway defaults do not auto-attach the gateway by themselves
- **WHEN** a developer starts a session from a blueprint that declares `gateway.host` or `gateway.port`
- **AND WHEN** the developer does not invoke a separate gateway attach lifecycle action
- **THEN** the runtime publishes attachability metadata for that session
- **AND THEN** the blueprint listener defaults do not cause a live gateway instance to start by themselves

#### Scenario: Gateway host or port overrides require an attach action
- **WHEN** a developer supplies gateway host or port overrides during session startup without an explicit attach lifecycle action
- **THEN** the runtime fails with an explicit gateway-lifecycle error
- **AND THEN** the session is not treated as having a live gateway instance implicitly

#### Scenario: Later gateway attach reuses tmux session env and manifest-backed authority
- **WHEN** a developer starts a runtime-owned tmux-backed session and later invokes gateway attach from the same tmux session or another attach-aware control path
- **THEN** the runtime resolves that live session through the published attach metadata and tmux session environment for that session
- **AND THEN** the developer does not need to have coupled gateway startup to the original launch command

#### Scenario: Runtime-owned headless backend can attach a live gateway when its adapter exists
- **WHEN** a developer requests live gateway attach for a runtime-owned tmux-backed native headless session whose gateway execution adapter is implemented
- **THEN** the runtime attaches a live gateway for that headless session
- **AND THEN** the runtime does not reject that attach request merely because the session is not REST-backed

#### Scenario: Runtime-owned local interactive backend can attach a live gateway when its adapter exists
- **WHEN** a developer requests live gateway attach for a runtime-owned tmux-backed `local_interactive` session whose gateway execution adapter is implemented
- **THEN** the runtime attaches a live gateway for that session
- **AND THEN** the runtime does not reject that attach request merely because the session is a serverless local interactive TUI rather than a REST-backed or native headless session

#### Scenario: Unsupported backend still rejects live gateway attach explicitly
- **WHEN** a developer requests live gateway attach for a runtime-owned tmux-backed backend whose gateway execution adapter is not implemented
- **THEN** the runtime fails that attach request with an explicit unsupported-backend error
- **AND THEN** the runtime does not silently convert that attach request into legacy direct control

### Requirement: Runtime-owned tmux sessions materialize internal gateway artifacts under the session root
When the runtime makes a tmux-backed session gateway-capable, it SHALL materialize session-owned gateway artifacts under the nested `gateway/` directory of that session root.

Those artifacts MAY include internal bootstrap state such as `attach.json`, derived outward-facing bookkeeping such as `gateway_manifest.json`, seeded `state.json`, and queue or bootstrap assets needed by runtime or gateway internals.

For runtime-owned sessions in v1, the canonical runtime-owned session root SHALL be `<runtime_root>/sessions/<backend>/<session_id>/`, using the runtime-generated session id used for manifest storage. The session manifest SHALL live at `<session-root>/manifest.json`, and the gateway root SHALL live at `<session-root>/gateway`.

Manifest-backed authority plus tmux-published manifest-first discovery SHALL remain the supported external contract. Internal gateway artifacts SHALL support runtime and gateway internals without redefining the authoritative attach or relaunch contract.

#### Scenario: Session start materializes internal gateway artifacts without a live gateway
- **WHEN** a developer starts a runtime-owned tmux-backed session without launch-time gateway attach
- **THEN** the runtime materializes the session-owned gateway root and its internal or derived artifacts for that live session
- **AND THEN** the session can remain gateway-capable even though no gateway instance is currently running

#### Scenario: Resume re-materializes internal gateway artifacts
- **WHEN** the runtime resumes control of a runtime-owned tmux-backed session
- **AND WHEN** gateway capability for that session can be determined from persisted session state
- **THEN** the runtime refreshes the applicable internal or derived gateway artifacts for that live session
- **AND THEN** later attach flows continue to resolve supported authority from `manifest.json` plus tmux or registry discovery

#### Scenario: Runtime-owned session root and gateway root use the persisted session id
- **WHEN** the runtime starts a runtime-owned tmux-backed session with generated session id `cao_rest-20260312-120000Z-abcd1234`
- **THEN** the stable runtime-owned session root for that session is derived from that persisted session id under `<runtime_root>/sessions/<backend>/<session_id>/`
- **AND THEN** the session manifest path for that session is `<session-root>/manifest.json`
- **AND THEN** the gateway root for that session is `<session-root>/gateway`

### Requirement: Runtime supports optional launch-time auto-attach for supported backends
When a caller explicitly requests launch-time gateway attach for a supported backend, the runtime SHALL start the agent session, resolve attach metadata for that live session, and then start a gateway instance without restarting the agent.

When launch-time auto-attach fails, the runtime SHALL fail that auto-attach action explicitly.

If the managed agent session has already started successfully when auto-attach fails, the runtime SHALL keep that managed session running and SHALL return a structured partial-start failure rather than tearing the session down implicitly.

#### Scenario: Launch-time auto-attach starts gateway after session startup
- **WHEN** a developer starts a supported runtime-owned tmux-backed session with launch-time gateway attach requested
- **THEN** the runtime starts the managed session first
- **AND THEN** the runtime starts a gateway instance for that live session using the published attach metadata
- **AND THEN** the managed session does not need to be restarted in order to gain gateway support

#### Scenario: Auto-attach failure reports explicit lifecycle error
- **WHEN** launch-time auto-attach fails after the managed tmux session has already started
- **THEN** the runtime reports an explicit gateway-attach error
- **AND THEN** the already-started managed session remains running
- **AND THEN** the failure surface includes the live session manifest path or identity needed for later retry or explicit stop

### Requirement: Gateway host is resolved and gateway port is finalized when a gateway instance is started
For gateway attach or launch-time auto-attach actions, the runtime SHALL resolve one effective gateway host and one effective gateway port request before starting that gateway instance.

The precedence order for the effective gateway host SHALL be:

1. lifecycle CLI override for the attach action in progress
2. caller environment variable `HOUMAO_AGENT_GATEWAY_HOST`
3. blueprint configuration value `gateway.host`
4. default `127.0.0.1`

Allowed effective gateway host values in this change are exactly `127.0.0.1` and `0.0.0.0`.

The precedence order for the effective gateway port SHALL be:

1. lifecycle CLI override for the attach action in progress
2. caller environment variable `HOUMAO_AGENT_GATEWAY_PORT`
3. blueprint configuration value `gateway.port`
4. a system-assigned port request during gateway startup when none of the above are provided

When none of the above sources provide a gateway port, the runtime SHALL request a system-assigned port during gateway startup and SHALL NOT pre-probe a free port in the parent runtime process.

After resolving that effective gateway host and effective gateway port request, the runtime SHALL use the resolved host and the actual bound port for the active gateway instance's metadata, tmux environment publication, and gateway startup.

If the resolved gateway listener cannot be bound during gateway start, the runtime SHALL fail that attach or auto-attach action explicitly and SHALL NOT silently replace it with a different host or port.

When a gateway instance starts successfully with a system-assigned port, the runtime SHALL persist that resolved host and port as the desired listener for the gateway root and SHALL reuse them on later restarts unless a caller explicitly overrides them.

#### Scenario: Default host remains loopback when no host override is supplied
- **WHEN** a developer starts a gateway attach action without an explicit gateway-host override
- **AND WHEN** caller environment omits `HOUMAO_AGENT_GATEWAY_HOST`
- **AND WHEN** the selected blueprint does not declare `gateway.host`
- **THEN** the runtime resolves `127.0.0.1` as the effective gateway host for that session
- **AND THEN** the started session does not expose all-interface binding by default

#### Scenario: Explicit gateway-host override enables all-interface bind
- **WHEN** a developer starts a gateway attach action with `--gateway-host 0.0.0.0`
- **THEN** the runtime resolves `0.0.0.0` as the effective gateway host for that session
- **AND THEN** the started gateway instance binds its HTTP listener on all interfaces for the resolved port

#### Scenario: CLI gateway-port override wins over env and blueprint defaults
- **WHEN** a developer starts a gateway attach action with `--gateway-port 43123`
- **AND WHEN** caller environment sets `HOUMAO_AGENT_GATEWAY_PORT=43124`
- **AND WHEN** the selected blueprint declares `gateway.port: 43125`
- **THEN** the runtime resolves `43123` as the effective gateway port for that session
- **AND THEN** the started session records and publishes `43123` as its gateway port

#### Scenario: Env gateway-port override wins over blueprint default
- **WHEN** a developer starts a gateway attach action without `--gateway-port`
- **AND WHEN** caller environment sets `HOUMAO_AGENT_GATEWAY_PORT=43124`
- **AND WHEN** the selected blueprint declares `gateway.port: 43125`
- **THEN** the runtime resolves `43124` as the effective gateway port for that session
- **AND THEN** the started session does not treat the blueprint default as the effective port

#### Scenario: Runtime requests a system-assigned port when no explicit gateway port is supplied
- **WHEN** a developer starts a gateway attach action without `--gateway-port`
- **AND WHEN** caller environment omits `HOUMAO_AGENT_GATEWAY_PORT`
- **AND WHEN** the selected blueprint does not declare `gateway.port`
- **THEN** the runtime starts gateway startup with a system-assigned port request instead of pre-probing a free local port
- **AND THEN** the started session records and publishes the actual bound port as its effective gateway port

#### Scenario: Successful system-assigned listener becomes the desired listener for restart
- **WHEN** the runtime starts a gateway instance for a session with a system-assigned port request and that gateway startup succeeds
- **THEN** the runtime persists that resolved host and port as the desired listener for that gateway root
- **AND THEN** a later restart reuses that same desired listener unless a caller explicitly overrides it

#### Scenario: Resolved port conflict fails attach
- **WHEN** the runtime attempts to start a gateway instance whose resolved gateway port is unavailable at bind time
- **THEN** the runtime fails that attach action with an explicit gateway-port error
- **AND THEN** it does not silently launch that gateway instance on a different port

### Requirement: Gateway capability and live attach are independent from mailbox enablement
The runtime SHALL allow a gateway-capable or gateway-running tmux-backed session to exist without also enabling mailbox transport or projecting mailbox runtime assets.

Gateway bootstrap, discovery publication, and resumed gateway control SHALL NOT depend on mailbox bindings being present for that session.

#### Scenario: Session start enables gateway without mailbox transport
- **WHEN** a developer makes a tmux-backed session gateway-capable or attaches a gateway with no mailbox transport configured
- **THEN** the runtime still prepares gateway attachability or starts the gateway instance as requested
- **AND THEN** gateway startup does not fail solely because mailbox support is not enabled

#### Scenario: Resume preserves gateway control without mailbox bindings
- **WHEN** a developer resumes control of a gateway-capable or gateway-running tmux-backed session whose gateway metadata is present
- **AND WHEN** mailbox-specific runtime bindings are absent for that session
- **THEN** the runtime still restores gateway discovery and gateway-aware control behavior for that live session
- **AND THEN** resumed gateway control does not require mailbox bindings to be reintroduced

### Requirement: Gateway-capable sessions persist and restore stable attach metadata
For gateway-capable runtime-owned tmux sessions, the runtime SHALL persist the manifest-backed gateway metadata needed to rediscover the same session-owned gateway root and protocol context on resume.

#### Scenario: Session start persists gateway metadata for resume
- **WHEN** a developer starts a gateway-capable runtime-owned tmux session
- **THEN** the runtime persists the gateway metadata needed to rediscover that session's session-owned gateway root and manifest-backed authority later
- **AND THEN** resumed control paths can validate or restore gateway discovery using persisted session state instead of re-deriving an unrelated gateway location

#### Scenario: Resume preserves stable attach identity for a live session
- **WHEN** a developer resumes control of a gateway-capable runtime-owned tmux session
- **THEN** the runtime uses the persisted session state to rediscover the expected session-owned gateway root and manifest-backed authority for that live session
- **AND THEN** the resumed control path does not silently attach the session to a different gateway-capability identity

### Requirement: Runtime-owned recovery preserves stable session identity while allowing managed-agent replacement
For runtime-owned gateway-capable sessions, the runtime SHALL treat the session root, nested gateway root, and stable attach identity as the durable identity of the logical session even if the managed agent process or terminal is restarted or rebound after unexpected failure.

When runtime-owned recovery reconnects to the same managed-agent instance, the runtime SHALL preserve that stable session identity without allocating a new session root or gateway root.

When runtime-owned recovery rebinds the logical session to a replacement managed-agent instance, the runtime SHALL preserve the existing session root, gateway root, and stable attach identity, and SHALL publish a new managed-agent instance epoch or generation for the replacement upstream instance.

Runtime-owned recovery SHALL NOT require allocating a brand-new gateway root solely because the previous managed-agent process died unexpectedly.

#### Scenario: Same logical session survives managed-agent restart
- **WHEN** a runtime-owned gateway-capable session experiences an unexpected managed-agent failure and bounded recovery reconnects or restarts that same logical session
- **THEN** the runtime preserves the original `<session-root>/` and nested `<session-root>/gateway/`
- **AND THEN** the gateway-facing identity of that logical session does not change solely because the managed agent process was restarted

#### Scenario: Replacement managed-agent instance increments the published epoch
- **WHEN** runtime-owned recovery can continue only by binding a replacement managed-agent instance for the same logical session
- **THEN** the runtime keeps the original stable session root and gateway root
- **AND THEN** the runtime publishes a new managed-agent instance epoch or generation for that replacement upstream instance
- **AND THEN** callers can distinguish "same logical session, replacement upstream instance" from "brand-new logical session"

### Requirement: Runtime seeds stable gateway state when no live gateway is attached
When the runtime publishes gateway capability for a runtime-owned tmux session, it SHALL create or materialize the nested gateway directory under that session's runtime root and SHALL seed `state.json` with a protocol-versioned offline or not-attached snapshot even if no live gateway instance exists yet.

When a gateway instance is detached gracefully, the runtime or gateway lifecycle SHALL rewrite `state.json` to the offline or not-attached condition and SHALL clear live gateway bindings while preserving stable attachability metadata.

When runtime-owned recovery observes unexpected managed-agent loss while a gateway remains attached, the runtime or gateway lifecycle SHALL update the shared status contract so that gateway-local health can remain readable while managed-agent connectivity, recovery state, and request-admission state reflect the outage explicitly.

#### Scenario: Session start seeds offline gateway state before first attach
- **WHEN** the runtime starts a gateway-capable runtime-owned tmux session with no launch-time gateway attach requested
- **THEN** the session-owned gateway directory already contains `state.json`
- **AND THEN** that seeded state artifact reports an offline or not-attached gateway condition rather than requiring a missing-file special case

#### Scenario: Graceful detach restores offline seeded state
- **WHEN** a gateway instance detaches gracefully from a gateway-capable runtime-owned tmux session
- **THEN** the system rewrites `state.json` to reflect that no live gateway instance is currently attached
- **AND THEN** the stable gateway root remains usable for later re-attach

#### Scenario: Unexpected managed-agent loss updates shared status without erasing gateway identity
- **WHEN** a gateway instance remains alive but the runtime-owned managed agent becomes unavailable unexpectedly
- **THEN** the shared status contract continues to identify the same logical session and gateway root
- **AND THEN** that status reports managed-agent recovery or unavailability explicitly instead of collapsing immediately to "no gateway attached"

### Requirement: Runtime publishes manifest-first stable discovery pointers and live gateway bindings separately
When the runtime makes a tmux-backed session gateway-capable, it SHALL publish stable manifest-first discovery pointers into the tmux session environment in addition to the existing agent-definition binding.

When a live gateway instance is currently attached, the runtime or gateway lifecycle SHALL also publish live gateway bindings for that running instance.

At minimum, the runtime SHALL publish:

- `HOUMAO_MANIFEST_PATH`
- `HOUMAO_AGENT_ID`

When a live gateway instance exists, the system SHALL additionally publish:

- `HOUMAO_AGENT_GATEWAY_HOST`
- `HOUMAO_AGENT_GATEWAY_PORT`
- `HOUMAO_GATEWAY_STATE_PATH`
- `HOUMAO_GATEWAY_PROTOCOL_VERSION`

The stable tmux discovery pointers SHALL also be the current-session entrypoint for tmux-backed relaunch.

#### Scenario: Session start publishes manifest-first stable discovery pointers
- **WHEN** the runtime starts a gateway-capable tmux-backed session
- **THEN** the tmux session environment contains `HOUMAO_MANIFEST_PATH` and `HOUMAO_AGENT_ID`
- **AND THEN** those bindings point to the stable manifest authority or authoritative identity for that session even when no gateway instance is running

#### Scenario: Live gateway attach publishes active gateway bindings
- **WHEN** the runtime or lifecycle command attaches a live gateway instance to a gateway-capable tmux-backed session
- **THEN** the tmux session environment contains `HOUMAO_AGENT_GATEWAY_HOST`, `HOUMAO_AGENT_GATEWAY_PORT`, `HOUMAO_GATEWAY_STATE_PATH`, and `HOUMAO_GATEWAY_PROTOCOL_VERSION`
- **AND THEN** those bindings point to the currently running gateway instance rather than merely to stable attachability

### Requirement: Runtime-owned stop-session teardown also cleans up a live attached gateway
When the runtime tears down a runtime-owned session through its authoritative `stop-session` path and that session currently has a live attached gateway, the runtime SHALL stop that gateway as part of the same teardown flow.

That runtime-owned teardown SHALL clear live gateway bindings and SHALL rewrite `state.json` to offline or not-attached state while preserving stable attachability metadata.

#### Scenario: Stop-session stops a live attached gateway for a runtime-owned session
- **WHEN** a runtime-owned session still has a live attached gateway and the operator invokes `stop-session`
- **THEN** the runtime stops that gateway as part of the same teardown flow
- **AND THEN** live gateway bindings are removed or invalidated
- **AND THEN** the session-owned `state.json` returns to offline or not-attached state while the stable gateway root remains addressable

### Requirement: Runtime exposes independent gateway attach and detach lifecycle actions
The runtime SHALL provide explicit lifecycle actions for attaching a gateway to a live gateway-capable session and for stopping a currently running gateway instance without stopping the managed agent session.

Attach lifecycle actions SHALL resolve the live session, read its stable attach metadata, and then attempt to start a gateway instance for that session.

Detach lifecycle actions SHALL stop the current gateway instance and preserve stable attachability metadata for later re-attach.

#### Scenario: Attach action starts gateway for a running session
- **WHEN** a developer requests gateway attach for a running gateway-capable tmux-backed session
- **THEN** the runtime resolves the live session and reads its attach metadata
- **AND THEN** the runtime starts a gateway instance without restarting the managed agent

#### Scenario: Detach action stops gateway without stopping the agent
- **WHEN** a developer requests gateway detach for a session that currently has a running gateway instance
- **THEN** the runtime stops that gateway instance
- **AND THEN** the managed agent session remains running
- **AND THEN** the session stays gateway-capable for later re-attach

### Requirement: Gateway-aware runtime control paths submit managed work through the gateway
For sessions with a currently running gateway instance, gateway-aware runtime control paths that submit terminal-mutating managed work SHALL use the session's gateway submission path rather than performing raw concurrent tmux mutation directly from the caller.

In v1, this requirement applies to runtime-owned prompt-submission and interrupt flows.

Read-oriented status inspection MAY read validated gateway state without entering the mutation queue.

In v1, when a gateway-aware control path targets a gateway-capable session with no live gateway instance attached, the runtime SHALL fail with an explicit no-live-gateway error and SHALL NOT auto-attach a gateway as a side effect of that control request.

When the gateway reports that the managed agent is unavailable, recovering, or blocked on reconciliation, gateway-aware runtime control paths SHALL surface those explicit gateway admission results rather than bypassing the gateway with direct concurrent control.

Before a runtime-owned gateway-aware control or status path trusts live gateway bindings, it SHALL validate those bindings structurally against the stable attach metadata and SHALL use `GET /health` as the authoritative liveness check for the live gateway instance.

Supporting files such as `state.json` or run-state metadata MAY be used to improve diagnostics after health failure, but SHALL NOT replace the health endpoint as the primary liveness decision for runtime-owned gateway clients.

#### Scenario: Runtime submits managed work through the gateway queue
- **WHEN** a runtime-owned control path submits gateway-managed terminal-mutating work for a resumed session with a live gateway instance attached
- **THEN** the runtime writes that work through the session's gateway submission path
- **AND THEN** the runtime does not bypass the gateway by performing raw concurrent terminal mutation directly from the caller for that gateway-managed request

#### Scenario: Runtime routes interrupt through the gateway for sessions with a live gateway instance
- **WHEN** an operator or tool requests interrupt for a resumed session with a live gateway instance attached
- **THEN** the runtime submits that interrupt as gateway-managed work
- **AND THEN** the runtime does not bypass the gateway with direct concurrent terminal mutation for that gateway-managed interrupt request

#### Scenario: Runtime preserves gateway admission semantics during upstream recovery
- **WHEN** a resumed session still has a live gateway instance attached but the gateway reports managed-agent recovery or reconciliation blocking
- **THEN** the runtime surfaces the gateway's explicit unavailable or conflict result to the caller
- **AND THEN** the runtime does not fall back to direct raw terminal mutation merely because the upstream agent is temporarily unavailable

#### Scenario: Stale live gateway bindings fail health-first validation
- **WHEN** a runtime-owned gateway-aware control path discovers live gateway env bindings for a session
- **AND WHEN** those bindings are structurally present but `GET /health` does not confirm a live gateway instance
- **THEN** the runtime treats that session as having no live gateway attached for that control path
- **AND THEN** the caller receives the explicit no-live-gateway outcome instead of an arbitrary raw connection failure

#### Scenario: Legacy direct control remains available when no gateway is attached
- **WHEN** a runtime-owned tmux-backed session is gateway-capable but no live gateway instance is currently attached
- **THEN** existing non-gateway direct control paths may still operate according to their legacy behavior
- **AND THEN** absence of a live gateway instance alone does not make the session uncontrollable

#### Scenario: Gateway-aware control does not auto-attach implicitly
- **WHEN** a gateway-aware control path targets a gateway-capable session with no live gateway instance attached
- **THEN** the runtime fails that request with an explicit no-live-gateway error
- **AND THEN** the runtime does not start a gateway instance implicitly as a side effect of that control request

#### Scenario: Runtime reads gateway status without consuming the mutation slot
- **WHEN** an operator or tool asks the runtime for gateway status on a session with a live gateway instance attached
- **THEN** the runtime reads validated gateway state for that session
- **AND THEN** the status read does not require the runtime to consume the gateway's terminal-mutation slot

### Requirement: Runtime-managed session control uses the `realm_controller` module surface
The repo-owned runtime SHALL expose its direct module entrypoint, canonical source-path references, and canonical runtime documentation under the `gig_agents.agents.realm_controller` / `realm_controller` name rather than `brain_launch_runtime`.

This rename SHALL preserve the existing runtime subcommands and their current session-control behavior.

#### Scenario: Module-form runtime invocation uses `realm_controller`
- **WHEN** a developer invokes the runtime through its documented module form
- **THEN** the canonical module path is `gig_agents.agents.realm_controller`
- **AND THEN** the runtime continues to expose the existing subcommands `build-brain`, `start-session`, `send-prompt`, `send-keys`, `mail`, and `stop-session`

#### Scenario: Canonical runtime docs and source mappings use `realm_controller`
- **WHEN** a reader navigates active runtime docs or repo-owned source mappings for the runtime
- **THEN** those docs and mappings use `realm_controller` as the canonical runtime name
- **AND THEN** active guidance does not present `brain_launch_runtime` as the preferred runtime surface

### Requirement: Runtime-owned tmux-backed sessions publish shared-registry discovery records
When the runtime starts or resumes control of a tmux-backed session whose registry launch authority is the runtime, it SHALL publish or refresh a shared-registry record for that live session under the effective shared-registry root's `live_agents/` directory.

The runtime SHALL determine whether it is the launch authority for shared-registry creation from explicit runtime-readable launch metadata associated with that live session or authority record, rather than inferring launch authority from the current registry contents alone.

By default, the effective shared-registry root SHALL be `~/.houmao/registry`.

When `HOUMAO_GLOBAL_REGISTRY_DIR` is set, the runtime SHALL publish and refresh shared-registry records under that override path instead.

For tmux-backed sessions whose launch authority is the runtime, the published shared-registry record SHALL persist the canonical `AGENTSYS-...` agent identity together with the authoritative `agent_id` and the actual tmux session name for that live session.

When runtime publication code receives an agent name in namespace-free form, it SHALL canonicalize that name to the exact `AGENTSYS-...` form before publishing the shared-registry record.

For a given live tmux-backed session whose launch authority is the runtime, the runtime SHALL persist and reuse the same shared-registry `generation_id` across later refreshes and resume-driven republishes of that same session.

That shared-registry record SHALL coexist with existing tmux session environment discovery pointers and SHALL NOT replace `HOUMAO_MANIFEST_PATH`, `HOUMAO_AGENT_DEF_DIR`, or the stable gateway attach pointers already published by the runtime.

The published record SHALL include the secret-free runtime-owned pointers available for that session, including the manifest path, runtime session root, authoritative `agent_id`, actual tmux session name, and any gateway or mailbox pointers that the runtime has already materialized.

For sessions created by another launcher such as `houmao-server`, the runtime SHALL continue publishing the stable tmux, manifest, session-root, and gateway-capability pointers needed for later discovery and attach flows, but it SHALL NOT create or refresh the shared-registry record for that session unless the runtime was also the launcher.

#### Scenario: Direct runtime-owned session start publishes a shared-registry record alongside tmux pointers
- **WHEN** the runtime starts a direct runtime-owned tmux-backed session with canonical identity `AGENTSYS-gpu`
- **THEN** the runtime publishes the normal tmux session environment discovery pointers for that session
- **AND THEN** the runtime also publishes a shared-registry record under `~/.houmao/registry/live_agents/<agent-id>/record.json` for that direct runtime-owned session

#### Scenario: Runtime publication canonicalizes namespace-free agent input
- **WHEN** runtime publication logic receives agent input `gpu` for a tmux-backed session whose launch authority is the runtime
- **THEN** it canonicalizes that input to `AGENTSYS-gpu` before publishing the shared-registry record
- **AND THEN** the published record stores canonical agent name `AGENTSYS-gpu`

#### Scenario: Externally launched session continues pointer publication while deferring registry publication
- **WHEN** the runtime starts or resumes a tmux-backed session that was launched by another authority such as `houmao-server`
- **AND WHEN** the session's launch metadata marks registry creation as external to the runtime
- **THEN** the runtime still publishes the stable manifest, session-root, tmux, and gateway-capability pointers for that session
- **AND THEN** shared-registry publication for that session remains with the external launcher rather than being duplicated by the runtime

### Requirement: Runtime refreshes shared-registry records when runtime-owned publication state changes
When the runtime materializes or refreshes stable gateway capability for a session, attaches or detaches a live gateway, refreshes mailbox bindings, or persists updated runtime-owned session state after prompt or control actions, it SHALL refresh the corresponding shared-registry record for that same logical session when the runtime is the launch authority for registry creation for that session.

When no live gateway is attached, the shared-registry record SHALL continue to publish stable gateway pointers when they exist, but SHALL omit live gateway connect metadata.

When mailbox bindings are available, the shared-registry record SHALL reflect the active mailbox principal id and full mailbox address for that session.

These refreshes SHALL keep the same `generation_id` for the same live session rather than manufacturing a replacement generation on each publication event.

For sessions whose registry launch authority is external to the runtime, the runtime SHALL still materialize or refresh the stable session-root, gateway, and mailbox pointers needed for later publication, but it SHALL NOT independently refresh the shared-registry record for that externally launched session.

#### Scenario: Direct runtime-owned live gateway attach refreshes the shared-registry record
- **WHEN** the runtime attaches a live gateway to a gateway-capable direct runtime-owned session whose launch authority is the runtime
- **THEN** the runtime refreshes the shared-registry record for that session
- **AND THEN** the record publishes the exact live gateway connect metadata for the running listener

#### Scenario: Externally launched gateway attach refreshes pointers for later external publication
- **WHEN** the runtime or gateway layer materializes updated live gateway metadata for a session whose registry launch authority is external to the runtime
- **THEN** the runtime refreshes the stable gateway pointers and other publication inputs for that session
- **AND THEN** the external launcher may consume those refreshed pointers to refresh the shared-registry record for that session without the runtime duplicating publication

#### Scenario: Direct runtime-owned prompt or control action refreshes the registry lease
- **WHEN** the runtime sends a prompt or persists updated state after another runtime-owned control action for a tmux-backed session whose launch authority is the runtime
- **THEN** the runtime refreshes that session's shared-registry record
- **AND THEN** the refreshed record keeps the same `generation_id` while extending the lease for that still-live session

### Requirement: Runtime teardown clears shared-registry discoverability when the runtime performs termination
When the runtime completes authoritative `stop-session` teardown for a tmux-backed session and that session still has a matching shared-registry record, the runtime SHALL remove that record or rewrite it so that shared-registry readers treat it as expired.

Unexpected failure MAY leave stale `live_agents/` directories behind, but runtime-owned graceful teardown SHALL clear discoverability for a session when the runtime is the actor that performed authoritative termination.

Launch authority does not exempt runtime-owned termination from cleanup. If another launcher created the record but the runtime later performs authoritative stop for that same matching session, the runtime SHALL clear or expire the record rather than leaving a live entry behind.

#### Scenario: Direct runtime-owned stop clears runtime-published registry discoverability
- **WHEN** an operator stops a direct runtime-owned tmux-backed session whose registry launch authority is the runtime
- **THEN** the runtime removes or expires that session's shared-registry record
- **AND THEN** later shared-registry readers do not treat that stopped direct runtime-owned session as live

#### Scenario: Runtime stop clears an externally launched record when the runtime performs termination
- **WHEN** an externally launched session is later stopped through runtime-owned authority
- **THEN** the runtime clears the local session and gateway publication pointers it owns for that stopped session
- **AND THEN** shared-registry discoverability for that stopped agent is also cleared by the runtime because the runtime performed the authoritative termination

### Requirement: Registry refresh failures do not overturn already-successful runtime control actions
When a tmux-backed runtime action has already completed its primary control work successfully and later manifest persistence attempts to refresh shared-registry discovery metadata, the system SHALL preserve the successful primary action result even if the registry refresh fails.

This applies at minimum to prompt delivery, interrupt, raw control input, mailbox-binding refresh, and other manifest-persisting runtime control flows that reuse the same live session.

The system SHALL still surface the registry refresh problem through an explicit warning, diagnostic, or equivalent operator-visible reporting path.

#### Scenario: Successful prompt delivery remains successful when registry refresh fails
- **WHEN** a tmux-backed runtime session successfully processes a prompt submission
- **AND WHEN** manifest persistence later encounters a shared-registry refresh failure
- **THEN** the prompt operation still reports success for the completed primary action
- **AND THEN** the registry failure is surfaced separately as a warning or diagnostic rather than replacing the prompt result

#### Scenario: Successful mailbox binding refresh remains successful when registry refresh fails
- **WHEN** a tmux-backed mailbox-enabled runtime session successfully refreshes its mailbox bindings
- **AND WHEN** the follow-on shared-registry refresh fails
- **THEN** the mailbox-binding refresh still reports success for the completed primary action
- **AND THEN** the registry refresh problem is surfaced separately from the mailbox result

### Requirement: Stop-session success is preserved when shared-registry cleanup fails after termination
When authoritative `stop-session` teardown has already terminated the addressed runtime-owned tmux-backed session successfully, a later shared-registry cleanup failure SHALL NOT change that stop result into a failed stop outcome.

The runtime SHALL still surface the registry cleanup failure separately so operators know cleanup did not finish cleanly.

#### Scenario: Registry cleanup failure does not negate a successful stop
- **WHEN** the runtime successfully terminates a runtime-owned tmux-backed session through `stop-session`
- **AND WHEN** later shared-registry record removal fails because of a filesystem or permission problem
- **THEN** the stop operation still reports the successful termination result
- **AND THEN** the registry cleanup problem is surfaced separately for operator follow-up

### Requirement: Runtime can start sessions through an optional `houmao-server` REST backend
The runtime SHALL support an optional `houmao-server` REST-backed mode for live interactive sessions.

When that mode is selected, the runtime SHALL:

- create or attach the live session through `houmao-server`
- persist the `houmao-server` base URL plus session and terminal identity in the session manifest
- treat `houmao-server` as the server authority for later control operations
- keep any `houmao-server` upstream-adapter details out of the public runtime backend identity
- treat `houmao-server` as part of the supported `houmao-server + houmao-mgr` pair rather than as a mixed-pair bridge to raw `cao`

For supported loopback `houmao-server` base URLs, runtime-owned HTTP communication SHALL bypass ambient proxy environment variables by default by ensuring loopback entries exist in `NO_PROXY` and `no_proxy`.

When `HOUMAO_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY` or `no_proxy` and will respect caller-provided values.

#### Scenario: Starting a `houmao-server` session persists server identity
- **WHEN** a developer starts a new interactive session using the `houmao-server` REST-backed mode
- **THEN** the runtime persists a session manifest that records the `houmao-server` base URL and terminal identity needed for resume and later control
- **AND THEN** subsequent runtime control does not need a separate CAO base URL override for that session

#### Scenario: Runtime does not promise mixed-pair bridging through `houmao-server`
- **WHEN** a developer uses the `houmao-server` REST-backed mode
- **THEN** the runtime treats that session as part of the `houmao-server` Houmao-managed path
- **AND THEN** it does not claim support for mixing that path with raw `cao` client workflows behind the scenes

#### Scenario: Loopback `houmao-server` communication bypasses ambient proxy env by default
- **WHEN** a developer starts or resumes a `houmao-server`-backed session using loopback base URL `http://127.0.0.1:9890`
- **AND WHEN** caller environment includes `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`
- **THEN** runtime-owned HTTP communication to that loopback `houmao-server` endpoint bypasses those proxy endpoints by default

### Requirement: `houmao-server` runtime sessions use a first-class persisted backend identity
Runtime-owned sessions that use the `houmao-server` REST-backed mode SHALL persist a first-class backend identity named `houmao_server_rest`.

Those persisted sessions SHALL use dedicated `houmao-server`-specific persisted sections rather than reusing `cao_rest`-specific sections for their public contract.

At minimum, the persisted `houmao-server` section SHALL carry the public `houmao-server` transport identity needed for resume and follow-up control, including:

- `api_base_url`
- server session identity
- terminal identity

The persisted public contract for `houmao_server_rest` SHALL keep child-CAO adapter details out of the runtime-owned manifest.

#### Scenario: Session manifest records `houmao_server_rest` rather than `cao_rest`
- **WHEN** a developer starts a runtime-owned session through the `houmao-server` REST-backed mode
- **THEN** the persisted session manifest records `backend = "houmao_server_rest"`
- **AND THEN** the manifest uses a dedicated `houmao-server` persisted section instead of overloading `cao` metadata

### Requirement: Runtime-owned artifacts remain authoritative for `houmao-server` sessions
For `houmao_server_rest` sessions, the runtime-owned session root and manifest SHALL remain the authoritative durable artifacts for later discovery and follow-up control.

When transitional shared-registry publication is used for a `houmao_server_rest` session, the registry runtime pointers SHALL point back to that runtime-owned manifest and session root.

Gateway and mailbox follow-up behavior that still depends on manifest-backed authority in v1 SHALL use those same runtime-owned artifacts for `houmao_server_rest` sessions.

#### Scenario: Registry and follow-up flows point back to the runtime-owned `houmao-server` manifest
- **WHEN** a `houmao_server_rest` session is published into the transitional shared registry
- **THEN** the registry runtime pointers reference the Houmao-owned session manifest and session root for that session
- **AND THEN** later resolution, gateway attach, and mailbox follow-up flows can keep using manifest-backed authority without reinterpreting the session as `cao_rest`

### Requirement: Runtime control of `houmao-server` sessions routes through `houmao-server`
For `houmao-server`-backed sessions, runtime control operations that inspect or mutate the live session SHALL route through `houmao-server` rather than bypassing it with direct CAO calls.

At minimum, `houmao-server`-routed operations in this change SHALL include:

- status inspection
- prompt submission
- control-input submission
- interrupt
- stop-session

When the runtime cannot reach the configured `houmao-server` for a `houmao-server`-backed session, runtime control SHALL fail explicitly. It SHALL NOT silently fall back to mutating the underlying CAO terminal directly behind `houmao-server`'s back.

Stopping a `houmao-server`-backed session through the runtime SHALL stop the live session through `houmao-server` and SHALL leave the persisted session in a stopped or unavailable condition consistent with the server response.

#### Scenario: Prompt submission for a `houmao-server` session goes through `houmao-server`
- **WHEN** a developer submits a prompt to a `houmao-server`-backed session
- **THEN** the runtime routes that request through the configured `houmao-server` endpoint
- **AND THEN** the runtime does not inject the prompt directly into CAO or another upstream backend outside `houmao-server`

#### Scenario: Stop-session for a `houmao-server` session does not bypass the server authority
- **WHEN** a developer stops a `houmao-server`-backed session through the runtime
- **THEN** the runtime routes that stop request through `houmao-server`
- **AND THEN** it does not bypass the server by directly deleting or interrupting the underlying CAO terminal

### Requirement: Pair-managed `houmao_server_rest` sessions are tmux-backed, reserve window 0, and publish stable gateway attachability before live attach
For pair-managed TUI sessions that use `backend = "houmao_server_rest"`, the runtime SHALL create or resume one tmux session per managed agent session.

The runtime SHALL choose and persist one tmux session name per launched session as a stable live-session handle rather than assuming the canonical agent identity is the tmux session name.

The runtime SHALL reserve tmux window `0` as the primary agent surface for that session and SHALL keep the managed agent itself on that primary surface across pair-managed turns.

Later relaunch of that tmux-backed pair-managed session SHALL reuse the same window `0` surface and SHALL NOT allocate a replacement tmux window.

The runtime SHALL publish `HOUMAO_MANIFEST_PATH=<absolute manifest path>` and `HOUMAO_AGENT_ID=<authoritative agent id>` into the tmux session environment so that pair-managed current-session discovery can locate the persisted session manifest directly and fall back through shared-registry resolution when needed.

The runtime SHALL reuse the existing runtime-owned gateway capability publication seam to materialize derived gateway bookkeeping, `state.json`, queue or bootstrap assets, and related session-owned gateway artifacts during pair launch or launch registration, before a live gateway is attached.

A pair-managed session SHALL NOT be treated as current-session attach-ready until both that runtime-owned manifest-backed gateway publication and successful managed-agent registration for the same persisted attach authority have completed.

The runtime SHALL allow auxiliary windows to exist later in the same tmux session for gateway or operator diagnostics, but they SHALL NOT displace the agent from window `0` and SHALL NOT redefine the primary pair-managed attach surface.

Runtime-controlled pair-managed turns and pair-managed tmux resolution SHALL continue targeting the agent surface in window `0` even when another tmux window is currently selected in the foreground for observability.

#### Scenario: Pair launch creates a gateway-capable tmux session before live attach
- **WHEN** a developer launches a pair-managed TUI session through `houmao-mgr`
- **THEN** the runtime persists the actual tmux session name for that live session
- **AND THEN** the tmux session environment contains `HOUMAO_MANIFEST_PATH`
- **AND THEN** the tmux session environment contains `HOUMAO_AGENT_ID`
- **AND THEN** the gateway capability artifacts are materialized through the shared runtime-owned gateway publication seam
- **AND THEN** window `0` is reserved as the primary agent surface for that session

#### Scenario: Current-session attach is unavailable before matching registration completes
- **WHEN** a delegated pair launch has already published the stable manifest-first discovery inputs into the tmux session
- **AND WHEN** managed-agent registration for that same persisted attach authority has not yet completed successfully
- **THEN** the session is not yet current-session attach-ready
- **AND THEN** pair-managed current-session gateway attach fails closed rather than guessing another authority or alias

#### Scenario: Foreground auxiliary window does not retarget pair-managed execution
- **WHEN** a pair-managed `houmao_server_rest` session has an auxiliary gateway or diagnostics window selected in the foreground
- **AND WHEN** the runtime starts another controlled turn against that managed session
- **THEN** the controlled work still executes on the agent surface in window `0`
- **AND THEN** the runtime does not need to treat the selected auxiliary window as the authoritative agent surface

### Requirement: Tmux-backed sessions support session-local relaunch without rebuilding the brain home
For tmux-backed managed sessions, the system SHALL expose a relaunch surface that reuses the already-built agent home and does not route through build-time `houmao-mgr agents launch` behavior.

The public operator surface SHALL be `houmao-mgr agents relaunch`, and gateway-managed relaunch SHALL use the same internal runtime relaunch primitive rather than shelling out to the build-time launch command.

For tmux-backed relaunchable sessions, the persisted manifest SHALL carry secret-free `agent_launch_authority` sufficient to describe how the managed agent surface is relaunched, while the owning tmux session environment SHALL carry the effective env values needed at relaunch time.

Tmux-backed relaunch SHALL resolve the target session through the same manifest-first discovery contract used by current-session attach.

Tmux-backed relaunch SHALL always target tmux window `0` for the managed agent surface and SHALL NOT allocate a new tmux window.

The system SHALL NOT require per-agent launcher directories, copied launcher scripts, or copied credentials in shared registry in order to relaunch a tmux-backed managed session.

For native headless sessions, relaunch remains valid between turns even when no live `runtime.agent_pid` is published.

#### Scenario: Current-session relaunch uses tmux session env and existing built home
- **WHEN** a developer runs `houmao-mgr agents relaunch` inside a tmux-backed managed session
- **THEN** the system resolves the session through `HOUMAO_MANIFEST_PATH` or `HOUMAO_AGENT_ID`
- **AND THEN** it relaunches the managed agent surface from manifest-owned relaunch posture plus the current tmux session env
- **AND THEN** it does not rebuild the brain home

#### Scenario: Gateway-managed relaunch shares the same runtime primitive
- **WHEN** an attached gateway requests relaunch for a tmux-backed managed session
- **THEN** the gateway uses the same manifest-backed runtime relaunch primitive as `houmao-mgr agents relaunch`
- **AND THEN** it does not fall back to build-time `houmao-mgr agents launch`

#### Scenario: Relaunch reuses window 0 rather than allocating a new window
- **WHEN** the runtime relaunches a tmux-backed managed session
- **THEN** it targets the managed agent surface in window `0`
- **AND THEN** it does not create or search for another tmux window when window `0` has been repurposed by the user

### Requirement: Relaunch preserves durable specialist env but not one-off instance-launch env

For Houmao-started tmux-backed sessions, relaunch SHALL rebuild provider-start state from durable persisted launch inputs rather than from one-off extra env supplied only at initial instance launch.

When the built brain manifest contains persistent specialist-owned launch env records, relaunch SHALL reapply those env records as part of the rebuilt launch plan.

When the original live session also received one-off extra env through `project easy instance launch --env-set`, that one-off extra env SHALL apply only to the current live session and SHALL NOT be persisted in relaunch authority.

The runtime SHALL NOT store one-off instance-launch extra env in:

- specialist config,
- the built brain manifest, or
- session-manifest relaunch authority.

#### Scenario: Relaunch keeps persistent specialist env records
- **WHEN** a specialist declares persistent launch env record `FEATURE_FLAG_X=1`
- **AND WHEN** one tmux-backed session for that specialist is later relaunched
- **THEN** the relaunched session still uses `FEATURE_FLAG_X=1`
- **AND THEN** the runtime obtains that value from durable specialist launch input rather than from the old live session's one-off launch state

#### Scenario: Relaunch drops one-off instance-launch env
- **WHEN** a tmux-backed session originally started with one-off `project easy instance launch --env-set FEATURE_FLAG_X=2`
- **AND WHEN** the underlying specialist does not declare persistent env record `FEATURE_FLAG_X`
- **AND WHEN** that session is later relaunched
- **THEN** the relaunched session does not keep `FEATURE_FLAG_X=2`
- **AND THEN** relaunch uses only durable launch input that was persisted before runtime rebuild

#### Scenario: Live-session headless turns can still use one-off instance-launch env before relaunch
- **WHEN** a headless tmux-backed session starts with one-off `project easy instance launch --env-set FEATURE_FLAG_X=2`
- **AND WHEN** the session remains live without relaunch
- **THEN** later runtime-controlled work in that same live session still uses `FEATURE_FLAG_X=2`
- **AND THEN** that behavior does not imply that `FEATURE_FLAG_X=2` is durable relaunch posture

### Requirement: Supported pair-managed tmux sessions keep the agent in window 0 while auxiliary windows remain non-authoritative
For pair-managed tmux sessions that place gateway or other support processes in the same tmux session, the runtime SHALL reserve tmux window `0` for the agent process.

The runtime SHALL support that same-session auxiliary-window topology for `houmao_server_rest`.

The runtime SHALL keep the `houmao-server` process and its internal child-CAO support state outside the agent's tmux session even when the gateway sidecar runs inside the managed agent session.

Only tmux window `0` is contractual in that topology. The names, counts, and indices of non-zero tmux windows SHALL remain implementation details and SHALL NOT become part of the public attach or control contract.

Gateway attach, detach, crash cleanup, or auxiliary-window recreation SHALL NOT kill, replace, or repurpose the reserved agent window `0` during normal lifecycle handling.

If the agent process later disappears unexpectedly and the runtime relaunches it inside the same tmux session, the runtime SHALL restore the agent process to window `0` before treating the session as recovered or ready again.

#### Scenario: Pair-managed auxiliary window keeps the agent anchored to window 0
- **WHEN** a `houmao_server_rest` session runs a gateway or monitoring process in another tmux window
- **THEN** the agent process remains in window `0`
- **AND THEN** the non-zero process window does not become part of the public agent contract

#### Scenario: Same-session gateway topology keeps the server process out of the agent tmux session
- **WHEN** a pair-managed `houmao_server_rest` session runs a same-session gateway companion
- **THEN** only the gateway sidecar is introduced into an auxiliary tmux window of the managed agent session
- **AND THEN** the `houmao-server` process and child-CAO support state remain outside that tmux session

#### Scenario: Gateway lifecycle preserves the reserved agent window
- **WHEN** a same-session gateway process attaches, detaches, exits unexpectedly, or is recreated
- **THEN** the runtime only changes the auxiliary process window state
- **AND THEN** window `0` remains reserved for the agent surface throughout that sidecar lifecycle

#### Scenario: Relaunch restores the agent process to window 0
- **WHEN** an agent process in a supported same-session pair layout disappears unexpectedly and the runtime relaunches it in the existing tmux session
- **THEN** the runtime restores the relaunched agent process to window `0`
- **AND THEN** the session is not treated as recovered until that canonical agent surface is re-established

### Requirement: Native headless tmux-backed sessions reserve window 0 for console output and remain gateway-attachable between turns
For runtime-owned native headless sessions that use tmux as the durable terminal container, the runtime SHALL keep window `0` reserved for the headless agent console surface.

The runtime SHALL publish `HOUMAO_MANIFEST_PATH=<absolute manifest path>` and `HOUMAO_AGENT_ID=<authoritative agent id>` into that tmux session so current-session gateway attach can resolve the manifest directly and fall back through shared-registry resolution when needed.

Gateway attach SHALL NOT assume a native headless worker process is currently running. Attach targets the logical persisted session, and the manifest SHALL contain enough authority for later headless turn launch even when `runtime.agent_pid` is empty.

If the runtime launches a same-session gateway surface for a native headless session, that surface SHALL live outside window `0` and SHALL NOT displace the headless console from window `0`.

Any native headless relaunch path SHALL reuse window `0` as the headless console surface and SHALL NOT allocate a replacement tmux window.

#### Scenario: Native headless session reserves window 0 and publishes manifest-first discovery
- **WHEN** a developer launches a native headless tmux-backed session
- **THEN** window `0` is reserved for the headless console surface
- **AND THEN** the tmux session environment contains `HOUMAO_MANIFEST_PATH`
- **AND THEN** the tmux session environment contains `HOUMAO_AGENT_ID`

#### Scenario: Native headless attach remains valid after a turn exits
- **WHEN** a native headless turn finishes and its worker process exits
- **AND WHEN** the tmux session and manifest remain live
- **THEN** current-session gateway attach remains valid for that logical session
- **AND THEN** a missing `runtime.agent_pid` does not make the session non-attachable

### Requirement: Runtime launch resolves operator prompt policy from the actual tool version
When a resolved brain manifest requests an operator prompt policy that forbids startup operator prompts, the runtime SHALL resolve that policy against the actual installed CLI tool version and backend before starting the provider process.

Tool-version detection SHALL probe the actual launch executable with a subprocess `--version` call and SHALL fail unattended launch before provider start if the executable is missing or the version output cannot be parsed for that tool family.

Compatible strategy resolution SHALL match the detected executable version against launch-policy strategy declarations of supported version ranges rather than relying on nearest-lower or latest-known fallback.

When the resolved manifest requests `operator_prompt_mode = as_is`, the runtime SHALL NOT perform unattended strategy resolution, version-gated no-prompt mutation, or unattended-owned startup arg injection for that launch.

#### Scenario: Runtime detects tool version and selects a compatible unattended strategy
- **WHEN** a session starts from a brain manifest that requests `operator_prompt_mode = unattended`
- **AND WHEN** the detected tool version and backend match exactly one launch policy strategy's declared supported-version range
- **THEN** the runtime selects exactly one compatible strategy before starting the provider process
- **AND THEN** the runtime applies that strategy's launch actions for the resolved working directory and runtime home

#### Scenario: Missing or unparseable tool version blocks unattended launch
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** the selected launch executable is missing or its version output cannot be parsed for the requested tool family
- **THEN** the runtime fails the launch before provider start
- **AND THEN** the error reports the executable probe failure as the reason unattended resolution could not proceed

#### Scenario: As-is launch bypasses unattended strategy resolution
- **WHEN** a session starts from a brain manifest that requests `operator_prompt_mode = as_is`
- **THEN** the runtime does not require unattended strategy lookup before provider start
- **AND THEN** the runtime does not block launch solely because no unattended strategy exists for the detected tool version and backend

### Requirement: Runtime unattended launch can synthesize provider startup state from minimal credentials
When unattended launch is requested, the runtime SHALL construct provider startup state by starting from the selected setup-projected runtime home and then allowing the selected strategy to create, patch, or validate strategy-owned provider config/state and launch surfaces before process start.

Unattended compatibility SHALL be evaluated independently from credential readiness. The runtime SHALL NOT define unattended support in terms of `auth.json`, API-key presence, or other secret material alone.

For strategy-owned unattended surfaces, the runtime SHALL NOT depend on pre-existing values in copied setup files or on caller-supplied launch args to reach unattended startup.

The runtime SHALL NOT require pre-existing user-owned tool config files solely to suppress startup prompts.

This contract SHALL apply to any Houmao-launched agent backend that supports unattended launch, whether the provider surface is TUI or headless.

#### Scenario: Fresh runtime home launches unattended from setup baseline plus strategy-owned overrides
- **WHEN** a session starts from a brain manifest that requests `operator_prompt_mode = unattended`
- **AND WHEN** the selected tool setup projects a baseline `config.toml` into a fresh runtime home
- **THEN** the runtime copies that setup baseline first
- **AND THEN** the selected strategy may patch its declared runtime-owned config keys and launch surfaces before provider start
- **AND THEN** unattended launch does not depend on a pre-existing user-authored no-prompt home directory

#### Scenario: Missing credential fails readiness without redefining unattended compatibility
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** a compatible unattended strategy exists for the detected tool version and backend
- **AND WHEN** the resolved provider still lacks the required secret material after provider selection is known
- **THEN** the runtime fails before provider start with a credential-readiness error
- **AND THEN** the failure does not report that unattended compatibility itself was unsupported

#### Scenario: Claude unattended launch follows the same authoritative contract
- **WHEN** a Claude Code session requests `operator_prompt_mode = unattended`
- **THEN** the runtime treats Claude's declared no-prompt state and launch surfaces as Houmao-owned for provider start
- **AND THEN** unattended startup does not depend on pre-existing Claude config files or caller-supplied low-level startup flags

### Requirement: Runtime launch records launch policy provenance
The system SHALL persist and surface launch policy provenance for startup-prompt-forbidden launches using a typed `launch_policy_provenance` structure rather than only untyped backend metadata.

That typed provenance SHALL include at minimum:

- requested `operator_prompt_mode`
- detected tool version
- selected strategy identifier
- selection source
- override env var name when an override is active

When the runtime starts a session with `operator_prompt_mode = as_is`, it SHALL record the requested mode in launch-request metadata but SHALL NOT fabricate strategy provenance for a strategy that was never resolved.

#### Scenario: Session metadata records resolved unattended strategy
- **WHEN** the runtime starts a session using a resolved unattended launch strategy
- **THEN** persisted launch metadata includes a typed `launch_policy_provenance` structure with the requested policy mode, detected tool version, selected strategy identifier, and selection source
- **AND THEN** redacted session-facing metadata omits secret values while preserving strategy provenance for debugging

#### Scenario: As-is launch does not fabricate unattended provenance
- **WHEN** the runtime starts a session with `operator_prompt_mode = as_is`
- **THEN** session-facing launch metadata records that requested mode as part of launch-request diagnostics
- **AND THEN** the runtime does not persist a typed unattended strategy provenance block for that launch

### Requirement: Runtime supports a transient strategy override for controlled experiments
The runtime SHALL support `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY=<strategy-id>` as a transient strategy-selection override for controlled unattended-launch experiments.

For runtime-managed launches, the override SHALL be read from the launch caller's process environment during launch-plan composition even when the selected runtime env payload does not otherwise project that variable into the provider's final runtime environment.

The runtime SHALL NOT persist that override into brain recipes or resolved brain manifests, and it SHALL NOT require the override variable to be present in the selected credential-env allowlist solely for strategy resolution.

#### Scenario: Environment override selects a specific unattended strategy
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` is set to a known compatible strategy id
- **THEN** the runtime selects that strategy instead of normal version-based lookup
- **AND THEN** `launch_policy_provenance` records that selection source was an environment override
- **AND THEN** the resolved brain manifest remains unchanged

#### Scenario: Runtime-managed launch sees process-level strategy override
- **WHEN** a runtime-managed session requests `operator_prompt_mode = unattended`
- **AND WHEN** the parent process environment sets `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY`
- **AND WHEN** the selected runtime env payload does not include that variable
- **THEN** launch-plan policy resolution still honors the override for strategy selection
- **AND THEN** the override variable is not required to be injected into the provider's final runtime env solely to make the override work

#### Scenario: Override does not change the detected executable version
- **WHEN** a runtime-managed session requests `operator_prompt_mode = unattended`
- **AND WHEN** `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` selects a known strategy id
- **THEN** the runtime still records the real detected executable version in launch-policy provenance and diagnostics
- **AND THEN** the override changes strategy selection without pretending the executable is a different version

### Requirement: Runtime refuses startup-prompt-forbidden launch when policy cannot be satisfied
The system SHALL fail before provider process start when a requested startup-prompt-forbidden launch policy cannot be satisfied for the detected tool version, backend, or launch context.

That failure SHALL preserve enough structured detail for higher-level launch surfaces to report that backend selection completed but provider startup was blocked by launch-policy compatibility.

#### Scenario: Unsupported version blocks unattended launch before provider start
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** no compatible strategy exists for the detected tool version and backend under the declared supported-version ranges
- **THEN** the runtime fails the launch before starting the provider process
- **AND THEN** the error identifies the requested policy, tool, backend, and detected version
- **AND THEN** higher-level callers can distinguish that no provider process was started

#### Scenario: Unsupported unattended backend fails closed
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** the selected backend is `gemini_headless` and no unattended strategy family exists for that backend
- **THEN** the runtime fails the launch before starting the provider process
- **AND THEN** the error identifies that unattended Gemini support is not part of this change

### Requirement: Runtime unattended launch covers startup operator prompts beyond classic permission dialogs
For `operator_prompt_mode = unattended`, the runtime SHALL treat version-supported startup operator prompts that block provider readiness as part of the launch policy surface, even when those prompts are not labeled as permission prompts by the provider.

#### Scenario: Codex startup prompt is suppressed even when it is a model migration notice
- **WHEN** a supported Codex version would otherwise stop at a startup model migration notice after trust and approval defaults are already satisfied
- **AND WHEN** `operator_prompt_mode = unattended`
- **THEN** the selected strategy treats that startup notice as part of unattended launch compatibility
- **AND THEN** the session either starts without that prompt or fails before provider start if no compatible suppression strategy exists

### Requirement: Shared launch-policy application is used across raw and runtime-managed launches
The system SHALL apply unattended launch policy through one shared Python launch-policy entrypoint across generated raw launch helpers and runtime-managed session backends.

Generated `launch.sh` helpers SHALL remain shell wrappers that invoke that shared Python entrypoint before the final tool `exec`.

#### Scenario: Raw launch helper uses the shared Python launch-policy entrypoint
- **WHEN** a generated brain `launch.sh` helper launches a brain with `operator_prompt_mode = unattended`
- **THEN** the shell helper invokes the shared Python launch-policy entrypoint before the final tool `exec`
- **AND THEN** raw helper launches resolve and apply the same unattended strategy family as runtime-managed launches

#### Scenario: CAO-backed sessions use the same local launch-policy engine
- **WHEN** a runtime-managed unattended launch starts through `cao_rest` or `houmao_server_rest`
- **THEN** the local runtime resolves and applies the same launch-policy engine before CAO-compatible terminal startup
- **AND THEN** CAO-backed sessions do not bypass version detection, override handling, or fail-closed unattended checks

### Requirement: Strategy-owned launch args are not silently overridden
When unattended launch is requested, the selected strategy SHALL own the effective no-prompt CLI args it requires and the equivalent caller launch-override surfaces that map onto strategy-owned runtime config.

The runtime SHALL canonicalize the effective launch request before provider start so strategy-owned unattended behavior wins over contradictory caller launch inputs.

For tools such as Codex that support config-override args, the runtime SHALL also canonicalize caller overrides that target strategy-owned unattended config keys even when the conflict is expressed through generic config-override syntax rather than a dedicated flag.

#### Scenario: Conflicting launch override is canonicalized to the unattended strategy
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** caller-supplied `launch_args_override` conflicts with a strategy-owned no-prompt arg or removes required strategy behavior
- **THEN** the runtime canonicalizes the effective launch args before provider start so the strategy-owned unattended behavior still applies
- **AND THEN** the final effective launch behavior does not depend on the caller-supplied conflicting arg

#### Scenario: Conflicting Codex config-override arg is canonicalized to the unattended strategy
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** caller-supplied launch overrides include a Codex `-c` config override for a strategy-owned unattended key such as `approval_policy`, `sandbox_mode`, or project trust
- **THEN** the runtime canonicalizes the effective startup surface before provider start so the strategy-owned unattended value still applies
- **AND THEN** the launch does not depend on the caller-supplied conflicting config value to become unattended

### Requirement: Runtime resolves the effective launch overrides for the selected backend before provider start
The system SHALL resolve the effective launch overrides during launch-plan composition using the resolved brain manifest, the selected backend, runtime launch policy, and backend-reserved protocol controls.

That resolution SHALL apply launch-override precedence in this order:

1. adapter-owned launch defaults persisted in the brain manifest
2. recipe-requested launch overrides persisted in the brain manifest
3. direct-build launch overrides when present in the manifest for that built brain
4. backend-aware launch-override translation and validation
5. runtime-owned launch policy application
6. backend-reserved protocol args and runtime continuity controls

#### Scenario: Runtime resolves a Claude headless launch override with a supported typed param
- **WHEN** a Claude brain manifest requests `launch_overrides.tool_params.include_partial_messages = true`
- **AND WHEN** the selected backend is `claude_headless`
- **THEN** launch-plan composition resolves that request into effective Claude headless launch behavior before provider start
- **AND THEN** the resulting launch plan preserves runtime-owned continuity and machine-readable output controls

### Requirement: Headless backend code owns only protocol-required launch args
For headless backends, runtime backend code SHALL own only the launch args and controls required by the headless protocol itself.

Optional provider launch behavior SHALL be resolved from declarative tool-launch metadata plus the requested `launch_overrides`, not invented as backend-only policy in headless `.py` code.

#### Scenario: Headless backend appends protocol-required args after optional launch resolution
- **WHEN** a headless launch uses optional provider behavior from tool-adapter defaults or `launch_overrides`
- **THEN** runtime resolution applies that optional behavior before final backend command assembly
- **AND THEN** the backend appends only the protocol-required headless args such as resume, machine-readable output mode, or provider-required subcommands

### Requirement: Runtime records effective launch-override provenance
The system SHALL persist and surface typed launch-override provenance for started sessions rather than exposing only one flattened executable-plus-args snapshot.

That provenance SHALL identify at minimum:

- the adapter-default launch snapshot used for the build
- the requested recipe or direct-build launch overrides
- the selected backend used for resolution
- the effective translated launch behavior after runtime resolution
- whether runtime launch policy or backend-reserved controls changed the final launch shape

#### Scenario: Session metadata explains why effective launch args differ from recipe intent
- **WHEN** a started session uses resolved launch behavior that differs from the raw requested override because runtime policy or backend-owned controls changed the final launch shape
- **THEN** persisted launch metadata records both the requested launch-overrides intent and the effective resolved launch behavior
- **AND THEN** debugging consumers can identify which layer changed the final launch plan

### Requirement: Runtime fails closed when the selected backend cannot honor a requested launch override
The system SHALL reject launch-override requests before provider start when the selected backend cannot honor the requested launch-overrides contract or when the request conflicts with backend-reserved controls.

The runtime SHALL NOT silently ignore unsupported launch-override requests as though they were effective.

#### Scenario: REST-backed launch rejects a launch override it cannot honor
- **WHEN** a resolved brain manifest requests a launch override that the selected `cao_rest` or `houmao_server_rest` backend does not support end to end
- **THEN** launch-plan composition fails before provider start
- **AND THEN** the error identifies that the rejected launch-override field is unsupported for that backend

#### Scenario: Runtime rejects a conflicting reserved protocol override
- **WHEN** a launch-overrides request attempts to remove, replace, or contradict a backend-reserved protocol control such as resume or machine-readable output mode
- **THEN** the runtime fails before provider start
- **AND THEN** the error identifies the request as conflicting with runtime-owned backend behavior

### Requirement: Runtime requires schema-version-2 brain manifests for the launch-overrides contract
Runtime launch planning for this contract SHALL require resolved brain manifests written with `schema_version = 2`.

The runtime SHALL NOT provide a compatibility reader that synthesizes the new launch-overrides contract from schema-version-1 manifests.

#### Scenario: Legacy schema-version-1 brain manifest is rejected with rebuild guidance
- **WHEN** a developer attempts to launch a brain home whose resolved brain manifest still uses `schema_version = 1`
- **THEN** launch-plan construction fails before provider start
- **AND THEN** the error directs the developer to rebuild the affected brain home with the current builder

### Requirement: Tmux-backed headless turns reuse the primary agent window
For one tmux-backed headless session, runtime-controlled prompt execution SHALL be serialized and SHALL NOT overlap.

The runtime SHALL execute each runtime-controlled headless turn on the stable primary agent surface in window 0 and SHALL NOT create a separate per-turn tmux window for normal turn execution.

The runtime SHALL launch each runtime-controlled headless turn through a same-pane fresh-process execution primitive on the stable primary surface rather than typing the command into a long-lived interactive shell.

After a runtime-controlled headless turn reaches terminal state, the runtime SHALL leave the stable primary surface attachable as the idle `agent` window for the next controlled turn.

Turn identity, stdout, stderr, exit status, and process metadata SHALL remain per-turn durable artifacts on disk rather than being encoded through tmux window allocation.

#### Scenario: Active headless turn runs on the primary agent surface
- **WHEN** the runtime starts a controlled turn for a tmux-backed headless session
- **THEN** that turn executes on the stable window-0 agent surface
- **AND THEN** rolling output remains visible on that same primary surface
- **AND THEN** the runtime does not create a separate per-turn tmux window for that turn

#### Scenario: Primary agent surface remains reusable after a controlled turn completes
- **WHEN** a runtime-controlled headless turn completes on the stable primary surface
- **THEN** the runtime leaves window 0 attachable as the `agent` surface
- **AND THEN** the next controlled turn can reuse that same primary surface without allocating a new tmux window

#### Scenario: Runtime-controlled headless turns do not overlap in one session
- **WHEN** one runtime-controlled headless turn is already active for a tmux-backed session
- **AND WHEN** another runtime-controlled prompt is addressed to that same live session before the first turn reaches terminal state
- **THEN** the runtime does not start a second overlapping CLI execution for that session
- **AND THEN** window 0 remains the only runtime-controlled execution surface for that headless agent

### Requirement: Local-interactive runtime separates semantic prompt submission from raw control input

For tmux-backed `local_interactive` sessions, the runtime SHALL expose a semantic prompt-submission operation that is distinct from the raw control-input operation.

The semantic prompt-submission operation SHALL mean “submit this message as one provider turn.” The raw control-input operation SHALL mean “inject these literal characters and exact special-key tokens into the live TUI.”

The raw control-input operation SHALL continue using the exact `<[key-name]>` contract defined by the runtime tmux-control-input capability, including explicit Enter-only submission behavior and optional literal escape mode for the entire sequence.

The semantic prompt-submission operation SHALL treat the entire prompt body as literal text, SHALL NOT interpret `<[key-name]>` substrings as special keys, and SHALL automatically submit once at the end.

#### Scenario: Semantic prompt submission is not routed through raw send-keys

- **WHEN** the runtime submits a prompt to a live `local_interactive` session
- **THEN** it uses the semantic prompt-submission path rather than the raw `<[key-name]>` control-input path
- **AND THEN** runtime-owned prompt semantics remain distinct from generic TUI key injection

#### Scenario: Prompt-looking special-key tokens remain literal under send-prompt

- **WHEN** the runtime semantically submits the prompt body `reply with <[Enter]> literally`
- **THEN** the provider receives the literal text `reply with <[Enter]> literally`
- **AND THEN** the runtime does not interpret that substring as a special key before the automatic final submit

#### Scenario: Raw control input preserves the exact special-key contract

- **WHEN** the runtime sends the raw control-input sequence `"/model<[Enter]><[Down]>"` to a live `local_interactive` session
- **THEN** it preserves the exact `<[key-name]>` parsing and delivery behavior defined for tmux control input
- **AND THEN** that raw path does not gain implicit prompt-submission semantics beyond the explicit keys the caller provided

### Requirement: Local-interactive semantic prompt submission uses submit-aware tmux delivery

For tmux-backed `local_interactive` sessions, semantic prompt submission SHALL use a submit-aware tmux delivery strategy that pastes the prompt text and submits it as separate phases.

At minimum, that strategy SHALL:

- insert the prompt text through tmux paste-buffer delivery rather than only through rapid literal `send-keys -l`
- request bracketed-paste wrappers when the target application supports them
- send the submit action separately from text insertion

For provider TUIs that distinguish explicit paste input from fast typed-character bursts, the runtime SHALL treat successful semantic prompt submission as requiring an actual submitted provider turn rather than leaving the prompt staged as multiline draft text in the composer.

#### Scenario: Codex prompt submission becomes a real submitted turn

- **WHEN** the runtime semantically submits a prompt into a live Codex `local_interactive` session
- **THEN** the provider receives that prompt as a submitted turn
- **AND THEN** the prompt is not left behind merely as multiline draft text caused by paste-burst reinterpretation of the submit key

#### Scenario: Submit-aware prompt delivery keeps raw key behavior separate

- **WHEN** the runtime semantically submits a prompt into a live `local_interactive` session
- **THEN** the runtime performs text insertion and submit as separate phases
- **AND THEN** later raw control-input delivery continues to behave according to the exact keys the caller requested rather than inheriting semantic prompt-submission side effects

#### Scenario: Raw send-keys does not auto-submit without explicit Enter

- **WHEN** the runtime sends the raw control-input sequence `"hello world"` to a live `local_interactive` session
- **THEN** it inserts the literal text `hello world`
- **AND THEN** it does not submit the draft because the caller did not include an explicit `<[Enter]>`

### Requirement: Resume-only local control does not reapply unattended provider-home mutations
For runtime-owned sessions whose resolved brain manifest requests `operator_prompt_mode = unattended`, resumed local control paths that do not start or relaunch a provider process SHALL NOT rewrite strategy-owned provider bootstrap files solely to inspect or control an already-live session.

At minimum, resumed local commands such as state queries, detail queries, prompt submission, interrupt submission, and local gateway lifecycle or status operations for an already-live session SHALL be able to reuse persisted launch metadata without re-running unattended file mutations against provider-owned bootstrap files such as Claude `settings.json` or `.claude.json`.

When a resumed path must prepare a new provider start or relaunch for that session, any strategy-owned provider-home mutation SHALL run only inside an explicit pre-start mutation phase rather than as an unconditional side effect of session resume.

#### Scenario: Read-only state query skips unattended provider-home mutation for a live session
- **WHEN** a developer runs `houmao-mgr agents state --agent-name gpu` against a live runtime-owned Claude local interactive session whose brain manifest requests `operator_prompt_mode = unattended`
- **THEN** the runtime resumes the session authority without rewriting strategy-owned Claude bootstrap files
- **AND THEN** the query does not fail merely because another local control command is touching the same runtime home

#### Scenario: Gateway status query skips unattended provider-home mutation for a live session
- **WHEN** a developer runs `houmao-mgr agents gateway status --agent-name gpu` against a live runtime-owned unattended Claude session
- **THEN** the runtime resolves the live gateway state without re-running provider-home mutation actions
- **AND THEN** the query does not depend on rewriting `settings.json` or `.claude.json` for that already-live session

### Requirement: Strategy-owned provider-home mutation is serialized and atomically committed
When the runtime must create, patch, or repair strategy-owned provider-home files for unattended start or relaunch, it SHALL serialize that mutation per runtime home and SHALL commit each finished file atomically so concurrent processes do not observe a truncated or partially written file.

This guarantee SHALL apply to every strategy-owned persisted file format used by the shared unattended launch-policy helpers, including JSON and TOML state.

If a previously strategy-owned file is blank or malformed due to a prior interrupted write, the runtime MAY repair that file only inside the serialized pre-start mutation phase for a declared owned path.

#### Scenario: Concurrent control paths do not observe a truncated strategy-owned JSON file
- **WHEN** two local processes address the same unattended runtime-owned session concurrently
- **AND WHEN** one process enters a pre-start mutation phase for a strategy-owned JSON file in that runtime home
- **THEN** the other process does not observe a zero-byte or partially written JSON file from that mutation
- **AND THEN** the other process does not fail with a malformed-state error caused only by an in-progress strategy-owned write

#### Scenario: Relaunch repair replaces the finished strategy-owned file atomically
- **WHEN** a relaunch path for an unattended runtime-owned Claude session must repair or rewrite strategy-owned `settings.json` or `.claude.json`
- **THEN** the runtime serializes that repair for the runtime home
- **AND THEN** each finished file becomes visible through one atomic replacement step rather than through truncate-then-write

#### Scenario: Blank strategy-owned file is repairable on the next provider-start phase
- **WHEN** a strategy-owned provider-home file for an unattended session is found blank during an explicit provider-start or relaunch phase
- **THEN** the runtime may rebuild that declared owned file from its strategy-owned baseline inside the serialized pre-start mutation phase
- **AND THEN** ordinary read-only resumed control does not need to perform that repair itself

### Requirement: Joined tmux-backed sessions materialize the standard runtime session envelope
The runtime SHALL support materializing a standard Houmao session envelope around an existing tmux session that was not originally started by Houmao, so later control can use the same manifest-first contract as native launches.

For joined TUI adoption, the effective backend SHALL be `local_interactive`. For joined native headless adoption, the effective backend SHALL be the provider-specific native headless backend (`claude_headless`, `codex_headless`, or `gemini_headless`).

The join materialization path SHALL create all of the following under the effective runtime root for the adopted session:

- a session root,
- placeholder `agent_def/` content,
- placeholder `brain_manifest.json`,
- a persisted session manifest,
- session-local gateway artifacts under `gateway/`,
- a shared-registry record for the adopted managed agent.

The join materialization path SHALL construct the persisted joined-session `launch_plan` directly from join inputs rather than deriving runtime launch behavior from the placeholder `brain_manifest.json`.

If a placeholder `brain_manifest.json` is written for a joined session, it SHALL remain a path or invariant artifact only and SHALL NOT be the authoritative source of runtime launch or relaunch behavior for that joined session.

The join materialization path SHALL create the resolved job directory on disk before publishing `HOUMAO_JOB_DIR`.

The join materialization path SHALL publish `HOUMAO_MANIFEST_PATH`, `HOUMAO_AGENT_ID`, `HOUMAO_AGENT_DEF_DIR`, and `HOUMAO_JOB_DIR` into the adopted tmux session environment.

For joined TUI adoption, the persisted manifest and later manifest rewrites SHALL preserve the adopted tmux window identity needed to find the live provider surface. Resume-time capability publication and other post-join local control paths SHALL NOT overwrite that adopted window metadata with `null` or a default launch-time window name.

The adopted session SHALL reuse the current tmux session name as the live tmux handle and SHALL keep tmux window `0` as the canonical managed agent surface even when the join command itself runs from another window of that same tmux session.

After successful join, the runtime SHALL treat shared-registry publication and later refresh or teardown for that adopted session as runtime-owned publication state even though the current provider process was originally started by the user.

For joined sessions, the initial shared-registry publication SHALL use a long sentinel lease that keeps the adopted session discoverable after the one-shot join command exits until the session is explicitly stopped or cleaned up.

The resulting manifest and tmux session environment SHALL remain the authoritative inputs for later `state`, `show`, `prompt`, `interrupt`, `gateway attach`, and related runtime-managed control paths rather than introducing a join-only discovery store.

#### Scenario: TUI join materializes a normal `local_interactive` runtime envelope
- **WHEN** the local join path adopts a live Codex TUI from tmux window `0`, pane `0`
- **THEN** it writes a normal session root containing placeholder `agent_def/`, placeholder `brain_manifest.json`, a persisted session manifest, and session-local `gateway/` artifacts
- **AND THEN** it publishes `HOUMAO_MANIFEST_PATH`, `HOUMAO_AGENT_ID`, `HOUMAO_AGENT_DEF_DIR`, and `HOUMAO_JOB_DIR` into that tmux session environment
- **AND THEN** it publishes a shared-registry record for the adopted managed agent without requiring a separate join-only discovery store

#### Scenario: Headless join materializes a native headless runtime envelope between turns
- **WHEN** the local join path adopts a tmux-backed Codex headless logical session between turns
- **THEN** it persists that adopted session as `backend = "codex_headless"` with the normal manifest, gateway, tmux-env, and shared-registry artifacts
- **AND THEN** later runtime-controlled headless turn submission can resume the same logical session from that manifest-backed authority

#### Scenario: Joined session launch behavior does not depend on the placeholder brain manifest
- **WHEN** the local join path materializes a joined session with a placeholder `brain_manifest.json`
- **THEN** the joined session's persisted `launch_plan` remains the authoritative launch and relaunch input for runtime control
- **AND THEN** runtime behavior does not require reconstructing provider launch semantics from the placeholder brain manifest

#### Scenario: Joined registry publication survives the one-shot join command
- **WHEN** a joined session is published to the shared registry
- **AND WHEN** the one-shot `houmao-mgr agents join` command exits successfully
- **THEN** the adopted session remains discoverable through its initial long sentinel lease
- **AND THEN** the design does not require a background lease-renewal daemon just to keep that joined session visible

#### Scenario: Joined local TUI resume preserves the adopted tmux window metadata
- **WHEN** a live Claude TUI is joined from tmux window `0` whose current window name is `claude`
- **AND WHEN** a later local control path resumes that joined session and republishes manifest-backed gateway capability
- **THEN** the persisted manifest still records the adopted window identity needed to find window `0`
- **AND THEN** later local TUI tracking does not fall back to probing window name `agent` only because the resume path rewrote the manifest

### Requirement: Joined tmux-backed sessions persist explicit adopted relaunch posture
For tmux-backed joined sessions, the persisted relaunch authority SHALL record that the session origin is tmux join adoption rather than Houmao-started provider launch.

For joined sessions, the persisted session manifest's `agent_launch_authority` SHALL be the source of truth for secret-free relaunch posture.

For this change, joined-session relaunch metadata SHALL remain a backward-compatible extension of the existing session manifest v4 contract rather than requiring a new manifest version solely for joined-session posture fields.

That persisted relaunch authority SHALL distinguish at minimum all of the following postures:

- `runtime_launch_plan`,
- `tui_launch_options`,
- `headless_launch_options`,
- `unavailable`.

The persisted relaunch authority SHALL include an explicit `posture_kind` discriminator. Runtime relaunch logic SHALL NOT infer the joined-session relaunch posture solely from field presence.

For `tui_launch_options` and `headless_launch_options`, the persisted relaunch authority SHALL store structured launch args together with structured Docker-style launch env specs:

- `NAME=value` is persisted as a literal binding record,
- `NAME` is persisted as an inherited binding record that resolves `NAME` from the adopted tmux session environment at relaunch time.

When a joined TUI session is adopted without any structured launch options, later `houmao-mgr agents relaunch` and gateway-managed relaunch SHALL fail explicitly with an unavailable-relaunch error while other manifest-backed control paths remain valid.

When a joined TUI or native headless session includes operator-supplied relaunch posture, later relaunch SHALL reuse tmux window `0` and SHALL NOT rebuild a brain home or invent a replacement launch contract.

For joined native headless sessions that persist `headless_launch_options`, the provider continuity state needed to continue later work SHALL remain in the backend-specific manifest section for that provider rather than being duplicated into the shared registry.

That backend-specific continuity state SHALL support all of the following meanings:

- no known-chat resume,
- resume the provider's most current known chat,
- resume one exact provider chat or session id.

The tmux session environment SHALL NOT become a second persistence store for relaunch posture. It SHALL be used only for existing manifest-discovery pointers and for resolving inherited launch-env bindings at relaunch time.

The shared registry SHALL NOT persist a second copy of joined-session relaunch posture. Shared-registry publication for joined sessions remains limited to discovery and stable runtime pointers.

The persisted operator-supplied relaunch posture SHALL remain secret-free manifest metadata. The runtime SHALL NOT copy credentials into the shared registry or into synthesized launcher directories just to relaunch a joined session.

#### Scenario: Joined TUI without structured launch options remains controllable but not relaunchable
- **WHEN** a live Claude Code TUI is adopted through `houmao-mgr agents join` without any `--launch-args` or `--launch-env`
- **THEN** later manifest-backed `state`, `show`, `prompt`, `interrupt`, and `gateway attach` operations remain valid for that joined session
- **AND THEN** a later `houmao-mgr agents relaunch` fails with an explicit unavailable-relaunch error instead of inventing a restart command

#### Scenario: Joined headless relaunch uses the persisted launch options and exact resume id
- **WHEN** a Codex native headless logical session was adopted with `--launch-args exec --launch-args --json --launch-env CODEX_HOME` and `--resume-id thread_123`
- **THEN** later relaunch uses those persisted launch args and launch env specs together with the persisted `resume_id`
- **AND THEN** the relaunched work reuses tmux window `0`
- **AND THEN** the runtime does not rebuild a brain home for that joined headless session

#### Scenario: Joined headless relaunch can use the latest known chat
- **WHEN** a Codex native headless logical session was adopted with `--launch-args exec --launch-args --json --resume-id last`
- **THEN** later runtime-controlled headless work uses the provider's most current known chat rather than requiring one exact persisted thread id
- **AND THEN** the relaunched work reuses tmux window `0`

#### Scenario: Joined headless relaunch can intentionally avoid known-chat resume
- **WHEN** a Codex native headless logical session was adopted with `--launch-args exec --launch-args --json` and without `--resume-id`
- **THEN** later runtime-controlled headless work does not resume a known provider chat
- **AND THEN** the relaunched work starts from a fresh provider session

#### Scenario: Joined relaunch resolves inherited env from tmux env while registry stays pointer-only
- **WHEN** a joined session persists launch env specs that include inherited entry `CODEX_HOME`
- **AND WHEN** the adopted tmux session environment currently publishes `CODEX_HOME=/tmp/codex-home`
- **THEN** later relaunch resolves `CODEX_HOME` from that tmux session environment
- **AND THEN** the shared-registry record for that joined session does not need to persist a second copy of the relaunch posture or inherited env value

### Requirement: Unattended runtime-owned config overrides replace conflicting setup values in the runtime home
When unattended launch is requested, the runtime SHALL treat strategy-owned runtime-home config keys as authoritative for provider start even when the copied setup baseline defines different values for those same keys.

The runtime SHALL preserve non-owned setup content in the runtime home, including provider-selection and model-provider configuration, unless a declared strategy-owned mutation explicitly changes that content.

#### Scenario: Codex unattended launch overwrites copied setup approval settings
- **WHEN** a selected Codex setup baseline defines `approval_policy` or `sandbox_mode` values in `config.toml`
- **AND WHEN** the brain manifest requests `operator_prompt_mode = unattended`
- **THEN** the runtime overwrites those strategy-owned keys in the runtime-home `config.toml` before provider start
- **AND THEN** unrelated setup-defined provider configuration remains intact

#### Scenario: Claude unattended launch preserves non-owned baseline content while overriding owned startup state
- **WHEN** a selected Claude setup baseline includes provider-specific defaults that are not strategy-owned unattended state
- **AND WHEN** the brain manifest requests `operator_prompt_mode = unattended`
- **THEN** the runtime preserves that non-owned baseline content
- **AND THEN** it still overwrites Claude's declared unattended-owned startup state before provider start

### Requirement: Unattended runtime-owned launch surfaces replace conflicting caller launch inputs
When unattended launch is requested, the runtime SHALL treat strategy-owned launch args and equivalent config-override surfaces as authoritative for provider start even when the caller requested different values.

The runtime MAY preserve caller-supplied diagnostics or provenance, but the final effective startup behavior SHALL be determined by the unattended strategy rather than by the caller's conflicting low-level launch inputs.

This rule SHALL apply equally to current tools such as Claude Code and Codex and to future Houmao-launched tools that declare unattended-owned launch surfaces.

#### Scenario: Codex unattended launch replaces caller startup-policy flags
- **WHEN** a caller requests unattended launch for Codex
- **AND WHEN** the caller also supplies direct launch flags or `-c` config overrides that would weaken unattended startup behavior
- **THEN** the runtime replaces or removes those conflicting effective startup inputs before provider start
- **AND THEN** the resulting Codex launch still uses the unattended strategy's startup policy

#### Scenario: Claude unattended launch replaces caller startup-policy flags
- **WHEN** a caller requests unattended launch for Claude Code
- **AND WHEN** the caller also supplies low-level startup inputs that would weaken the unattended strategy's owned launch surfaces
- **THEN** the runtime replaces or removes those conflicting effective startup inputs before provider start
- **AND THEN** the resulting Claude launch still uses the unattended strategy's startup policy

### Requirement: Project-aware build and launch results describe selected local roots explicitly
Maintained project-aware build and launch surfaces SHALL describe overlay-local default roots, explicit root overrides, and implicit overlay bootstrap in operator-facing result text and machine-readable payload details.

When a maintained build or launch flow resolves runtime or jobs state from the selected project overlay, the result SHALL describe that scope as the active project runtime root or overlay-local jobs scope rather than as a generic shared-root default.

When a maintained build or launch flow implicitly bootstraps the selected overlay, the operator-facing result SHALL surface that bootstrap outcome explicitly instead of requiring the operator to infer it from created files on disk.

#### Scenario: Project-aware build reports overlay-local runtime selection and bootstrap
- **WHEN** an operator runs a maintained project-aware build or launch command without an explicit runtime-root override
- **AND WHEN** the command bootstraps the selected overlay for that invocation
- **THEN** the operator-facing result describes the resolved runtime scope as the active project runtime root under the selected overlay
- **AND THEN** the result surfaces that the overlay was bootstrapped implicitly during that invocation

#### Scenario: Explicit runtime override remains described as an explicit override
- **WHEN** an operator runs a maintained build or launch command with an explicit runtime-root override
- **THEN** the operator-facing result describes that root as an explicit runtime-root override
- **AND THEN** it does not describe that path as though it were the active project runtime root selected from overlay-local defaults
