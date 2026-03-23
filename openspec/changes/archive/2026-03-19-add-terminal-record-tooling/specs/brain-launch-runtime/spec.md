## MODIFIED Requirements

### Requirement: Runtime CLI exposes a `send-keys` raw control-input path distinct from prompt submission
The runtime SHALL provide a caller-facing `send-keys` control-input command for resumed CAO-backed tmux sessions that is distinct from `send-prompt`.

The runtime session-control surface SHALL expose the corresponding advanced mixed-input operation as `send_input_ex()`.

The existing `send-prompt` command SHALL retain its current high-level prompt-turn semantics.

The control-input command SHALL:
- require `--agent-identity` and `--sequence`,
- support the global `--escape-special-keys` flag and the existing optional `--agent-def-dir` override pattern,
- accept the mixed sequence grammar defined by `runtime-tmux-control-input`,
- deliver the requested input without automatically pressing `Enter`,
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
