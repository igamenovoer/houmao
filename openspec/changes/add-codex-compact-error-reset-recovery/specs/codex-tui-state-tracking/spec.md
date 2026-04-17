## MODIFIED Requirements

### Requirement: Codex TUI single-snapshot signals come from current visible surface facts
The `codex_tui` profile SHALL derive its single-snapshot facts from the current visible surface only.

At minimum, the profile SHALL be able to recognize:
- agent-turn-backed activity rows,
- in-flight tool or command transcript cells,
- blocking operator-interaction overlays,
- exact interruption surfaces,
- steer-resubmission handoff surfaces,
- generic red error-cell presence as current-error evidence,
- chat-context state `reset_required` when a current prompt-adjacent error surface matches a narrow compact/server reset-required signature, and
- ready-composer posture, including prompt-area `editing_input` semantics derived through a version-selected prompt behavior variant.

Agent-turn-backed activity rows, in-flight tool cells, generic current-error evidence, and `reset_required` chat-context evidence SHALL be derived from the live edge of the current latest-turn surface near the prompt/composer rather than from arbitrary historical transcript rows preserved in scrollback above the current turn.

Historical Codex running rows, tool transcript cells, or error cells outside that live-edge region SHALL NOT by themselves produce current single-snapshot active evidence, current-error evidence, or `reset_required` chat-context state.

Current-error evidence SHALL block success settlement for the current turn, but it SHALL NOT by itself force `surface.accepting_input`, `surface.editing_input`, `surface.ready_posture`, or the resulting prompt-ready posture away from the current prompt-area facts.

Chat-context state `reset_required` SHALL remain distinct from prompt readiness, successful completion, and `known_failure`. A snapshot MAY be prompt-ready and also have chat-context state `reset_required`.

Generic red error cells that do not match the reset-required signature SHALL NOT produce chat-context state `reset_required`.

That prompt behavior variant SHALL consume prompt-area snapshot content derived from the raw interactive surface rather than stripped prompt text alone.

The prompt behavior variant MAY use style, layout, text, or other prompt-local evidence to recognize placeholder presentation, and the repository SHALL NOT require one specific prompt-classification mechanism as the stable contract.

If the prompt remains visible but the selected prompt behavior variant cannot confidently distinguish placeholder presentation from real draft input, the `codex_tui` profile SHALL expose `editing_input=unknown` for that current snapshot rather than manufacturing `editing_input=yes` or `editing_input=no`.

The single-snapshot layer SHALL NOT require host parser metadata as input.

#### Scenario: Agent-turn-backed activity row counts as current active evidence
- **WHEN** the current Codex TUI snapshot shows an agent-turn-backed running row or in-flight tool cell for the live latest-turn region
- **THEN** the `codex_tui` profile exposes active-turn evidence from that current surface
- **AND THEN** the shared tracker can classify the current turn as active without requiring a separate host parser contract

#### Scenario: Historical running row outside the live edge does not count as current active evidence
- **WHEN** the tmux-backed Codex snapshot still contains a historical `• Working (... esc to interrupt)` row above the current prompt-ready live region
- **AND WHEN** that historical row is outside the current live latest-turn surface
- **THEN** the `codex_tui` profile does not expose current single-snapshot active evidence from that historical row alone
- **AND THEN** the tracker does not keep the current turn active solely because that stale transcript row remains in scrollback

#### Scenario: Historical error outside the live edge does not count as current error evidence
- **WHEN** the tmux-backed Codex snapshot contains an old red error cell or compact/server-error text in scrollback above the current prompt-ready live region
- **AND WHEN** the prompt-adjacent live-edge region does not contain a current error surface
- **THEN** the `codex_tui` profile does not expose current-error evidence or chat-context state `reset_required` from that historical text alone
- **AND THEN** the tracker does not block prompt-ready posture solely because a long transcript still shows an old error above the current turn

#### Scenario: Blocking overlay degrades posture without manufacturing a terminal result
- **WHEN** the current Codex TUI snapshot shows an approval modal, request-user-input modal, MCP elicitation, or app-link suggestion overlay
- **THEN** the `codex_tui` profile exposes a blocking interactive surface for that snapshot
- **AND THEN** the shared tracker does not manufacture success, interruption, or known-failure from that overlay alone

#### Scenario: Generic red error cell blocks success without becoming known-failure
- **WHEN** the current Codex TUI snapshot shows a prompt-adjacent latest-turn generic red `■ ...` error cell that does not match a narrower terminal rule
- **THEN** the `codex_tui` profile exposes current-error evidence for that current turn
- **AND THEN** the shared tracker blocks success for that turn without emitting `known_failure` from that signal alone

#### Scenario: Generic red error does not require context reset
- **WHEN** the current Codex TUI snapshot shows a prompt-adjacent latest-turn generic red error cell that does not match the reset-required signature
- **THEN** the `codex_tui` profile does not expose chat-context state `reset_required`
- **AND THEN** gateway policy cannot require a context reset solely from that generic error

#### Scenario: Ready composer after generic error remains prompt-ready
- **WHEN** the current Codex TUI snapshot shows a prompt-adjacent latest-turn generic red error cell and a stable ready composer that accepts input with no draft editing
- **AND WHEN** the current surface has no active-turn evidence or blocking overlay
- **THEN** the `codex_tui` profile preserves prompt-ready surface facts for that snapshot
- **AND THEN** the shared tracker does not report the surface as non-ready solely because the previous visible turn contains an error

#### Scenario: Reset-required compact server error coexists with prompt-ready input
- **WHEN** the current Codex TUI snapshot shows a prompt-adjacent compact/server-error surface matching the reset-required signature and a stable ready composer that accepts input with no draft editing
- **AND WHEN** the current surface has no active-turn evidence or blocking overlay
- **THEN** the `codex_tui` profile exposes current-error evidence and chat-context state `reset_required`
- **AND THEN** it still preserves prompt-ready surface facts so gateway policy can send a context reset command

#### Scenario: Placeholder presentation does not count as editing
- **WHEN** the selected Codex prompt behavior variant classifies the visible prompt area as placeholder presentation
- **THEN** the `codex_tui` profile reports `editing_input=no`
- **AND THEN** visible placeholder text is not treated as a user draft only because it appears in the prompt area

#### Scenario: Real draft input remains editing even when text matches a known placeholder phrase
- **WHEN** the selected Codex prompt behavior variant classifies the visible prompt area as real user draft input
- **THEN** the `codex_tui` profile reports `editing_input=yes`
- **AND THEN** that result does not depend on whether the stripped draft text happens to equal one previously known placeholder string

#### Scenario: Dynamic placeholder text does not require a stable literal list
- **WHEN** Codex uses different placeholder wording within a supported prompt behavior family
- **THEN** the selected prompt behavior variant can still classify that prompt area as placeholder presentation
- **AND THEN** the `codex_tui` capability does not require the stable tracker contract to enumerate every placeholder literal

#### Scenario: Unrecognized prompt presentation yields unknown editing state
- **WHEN** the selected Codex prompt behavior variant cannot confidently distinguish placeholder presentation from real draft input for the current visible prompt area
- **THEN** the `codex_tui` profile reports `editing_input=unknown`
- **AND THEN** the tracker preserves that ambiguity for drift investigation instead of manufacturing a placeholder or draft conclusion
