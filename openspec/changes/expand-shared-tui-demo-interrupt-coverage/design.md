## Context

The shared tracked-TUI demo pack already has a recorded-validation workflow, a maintained real fixture corpus, and a sample-aligned ground-truth comparison contract. That existing contract is strong enough to judge a repeated interruption lifecycle once a fixture is captured and labeled, because the replay comparison already works per sample over the public tracked-state fields.

The current gap is not in the core comparison model. The gap is in coverage and control:

- the maintained fixture matrix only guarantees single-interrupt coverage,
- the committed Codex interrupted fixture does not currently reach a true interrupted-ready public state,
- scenario steps express raw keystrokes and kill-style session loss rather than semantic operator intents, and
- sweep verdicts collapse label checking to first occurrence, which cannot prove repeated interruption.

The design therefore needs to expand fixture coverage without making the capture workflow circular or coupling authoring to reducer output.

## Goals / Non-Goals

**Goals:**

- Add a maintained repeated intentional-interruption lifecycle for both Claude and Codex.
- Keep the current single-interrupt fixtures as smaller debug targets while adding a stronger lifecycle fixture.
- Represent intentional interrupt and intentional close as semantic scenario actions with tool-specific implementations.
- Keep sample-aligned ground-truth replay comparison as the primary correctness gate for repeated interruption.
- Allow cadence sweeps for the new lifecycle to express repeated transition requirements rather than only first-occurrence presence.

**Non-Goals:**

- Redesign the shared tracked-state model or add a new public “closed” state.
- Make scenario execution depend on reducer output from the tracker under test.
- Remove the existing single-interrupt fixtures.
- Guarantee that the same literal key sequence implements interruption across all tools and versions.

## Decisions

### Decision: Add new repeated-lifecycle fixtures instead of replacing the single-interrupt cases

The demo should keep `*_interrupted_after_active` as a minimal smoke case and add a new repeated lifecycle case such as `*_double_interrupt_then_close`.

This keeps one fixture optimized for quick debugging of the basic interrupted-ready transition and one fixture optimized for the full operator lifecycle:

```text
ready
  -> active turn 1
  -> ready interrupted 1
  -> active turn 2
  -> ready interrupted 2
  -> diagnostics lost after close
```

Replacing the existing single-interrupt cases would make debugging slower and would blur whether a failure is about the basic interrupt signal or about repeated-turn state reset.

### Decision: Introduce semantic scenario intents for interruption and close

The scenario layer should add intent-level actions for `interrupt_turn` and `close_tool` instead of relying only on raw `send_key` or crash-style `kill_session`.

Rationale:

- The requirement is about intentional operator behavior, not about one hardcoded key.
- Claude and Codex may require different recipes to surface a true interrupted-ready posture.
- “Close the session intentionally” is not the same contract as “crash the process” or “kill tmux”.

Alternatives considered:

- Keep using raw `send_key` and `kill_session` only.
  - Rejected because it encodes tool behavior accidentally and already failed to give honest interrupted coverage for Codex.
- Drive capture from the tracker’s own live public state.
  - Rejected because it creates circularity between the system being judged and the workflow that produces the judging fixture.

### Decision: Keep repeated-interruption correctness in the strict GT path

The primary correctness gate for the new lifecycle should remain recorded validation against human-authored sample-aligned labels.

For the repeated lifecycle, authoring guidance should require labels that distinguish:

- first active turn,
- first interrupted-ready span,
- second active turn,
- second interrupted-ready span, and
- post-close diagnostics-down or unavailable span.

The important semantic check is not only that interruption appears twice. It is also that the second prompt resets `last_turn_result` back to `none` while the turn is active, and that closing does not invent `success` or `known_failure`.

Alternative considered:

- Add special-purpose repeated-turn logic to the GT comparison engine.
  - Rejected because the current sample-aligned comparison already expresses the requirement directly.

### Decision: Extend sweep contracts to express repeated transition sequences

If the demo continues to make cadence-robustness claims for interrupted scenarios, the sweep contract needs stronger sequence semantics than the current first-occurrence-only model.

The recommended direction is to extend sweep contracts with one of these shapes:

- ordered required sequence with duplicates, such as `["active", "ready_interrupted", "active", "ready_interrupted", "tui_down"]`, or
- occurrence-aware assertions, such as `ready_interrupted >= 2` combined with ordering rules.

Either approach is acceptable as long as the sweep can distinguish one interrupted cycle from two. The sequence form is preferable because it matches the operator lifecycle more directly and produces clearer failure reports.

Alternative considered:

- Leave sweep contracts unchanged and rely only on strict GT comparison for repeated interruption.
  - Accepted as a minimum fallback, but not preferred if the demo wants an explicit robustness claim for this lifecycle.

### Decision: Use distinct prompts for turn 1 and turn 2 during authoring

The repeated-lifecycle authoring workflow should use two concrete long-running prompts rather than replaying the exact same prompt text twice.

Rationale:

- pane snapshots become easier to inspect and label,
- the second turn is easier to distinguish from the first when reviewing captures and videos, and
- operator mistakes during recapture are easier to detect.

This is an authoring and scenario-guidance decision, not a public tracker requirement.

## Risks / Trade-offs

- [Codex still fails to surface a true interrupted-ready state] -> Keep the requirement honest, implement interrupt as a tool-specific intent, and do not relabel active continuation as interrupted.
- [Intent-level scenario actions add workflow complexity] -> Limit the new actions to interruption and close, and keep raw low-level actions available for debugging.
- [Close posture may vary by tool version] -> Assert the existing public diagnostics contract (`tui_down` or `unavailable`) rather than inventing a new “closed” state.
- [Stronger sweep contracts increase config and reporting complexity] -> Keep the extension narrow and sequence-oriented instead of introducing a general temporal rule engine.

## Migration Plan

1. Extend the scenario model and capture driver with semantic interrupt/close actions.
2. Add new repeated-lifecycle scenarios for Claude and Codex.
3. Document the new fixture matrix and authoring guidance.
4. Capture and label temporary repeated-lifecycle fixtures for both tools.
5. Promote only fixtures that pass strict recorded validation.
6. Update sweep definitions and tests if repeated-lifecycle robustness remains part of the demo claim.

Rollback is straightforward: keep the single-interrupt fixtures and disable the new repeated-lifecycle scenarios or contracts if a tool-specific interrupt recipe proves unstable.

## Open Questions

- What exact tool-specific action should Codex use for `interrupt_turn` so the public state honestly becomes interrupted-ready?
- Should intentional close prefer a graceful tool exit path before falling back to session termination?
- Should the sweep extension use explicit ordered sequences, occurrence counts, or both?
