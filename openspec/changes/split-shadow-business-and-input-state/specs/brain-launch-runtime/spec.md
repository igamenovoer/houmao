## MODIFIED Requirements

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

For `shadow_only`, readiness SHALL follow the currently active input surface rather than any historical slash-command line still visible in earlier scrollback. Completed slash-command or model-switch output that remains in the projected dialog SHALL NOT keep a later recovered normal prompt in a non-ready state.
For `shadow_only`, an active modal surface such as slash-command SHALL remain non-ready until the provider returns to a freeform prompt, but SHALL NOT be treated as an operator-blocked failure solely because it is modal.
For `shadow_only`, a surface with `business_state = awaiting_operator` SHALL be treated as blocked and SHALL fail the active turn with explicit blocked-surface diagnostics.
For `shadow_only`, a surface with `business_state = working` and `input_mode = freeform` SHALL remain in progress and SHALL NOT be treated as submit-ready or complete merely because typing is possible.

The runtime SHALL NOT mix parser families in one turn. If a mode-specific parser or projection step fails, the turn SHALL fail without invoking the other mode in the same turn.
The runtime SHALL NOT perform an automatic retry under the other parser mode after a mode-specific failure.

#### Scenario: `cao_only` waits for CAO status and uses `mode=last`
- **WHEN** a developer sends a prompt via a CAO-backed session with `parsing_mode=cao_only` while the terminal is `processing`
- **THEN** the system polls CAO terminal status until it becomes `idle|completed` or times out
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

## ADDED Requirements

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
