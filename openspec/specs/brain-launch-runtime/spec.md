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
For headless sessions of tmux-backed CLI tools (at minimum Claude Code, Gemini, and Codex), the runtime SHALL create and own a tmux session per started session.

The runtime SHALL choose and persist one tmux session name per started session as a unique live-session handle rather than assuming the canonical agent identity is the tmux session name.

The runtime SHALL publish `AGENTSYS_MANIFEST_PATH=<absolute manifest path>` into the tmux session environment so that name-based `--agent-identity` resolution can locate the persisted session manifest.

#### Scenario: Start a headless session creates a tmux identity with manifest pointer
- **WHEN** a developer starts a headless Codex, Claude, or Gemini session without CAO
- **THEN** the runtime creates a tmux-backed live session and persists its actual tmux session name as metadata for that live session
- **AND THEN** the tmux session environment contains `AGENTSYS_MANIFEST_PATH` pointing at the persisted session manifest JSON

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
The system SHALL apply the selected role package as the initial tool instructions before the first user prompt is processed.

#### Scenario: Role is injected on session start
- **WHEN** a session is started with role `R`
- **THEN** the tool is initialized with `R` as initial instructions using a tool-supported mechanism when available
- **AND THEN** if the tool lacks a native mechanism, the system sends `R` as a clearly delimited bootstrap message before the first user prompt

#### Scenario: Role bootstrap is not replayed on resumed headless turns
- **WHEN** a headless session has already applied role `R` during bootstrap
- **AND WHEN** a developer sends a follow-up prompt using the persisted resume identity
- **THEN** the system does not replay role bootstrap content unless the caller explicitly starts a new session

### Requirement: Optional CAO backend via REST boundary
The system SHALL optionally support launching and driving sessions via CAO
using CAO's REST API, without requiring the core runtime to depend on CAO
internals.

For supported loopback CAO base URLs (`http://localhost:<port>`,
`http://127.0.0.1:<port>` with explicit ports), runtime-owned CAO HTTP
communication SHALL bypass ambient proxy environment variables by default by
ensuring loopback entries exist in `NO_PROXY`/`no_proxy`.

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY`
or `no_proxy` and will respect caller-provided values (for example, to enable
traffic-watching development proxies).

When starting a CAO-backed session, the runtime SHALL pass the resolved working directory through to CAO as launch input and SHALL NOT impose a repo-owned validation rule that requires the workdir to live under the user home tree, the tool home, or the launcher home.

#### Scenario: CAO-backed session launch and messaging
- **WHEN** a developer starts a CAO-backed session and provides a CAO API base URL at session start
- **THEN** the system creates a CAO session/terminal using the resolved working directory, sends prompts, and fetches replies using CAO REST endpoints
- **AND THEN** the system persists the CAO API base URL and terminal identity in the session manifest
- **AND THEN** subsequent prompt and stop operations target the CAO terminal using only the persisted session manifest fields (no CAO base URL override)

#### Scenario: Loopback CAO runtime communication bypasses caller proxy env on a non-default port
- **WHEN** a developer starts or resumes a CAO-backed session using loopback CAO base URL `http://127.0.0.1:9991`
- **AND WHEN** caller environment includes `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`
- **THEN** runtime-owned CAO HTTP communication bypasses those proxy endpoints by default
- **AND THEN** loopback CAO connectivity depends on local CAO availability rather than external proxy availability

#### Scenario: Preserve mode respects caller `NO_PROXY` for loopback
- **WHEN** a developer starts or resumes a CAO-backed session using a supported loopback CAO base URL
- **AND WHEN** caller environment includes `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`
- **THEN** runtime-owned CAO HTTP communication uses caller-provided proxy and `NO_PROXY` settings

#### Scenario: CAO-backed launch does not reject a workdir outside launcher home
- **WHEN** a developer starts a CAO-backed session whose resolved workdir is outside the launcher home or user home tree
- **AND WHEN** the installed CAO server accepts that workdir
- **THEN** the runtime passes the resolved workdir through to CAO
- **AND THEN** the runtime does not fail solely because that workdir is outside those home paths

### Requirement: Mailbox enablement is resolved before session start and persisted for resume
The runtime SHALL enable filesystem mailbox support through declarative recipe configuration and MAY allow explicit `start-session` CLI overrides for transport-specific ad hoc sessions.

The runtime SHALL resolve one effective mailbox configuration before building the launch plan, SHALL persist that resolved mailbox configuration in the session manifest, and SHALL restore it when resuming the session.

#### Scenario: Recipe configuration enables mailbox support
- **WHEN** a developer starts an agent session whose resolved recipe enables filesystem mailbox support
- **THEN** the runtime resolves that mailbox configuration before building the launch plan
- **AND THEN** the resolved session uses that mailbox transport and principal binding for subsequent mailbox-aware runtime work

#### Scenario: Start session CLI overrides mailbox transport or root
- **WHEN** a developer starts an agent session with explicit mailbox CLI overrides such as transport or filesystem root
- **THEN** the runtime applies those overrides to the effective mailbox configuration for that session
- **AND THEN** the resulting session manifest records the overridden mailbox transport and bindings rather than forcing resume to re-derive them from recipe defaults

#### Scenario: Resume restores persisted mailbox bindings
- **WHEN** a developer resumes a previously started mailbox-enabled session
- **THEN** the runtime restores the mailbox transport, principal binding, and transport-specific mailbox bindings from the persisted session manifest
- **AND THEN** runtime mailbox commands for that resumed session preserve the same sender principal and mailbox root unless an explicit refresh changes them later

### Requirement: Mailbox-enabled runtime sessions project mailbox system skills and mailbox env bindings
When filesystem mailbox support is enabled for a started session, the runtime SHALL project the platform-owned mailbox system skills into the active agent skillset under a reserved runtime-owned namespace and SHALL populate the filesystem mailbox binding env contract before mailbox-related work is expected from the agent.

When no explicit filesystem mailbox content root override is supplied, the runtime SHALL derive the effective filesystem mailbox content root from the independent Houmao mailbox root rather than from the effective runtime root.

When no explicit filesystem mailbox content root override is supplied and `AGENTSYS_GLOBAL_MAILBOX_DIR` is set to an absolute directory path, the runtime SHALL derive the effective Houmao mailbox root from that env-var override before publishing `AGENTSYS_MAILBOX_FS_ROOT`.

When active filesystem mailbox env bindings depend on the current session address having an active mailbox registration, the runtime SHALL bootstrap or confirm that session's mailbox registration before deriving those env bindings for `start-session`.

The runtime SHALL satisfy that registration-dependent env-binding contract through bootstrap ordering rather than by synthesizing fallback mailbox paths when the active registration is missing.

#### Scenario: Start session projects mailbox system skills with filesystem bindings
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the tool adapter's active skills destination under the reserved runtime-owned namespace
- **AND THEN** the runtime starts the session with the filesystem mailbox binding env vars needed by those mailbox system skills
- **AND THEN** the runtime sets `AGENTSYS_MAILBOX_FS_ROOT` to the effective mailbox content root for that session

#### Scenario: Start session defaults filesystem mailbox root from the Houmao mailbox root
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from the Houmao mailbox root default
- **AND THEN** the runtime sets `AGENTSYS_MAILBOX_FS_ROOT` to that derived default path

#### Scenario: Mailbox-root env-var override redirects the effective mailbox root
- **WHEN** `AGENTSYS_GLOBAL_MAILBOX_DIR` is set to `/tmp/houmao-mailbox`
- **AND WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from `/tmp/houmao-mailbox`
- **AND THEN** the runtime sets `AGENTSYS_MAILBOX_FS_ROOT` to that derived path

#### Scenario: Second mailbox-enabled session joins an initialized shared mailbox root without manual pre-registration
- **WHEN** one mailbox-enabled session has already initialized and registered itself into a shared filesystem mailbox root
- **AND WHEN** a second mailbox-enabled session starts against that same shared mailbox root with its own mailbox address
- **THEN** the runtime bootstraps or confirms the second session's mailbox registration before deriving registration-dependent filesystem mailbox env bindings
- **AND THEN** the second `start-session` succeeds without requiring manual mailbox pre-registration outside the runtime startup path

### Requirement: Runtime sessions support filesystem mailbox binding refresh
The runtime SHALL support an explicit control path that refreshes filesystem mailbox binding env vars for an active session without requiring regeneration of the mailbox system skill templates.

#### Scenario: Refresh mailbox bindings for an active session
- **WHEN** a developer or orchestrator requests filesystem mailbox-binding refresh for an active session
- **THEN** the runtime updates the filesystem mailbox binding env vars for that session
- **AND THEN** the runtime updates the persisted session manifest to match the refreshed mailbox binding state
- **AND THEN** subsequent runtime-controlled work in that session uses the refreshed filesystem mailbox bindings

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

### Requirement: Runtime mail commands use skill-directed prompts with appended mailbox metadata and validate a sentinel-delimited result contract
The runtime SHALL translate each `mail` command invocation into a runtime-owned mailbox prompt delivered through the existing prompt-turn control path rather than directly manipulating mailbox files or mailbox SQLite state itself.

That mailbox prompt SHALL explicitly tell the agent which projected mailbox system skill to use for the mailbox operation and SHALL append structured mailbox metadata needed for the mailbox operation and result parsing.

The `mail` command handler SHALL validate exactly one structured mailbox result payload returned between `AGENTSYS_MAIL_RESULT_BEGIN` and `AGENTSYS_MAIL_RESULT_END` sentinels in the agent output and SHALL surface that result to the operator in a parseable form.

That sentinel-delimited structured result contract SHALL be the correctness boundary for mailbox result parsing. The runtime SHALL NOT rely on generic shadow dialog projection fidelity as the guarantee that mailbox result text was recovered exactly.

#### Scenario: Mail command uses skill-directed prompt with appended mailbox metadata
- **WHEN** a developer invokes a runtime `mail` command for a mailbox-enabled session
- **THEN** the runtime delivers a runtime-owned mailbox prompt through the existing prompt-turn control surface for that session
- **AND THEN** that prompt explicitly names the projected mailbox system skill the agent should use
- **AND THEN** that prompt tells the agent to inspect the shared mailbox `rules/` directory before interacting with shared mailbox state
- **AND THEN** that prompt tells the agent to use shared scripts from `rules/scripts/` for any mailbox step that touches `index.sqlite` or `locks/`
- **AND THEN** that prompt appends structured mailbox metadata for the mailbox operation and result contract

#### Scenario: Mail command returns structured mailbox result
- **WHEN** a mailbox-enabled agent completes a runtime `mail` request
- **THEN** the agent returns one structured mailbox result payload describing the mailbox operation outcome between the required sentinels
- **AND THEN** the runtime validates and prints that result in a parseable form for the operator

#### Scenario: Shadow-mode mailbox parsing relies on the schema contract rather than exact projection cleanup
- **WHEN** a mailbox-enabled shadow-mode session returns one sentinel-delimited JSON result together with surrounding TUI noise or imperfect projection cleanup
- **THEN** the runtime still treats the sentinel-delimited structured payload as the reliability boundary
- **AND THEN** mailbox correctness does not depend on `dialog_projection.dialog_text` being an exact recovered reply transcript

#### Scenario: Mail command fails on malformed sentinel payload
- **WHEN** a mailbox-enabled agent omits the required sentinels, emits malformed JSON, or returns more than one sentinel-delimited mailbox result payload
- **THEN** the runtime returns an explicit mailbox-result parsing error for that `mail` command
- **AND THEN** the runtime does not send an automatic retry prompt in v1

#### Scenario: Mail command fails fast when session cannot accept a new turn
- **WHEN** a developer invokes a runtime `mail` command for a session that is already busy or otherwise cannot safely accept a new prompt turn
- **THEN** the runtime returns an explicit mailbox-command error
- **AND THEN** the runtime does not silently queue hidden mailbox work for later execution

### Requirement: Runtime mail send and reply commands require full recipient addresses and explicit body inputs
The runtime `mail` command surface SHALL treat `send` and `reply` as explicit mailbox operations rather than prompt-composition helpers.

For `mail send`, the runtime SHALL require recipients in full mailbox-address form for all `--to` and `--cc` inputs.

For `mail send` and `mail reply`, the runtime SHALL require explicit body input through `--body-file` or `--body-content`.

The runtime SHALL reject `--instruction` for `mail send` and `mail reply`.

#### Scenario: Mail send accepts full mailbox address plus explicit inline body
- **WHEN** a developer invokes `mail send` for a resumed mailbox-enabled session with `--to AGENTSYS-bob@agents.localhost` and `--body-content`
- **THEN** the runtime accepts the request as a mailbox operation
- **AND THEN** the resulting mailbox request preserves the sender identity already bound to that session

#### Scenario: Mail send rejects ambiguous short recipient names
- **WHEN** a developer invokes `mail send` with `--to bob`
- **THEN** the runtime fails fast with an explicit validation error
- **AND THEN** the error explains that a full mailbox address is required

#### Scenario: Mail send or reply rejects missing explicit body input
- **WHEN** a developer invokes `mail send` or `mail reply` without `--body-file` and without `--body-content`
- **THEN** the runtime fails fast before prompting the live agent session
- **AND THEN** the error explains that explicit mail body content is required

#### Scenario: Mail send or reply rejects instruction-style composition
- **WHEN** a developer invokes `mail send` or `mail reply` with `--instruction`
- **THEN** the runtime rejects that request explicitly
- **AND THEN** the operator is directed to use `--body-file` or `--body-content` instead

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

### Requirement: Runtime filesystem mailbox env bindings follow the active mailbox registration path
When the runtime starts or refreshes a mailbox-enabled filesystem session, it SHALL derive mailbox filesystem bindings from the active mailbox registration rather than by reconstructing a mailbox path from `principal_id`.

At minimum, `AGENTSYS_MAILBOX_FS_INBOX_DIR` SHALL point at the inbox path for the active mailbox registration for the session's bound mailbox address.

If runtime bootstrap or refresh can detect that the target mailbox root still uses the unsupported principal-keyed layout from the earlier implementation, it SHALL fail explicitly and direct the operator to delete and re-bootstrap that mailbox root.

#### Scenario: Start session publishes address-based inbox binding
- **WHEN** the runtime starts a mailbox-enabled session whose active registration is `AGENTSYS-research@agents.localhost`
- **THEN** `AGENTSYS_MAILBOX_FS_INBOX_DIR` points at the inbox path for that active registration
- **AND THEN** the runtime does not derive that path by concatenating `mailboxes/<principal_id>/inbox`

#### Scenario: Refresh mailbox bindings follows the current active registration path
- **WHEN** the runtime refreshes mailbox bindings for an active mailbox-enabled session after resolving the active registration
- **THEN** `AGENTSYS_MAILBOX_FS_INBOX_DIR` is updated from the active mailbox registration path for that address
- **AND THEN** subsequent runtime-controlled mailbox work uses the refreshed path

#### Scenario: Unsupported stale mailbox root fails binding refresh explicitly
- **WHEN** the runtime attempts to bootstrap or refresh mailbox bindings against a stale principal-keyed mailbox root from the earlier implementation
- **THEN** the runtime fails explicitly
- **AND THEN** the error tells the operator to delete and re-bootstrap the mailbox root rather than silently deriving incorrect bindings

### Requirement: Runtime-generated CAO agent profiles from roles
When using CAO, the system SHALL generate CAO agent profiles at runtime from repo role packages rather than requiring committed/static CAO profile files.

#### Scenario: Generate and install a CAO profile for a role
- **WHEN** a developer launches a CAO-backed session with role `R`
- **THEN** the system generates an agent profile whose system prompt is derived from `agents/roles/<R>/system-prompt.md`
- **AND THEN** the CAO terminal launch references that generated profile by name

### Requirement: Credential env var allowlist enforcement at launch
The system SHALL apply only allowlisted credential environment variables at launch time, as defined by the selected tool adapter and credential profile.

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

#### Scenario: Headless session includes allowlisted model env vars from credential profile
- **WHEN** a developer starts a Claude headless session and the selected credential profile env file defines `ANTHROPIC_MODEL` (and/or `ANTHROPIC_SMALL_FAST_MODEL` and/or `CLAUDE_CODE_SUBAGENT_MODEL` and/or one of the `ANTHROPIC_DEFAULT_*_MODEL` pinning vars)
- **THEN** the headless Claude subprocess environment SHALL include the corresponding model-selection env var(s)

### Requirement: Credential profile sharing is permitted
The system SHALL allow launching multiple sessions that reference the same credential profile.

#### Scenario: Launch does not require exclusive credential ownership
- **WHEN** a developer launches two sessions selecting the same credential profile name
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
The system SHALL persist a session manifest JSON (session handle) alongside the brain manifest for audit/resume/stop.

#### Scenario: Start session writes a session manifest
- **WHEN** a developer starts a session
- **THEN** the system writes a session manifest JSON that records the backend type and the minimal reconnect/stop fields (e.g., process identity for long-lived backends, `session_id` for resumable headless backends, terminal IDs and CAO API base URL for CAO, artifact paths, working directory)

#### Scenario: Resume headless session from persisted manifest
- **WHEN** a developer resumes a Claude/Gemini session from a persisted session manifest
- **THEN** the system uses the persisted `session_id` with backend resume flags for the next prompt
- **AND THEN** if required resume fields are missing or invalid, the system returns an explicit resume error instead of silently starting an unrelated new conversation

#### Scenario: Resume CAO session from persisted manifest (manifest-only addressing)
- **WHEN** a developer resumes a CAO-backed session from a persisted session manifest (for prompt sending or stop)
- **THEN** the system uses the persisted `cao.api_base_url` and `cao.terminal_id` as the sole address for the resumed operation (no external base URL override)
- **AND THEN** if required CAO manifest fields are missing/blank or internally inconsistent (for example `cao.api_base_url` != `backend_state.api_base_url`), the system fails fast with `SessionManifestError`
- **AND THEN** if CAO network/HTTP requests fail, the system reports the failure as `BackendExecutionError`

### Requirement: Runtime defaults new build and session state to the Houmao runtime root
When the caller does not provide an explicit runtime-root override, the runtime SHALL default new Houmao-managed build and session state to `~/.houmao/runtime`.

When no explicit runtime-root override is supplied and `AGENTSYS_GLOBAL_RUNTIME_DIR` is set to an absolute directory path, the runtime SHALL use that env-var value as the effective runtime root instead of the built-in default.

At minimum, this default SHALL apply to:
- generated brain homes under `~/.houmao/runtime/homes/<home-id>/`,
- generated manifests under `~/.houmao/runtime/manifests/<home-id>.yaml`,
- runtime-owned session roots for started sessions,
- other durable runtime-owned session artifacts that are derived from the effective runtime root.

Explicit runtime-root overrides SHALL continue to take precedence over the default.

The default build-state layout SHALL NOT require tool- or family-based directory bucketing in order to associate a generated home or manifest with an agent.

When the runtime needs to associate that flat build or session state with one agent, it SHALL rely on persisted canonical agent name, authoritative `agent_id`, persisted terminal metadata, and other explicit runtime metadata rather than on bucket names in the directory hierarchy.

Whenever runtime-owned directory naming needs one path component that stands for one agent rather than one session, backend, or service instance, the runtime SHALL use authoritative `agent_id` for that directory name instead of canonical agent name.

#### Scenario: Build flow defaults generated homes and manifests to the Houmao runtime root
- **WHEN** a developer runs a build flow without an explicit runtime-root override
- **THEN** the generated brain home and manifest are written under `~/.houmao/runtime`

#### Scenario: Build flow does not require tool-family buckets in the default layout
- **WHEN** a developer runs a build flow without an explicit runtime-root override
- **THEN** the generated home path is rooted under `~/.houmao/runtime/homes/<home-id>/`
- **AND THEN** the generated manifest path is rooted under `~/.houmao/runtime/manifests/<home-id>.yaml`
- **AND THEN** those default paths do not require an intermediate tool- or family-grouping bucket

#### Scenario: Start-session defaults durable session state to the Houmao runtime root
- **WHEN** a developer starts a runtime-owned session without an explicit runtime-root override
- **THEN** the session manifest and other durable runtime-owned session artifacts are rooted under `~/.houmao/runtime`

#### Scenario: Runtime-root env-var override redirects durable runtime state
- **WHEN** `AGENTSYS_GLOBAL_RUNTIME_DIR` is set to `/tmp/houmao-runtime`
- **AND WHEN** a developer starts a runtime-owned session without an explicit runtime-root override
- **THEN** the session manifest and other durable runtime-owned session artifacts are rooted under `/tmp/houmao-runtime`

### Requirement: Runtime materializes canonical agent name and authoritative `agent_id` for system-owned association
For runtime-owned sessions, the runtime SHALL persist canonical agent name as a strong human-facing metadata field for normal operator use, but it SHALL NOT treat canonical agent name as the authoritative writable-state key.

The runtime SHALL materialize an authoritative `agent_id` in persisted runtime-owned metadata and in any shared-registry publication derived from that session, and that `agent_id` SHALL replace registry-specific `agent_key` for cross-module identity association.

The session-manifest schema for this capability SHALL expose canonical agent name and authoritative `agent_id` as first-class top-level manifest fields rather than burying them inside `backend_state`.

When the caller does not provide an explicit `agent_id`, the runtime SHALL first reuse a previously persisted `agent_id` for the same built or resumed agent when one exists in manifest metadata, build metadata, or equivalent runtime-owned metadata.

Only when no explicit `agent_id` and no previously persisted `agent_id` exist SHALL the runtime bootstrap the initial `agent_id` as the full lowercase `md5(canonical agent name).hexdigest()`.

When runtime-controlled start, resume, or publication logic encounters an existing association for the same `agent_id` but a different canonical agent name, the runtime SHALL emit a warning and continue treating that `agent_id` as authoritative for system-owned writable association.

When runtime-controlled lookup encounters more than one live or persisted association for the same canonical agent name but different authoritative `agent_id` values, the runtime SHALL surface ambiguity rather than silently treating those associations as one agent.

#### Scenario: Start-session bootstraps a default agent id from the canonical agent name when no persisted id exists
- **WHEN** a developer starts a runtime-owned session with canonical agent name `AGENTSYS-gpu`
- **AND WHEN** the caller does not provide an explicit `agent_id`
- **AND WHEN** no previously persisted `agent_id` exists for that same built or resumed agent
- **THEN** the runtime materializes the full lowercase `md5("AGENTSYS-gpu").hexdigest()` value as the session's initial authoritative `agent_id`
- **AND THEN** persisted runtime-owned metadata for that session records both the canonical agent name and the bootstrapped `agent_id`

#### Scenario: Start-session reuses a previously persisted agent id
- **WHEN** a developer starts or resumes a runtime-owned session for an agent whose existing persisted metadata already carries `agent_id=abc123`
- **AND WHEN** the caller does not provide an explicit replacement `agent_id`
- **THEN** the runtime reuses `agent_id=abc123`
- **AND THEN** it does not silently replace that authoritative identity by recomputing from the current canonical agent name

#### Scenario: Agent-keyed runtime-owned directories use agent id rather than canonical agent name
- **WHEN** runtime-owned directory derivation needs one path component that stands for one agent
- **THEN** the runtime uses that agent's authoritative `agent_id` for the directory name
- **AND THEN** canonical agent name remains an operator-facing metadata field rather than the writable directory key

#### Scenario: Explicit agent id reused with a different canonical name triggers a warning
- **WHEN** runtime-owned metadata or shared-registry publication already associates `agent_id=abc123` with canonical agent name `AGENTSYS-gpu`
- **AND WHEN** a later runtime-controlled start or publication explicitly uses `agent_id=abc123` with canonical agent name `AGENTSYS-editor`
- **THEN** the runtime emits a warning about the different-name same-id association
- **AND THEN** the runtime still treats `agent_id=abc123` as the authoritative writable-state identity

#### Scenario: Same canonical name with different agent ids is reported as ambiguous
- **WHEN** runtime-controlled lookup sees more than one live or persisted session metadata surface for canonical agent name `AGENTSYS-gpu`
- **AND WHEN** those metadata surfaces carry different authoritative ids such as `agent_id=abc123` and `agent_id=def456`
- **THEN** the runtime reports that canonical-name lookup is ambiguous
- **AND THEN** it requires disambiguation by `agent_id`, manifest path, or another explicit metadata surface

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
For each runtime-owned started session, the runtime SHALL derive a per-agent job dir at `<working-directory>/.houmao/jobs/<session-id>/`.

When no explicit job-dir override is supplied and `AGENTSYS_LOCAL_JOBS_DIR` is set to an absolute directory path for that launch or started agent, the runtime SHALL derive the effective per-agent job dir as:
- `<AGENTSYS_LOCAL_JOBS_DIR>/<session-id>/`

The runtime SHALL create that directory before the session needs runtime-managed scratch space and SHALL expose its absolute path to the launched session through `AGENTSYS_JOB_DIR`.

The per-agent job dir SHALL be intended for session-local logs, temporary outputs, and destructive scratch work, and SHALL NOT replace the durable runtime-owned session root under the effective runtime root.

Resume and later runtime-controlled work for the same persisted session SHALL continue to use the same derived per-agent job dir rather than allocating a replacement directory for that same session id.

For this capability, runtime-controlled stop behavior SHALL NOT automatically remove the job dir.

#### Scenario: Start-session creates the job dir and publishes its binding
- **WHEN** a developer starts a runtime-owned session with working directory `/repo/app`
- **AND WHEN** the generated session id is `session-20260314-120000Z-abcd1234`
- **THEN** the runtime creates `/repo/app/.houmao/jobs/session-20260314-120000Z-abcd1234/`
- **AND THEN** the started session environment includes `AGENTSYS_JOB_DIR` pointing to that absolute path

#### Scenario: Resume reuses the same job dir for the same session
- **WHEN** the runtime resumes control of a previously started session whose working directory and session id already determine one per-agent job dir
- **THEN** resumed runtime-controlled work continues to use that same per-agent job dir
- **AND THEN** the runtime does not allocate a different destructive-scratch directory for that same logical session

#### Scenario: Local-jobs-dir env-var override relocates the effective job dir
- **WHEN** `AGENTSYS_LOCAL_JOBS_DIR` is set to `/tmp/houmao-jobs`
- **AND WHEN** the runtime starts a runtime-owned session whose generated session id is `session-20260314-120000Z-abcd1234`
- **THEN** the runtime creates `/tmp/houmao-jobs/session-20260314-120000Z-abcd1234/`
- **AND THEN** the started session environment includes `AGENTSYS_JOB_DIR` pointing to that absolute path

#### Scenario: Stop-session does not auto-clean the job dir in this version
- **WHEN** a runtime-owned session has created a job dir for one session id
- **AND WHEN** a developer later stops that session through runtime-controlled stop behavior
- **THEN** the runtime leaves the job dir in place in this version
- **AND THEN** later cleanup of that scratch directory remains manual

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
- applying configured non-interactive launch flags needed to reduce interactive startup prompts (including `approval_policy` / `sandbox_mode` only when explicitly present in the selected Codex config profile; the runtime SHALL NOT hardcode new approval/sandbox defaults).

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

#### Scenario: Unknown business state reaches stalled threshold
- **WHEN** shadow polling remains on a supported surface with `business_state = unknown`
- **AND WHEN** elapsed unknown duration reaches `unknown_to_stalled_timeout_seconds`
- **THEN** runtime marks the shadow lifecycle state as `stalled`

#### Scenario: Unknown input mode alone does not enter stalled
- **WHEN** shadow polling remains on a supported surface with a known `business_state`
- **AND WHEN** only `input_mode = unknown`
- **THEN** runtime keeps the surface non-ready
- **AND THEN** it does not enter `stalled` solely because the input mode is unknown

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
- `shadow_only`: readiness and completion from runtime shadow surface assessment derived from CAO `output?mode=full`, with prompt submission and completion determined by runtime predicates over `availability`, `business_state`, `input_mode`, and post-submit progress evidence.

For `shadow_only`, the runtime SHALL treat a surface as submit-ready only when all of the following are true:

- `availability = supported`
- `business_state = idle`
- `input_mode = freeform`

For `shadow_only`, the runtime SHALL surface projected dialog data derived from `output?mode=full` and SHALL NOT require parser-owned prompt-associated answer extraction to complete the turn.
For `shadow_only`, success terminality SHALL require a return to the submit-ready surface plus either:
- projected-dialog change observed after submit, or
- post-submit observation of `business_state = working`.

This completion gate intentionally uses full `submit_ready`, not merely "the surface looks typeable again." A `shadow_only` turn SHALL NOT complete while `business_state = working`, even when `input_mode = freeform`.

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
- **AND WHEN** projected dialog has not changed since submit
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

1. update progress evidence from projected-dialog change and `business_state = working`
2. `availability in {unsupported, disconnected}` -> fail
3. `business_state = awaiting_operator` -> blocked outcome
4. unknown-for-stall surface -> unknown or stalled path
5. `business_state = working` -> keep `in_progress` regardless of `input_mode`
6. `submit_ready` plus previously-seen progress evidence -> complete
7. otherwise remain in a post-submit waiting state

#### Scenario: Working modal surface remains in progress during completion
- **WHEN** a post-submit `shadow_only` observation shows `availability = supported`, `business_state = working`, and `input_mode = modal`
- **THEN** the runtime keeps the turn in an in-progress lifecycle path
- **AND THEN** it does not complete the turn or treat the modal input mode as a blocked outcome by itself

#### Scenario: Awaiting-operator surface is evaluated before ready or complete
- **WHEN** a `shadow_only` observation shows `business_state = awaiting_operator`
- **THEN** the runtime routes the observation to a blocked-surface outcome before considering ready or completion gating
- **AND THEN** it does not treat that observation as submit-ready or completed

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
For `shadow_only`, the surfaced `dialog_projection` SHALL remain a best-effort text projection that is suitable for lifecycle diffing, operator inspection, and caller-owned best-effort extraction, but SHALL NOT be represented as an exact recovered reply transcript.
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
For CAO-backed sessions, parsing mode selection (`cao_only` or `shadow_only`) SHALL NOT change AGENTSYS agent-identity semantics or tmux manifest-pointer addressing behavior.

#### Scenario: Start-session still publishes AGENTSYS identity and manifest pointer in both modes
- **WHEN** a developer starts a CAO-backed session with `parsing_mode=cao_only` or `parsing_mode=shadow_only`
- **THEN** the runtime still persists canonical `AGENTSYS-...` identity metadata and the manifest pointer for the session
- **AND THEN** the tmux session name remains a distinct live-session handle rather than the authoritative agent identity
- **AND THEN** tmux session env includes `AGENTSYS_MANIFEST_PATH` pointing to the absolute persisted session manifest path

#### Scenario: Name-based prompt/stop addressing remains mode-independent
- **WHEN** a developer targets an agent by `--agent-identity <name>`
- **AND WHEN** the underlying CAO session was started in either parsing mode
- **THEN** manifest resolution still uses tmux session + `AGENTSYS_MANIFEST_PATH`
- **AND THEN** manifest/session mismatch checks still fail fast before control operations proceed

### Requirement: Name-addressed tmux-backed session control SHALL recover `agent_def_dir` from session environment
For tmux-backed session-control commands that accept `--agent-identity` (`send-prompt`, `send-keys`, and `stop-session`), the system SHALL allow callers to omit `--agent-def-dir` when the identity is name-based rather than path-like.

When `--agent-identity` is name-based and `--agent-def-dir` is omitted, the
system SHALL:
- resolve the addressed tmux session by canonical agent identity,
- prefer the tmux-published `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR` values when they are present and valid,
- fall back to fresh shared-registry discovery metadata when tmux-local discovery pointers are missing, blank, or stale, and
- use the recovered absolute agents root for resume or control operations.

The shared-registry fallback SHALL apply only to discovery-pointer unavailability. Hard validation mismatches such as a manifest whose persisted tmux session identity does not match the addressed agent name SHALL still fail fast.

When `--agent-def-dir` is provided explicitly, the system SHALL use the
explicit CLI value instead of the tmux-published or registry-published fallback.

Manifest-path control flows are unchanged by this requirement.

#### Scenario: Name-based send-prompt omits explicit agent-def-dir
- **WHEN** a developer runs `send-prompt --agent-identity chris --prompt "hello"`
- **AND WHEN** tmux session `AGENTSYS-chris` exists
- **AND WHEN** that tmux session publishes valid `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR` values
- **THEN** the runtime resumes and delivers the prompt without requiring explicit `--agent-def-dir`

#### Scenario: Name-based stop-session omits explicit agent-def-dir
- **WHEN** a developer runs `stop-session --agent-identity chris`
- **AND WHEN** tmux session `AGENTSYS-chris` exists
- **AND WHEN** that tmux session publishes valid `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR` values
- **THEN** the runtime resumes and stops the addressed session without requiring explicit `--agent-def-dir`

#### Scenario: Name-based send-keys omits explicit agent-def-dir
- **WHEN** a developer runs `send-keys --agent-identity chris --sequence "<[Escape]>"`
- **AND WHEN** tmux session `AGENTSYS-chris` exists
- **AND WHEN** that tmux session publishes valid `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR` values
- **THEN** the runtime resumes and delivers the control-input request without requiring explicit `--agent-def-dir`

#### Scenario: Explicit CLI agent-def-dir overrides tmux fallback
- **WHEN** a developer runs `stop-session --agent-identity chris --agent-def-dir /abs/custom/agents`
- **AND WHEN** tmux session `AGENTSYS-chris` publishes a different `AGENTSYS_AGENT_DEF_DIR`
- **THEN** the runtime uses `/abs/custom/agents` as the effective agent-definition root

#### Scenario: Registry fallback covers missing tmux manifest pointer
- **WHEN** a developer runs `send-prompt --agent-identity chris --prompt "hi"`
- **AND WHEN** tmux session `AGENTSYS-chris` exists
- **AND WHEN** `AGENTSYS_MANIFEST_PATH` is missing, blank, or stale in that tmux session environment
- **AND WHEN** a fresh shared-registry record exists for `AGENTSYS-chris`
- **THEN** the runtime resolves the session through the shared-registry record instead of failing immediately on the tmux-local pointer problem

#### Scenario: Registry fallback covers missing tmux agent-def-dir pointer
- **WHEN** a developer runs `send-prompt --agent-identity chris --prompt "hi"`
- **AND WHEN** tmux session `AGENTSYS-chris` exists
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR` is missing, blank, or stale in that tmux session environment
- **AND WHEN** a fresh shared-registry record exists for `AGENTSYS-chris`
- **THEN** the runtime resolves the effective agent-definition root through the shared-registry record instead of failing immediately on the tmux-local pointer problem

#### Scenario: Identity mismatch still fails fast instead of falling back
- **WHEN** a developer runs a tmux-backed name-based control command for `AGENTSYS-chris`
- **AND WHEN** a candidate tmux-local or shared-registry manifest resolves to persisted tmux session identity other than `AGENTSYS-chris`
- **THEN** the runtime rejects the operation with an explicit mismatch error
- **AND THEN** it does not silently recover by targeting a different live session

#### Scenario: Manifest-path control does not depend on tmux fallback
- **WHEN** a developer runs `stop-session --agent-identity /abs/runtime/sessions/cao_rest/session.json`
- **THEN** the runtime keeps the existing manifest-path control flow
- **AND THEN** this change does not require tmux session environment lookup for that request

### Requirement: Runtime-launched agent subprocess env injects loopback `NO_PROXY` by default
The runtime SHALL, when launching agent backends via subprocess (for example,
Codex app-server and Claude/Gemini headless CLIs), preserve proxy variables for
agent egress and SHALL, by default, ensure loopback entries exist in `NO_PROXY`
and `no_proxy` (merge+append semantics; entries include `localhost`,
`127.0.0.1`, and `::1`).

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY`
or `no_proxy` for the spawned process and will respect caller-provided values.

#### Scenario: Non-CAO backend subprocess env injects loopback `NO_PROXY` by default
- **WHEN** a developer launches a non-CAO backend session (for example, Codex app-server or a headless CLI)
- **AND WHEN** caller environment includes `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`
- **THEN** the runtime-launched backend subprocess environment includes loopback `NO_PROXY`/`no_proxy` entries by default

#### Scenario: Preserve mode does not modify non-CAO subprocess `NO_PROXY`
- **WHEN** a developer launches a non-CAO backend session
- **AND WHEN** caller environment includes `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`
- **THEN** the runtime does not inject or modify `NO_PROXY`/`no_proxy` for the spawned backend process

### Requirement: Runtime CLI exposes a `send-keys` raw control-input path distinct from prompt submission
The runtime SHALL provide a caller-facing `send-keys` control-input command for resumed CAO-backed tmux sessions that is distinct from `send-prompt`.

The runtime session-control surface SHALL expose the corresponding advanced mixed-input operation as `send_input_ex()`.

The existing `send-prompt` command SHALL retain its current high-level prompt-turn semantics.

The control-input command SHALL:
- require `--agent-identity` and `--sequence`,
- support the global `--escape-special-keys` flag and the existing optional `--agent-def-dir` override pattern,
- accept the mixed sequence grammar defined by `runtime-tmux-control-input`,
- deliver the requested input without automatically pressing `Enter`, and
- return a single `SessionControlResult` with `action="control_input"` after delivery without waiting for prompt completion or advancing prompt-turn state.

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

In v1, the runtime SHALL publish attach metadata by default for newly started runtime-owned tmux-backed sessions and SHALL support live gateway attach for runtime-owned `backend=cao_rest` sessions first.

Supplying gateway listener overrides without either launch-time auto-attach or an explicit attach lifecycle action SHALL fail with an explicit error.

If a caller requests live gateway attach for any backend whose gateway adapter is not yet implemented, the runtime SHALL fail with an explicit unsupported-backend error rather than silently falling back to implicit direct control.

#### Scenario: Blueprint gateway defaults do not auto-attach the gateway by themselves
- **WHEN** a developer starts a session from a blueprint that declares `gateway.host` or `gateway.port`
- **AND WHEN** the developer does not request launch-time gateway attach
- **THEN** the runtime publishes attachability metadata for that session
- **AND THEN** the blueprint listener defaults do not cause a live gateway instance to start by themselves

#### Scenario: Gateway host or port overrides require an attach action
- **WHEN** a developer supplies gateway host or port overrides without requesting launch-time attach or an explicit attach lifecycle action
- **THEN** the runtime fails with an explicit gateway-lifecycle error
- **AND THEN** the session is not treated as having a live gateway instance implicitly

#### Scenario: Unsupported backend rejects live gateway attach in v1
- **WHEN** a developer requests live gateway attach for a runtime-owned tmux-backed backend other than the currently supported adapter set
- **THEN** the runtime fails that attach request with an explicit unsupported-backend error
- **AND THEN** the runtime does not silently convert that attach request into legacy direct control

### Requirement: Runtime-owned tmux sessions publish a stable gateway attach contract
When the runtime makes a tmux-backed session gateway-capable, it SHALL publish a stable attach contract for that session in a secret-free file and SHALL expose the absolute path to that file through tmux session environment.

The attach contract SHALL be sufficient for a later gateway attach flow to determine how to observe and control the live session.

The attach contract SHALL use one strict versioned schema for both runtime-owned sessions in v1 and future manual-session adopters.

That strict schema SHALL require a shared core containing at least:

- `schema_version`
- `attach_identity`
- `backend`
- `tmux_session_name`
- `working_directory`
- `backend_metadata`

That strict schema MAY additionally include runtime-owned-only fields such as:

- `manifest_path`
- `agent_def_dir`
- `runtime_session_id`
- `desired_host`
- `desired_port`

Runtime-owned attach-contract publication SHALL populate the shared core and any runtime-owned fields that are available for that live session.

Runtime-owned attachability publication SHALL coexist with the existing manifest and agent-definition discovery pointers instead of replacing them.

For runtime-owned sessions in v1, the canonical runtime-owned session root SHALL be `<runtime_root>/sessions/<backend>/<session_id>/`, using the runtime-generated session id used for manifest storage. The session manifest SHALL live at `<session-root>/manifest.json`, the gateway root SHALL live at `<session-root>/gateway`, and the attach contract SHALL live at `<session-root>/gateway/attach.json`.

#### Scenario: Session start publishes attach metadata without a live gateway
- **WHEN** a developer starts a runtime-owned tmux-backed session without launch-time gateway attach
- **THEN** the runtime publishes stable gateway attach metadata for that live session
- **AND THEN** the session can remain gateway-capable even though no gateway instance is currently running

#### Scenario: Resume re-publishes attach metadata
- **WHEN** the runtime resumes control of a runtime-owned tmux-backed session
- **AND WHEN** attachability metadata for that session can be determined from persisted session state
- **THEN** the runtime re-publishes the attach-contract pointer for that live session
- **AND THEN** later attach flows do not need to rediscover the session from unrelated state

#### Scenario: Runtime-owned session root and gateway root use the persisted session id
- **WHEN** the runtime starts a runtime-owned tmux-backed session with generated session id `cao_rest-20260312-120000Z-abcd1234`
- **THEN** the stable runtime-owned session root for that session is derived from that persisted session id under `<runtime_root>/sessions/<backend>/<session_id>/`
- **AND THEN** the session manifest path for that session is `<session-root>/manifest.json`
- **AND THEN** the gateway root for that session is `<session-root>/gateway`
- **AND THEN** the attach-contract path for that session is `<session-root>/gateway/attach.json`

#### Scenario: Runtime-owned attach contract publishes required core plus optional runtime fields
- **WHEN** the runtime publishes attach metadata for a gateway-capable runtime-owned tmux session
- **THEN** the attach contract includes the required shared core fields for attach identity, backend kind, tmux session name, working directory, and backend metadata
- **AND THEN** runtime-owned fields such as `manifest_path` and `runtime_session_id` are included when available
- **AND THEN** the contract is validated as one strict versioned schema rather than as an open-ended map

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
2. caller environment variable `AGENTSYS_AGENT_GATEWAY_HOST`
3. blueprint configuration value `gateway.host`
4. default `127.0.0.1`

Allowed effective gateway host values in this change are exactly `127.0.0.1` and `0.0.0.0`.

The precedence order for the effective gateway port SHALL be:

1. lifecycle CLI override for the attach action in progress
2. caller environment variable `AGENTSYS_AGENT_GATEWAY_PORT`
3. blueprint configuration value `gateway.port`
4. a system-assigned port request during gateway startup when none of the above are provided

When none of the above sources provide a gateway port, the runtime SHALL request a system-assigned port during gateway startup and SHALL NOT pre-probe a free port in the parent runtime process.

After resolving that effective gateway host and effective gateway port request, the runtime SHALL use the resolved host and the actual bound port for the active gateway instance's metadata, tmux environment publication, and gateway startup.

If the resolved gateway listener cannot be bound during gateway start, the runtime SHALL fail that attach or auto-attach action explicitly and SHALL NOT silently replace it with a different host or port.

When a gateway instance starts successfully with a system-assigned port, the runtime SHALL persist that resolved host and port as the desired listener for the gateway root and SHALL reuse them on later restarts unless a caller explicitly overrides them.

#### Scenario: Default host remains loopback when no host override is supplied
- **WHEN** a developer starts a gateway attach action without an explicit gateway-host override
- **AND WHEN** caller environment omits `AGENTSYS_AGENT_GATEWAY_HOST`
- **AND WHEN** the selected blueprint does not declare `gateway.host`
- **THEN** the runtime resolves `127.0.0.1` as the effective gateway host for that session
- **AND THEN** the started session does not expose all-interface binding by default

#### Scenario: Explicit gateway-host override enables all-interface bind
- **WHEN** a developer starts a gateway attach action with `--gateway-host 0.0.0.0`
- **THEN** the runtime resolves `0.0.0.0` as the effective gateway host for that session
- **AND THEN** the started gateway instance binds its HTTP listener on all interfaces for the resolved port

#### Scenario: CLI gateway-port override wins over env and blueprint defaults
- **WHEN** a developer starts a gateway attach action with `--gateway-port 43123`
- **AND WHEN** caller environment sets `AGENTSYS_AGENT_GATEWAY_PORT=43124`
- **AND WHEN** the selected blueprint declares `gateway.port: 43125`
- **THEN** the runtime resolves `43123` as the effective gateway port for that session
- **AND THEN** the started session records and publishes `43123` as its gateway port

#### Scenario: Env gateway-port override wins over blueprint default
- **WHEN** a developer starts a gateway attach action without `--gateway-port`
- **AND WHEN** caller environment sets `AGENTSYS_AGENT_GATEWAY_PORT=43124`
- **AND WHEN** the selected blueprint declares `gateway.port: 43125`
- **THEN** the runtime resolves `43124` as the effective gateway port for that session
- **AND THEN** the started session does not treat the blueprint default as the effective port

#### Scenario: Runtime requests a system-assigned port when no explicit gateway port is supplied
- **WHEN** a developer starts a gateway attach action without `--gateway-port`
- **AND WHEN** caller environment omits `AGENTSYS_AGENT_GATEWAY_PORT`
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
For gateway-capable runtime-owned tmux sessions, the runtime SHALL persist the stable gateway attach metadata needed to rediscover the same session-owned gateway root, attach contract, and protocol context on resume.

#### Scenario: Session start persists gateway metadata for resume
- **WHEN** a developer starts a gateway-capable runtime-owned tmux session
- **THEN** the runtime persists the gateway metadata needed to rediscover that session's session-owned gateway root and attach context later
- **AND THEN** resumed control paths can validate or restore gateway discovery using persisted session state instead of re-deriving an unrelated gateway location

#### Scenario: Resume preserves stable attach identity for a live session
- **WHEN** a developer resumes control of a gateway-capable runtime-owned tmux session
- **THEN** the runtime uses the persisted session state to rediscover the expected session-owned gateway root and attach contract for that live session
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

### Requirement: Runtime publishes stable attach pointers and ephemeral live gateway bindings separately
When the runtime makes a tmux-backed session gateway-capable, it SHALL publish stable attach pointers into the tmux session environment in addition to the existing manifest and agent-definition bindings.

When a live gateway instance is currently attached, the runtime or gateway lifecycle SHALL also publish live gateway bindings for that running instance.

At minimum, the runtime SHALL publish:

- `AGENTSYS_GATEWAY_ATTACH_PATH`
- `AGENTSYS_GATEWAY_ROOT`

When a live gateway instance exists, the system SHALL additionally publish:

- `AGENTSYS_AGENT_GATEWAY_HOST`
- `AGENTSYS_AGENT_GATEWAY_PORT`
- `AGENTSYS_GATEWAY_STATE_PATH`
- `AGENTSYS_GATEWAY_PROTOCOL_VERSION`

When runtime-owned recovery rebinds the same logical session to a replacement managed-agent instance, the runtime or gateway lifecycle SHALL also refresh any published runtime-managed metadata needed to distinguish the new managed-agent instance from the one that failed.

When resumed runtime control has already determined the effective attach metadata or live gateway bindings for the same live session, it SHALL re-publish the applicable bindings into the tmux session environment.

#### Scenario: Session start publishes stable attach pointers
- **WHEN** the runtime starts a gateway-capable tmux-backed session
- **THEN** the tmux session environment contains `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`
- **AND THEN** those bindings point to the stable attach contract and nested session-owned gateway root for that session even when no gateway instance is running

#### Scenario: Live gateway attach publishes active gateway bindings
- **WHEN** the runtime or lifecycle command attaches a live gateway instance to a gateway-capable tmux-backed session
- **THEN** the tmux session environment contains `AGENTSYS_AGENT_GATEWAY_HOST`, `AGENTSYS_AGENT_GATEWAY_PORT`, `AGENTSYS_GATEWAY_STATE_PATH`, and `AGENTSYS_GATEWAY_PROTOCOL_VERSION`
- **AND THEN** those bindings point to the currently running gateway instance rather than merely to stable attachability

#### Scenario: Managed-agent replacement refreshes runtime-managed metadata
- **WHEN** runtime-owned recovery preserves a logical session but binds a replacement managed-agent instance for it
- **THEN** the runtime or gateway lifecycle refreshes the runtime-managed metadata associated with that logical session
- **AND THEN** later gateway-aware readers can distinguish the replacement managed-agent instance from the one that failed without allocating a new gateway root

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
When the runtime starts or resumes control of a runtime-owned tmux-backed session, it SHALL publish or refresh a shared-registry record for that live session under the effective shared-registry root's `live_agents/` directory.

By default, the effective shared-registry root SHALL be `~/.houmao/registry`.

When `AGENTSYS_GLOBAL_REGISTRY_DIR` is set, the runtime SHALL publish and refresh shared-registry records under that override path instead.

For runtime-owned tmux-backed sessions, the published shared-registry record SHALL persist the canonical `AGENTSYS-...` agent identity together with the authoritative `agent_id` and the actual tmux session name for that live session.

When runtime publication code receives an agent name in namespace-free form, it SHALL canonicalize that name to the exact `AGENTSYS-...` form before publishing the shared-registry record.

For a given live runtime-owned tmux-backed session, the runtime SHALL persist and reuse the same shared-registry `generation_id` across later refreshes and resume-driven republishes of that same session.

That shared-registry record SHALL coexist with existing tmux session environment discovery pointers and SHALL NOT replace `AGENTSYS_MANIFEST_PATH`, `AGENTSYS_AGENT_DEF_DIR`, or the stable gateway attach pointers already published by the runtime.

The published record SHALL include the secret-free runtime-owned pointers available for that session, including the manifest path, runtime session root, authoritative `agent_id`, actual tmux session name, and any gateway or mailbox pointers that the runtime has already materialized.

#### Scenario: Session start publishes a shared-registry record alongside tmux pointers
- **WHEN** the runtime starts a runtime-owned tmux-backed session with canonical identity `AGENTSYS-gpu`
- **THEN** the runtime publishes the normal tmux session environment discovery pointers for that session
- **AND THEN** the runtime also publishes a shared-registry record under `~/.houmao/registry/live_agents/<agent-id>/record.json` that stores canonical agent name `AGENTSYS-gpu`

#### Scenario: Runtime publication canonicalizes namespace-free agent input
- **WHEN** runtime publication logic receives agent input `gpu` for a tmux-backed session
- **THEN** it canonicalizes that input to `AGENTSYS-gpu` before publishing the shared-registry record
- **AND THEN** the published record stores canonical agent name `AGENTSYS-gpu`

#### Scenario: CI override redirects runtime publication
- **WHEN** the runtime starts a runtime-owned tmux-backed session
- **AND WHEN** `AGENTSYS_GLOBAL_REGISTRY_DIR` is set for that process
- **THEN** the runtime publishes the shared-registry record for that session under the override path
- **AND THEN** the runtime does not publish that record under the default home-relative root for that process

#### Scenario: Resume refreshes the shared-registry record from persisted session state
- **WHEN** the runtime resumes control of a runtime-owned tmux-backed session whose manifest and gateway metadata can be determined
- **THEN** the runtime refreshes that session's shared-registry record
- **AND THEN** later discovery flows can locate the same live session without depending on a shared runtime-root layout

#### Scenario: Resume reuses the same shared-registry generation for the same live session
- **WHEN** the runtime resumes control of a runtime-owned tmux-backed session that already published a shared-registry record generation
- **THEN** the resumed publication reuses that same `generation_id`
- **AND THEN** resume does not create a replacement generation for the same still-live session

### Requirement: Runtime refreshes shared-registry records when runtime-owned publication state changes
When the runtime materializes or refreshes stable gateway capability for a session, attaches or detaches a live gateway, refreshes mailbox bindings, or persists updated runtime-owned session state after prompt or control actions, it SHALL refresh the corresponding shared-registry record for that same logical session.

When no live gateway is attached, the shared-registry record SHALL continue to publish stable gateway pointers when they exist, but SHALL omit live gateway connect metadata.

When mailbox bindings are available, the shared-registry record SHALL reflect the active mailbox principal id and full mailbox address for that session.

These refreshes SHALL keep the same `generation_id` for the same live session rather than manufacturing a replacement generation on each publication event.

#### Scenario: Live gateway attach adds connect metadata to the shared-registry record
- **WHEN** the runtime attaches a live gateway to a gateway-capable runtime-owned session
- **THEN** the runtime refreshes the shared-registry record for that session
- **AND THEN** the record publishes the exact live gateway connect metadata for the running listener

#### Scenario: Gateway detach preserves stable pointers but removes live connect metadata
- **WHEN** the runtime detaches a live gateway from a gateway-capable runtime-owned session
- **THEN** the runtime refreshes the shared-registry record for that session
- **AND THEN** the record keeps stable gateway pointers such as the attach-contract path when available
- **AND THEN** the record no longer advertises live gateway connect metadata

#### Scenario: Mailbox binding refresh updates mailbox identity in the shared-registry record
- **WHEN** the runtime refreshes mailbox bindings for a mailbox-enabled session
- **THEN** the runtime refreshes the shared-registry record for that session
- **AND THEN** the record reflects the active mailbox principal id and full mailbox address for the refreshed binding

#### Scenario: Prompt or control action refreshes the shared-registry lease for the same live session
- **WHEN** the runtime sends a prompt or persists updated state after another runtime-owned control action for a tmux-backed session that already published a shared-registry record
- **THEN** the runtime refreshes that session's shared-registry record
- **AND THEN** the refreshed record keeps the same `generation_id` while extending the lease for that still-live session

### Requirement: Runtime-owned teardown clears shared-registry discoverability for stopped sessions
When the runtime completes authoritative `stop-session` teardown for a runtime-owned tmux-backed session that has a shared-registry record, the runtime SHALL remove that record or rewrite it so that shared-registry readers treat it as expired.

Unexpected failure MAY leave stale `live_agents/` directories behind, but runtime-owned graceful teardown SHALL clear discoverability for the stopped session.

#### Scenario: Stop-session clears shared-registry discoverability
- **WHEN** an operator stops a runtime-owned tmux-backed session that previously published a shared-registry record
- **THEN** the runtime removes the record or expires it as part of teardown
- **AND THEN** later shared-registry readers do not treat that stopped session as live

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
