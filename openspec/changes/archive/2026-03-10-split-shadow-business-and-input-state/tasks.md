## 1. Shared Contract Update

- [x] 1.1 Replace the shared `SurfaceAssessment` fields in `shadow_parser_core.py` from `activity` and `accepts_input` to `business_state` and `input_mode`.
- [x] 1.2 Add module-level helper predicates for `submit_ready`, operator-blocked detection, and unknown-for-stall evaluation without reintroducing the old one-dimensional contract as the primary API.
- [x] 1.3 Rename `waiting_user_answer_excerpt` to `operator_blocked_excerpt` across shared types, payload shaping, and parser or runtime documentation.

## 2. Provider Parser Mapping

- [x] 2.1 Update Claude shadow parsing to map spinner, prompt, trust, selection, slash-command, and setup surfaces onto the new `business_state` and `input_mode` axes using one evidence-to-axis precedence pass.
- [x] 2.2 Update Codex shadow parsing to map processing, approval, selection, slash-command, and prompt surfaces onto the new `business_state` and `input_mode` axes using one evidence-to-axis precedence pass.
- [x] 2.3 Refresh provider parser fixtures or unit tests to cover mixed-state surfaces such as `working + freeform`, `working + modal`, `idle + modal`, and `awaiting_operator + modal`.

## 3. Runtime Lifecycle Update

- [x] 3.1 Refactor shadow readiness logic in `cao_rest.py` to use the derived submit-ready predicate and the explicit readiness evaluation order instead of `accepts_input`.
- [x] 3.2 Refactor shadow completion logic in `cao_rest.py` to preserve stateful progress evidence, require full submit-ready for completion, and follow the explicit completion evaluation order.
- [x] 3.3 Split runtime handling of operator-blocked surfaces from modal-but-not-blocked surfaces so trust or approval prompts fail explicitly while slash-command surfaces remain non-ready without immediate failure.
- [x] 3.4 Update unknown-to-stalled detection so `business_state = unknown` triggers stall timing while `input_mode = unknown` alone stays non-ready without stalled escalation.

## 4. Verification And Docs

- [x] 4.1 Update runtime lifecycle tests to cover operator-blocked precedence, modal non-ready behavior, working-with-modal and working-with-freeform transitions, and one-axis-unknown cases.
- [x] 4.2 Update developer docs and provider contract docs so the public parsing vocabulary matches `business_state` and `input_mode`.
- [x] 4.3 Run focused validation for `shadow_only` parsing and runtime flows, then capture any follow-on quiescence work as a separate change if still needed.
