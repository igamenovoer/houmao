## 1. Public Contract

- [x] 1.1 Replace the public tracked-state models and route payloads with the simplified `diagnostics` / `surface` / `turn` / `last_turn` structure.
- [x] 1.2 Update tracked-state serialization, inspect surfaces, and transition history so they reference the new public fields instead of readiness/completion/authority-heavy fields.
- [x] 1.3 Revise server route and model tests to lock the new JSON contract and remove assertions on old public lifecycle fields and command-vs-chat distinctions.

## 2. Tracker Mapping

- [x] 2.1 Map the current parsed-surface and tracker evidence into foundational observables for `accepting_input`, `editing_input`, and `ready_posture`.
- [x] 2.2 Map the current anchored/background tracking machinery into the simplified `turn.phase` and `last_turn` contract, including explicit-input versus inferred-input source, a conservative non-causal path for unexplained TUI churn, `turn.phase=unknown` handling for ambiguous menus, selections, permission prompts, and similar unstable interactive UI, and narrow `known_failure` emission only for supported recognized failure signatures.
- [x] 2.3 Treat progress bars, spinners, and similar activity signs as supporting evidence only, and ensure active-turn inference can still succeed from other evidence such as scrolling dialog growth or turn-related transcript changes.
- [x] 2.4 Keep all timed state-tracking behavior on ReactiveX observation streams and remove any new manual timer bookkeeping from the simplified contract mapping.
- [x] 2.5 Demote old public readiness/completion/authority states to internal-only or debug-only use while preserving generic stability as diagnostic evidence.

## 3. Consumers And Docs

- [x] 3.1 Update the dual shadow-watch demo monitor, inspect output, and operator-facing copy to present the simplified server-owned turn model.
- [x] 3.2 Rewrite the `houmao-server` state-tracking docs and any reference pages that currently teach `candidate_complete`, `completed`, `stalled`, turn-authority, or command-vs-chat differentiation as the primary consumer model.
- [x] 3.3 Add or update verification for ready, active with and without visible progress signals, unknown-turn handling for ambiguous interactive UI and unmatched failure-like surfaces, success including short-answer success without `Worked for <duration>`, premature-success invalidation when later observations show continued surface growth, known failure, interruption, direct-tmux inference, and unexplained UI churn that must not manufacture turn transitions.
- [x] 3.4 Keep maintainer-facing verification replay-grade: compare content-first groundtruth against ReactiveX replay over the same recorded observations, and formalize any newly stabilized tool/version matcher changes as `tui-signals/` notes instead of leaving them implicit in detector code.
