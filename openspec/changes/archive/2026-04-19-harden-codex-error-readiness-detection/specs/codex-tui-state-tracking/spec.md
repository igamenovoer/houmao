## MODIFIED Requirements

### Requirement: Codex TUI single-snapshot signals come from current visible surface facts
The `codex_tui` profile SHALL derive its single-snapshot facts from the current visible surface only.

At minimum, the profile SHALL be able to recognize:
- agent-turn-backed activity rows,
- in-flight tool or command transcript cells,
- blocking operator-interaction overlays,
- exact interruption surfaces,
- steer-resubmission handoff surfaces,
- prompt-adjacent terminal failure surfaces for the current turn, including red error-style blocks and warning-style failure blocks recognized from bounded structure plus essential semantic tokens,
- recoverable degraded chat-context evidence when a prompt-adjacent terminal failure matches the compact/server degraded family through bounded compact/server semantics rather than an exact full-sentence literal,
- live-edge retry or reconnect status surfaces as current active evidence when they match bounded recovery semantics for the current turn, and
- ready-composer posture, including prompt-area `editing_input` semantics derived through a version-selected prompt behavior variant.

Agent-turn-backed activity rows, in-flight tool cells, prompt-adjacent terminal failure evidence, recoverable degraded chat-context evidence, and live-edge retry or reconnect status SHALL be derived from bounded current-turn surface regions near the prompt or live edge rather than from arbitrary historical transcript rows preserved in scrollback above the current turn.

Historical Codex running rows, tool transcript cells, terminal failure blocks, warning rows, or retry text outside those bounded current-turn regions SHALL NOT by themselves produce current single-snapshot active evidence, current-error evidence, `known_failure`, or recoverable degraded chat-context evidence.

Current prompt-adjacent terminal failure evidence SHALL block success settlement for the current turn, but it SHALL NOT by itself force `surface.accepting_input`, `surface.editing_input`, `surface.ready_posture`, or the resulting prompt-ready posture away from the current prompt-area facts.

Recognized warning-style prompt-adjacent terminal failures MAY produce `known_failure` when the selected Codex profile identifies a bounded terminal failure family strong enough to justify that outcome.

Live-edge retry or reconnect status SHALL block success settlement and SHALL count as active-turn evidence while that bounded current-turn recovery surface remains visible.

Recoverable degraded chat-context evidence SHALL remain distinct from prompt readiness, successful completion, and `known_failure`. A snapshot MAY be prompt-ready and also have recoverable degraded chat context.

Prompt-adjacent terminal failures that do not match the compact/server degraded family SHALL NOT produce recoverable degraded chat-context evidence.

Ambient warnings that do not belong to a bounded prompt-adjacent terminal failure block or bounded live-edge retry surface SHALL NOT by themselves produce current-error evidence, `known_failure`, active evidence, or degraded chat-context evidence.

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

#### Scenario: Blocking overlay degrades posture without manufacturing a terminal result
- **WHEN** the current Codex TUI snapshot shows an approval modal, request-user-input modal, MCP elicitation, or app-link suggestion overlay
- **THEN** the `codex_tui` profile exposes a blocking interactive surface for that snapshot
- **AND THEN** the shared tracker does not manufacture success, interruption, or known-failure from that overlay alone

#### Scenario: Warning-style terminal failure near prompt preserves readiness and blocks success
- **WHEN** the current Codex TUI snapshot shows a prompt-adjacent warning-style failure block that matches a recognized bounded terminal-failure family
- **AND WHEN** the current prompt is visible, accepting input, not editing input, and not blocked by an overlay
- **THEN** the `codex_tui` profile preserves prompt-ready surface facts for that snapshot
- **AND THEN** the profile blocks success candidacy for that turn
- **AND THEN** the profile does not require an exact full-sentence warning literal to recognize that failure family

#### Scenario: Live-edge retry status remains active instead of prompt-ready success
- **WHEN** the current Codex TUI snapshot shows a bounded live-edge retry or reconnect status surface for the current turn
- **THEN** the `codex_tui` profile exposes active-turn evidence for that current turn
- **AND THEN** the profile blocks success candidacy while that retry surface remains visible
- **AND THEN** the tracker does not treat that surface as a prompt-ready successful return solely because a prompt line is also visible

#### Scenario: Historical failure or warning outside the bounded current-turn scope does not count
- **WHEN** the tmux-backed Codex snapshot contains an old failure block, warning row, or compact/server-error text in scrollback above the current prompt-ready live region
- **AND WHEN** the bounded prompt-adjacent and live-edge regions do not contain a current failure or retry surface
- **THEN** the `codex_tui` profile does not expose current-error evidence, `known_failure`, active evidence, or recoverable degraded chat-context evidence from that historical text alone
- **AND THEN** the tracker does not block prompt-ready posture solely because a long transcript still shows an old failure above the current turn

#### Scenario: Ambient warning does not mutate current turn state
- **WHEN** the current Codex TUI snapshot contains a visible warning row that does not belong to the bounded prompt-adjacent terminal failure block and does not belong to the bounded live-edge retry surface
- **THEN** the `codex_tui` profile does not expose current-error evidence, `known_failure`, or active evidence from that warning alone
- **AND THEN** the tracker preserves the current turn decision from stronger current-turn evidence instead of treating the warning as terminal by default

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

### Requirement: Prompt-adjacent compact errors are recoverable degraded context
The `codex_tui` profile SHALL classify a current prompt-adjacent compact/server terminal failure surface as recoverable degraded-context evidence rather than mandatory reset evidence.

When the current prompt-adjacent compact/server terminal failure surface is present, the profile SHALL expose current-error evidence for the current turn and SHALL prevent success candidacy for that surface.

When the current prompt-adjacent compact/server terminal failure surface is present and the current composer facts otherwise indicate prompt readiness, the profile SHALL preserve prompt readiness instead of forcing the input surface to unknown or active solely because of that error.

The profile SHALL derive this compact/server degraded classification from the bounded prompt-adjacent prompt region and from the essential compact/server semantics carried by that failure surface. It SHALL NOT require an exact full-sentence literal to classify the compact/server degraded family.

The profile SHALL NOT classify old compact/server failure text from arbitrary historical scrollback as current degraded-context evidence.

The profile SHALL NOT use a public state name that implies mandatory reset for this recoverable condition.

#### Scenario: Compact or server failure near prompt keeps promptable degraded state
- **WHEN** the current Codex TUI snapshot shows a prompt-adjacent terminal failure surface whose bounded text carries the essential compact/server degraded semantics
- **AND WHEN** the prompt is visible, accepting input, not editing input, not blocked by an overlay, and has no current active-turn evidence
- **THEN** the `codex_tui` profile exposes current-error evidence for the current turn
- **AND THEN** the profile blocks success candidacy for that turn
- **AND THEN** the profile preserves prompt-ready input posture for downstream tracked-state reduction
- **AND THEN** the profile exposes recoverable degraded-context evidence without requiring a context reset

#### Scenario: Historical compact or server failure does not degrade current prompt state
- **WHEN** a Codex TUI snapshot contains an older compact/server failure surface in long scrollback above the current prompt area
- **AND WHEN** the bounded prompt-adjacent region near the current prompt does not contain that compact/server degraded family
- **THEN** the `codex_tui` profile does not expose degraded-context evidence from that historical failure
- **AND THEN** the profile does not expose current-error evidence solely because that historical failure remains visible

#### Scenario: Prompt-adjacent terminal failure without compact or server semantics remains a failure blocker only
- **WHEN** the current Codex TUI snapshot shows a prompt-adjacent terminal failure surface that does not match the compact/server degraded family
- **THEN** the `codex_tui` profile exposes terminal failure evidence for the current turn
- **AND THEN** the profile blocks success candidacy for that turn
- **AND THEN** the profile does not expose recoverable compact/server degraded-context evidence
