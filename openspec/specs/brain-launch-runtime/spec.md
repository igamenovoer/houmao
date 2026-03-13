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

The tmux session name SHALL follow the `AGENTSYS-...` agent identity rules.

The runtime SHALL publish `AGENTSYS_MANIFEST_PATH=<absolute manifest path>` into the tmux session environment so that name-based `--agent-identity` resolution can locate the persisted session manifest.

#### Scenario: Start a headless session creates a tmux identity with manifest pointer
- **WHEN** a developer starts a headless Codex, Claude, or Gemini session without CAO
- **THEN** the runtime creates a tmux session whose name is in the `AGENTSYS-` namespace
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

#### Scenario: CAO-backed session launch and messaging
- **WHEN** a developer starts a CAO-backed session and provides a CAO API base URL at session start
- **THEN** the system creates a CAO session/terminal, sends prompts, and fetches replies using CAO REST endpoints
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

#### Scenario: Start session projects mailbox system skills with filesystem bindings
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the tool adapter's active skills destination under the reserved runtime-owned namespace
- **AND THEN** the runtime starts the session with the filesystem mailbox binding env vars needed by those mailbox system skills
- **AND THEN** the runtime sets `AGENTSYS_MAILBOX_FS_ROOT` to the effective mailbox content root for that session

#### Scenario: Start session defaults filesystem mailbox root from runtime root
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from the configured runtime root
- **AND THEN** the runtime sets `AGENTSYS_MAILBOX_FS_ROOT` to that derived default path

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
The system SHALL keep JSON Schema files for runtime-generated structured artifacts inside the runtime package under `src/gig_agents/.../schemas/`.

#### Scenario: Session manifest schema is versioned and discoverable
- **WHEN** developers inspect the runtime package source
- **THEN** they can find versioned JSON Schema files (for example `session_manifest.v1.schema.json`) under the runtime package `schemas/` directory
- **AND THEN** generated artifacts include schema version information that selects the matching schema for validation

### Requirement: CAO parsing mode is explicit and constrained
For CAO-backed sessions, the system SHALL resolve a parsing mode at session start from configuration.

Allowed values are exactly:
- `cao_only`
- `shadow_only`

The selected mode SHALL be persisted in session runtime state so resumed operations use the same parsing mode.

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

#### Scenario: Session start fails when parsing mode cannot be resolved
- **WHEN** a caller starts a CAO-backed session and configuration does not provide an explicit parsing mode or a valid tool default
- **THEN** the system rejects the start request with an explicit validation error

#### Scenario: Unknown parsing mode is rejected
- **WHEN** a caller requests a parsing mode other than `cao_only` or `shadow_only`
- **THEN** the system rejects the request with an explicit unsupported-mode error

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
- **AND THEN** the runtime does not represent that projection as the authoritative final answer for the submitted prompt by default

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

### Requirement: CAO session start supports a human agent identity name and uses it as the tmux session name
When starting a CAO-backed session, the system SHALL allow the caller to provide an agent identity name via `start-session --agent-identity <name>` (name-only for CAO in this change).
For CAO-backed sessions, the system SHALL use the canonical `AGENTSYS-...` identity as the tmux session name.

If the caller does not provide a name, the system SHALL generate a short, easy-to-type name derived from the tool and role/blueprint identity, and SHALL add a conflict-avoiding suffix when needed.

#### Scenario: Start CAO session with an explicit name uses the canonical tmux session name
- **WHEN** a developer starts a CAO-backed session with `start-session --agent-identity gpu`
- **THEN** the tmux session name used for the session is `AGENTSYS-gpu`

#### Scenario: Start CAO session without a name auto-generates a short identity
- **WHEN** a developer starts a CAO-backed session without providing `--agent-identity`
- **THEN** the runtime selects a short `AGENTSYS-...` tmux session name derived from tool + role/blueprint
- **AND THEN** the selected name is unique among existing tmux sessions

### Requirement: CAO session start returns the selected agent identity
For CAO-backed sessions, the `start-session` CLI output SHALL include the selected canonical agent identity so callers can reuse it for subsequent prompt/stop operations.

#### Scenario: `start-session` output includes the canonical identity
- **WHEN** a developer starts a CAO-backed session
- **THEN** the `start-session` CLI output includes the selected canonical agent identity (for example `AGENTSYS-gpu`)

### Requirement: CAO `start-session` output includes resolved parsing mode
For CAO-backed sessions, the `start-session` CLI output SHALL include the resolved `parsing_mode` alongside the canonical agent identity.

#### Scenario: Start-session output includes parsing mode
- **WHEN** a developer starts a CAO-backed session with `parsing_mode=cao_only` or `parsing_mode=shadow_only`
- **THEN** the `start-session` output includes the resolved `parsing_mode`

### Requirement: Parsing mode changes do not alter AGENTSYS identity/addressing contracts
For CAO-backed sessions, parsing mode selection (`cao_only` or `shadow_only`) SHALL NOT change AGENTSYS agent-identity semantics or tmux manifest-pointer addressing behavior.

#### Scenario: Start-session still publishes AGENTSYS identity and manifest pointer in both modes
- **WHEN** a developer starts a CAO-backed session with `parsing_mode=cao_only` or `parsing_mode=shadow_only`
- **THEN** the tmux session identity follows canonical `AGENTSYS-...` naming rules
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
- recover the session manifest path from `AGENTSYS_MANIFEST_PATH`,
- recover the agent-definition root from `AGENTSYS_AGENT_DEF_DIR`, and
- use that recovered absolute agents root for resume/control operations.

When `--agent-def-dir` is provided explicitly, the system SHALL use the
explicit CLI value instead of the tmux-published fallback.

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

#### Scenario: Name-based fallback fails on missing tmux agent-def-dir pointer
- **WHEN** a developer runs `send-prompt --agent-identity chris --prompt "hi"`
- **AND WHEN** tmux session `AGENTSYS-chris` exists
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR` is missing or blank in that tmux session environment
- **THEN** the runtime rejects the operation with an explicit resolution error
- **AND THEN** it does not silently fall back to cwd-derived agent-definition defaults

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
For CAO-backed session startup (`backend=cao_rest`), when the runtime pre-creates
one bootstrap tmux window for env setup and CAO subsequently creates the real
agent terminal window, the runtime SHALL (best-effort) make the CAO terminal
window the session's current tmux window and SHALL prune the bootstrap window
when it can be safely identified as distinct from the CAO terminal window.

The runtime SHALL record the bootstrap tmux `window_id` immediately after
session creation and SHALL use `window_id` targeting (not index assumptions) for
window selection and pruning.

The runtime SHALL resolve the CAO terminal window id from `terminal.name` using
bounded retry (to tolerate transient tmux visibility races). If the CAO window
cannot be resolved within the bound, startup still succeeds and the runtime
emits a warning diagnostic.

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
