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

For supported loopback CAO base URLs (`http://localhost:9889`,
`http://127.0.0.1:9889`), runtime-owned CAO HTTP communication SHALL bypass
ambient proxy environment variables by default by ensuring loopback entries
exist in `NO_PROXY`/`no_proxy`.

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY`
or `no_proxy` and will respect caller-provided values (for example, to enable
traffic-watching development proxies).

#### Scenario: CAO-backed session launch and messaging
- **WHEN** a developer starts a CAO-backed session and provides a CAO API base URL at session start
- **THEN** the system creates a CAO session/terminal, sends prompts, and fetches replies using CAO REST endpoints
- **AND THEN** the system persists the CAO API base URL and terminal identity in the session manifest
- **AND THEN** subsequent prompt and stop operations target the CAO terminal using only the persisted session manifest fields (no CAO base URL override)

#### Scenario: Loopback CAO runtime communication bypasses caller proxy env
- **WHEN** a developer starts or resumes a CAO-backed session using a supported loopback CAO base URL
- **AND WHEN** caller environment includes `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`
- **THEN** runtime-owned CAO HTTP communication bypasses those proxy endpoints by default
- **AND THEN** loopback CAO connectivity depends on local CAO availability rather than external proxy availability

#### Scenario: Preserve mode respects caller `NO_PROXY` for loopback
- **WHEN** a developer starts or resumes a CAO-backed session using a supported loopback CAO base URL
- **AND WHEN** caller environment includes `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`
- **THEN** runtime-owned CAO HTTP communication uses caller-provided proxy and `NO_PROXY` settings

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
- readiness wait (before prompt submission), and
- completion wait (during turn execution).

When shadow status remains `unknown` continuously for at least `unknown_to_stalled_timeout_seconds`, runtime SHALL transition runtime status to `stalled` for the active wait phase.

#### Scenario: Unknown status duration reaches stalled threshold
- **WHEN** shadow polling repeatedly classifies output as `unknown`
- **AND WHEN** the continuous unknown duration reaches configured timeout
- **THEN** runtime marks the shadow lifecycle state as `stalled`

#### Scenario: Unknown during readiness reaches stalled threshold
- **WHEN** runtime is waiting for shadow-ready state before prompt submission
- **AND WHEN** shadow polling remains `unknown` continuously for at least `unknown_to_stalled_timeout_seconds`
- **THEN** runtime marks the shadow lifecycle state as `stalled` for the readiness phase

#### Scenario: Unknown during completion reaches stalled threshold
- **WHEN** runtime is waiting for shadow completion during turn execution
- **AND WHEN** shadow polling remains `unknown` continuously for at least `unknown_to_stalled_timeout_seconds`
- **THEN** runtime marks the shadow lifecycle state as `stalled` for the completion phase

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
When using the CAO backend, the system SHALL only send terminal input when the target terminal is ready for the selected parsing mode, SHALL not use CAO inbox messaging, and SHALL fetch/derive output only after request completion for the same mode.

Mode-specific readiness/completion behavior SHALL be:
- `cao_only`: readiness/completion from CAO terminal status (`idle|completed`) and answer retrieval from CAO `output?mode=last`.
- `shadow_only`: readiness/completion from runtime shadow surface assessment derived from CAO `output?mode=full`, with turn completion determined by runtime turn-monitor logic over post-submit surface transitions and snapshot/projection change.

For `shadow_only`, the runtime SHALL surface projected dialog data derived from `output?mode=full` and SHALL NOT require parser-owned prompt-associated answer extraction to complete the turn.
For `shadow_only`, success terminality SHALL require a return to `ready_for_input` plus either:
- projected-dialog change observed after submit, or
- post-submit observation of `working`.

The runtime SHALL NOT mix parser families in one turn. If a mode-specific parser/projection step fails, the turn SHALL fail without invoking the other mode in the same turn.
The runtime SHALL NOT perform an automatic retry under the other parser mode after a mode-specific failure.

#### Scenario: `cao_only` waits for CAO status and uses `mode=last`
- **WHEN** a developer sends a prompt via a CAO-backed session with `parsing_mode=cao_only` while the terminal is `processing`
- **THEN** the system polls CAO terminal status until it becomes `idle|completed` (or timeout)
- **AND THEN** the system sends direct terminal input
- **AND THEN** the system waits for completion using CAO status and fetches answer text from `output?mode=last`

#### Scenario: `shadow_only` waits for surface state and returns projected dialog
- **WHEN** a developer sends a prompt via a CAO-backed session with `parsing_mode=shadow_only`
- **THEN** the system polls `output?mode=full` and computes runtime shadow readiness/completion from provider surface assessment plus runtime turn-monitor logic
- **AND THEN** the system sends direct terminal input only after a shadow-ready state is observed
- **AND THEN** after turn completion the system surfaces projected dialog data and state/provenance metadata derived from `mode=full`
- **AND THEN** the system does not require parser-owned prompt-associated answer extraction to complete the turn

#### Scenario: `shadow_only` does not complete on idle alone when no post-submit evidence exists
- **WHEN** a `shadow_only` turn returns to `ready_for_input`
- **AND WHEN** the runtime has not observed post-submit `working`
- **AND WHEN** projected dialog has not changed since submit
- **THEN** the runtime does not mark the turn complete yet
- **AND THEN** it continues monitoring or fails according to turn-monitor timeout/stall policy

#### Scenario: No in-turn parser mixing on failure
- **WHEN** mode-specific projection or state-evaluation fails during a CAO-backed turn
- **THEN** the system returns a mode-specific error
- **AND THEN** the system does not fall back to the other parser mode within the same turn

#### Scenario: No cross-mode automatic retry after failure
- **WHEN** a CAO-backed turn fails in `parsing_mode=shadow_only` or `parsing_mode=cao_only`
- **THEN** the system reports the mode-specific failure
- **AND THEN** the system does not automatically retry the turn under the other parser mode

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
