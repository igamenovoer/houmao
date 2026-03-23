## Context

The shared tracked-TUI stack currently has one cross-tool lifecycle bug and two Claude-specific detector bugs that only become obvious in longer real interactions.

- The shared session reducer keeps the previous terminal `last_turn` result alive too long, so a new draft or second active turn can still report `last_turn.result=interrupted` or `success` until some later state transition overwrites it.
- Claude terminal-status detection is scoped too broadly, so an old interrupted or failure status line that remains visible in scrollback can still dominate the current turn posture.
- Claude prompt-style handling is still too brittle during overlapping activity, so real typed draft text can degrade to `surface.editing_input=unknown` when prompt-marker color and reset codes bleed into the payload classifier.

The recorded-validation workflow already has real fixtures, span-based labels, cadence sweeps, and a maintained corpus. The missing piece is a stronger canonical interaction that keeps these specific regressions under automated pressure. Existing explicit-success and close-oriented interrupt fixtures are useful, but they do not keep a long success-interrupt-success lifecycle in the maintained regression suite.

Within the current codebase, the mutable tracker lifecycle logic lives in `src/houmao/shared_tui_tracking/session.py` under `TuiTrackerSession`, while `src/houmao/shared_tui_tracking/reducer.py` is the replay-facing wrapper that drives the same tracker core over recorded observations. This change therefore needs to describe the chosen mutation points in `TuiTrackerSession` clearly, while keeping replay and recorded-validation artifacts aligned with the same public-state semantics.

## Goals / Non-Goals

**Goals:**

- Clear stale terminal `last_turn` outcomes as soon as a newer turn becomes visible.
- Keep Claude interruption and failure evidence scoped to the latest turn region instead of any stale visible transcript block.
- Make Claude active-draft detection robust when prompt-marker styling and SGR reset sequences appear alongside real typed text.
- Maintain a real recorded complex interaction fixture for both Claude and Codex that exercises success, repeated interruption, overlapping active drafting, and final recovery to success.
- Turn those complex fixtures into a standing quality gate through replay validation, ordered sweep expectations, and maintained tests.

**Non-Goals:**

- Redesign the public tracked-state vocabulary or add a new public lifecycle kind.
- Replace the smaller existing fixtures that remain useful for narrower debugging.
- Make authoring or validation depend on `houmao-server` state or on the tracker under test to drive capture decisions.
- Introduce a shared cross-app prompt/status behavior registry outside the existing profile-owned detector boundary.

## Decisions

### Decision: Clear terminal `last_turn` state on first newer-turn authority

The shared session reducer should treat the first authoritative sign of a newer turn as the point where the previous terminal result is no longer current. That invalidation should happen on newer-turn draft visibility and on newer-turn submission or active evidence, not only after the later turn reaches success.

The implementation direction is one shared stale-terminal invalidation helper that is reused by both explicit-input authority and snapshot-driven newer-turn authority. In practice that means the explicit-input path in `TuiTrackerSession._handle_input_event()` and the early snapshot-processing path should both clear stale terminal `last_turn` state through the same rule instead of burying interrupted or known-failure clearing inside the existing success-settle logic.

Why:

- The bug affects both Claude and Codex, so the reset rule belongs in the shared reducer rather than in one profile.
- The public meaning of `last_turn` is “most recent completed turn,” which stops being current once a newer turn is visibly underway.

Alternative considered:

- Clear terminal state only when the next turn reaches a stable ready posture.
  - Rejected because it preserves exactly the stale `last=interrupted` bug the change is meant to remove.

### Decision: Scope Claude terminal-status evidence to the latest turn region

Claude should stop interpreting the last visible status line anywhere on screen as the current terminal status. Instead, the selected Claude profile should derive the latest-turn region and restrict interruption or known-failure detection to status evidence that belongs to that region.

For v1, the region boundary stays stateless and prompt-anchored: the last visible Claude prompt marker is the current-turn anchor, and terminal status evidence is only considered from that anchor downward. When no current prompt anchor is visible, the detector should degrade conservatively rather than falling back to full-pane transcript scanning that can resurrect stale interrupted or failure text from older turns.

Why:

- Claude keeps older transcript blocks visible for a long time, and those blocks can still contain `Interrupted` or other terminal-looking text after later turns have already started or finished.
- The scoping rule is tool-specific UI behavior, so it belongs in the Claude profile layer.

Alternative considered:

- Keep using one global “last status line on screen” helper.
  - Rejected because it is not robust once transcript history and current prompt share the same viewport.

### Decision: Treat prompt-marker color and reset codes as neutral for Claude draft detection

Claude prompt classification should continue to use style-aware behavior, but only the payload styling that meaningfully distinguishes placeholder from real draft should affect the result. Prompt-marker color, cursor styling, and `39`/`49` style resets should not cause real draft text to fall back to `unknown`.

For v1, this means foreground/background color-setting families and their resets are treated as neutral prompt-rendering noise for Claude prompt payload classification. Dimness, inverse styling, and still-unrecognized non-color style families remain meaningful so the classifier preserves the current placeholder-vs-draft boundary while removing the observed prompt-marker color leak.

Why:

- The active-draft regression is caused by style leakage rather than by a lack of prompt classification.
- This keeps the existing style-aware approach while tightening the classification boundary to the evidence that actually matters.

Alternative considered:

- Fall back to stripped prompt text for active drafts.
  - Rejected because it would reintroduce the placeholder false-positive problem that was already found on Claude startup.

### Decision: Keep a complex recorded fixture family as a maintained regression gate

The demo pack should keep one longer canonical recorded fixture per tool that exercises:

1. short prompt -> settled success,
2. long prompt with a ready-draft hold,
3. active turn with an overlapping active-draft hold,
4. first intentional interrupt,
5. second prompt with another ready-draft hold,
6. second active turn with another active-draft hold,
7. second intentional interrupt, and
8. final short prompt -> settled success.

These fixtures should live in the maintained committed corpus and be replayed by automated validation rather than being treated as one-off authoring artifacts.

The corresponding authoring workflow should also keep the prompt region visible while the overlapping active-draft spans are sampled. Hold durations alone are not sufficient if the prompt anchor scrolls off-screen, because the classifier and later label review depend on the current prompt region remaining visible in captured snapshots.

Why:

- The bugs here only appear when terminal outcomes, newer drafts, and repeated interrupted turns overlap in one session.
- Real captured fixtures are the most honest regression surface for these UI-state problems.

Alternative considered:

- Keep only small single-purpose fixtures and rely on manual live-watch checks for the long lifecycle.
  - Rejected because the regressions were already able to pass the smaller automated suite.

### Decision: Use both strict ground-truth replay and ordered sweep sequences for the complex fixture

The primary oracle for the complex fixture should remain the sample-aligned `labels.json` replay comparison. In addition, the maintained sweep configuration should require an ordered repeated transition sequence equivalent to `ready_success -> active -> ready_interrupted -> active -> ready_interrupted -> ready_success`.

That sweep contract remains intentionally coarse. The fine-grained `ready_draft` and `active_draft` semantics are still judged by sample-aligned ground-truth labels rather than by widening the sweep state vocabulary with additional draft-only labels.

Why:

- Ground truth is needed to judge `editing_input=yes` and `last_turn=none` during ready-draft and active-draft spans.
- The ordered sweep sequence provides a cheaper cadence-robustness signal and catches collapse of the second active or second interrupted phase.

Alternative considered:

- Use only the strict replay labels and skip sweep expectations for the long fixture.
  - Rejected because cadence robustness is part of the demo pack’s value, and the second-active collapse bug is easy to express in the ordered sweep contract.

## Risks / Trade-offs

- [Tool UI drift changes the shape of the latest-turn region again] -> Keep the scoping and style logic profile-owned, version-selectable, and covered by raw-surface unit tests plus real recorded fixtures.
- [The complex regression fixtures take longer to capture and review] -> Keep the smaller fixtures for narrow debugging and reserve the complex cases for the standing quality gate.
- [Cadence sweeps become noisy if draft or interrupt spans are too short] -> Document minimum settle and hold durations in the authoring guidance and encode them into the maintained scenario definitions.
- [Resetting `last_turn` too aggressively could erase a still-current terminal result] -> Reset only on authoritative newer-turn evidence such as visible non-placeholder draft, explicit submission, or newer active-turn evidence.

## Migration Plan

1. Update the shared reducer so newer-turn evidence clears stale terminal `last_turn` state.
2. Tighten Claude profile behavior for latest-turn status scoping and active-draft style handling.
3. Add unit coverage for the new reducer and Claude classifier semantics.
4. Revalidate any previously committed recorded fixtures whose labels can shift under the new lifecycle semantics, and update those labels when needed before treating the maintained corpus as green.
5. Add maintained complex recorded scenarios and canonical fixtures for Claude and Codex.
6. Update recorded-validation and sweep expectations so those fixtures are exercised automatically while keeping draft-specific judgments in the strict ground-truth path.
7. Promote the new or refreshed fixtures only after replay mismatch count reaches zero and the ordered sweep contract passes.

Rollback is straightforward: revert the reducer/profile changes and temporarily remove the complex-fixture quality gate while preserving the existing smaller fixtures.

## Open Questions

- None for proposal purposes. The remaining implementation choices are local details such as exact helper names and the final fixture case identifiers.
