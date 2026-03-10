## ADDED Requirements

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
