# KQ-5: Merge Semantics Against Real Streams

Status: open. Owner: iteration 2 (after capture). Campaign: [debug-intent.md](../debug-intent.md).

## Question

Do the state-transition rules in `openspec/changes/add-cli-hook-observation-channel/design/state-transitions.md` reproduce correct merged state when driven by real captured hook streams paired with TUI recordings, and which implementation variant (E2/E3 arms) expresses them best?

## Propositions

### P5.1 Turn lifecycle rules

Terminal latch with interrupt-only override, immediate `phase=ready` on hook terminal, and gateway/direct-input source attribution replay correctly on S1, S2, and S6 streams. Test: replay harness asserts the expected state timeline per scenario.

### P5.2 Blocked entry and exit

`blocked` enters only from `PermissionRequest`, exits via resolution events or TUI modal dismissal, and never appears in TUI-only replay. Test: S3 replay plus a TUI-only control replay.

### P5.3 Supersede and orphan handling

Overlapping or orphaned events follow the supersede rule with orphan diagnostics and no manufactured turns. Test: S7 replay plus synthetic reordering of captured streams.

### P5.4 Correction after staleness

Agreement no-ops and disagreement-corrects-with-audit-trail behave as specified. Test: fault-injected replay (drop a stream window, settle via TUI, then redeliver the buffered terminal).

### P5.5 Work axis transitions

`work` transitions follow the terminal-payload rule and, if KQ-4 found clearing events, the live-clearing rule. Test: S5 replay.

### P5.6 TUI-only equivalence

With the channel absent or degraded, replayed state is byte-equivalent to the TUI-only baseline for every existing field. Test: replay all captured sessions with the channel disabled and compare against the same streams replayed without hook inputs.

## Answer

Unresolved.

## Scope

Merge and transition correctness against evidence. The production rewrite is out of scope; this question selects and validates the variant the OpenSpec apply phase will implement. Evidence: `evidences/` links added as produced.
