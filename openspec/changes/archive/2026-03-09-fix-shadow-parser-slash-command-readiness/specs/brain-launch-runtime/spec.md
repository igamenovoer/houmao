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

For `shadow_only`, readiness SHALL follow the currently active input surface rather than any historical slash-command line still visible in earlier scrollback. Completed slash-command or model-switch output that remains in the projected dialog SHALL NOT keep a later recovered normal prompt in a non-ready state.
For `shadow_only`, an actually active slash-command or user-selection surface SHALL remain non-ready until the provider returns to a safe normal prompt or the runtime raises the corresponding waiting-user/readiness failure.

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

#### Scenario: Historical slash-command output does not block recovered shadow readiness
- **WHEN** a developer previously used a slash command or manual model switch in a CAO-backed session
- **AND WHEN** that slash-command echo or result is still visible in `output?mode=full`
- **AND WHEN** the current provider surface has already returned to a normal prompt that accepts input
- **THEN** the runtime treats the session as shadow-ready
- **AND THEN** it sends the next direct terminal input instead of waiting for a different surface classification

#### Scenario: Active slash-command surface remains non-ready
- **WHEN** a `shadow_only` CAO-backed session is still showing an active slash-command surface or command-driven user-selection surface
- **THEN** the runtime does not submit the next prompt
- **AND THEN** it continues waiting or raises the corresponding readiness/waiting-user failure until the surface returns to a safe normal prompt

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
