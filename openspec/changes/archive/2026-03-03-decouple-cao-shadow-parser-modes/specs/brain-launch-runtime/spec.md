## ADDED Requirements

### Requirement: CAO parsing mode is explicit and constrained
For CAO-backed sessions, the system SHALL resolve a parsing mode at session start from configuration.

Allowed values are exactly:
- `cao_only`
- `shadow_only`

The selected mode SHALL be persisted in session runtime state so resumed operations use the same parsing mode.

Default mapping SHALL be:
- `tool=claude` -> `shadow_only`
- `tool=codex` -> `cao_only`

#### Scenario: Session start resolves parsing mode from tool default
- **WHEN** a caller starts a CAO-backed session without explicitly specifying parsing mode
- **AND WHEN** the tool is `claude`
- **THEN** the resolved parsing mode is `shadow_only`

#### Scenario: Session start fails when parsing mode cannot be resolved
- **WHEN** a caller starts a CAO-backed session and configuration does not provide an explicit parsing mode or a valid tool default
- **THEN** the system rejects the start request with an explicit validation error

#### Scenario: Unknown parsing mode is rejected
- **WHEN** a caller requests a parsing mode other than `cao_only` or `shadow_only`
- **THEN** the system rejects the request with an explicit unsupported-mode error

### Requirement: CAO `start-session` output includes resolved parsing mode
For CAO-backed sessions, the `start-session` CLI output SHALL include the resolved `parsing_mode` alongside the canonical agent identity.

#### Scenario: Start-session output includes parsing mode
- **WHEN** a developer starts a CAO-backed session with `parsing_mode=cao_only` or `parsing_mode=shadow_only`
- **THEN** the `start-session` output includes the resolved `parsing_mode`

## MODIFIED Requirements

### Requirement: CAO backend sends input only when terminal is ready and does not use inbox
When using the CAO backend, the system SHALL only send terminal input when the target terminal is ready for the selected parsing mode, SHALL not use CAO inbox messaging, and SHALL fetch/derive output only after request completion for the same mode.

Mode-specific readiness/completion behavior SHALL be:
- `cao_only`: readiness/completion from CAO terminal status (`idle|completed`) and answer retrieval from CAO `output?mode=last`.
- `shadow_only`: readiness/completion from runtime shadow status derived from CAO `output?mode=full`, with answer extraction by the runtime shadow parser.

The runtime SHALL NOT mix parser families in one turn. If a mode-specific parser/extraction step fails, the turn SHALL fail without invoking the other mode in the same turn.
The runtime SHALL NOT perform an automatic retry under the other parser mode after a mode-specific failure.

#### Scenario: `cao_only` waits for CAO status and uses `mode=last`
- **WHEN** a developer sends a prompt via a CAO-backed session with `parsing_mode=cao_only` while the terminal is `processing`
- **THEN** the system polls CAO terminal status until it becomes `idle|completed` (or timeout)
- **AND THEN** the system sends direct terminal input
- **AND THEN** the system waits for completion using CAO status and fetches answer text from `output?mode=last`

#### Scenario: `shadow_only` waits for shadow status and uses `mode=full`
- **WHEN** a developer sends a prompt via a CAO-backed session with `parsing_mode=shadow_only`
- **THEN** the system polls `output?mode=full` and computes runtime shadow readiness/completion status
- **AND THEN** the system sends direct terminal input only after shadow-ready state is observed
- **AND THEN** the system extracts answer text using the runtime shadow parser after shadow completion

#### Scenario: No in-turn parser mixing on failure
- **WHEN** mode-specific extraction fails during a CAO-backed turn
- **THEN** the system returns a mode-specific error
- **AND THEN** the system does not fall back to the other parser mode within the same turn

#### Scenario: No cross-mode automatic retry after failure
- **WHEN** a CAO-backed turn fails in `parsing_mode=shadow_only` or `parsing_mode=cao_only`
- **THEN** the system reports the mode-specific failure
- **AND THEN** the system does not automatically retry the turn under the other parser mode

### Requirement: Shared post-processing provides a stable runtime contract in both modes
For CAO-backed turns in both `parsing_mode=cao_only` and `parsing_mode=shadow_only`, the runtime SHALL apply a shared, parser-agnostic post-processing step after mode-specific gating/extraction.

This shared post-processing step SHALL NOT sanitize/rewrite extracted answer text. It SHALL canonicalize status/provenance into runtime-stable values for downstream consumers and record/log raw backend values for diagnostics.

#### Scenario: Shared post-processing runs regardless of parsing mode
- **WHEN** a CAO-backed turn completes in `parsing_mode=cao_only` or `parsing_mode=shadow_only`
- **THEN** shared post-processing is applied before the result is surfaced to the caller

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
