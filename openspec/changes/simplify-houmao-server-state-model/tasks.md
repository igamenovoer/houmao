## 1. Public Contract

- [ ] 1.1 Replace the public tracked-state models and route payloads with the simplified `diagnostics` / `surface` / `work` / `last_outcome` structure.
- [ ] 1.2 Update tracked-state serialization, inspect surfaces, and transition history so they reference the new public fields instead of readiness/completion/authority-heavy fields.
- [ ] 1.3 Revise server route and model tests to lock the new JSON contract and remove assertions on old public lifecycle fields.

## 2. Tracker Mapping

- [ ] 2.1 Map the current parsed-surface and tracker evidence into foundational observables for `processing`, `accepting_input`, `editing_input`, and input kind, including exact slash-command detection for prompts that match only `/<command-name>` with optional trailing spaces.
- [ ] 2.2 Map the current anchored/background tracking machinery into the simplified `work.kind`, `work.phase`, and `last_outcome` contract, including explicit-input versus inferred-input source and a conservative non-causal path for unexplained TUI churn.
- [ ] 2.3 Keep all timed state-tracking behavior on ReactiveX observation streams and remove any new manual timer bookkeeping from the simplified contract mapping.
- [ ] 2.4 Demote old public readiness/completion/authority states to internal-only or debug-only use while preserving generic stability as diagnostic evidence.

## 3. Consumers And Docs

- [ ] 3.1 Update the dual shadow-watch demo monitor, inspect output, and operator-facing copy to present the simplified server-owned state model.
- [ ] 3.2 Rewrite the `houmao-server` state-tracking docs and any reference pages that currently teach `candidate_complete`, `completed`, `stalled`, or turn-authority as the primary consumer model.
- [ ] 3.3 Add or update verification for ready, active, awaiting-user, success, failure, interruption, exact slash-command classification, direct-tmux inference, and unexplained UI churn that must not manufacture work-cycle transitions.
