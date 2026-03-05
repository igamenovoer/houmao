## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Codex runtime launch applies non-interactive home bootstrap
For Codex launches, the runtime SHALL apply a runtime-owned bootstrap step to the generated Codex home configuration before starting the tool for:
- `backend=codex_app_server`
- `backend=codex_headless`
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

## REMOVED Requirements

### Requirement: Codex interactive backend via `codex app-server`
**Reason**: `codex app-server` is a tool-specific long-lived protocol that is not resumable from a persisted session manifest after runtime restart, and it diverges from the unified “CLI turn + resume id” headless pattern.

**Note**: In this change, `backend=codex_app_server` remains temporarily available as an explicit opt-in override for one deprecation window. It is no longer required and is not the default non-CAO Codex backend.

**Migration**: Use the Codex headless backend (`codex exec --json` for the first turn, then `codex exec --json resume <thread_id>` for subsequent turns) and persist the tool-native resume identifier in the session manifest.

#### Scenario: Codex headless replaces the app-server requirement
- **WHEN** a developer needs a resumable non-CAO Codex session across runtime restarts
- **THEN** they use the Codex headless backend based on `codex exec --json` + resume id rather than `codex app-server`
