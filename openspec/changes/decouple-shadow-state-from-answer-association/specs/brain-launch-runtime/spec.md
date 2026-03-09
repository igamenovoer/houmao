## MODIFIED Requirements

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
