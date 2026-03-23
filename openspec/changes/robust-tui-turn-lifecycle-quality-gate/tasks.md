## 1. Shared Lifecycle Reset

- [ ] 1.1 Update the shared tracker session reducer so visible newer-turn draft evidence and newer-turn submit or active evidence clear stale `last_turn.result` and `last_turn.source` through one shared invalidation helper reused by the explicit-input path and the snapshot-processing path.
- [ ] 1.2 Add reducer or session tests that cover explicit-input stale-clear behavior, draft-after-success, draft-after-interrupt, and second-active-turn reset semantics without regressing existing success timing behavior.

## 2. Claude Detector Robustness

- [ ] 2.1 Add Claude profile-owned latest-turn region scoping so interrupted and known-failure status matching ignores stale transcript status lines outside the current turn region by using the last visible prompt anchor as a stateless boundary and degrading conservatively when no current prompt anchor is visible.
- [ ] 2.2 Tighten Claude prompt-behavior classification so foreground/background color-setting SGR families and their resets do not downgrade real active draft text to `surface.editing_input=unknown`, while dim, inverse, and unexpected non-color styles remain meaningful.
- [ ] 2.3 Add raw-surface and session tests for Claude placeholder prompts, overlapping active drafting, and stale interrupted-status scrollback cases.

## 3. Complex Recorded Quality Gate

- [ ] 3.1 Add maintained Claude and Codex complex scenario definitions plus ordered sweep contracts for the success-interrupt-success lifecycle.
- [ ] 3.2 Capture or refresh the canonical complex recorded fixtures and labels so both tools preserve settled success, ready-draft, active-draft, interrupted-ready, and final success spans, and revalidate or update any previously committed recorded labels affected by the lifecycle-reset change.
- [ ] 3.3 Update maintained demo-pack validation tests so replay comparison and ordered sweep checks run automatically against the complex fixtures while keeping draft-specific judgments in the strict ground-truth path.

## 4. Documentation And Verification

- [ ] 4.1 Update the demo-pack README and fixture-authoring guidance to document the complex operator plan, required hold durations, prompt-region visibility during active-draft capture, and the expected lifecycle labels.
- [ ] 4.2 Run targeted verification covering shared tracker unit tests, Claude detector tests, recorded fixture validation for new and previously affected fixtures, and cadence sweeps for the new complex fixtures.
