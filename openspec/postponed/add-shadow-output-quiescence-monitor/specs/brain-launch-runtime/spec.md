## MODIFIED Requirements

### Requirement: CAO shadow polling supports configurable unknown-to-stalled policy
For CAO sessions in `parsing_mode=shadow_only`, the runtime SHALL support a configurable shadow timing policy with at least:
- `ready_quiet_window_seconds`
- `completion_quiet_window_seconds`
- `unknown_to_stalled_timeout_seconds`
- `stalled_is_terminal`

When unset, `ready_quiet_window_seconds` and `completion_quiet_window_seconds` SHALL use positive built-in defaults selected by runtime and recorded in diagnostics.
When unset, `unknown_to_stalled_timeout_seconds` SHALL default to 30 seconds.

The same `unknown_to_stalled_timeout_seconds` value applies to both:
- readiness wait (before prompt submission), and
- completion wait (during turn execution).

For `shadow_only`, the runtime SHALL treat fresh tmux snapshot change as a restart signal for timing windows derived from `output?mode=full`. A new change observed before a quiet-window or unknown-window threshold is reached SHALL restart the corresponding countdown.

When shadow status remains `unknown` without an intervening tmux snapshot change for at least `unknown_to_stalled_timeout_seconds`, runtime SHALL transition runtime status to `stalled` for the active wait phase.

#### Scenario: Stable unknown status reaches stalled threshold
- **WHEN** shadow polling repeatedly classifies output as `unknown`
- **AND WHEN** no new tmux snapshot change occurs before the configured timeout elapses
- **THEN** runtime marks the shadow lifecycle state as `stalled`

#### Scenario: Unknown with ongoing output churn does not enter stalled early
- **WHEN** runtime is waiting in `parsing_mode=shadow_only`
- **AND WHEN** shadow polling remains `unknown`
- **AND WHEN** tmux snapshot content keeps changing before `unknown_to_stalled_timeout_seconds` elapses
- **THEN** runtime does not mark the lifecycle state as `stalled` yet
- **AND THEN** the unknown-to-stalled countdown restarts from the latest observed change

#### Scenario: Unknown during readiness reaches stalled threshold after quiet period
- **WHEN** runtime is waiting for shadow-ready state before prompt submission
- **AND WHEN** shadow polling remains `unknown`
- **AND WHEN** tmux snapshot content stays unchanged for at least `unknown_to_stalled_timeout_seconds`
- **THEN** runtime marks the shadow lifecycle state as `stalled` for the readiness phase

#### Scenario: Unknown during completion reaches stalled threshold after quiet period
- **WHEN** runtime is waiting for shadow completion during turn execution
- **AND WHEN** shadow polling remains `unknown`
- **AND WHEN** tmux snapshot content stays unchanged for at least `unknown_to_stalled_timeout_seconds`
- **THEN** runtime marks the shadow lifecycle state as `stalled` for the completion phase

### Requirement: CAO backend sends input only when terminal is ready and does not use inbox
When using the CAO backend, the system SHALL only send terminal input when the target terminal is ready for the selected parsing mode, SHALL not use CAO inbox messaging, and SHALL fetch/derive output only after request completion for the same mode.

Mode-specific readiness/completion behavior SHALL be:
- `cao_only`: readiness/completion from CAO terminal status (`idle|completed`) and answer retrieval from CAO `output?mode=last`.
- `shadow_only`: readiness/completion from runtime shadow surface assessment derived from CAO `output?mode=full`, with turn completion determined by runtime turn-monitor logic over post-submit surface transitions, projected-dialog change, and restartable tmux-output quiescence windows.

For `shadow_only`, the runtime SHALL surface projected dialog data derived from `output?mode=full` and SHALL NOT require parser-owned prompt-associated answer extraction to complete the turn.
For `shadow_only`, readiness SHALL require both:
- the current provider surface accepts input, and
- tmux snapshot content has remained unchanged for at least `ready_quiet_window_seconds`.
For `shadow_only`, success terminality SHALL require all of:
- a return to `ready_for_input`,
- either projected-dialog change observed after submit or post-submit observation of `working`, and
- tmux snapshot content has remained unchanged for at least `completion_quiet_window_seconds`.
For `shadow_only`, any newly observed tmux snapshot change before the applicable quiet-window threshold is reached SHALL restart the readiness or completion countdown.
For `shadow_only`, readiness SHALL follow the currently active input surface rather than any historical slash-command line still visible in earlier scrollback. Completed slash-command or model-switch output that remains in the projected dialog SHALL NOT keep a later recovered normal prompt in a non-ready state.
For `shadow_only`, an actually active slash-command or user-selection surface SHALL remain non-ready until the provider returns to a safe normal prompt or the runtime raises the corresponding waiting-user/readiness failure.

The runtime SHALL NOT mix parser families in one turn. If a mode-specific parser/projection step fails, the turn SHALL fail without invoking the other mode in the same turn.
The runtime SHALL NOT perform an automatic retry under the other parser mode after a mode-specific failure.

#### Scenario: `cao_only` waits for CAO status and uses `mode=last`
- **WHEN** a developer sends a prompt via a CAO-backed session with `parsing_mode=cao_only` while the terminal is `processing`
- **THEN** the system polls CAO terminal status until it becomes `idle|completed` (or timeout)
- **AND THEN** the system sends direct terminal input
- **AND THEN** the system waits for completion using CAO status and fetches answer text from `output?mode=last`

#### Scenario: `shadow_only` waits for a quiet ready surface before submitting input
- **WHEN** a developer sends a prompt via a CAO-backed session with `parsing_mode=shadow_only`
- **AND WHEN** the provider surface accepts input
- **AND WHEN** tmux snapshot content is still changing
- **THEN** the system keeps waiting instead of submitting input immediately
- **AND THEN** it sends direct terminal input only after a shadow-ready quiet window is observed

#### Scenario: `shadow_only` completes only after progress evidence and quiet settling
- **WHEN** a developer sends a prompt via a CAO-backed session with `parsing_mode=shadow_only`
- **AND WHEN** the runtime has observed post-submit `working` or projected-dialog change
- **AND WHEN** the provider surface returns to `ready_for_input`
- **AND WHEN** tmux snapshot content remains unchanged for at least `completion_quiet_window_seconds`
- **THEN** the system marks the turn complete
- **AND THEN** it surfaces projected dialog data and state/provenance metadata derived from `mode=full`

#### Scenario: Fresh output change restarts the completion quiet window
- **WHEN** a `shadow_only` turn has already observed post-submit progress evidence
- **AND WHEN** the provider surface has returned to `ready_for_input`
- **AND WHEN** a new tmux snapshot change occurs before `completion_quiet_window_seconds` elapses
- **THEN** the runtime does not mark the turn complete yet
- **AND THEN** the completion quiet-window countdown restarts from that latest change

#### Scenario: Historical slash-command output does not block recovered shadow readiness
- **WHEN** a developer previously used a slash command or manual model switch in a CAO-backed session
- **AND WHEN** that slash-command echo or result is still visible in `output?mode=full`
- **AND WHEN** the current provider surface has already returned to a normal prompt that accepts input
- **AND WHEN** tmux snapshot content has remained unchanged for at least `ready_quiet_window_seconds`
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

## ADDED Requirements

### Requirement: Shadow runtime quiescence timing is observable in diagnostics
For CAO-backed sessions in `parsing_mode=shadow_only`, runtime diagnostics SHALL record the effective quiescence timing configuration used for the turn.

At minimum, diagnostics SHALL include:
- `ready_quiet_window_seconds`,
- `completion_quiet_window_seconds`,
- `unknown_to_stalled_timeout_seconds`,
- `stalled_is_terminal`.

#### Scenario: Diagnostics expose effective quiet-window timing
- **WHEN** a `shadow_only` CAO-backed turn completes or fails after entering shadow monitoring
- **THEN** the surfaced diagnostics include the effective readiness quiet window, completion quiet window, unknown-to-stalled timeout, and stalled terminality mode
