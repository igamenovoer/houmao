## ADDED Requirements

### Requirement: Prompt-ready terminal failures preserve readiness while blocking success
When a supported tracked TUI profile recognizes a bounded current-turn terminal failure surface and the visible composer is otherwise submit-ready, the authoritative tracked state SHALL preserve prompt-derived readiness instead of degrading the surface solely because that failure is visible.

In that case, the tracker SHALL continue to derive `surface.accepting_input`, `surface.editing_input`, and `surface.ready_posture` from the current prompt and overlay facts.

The tracker SHALL NOT settle `last_turn.result=success` while that bounded terminal failure surface remains the current turn outcome.

When the selected profile identifies a recognized terminal failure family strong enough to justify a terminal failure result, the tracker MAY publish `last_turn.result=known_failure` while preserving the current prompt-derived readiness.

Recoverable degraded compact/server failures remain distinct from stronger recognized terminal failures. They SHALL preserve prompt-derived readiness and block success, but they SHALL NOT become `known_failure` solely because degraded context is present.

#### Scenario: Warning-style terminal failure keeps ready input but does not settle success
- **WHEN** a supported tracked TUI profile recognizes a bounded prompt-ready terminal failure surface for the current turn
- **AND WHEN** the current surface accepts input, is not editing input, is not blocked by an overlay, and has no current active evidence
- **THEN** the authoritative tracked state reports the prompt-derived ready surface posture for that current snapshot
- **AND THEN** the tracker does not settle `last_turn.result=success` while that terminal failure surface remains current

#### Scenario: Recognized prompt-ready terminal failure may publish known failure without degrading readiness
- **WHEN** a supported tracked TUI profile recognizes a bounded current-turn terminal failure family strong enough to justify `known_failure`
- **AND WHEN** the visible prompt is genuinely submit-ready
- **THEN** the authoritative tracked state may publish `last_turn.result=known_failure`
- **AND THEN** the tracker still preserves the prompt-derived ready surface posture for the current snapshot

#### Scenario: Recoverable degraded compact failure remains non-success and non-known-failure
- **WHEN** a supported tracked TUI profile recognizes a bounded prompt-ready compact/server degraded failure surface for the current turn
- **THEN** the authoritative tracked state preserves prompt-derived readiness for that current snapshot
- **AND THEN** the tracker does not settle `last_turn.result=success`
- **AND THEN** the tracker does not publish `last_turn.result=known_failure` solely because degraded context is present

### Requirement: Live retry or reconnect recovery surfaces remain active
When a supported tracked TUI profile recognizes a bounded live-edge retry, reconnect, or stream-recovery surface for the current turn, the authoritative tracked state SHALL treat that surface as active-turn evidence rather than as a ready-return completion.

While that bounded retry or reconnect surface remains current, the tracker SHALL keep `turn.phase=active` and SHALL block success settlement for that turn.

Historical retry or reconnect text outside the bounded current-turn scope SHALL NOT by itself keep the turn active after the surface has genuinely returned to a ready non-active state.

#### Scenario: Current retry status keeps the turn active
- **WHEN** a supported tracked TUI profile recognizes a bounded live-edge retry or reconnect recovery surface for the current turn
- **THEN** the authoritative tracked state reports `turn.phase=active`
- **AND THEN** the tracker does not treat that surface as a ready-return success candidate

#### Scenario: Historical retry text does not keep a later ready prompt active
- **WHEN** older retry or reconnect text remains visible outside the bounded current-turn scope
- **AND WHEN** the current supported surface is submit-ready and lacks current active evidence
- **THEN** the authoritative tracked state does not keep `turn.phase=active` solely because that historical retry text remains visible
- **AND THEN** the tracker can return to the ordinary ready posture for the current turn
