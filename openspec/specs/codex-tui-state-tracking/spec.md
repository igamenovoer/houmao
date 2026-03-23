# codex-tui-state-tracking Specification

## Purpose
Define the interactive Codex TUI tracked-state profile and signal semantics used by the shared tracked-TUI core.

## Requirements

### Requirement: Codex TUI tracking is limited to the interactive Codex screen surface
The repository SHALL model Codex interactive tracked-TUI behavior under a dedicated `codex_tui` app family whose input is raw captured screen text from the interactive Codex TUI surface.

That capability SHALL be limited to the interactive TUI case that requires raw snapshot parsing and keyboard-style interaction. It SHALL NOT treat structured headless Codex control modes such as `codex app-server` or prompt-oriented Codex CLI execution as part of the Codex tracked-TUI surface contract.

#### Scenario: Interactive Codex TUI is tracked from raw screen snapshots
- **WHEN** a host captures raw interactive Codex pane snapshots from tmux or a replay artifact
- **THEN** the standalone tracker resolves Codex through the `codex_tui` tracked-TUI capability
- **AND THEN** state reduction is based on those raw interactive TUI snapshots

#### Scenario: Structured headless Codex modes stay outside tracked-TUI scope
- **WHEN** a repo-owned flow uses a structured Codex control mode with an upstream machine contract rather than raw interactive screen snapshots
- **THEN** that flow does not require the `codex_tui` tracked-TUI capability for its state semantics
- **AND THEN** the tracked-TUI subsystem does not re-model that headless contract through screen-scraping rules

### Requirement: Codex TUI single-snapshot signals come from current visible surface facts
The `codex_tui` profile SHALL derive its single-snapshot facts from the current visible surface only.

At minimum, the profile SHALL be able to recognize:
- agent-turn-backed activity rows,
- in-flight tool or command transcript cells,
- blocking operator-interaction overlays,
- exact interruption surfaces,
- steer-resubmission handoff surfaces,
- generic red error-cell presence as current-error evidence, and
- ready-composer posture, including prompt-area `editing_input` semantics derived through a version-selected prompt behavior variant.

That prompt behavior variant SHALL consume prompt-area snapshot content derived from the raw interactive surface rather than stripped prompt text alone.

The prompt behavior variant MAY use style, layout, text, or other prompt-local evidence to recognize placeholder presentation, and the repository SHALL NOT require one specific prompt-classification mechanism as the stable contract.

If the prompt remains visible but the selected prompt behavior variant cannot confidently distinguish placeholder presentation from real draft input, the `codex_tui` profile SHALL expose `editing_input=unknown` for that current snapshot rather than manufacturing `editing_input=yes` or `editing_input=no`.

The single-snapshot layer SHALL NOT require host parser metadata as input.

#### Scenario: Agent-turn-backed activity row counts as current active evidence
- **WHEN** the current Codex TUI snapshot shows an agent-turn-backed running row or in-flight tool cell for the latest turn
- **THEN** the `codex_tui` profile exposes active-turn evidence from that current surface
- **AND THEN** the shared tracker can classify the current turn as active without requiring a separate host parser contract

#### Scenario: Blocking overlay degrades posture without manufacturing a terminal result
- **WHEN** the current Codex TUI snapshot shows an approval modal, request-user-input modal, MCP elicitation, or app-link suggestion overlay
- **THEN** the `codex_tui` profile exposes a blocking interactive surface for that snapshot
- **AND THEN** the shared tracker does not manufacture success, interruption, or known-failure from that overlay alone

#### Scenario: Generic red error cell blocks success without becoming known-failure
- **WHEN** the current Codex TUI snapshot shows a latest-turn generic red `■ ...` error cell that does not match a narrower terminal rule
- **THEN** the `codex_tui` profile exposes current-error evidence for that current turn
- **AND THEN** the shared tracker blocks success for that turn without emitting `known_failure` from that signal alone

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

### Requirement: Codex TUI temporal inference uses a sliding recent-snapshot window
The `codex_tui` profile SHALL be allowed to derive temporal hints from a sliding time window over recent snapshots rather than relying only on adjacent-snapshot comparison.

That temporal inference SHALL support Codex-specific cases where the visible running row may disappear while streamed answer content continues to grow.

The profile SHALL prefer degrading certainty when the recent snapshot window is too sparse or ambiguous rather than manufacturing active or successful turn outcomes from insufficient evidence.

#### Scenario: Hidden status row does not hide an active answering turn
- **WHEN** recent ordered Codex TUI snapshots within the current sliding window show continued latest-turn transcript growth
- **AND WHEN** the visible running row is absent in the newest snapshot
- **THEN** the `codex_tui` profile may still expose temporal active-turn evidence for the shared tracker
- **AND THEN** the tracker does not require a visible running row on every active Codex turn

#### Scenario: Sparse recent window degrades temporal inference
- **WHEN** the recent Codex TUI snapshot window is too sparse or inconsistent to support confident temporal inference
- **THEN** the `codex_tui` profile degrades that temporal evidence rather than manufacturing a stronger lifecycle conclusion
- **AND THEN** the shared tracker may remain in `unknown` posture until stronger evidence appears

### Requirement: Codex TUI success is a stable ready return after prior turn authority
The `codex_tui` profile SHALL treat successful completion as a stable return to ready posture after prior armed turn authority.

That prior armed turn authority MAY come from either an explicit input event or prior stronger active-turn evidence that armed the shared tracker through surface inference.

A visible `Worked for ...` separator MAY contribute supporting evidence, but it SHALL NOT be required for successful completion.

Current overlays, exact interruption surfaces, or current latest-turn red error cells SHALL block success settlement for the current turn.

#### Scenario: Stable ready return settles success without a Worked-for marker
- **WHEN** the current Codex TUI surface returns to a ready composer posture after prior turn authority
- **AND WHEN** that ready posture remains stable for the configured settle window without current blockers
- **THEN** the shared tracker may settle the turn as `success`
- **AND THEN** the `codex_tui` capability does not require a visible `Worked for ...` separator to do so

#### Scenario: Exact interruption overrides ready-return success
- **WHEN** the current Codex TUI surface matches the exact interruption pattern and shows the ready composer again
- **THEN** the shared tracker records `interrupted` for the completed turn
- **AND THEN** the same ready-return surface is not settled as `success`

#### Scenario: Initial idle ready posture does not settle success
- **WHEN** the Codex TUI shows a ready composer posture without prior armed turn authority for the current turn
- **THEN** the shared tracker does not settle that posture as `success`
- **AND THEN** the tracker waits for explicit input or stronger active-turn evidence before treating a later ready return as a completion signal
