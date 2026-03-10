## 1. Shared Contract Update

- [ ] 1.1 Replace the shared `SurfaceAssessment` fields in `shadow_parser_core.py` from `activity` and `accepts_input` to `business_state` and `input_mode`.
- [ ] 1.2 Add shared helper predicates or helpers for derived submit readiness without reintroducing the old one-dimensional contract as the primary API.
- [ ] 1.3 Update shared parser documentation and any typed payload shaping code that currently describes `activity` or `accepts_input`.

## 2. Provider Parser Mapping

- [ ] 2.1 Update Claude shadow parsing to map spinner, prompt, trust, selection, slash-command, and setup surfaces onto the new `business_state` and `input_mode` axes.
- [ ] 2.2 Update Codex shadow parsing to map processing, approval, selection, slash-command, and prompt surfaces onto the new `business_state` and `input_mode` axes.
- [ ] 2.3 Refresh provider parser fixtures or unit tests to cover mixed-state surfaces such as `working + freeform`, `idle + modal`, and `awaiting_operator + modal`.

## 3. Runtime Lifecycle Update

- [ ] 3.1 Refactor shadow readiness logic in `cao_rest.py` to use the derived submit-ready predicate instead of `accepts_input`.
- [ ] 3.2 Refactor shadow completion logic in `cao_rest.py` to require post-submit progress evidence plus a return to the derived submit-ready predicate.
- [ ] 3.3 Split runtime handling of operator-blocked surfaces from modal-but-not-blocked surfaces so trust or approval prompts fail explicitly while slash-command surfaces remain non-ready without immediate failure.

## 4. Verification And Docs

- [ ] 4.1 Update runtime lifecycle tests to cover operator-blocked, modal non-ready, and working-but-freeform transitions.
- [ ] 4.2 Update developer docs and provider contract docs so the public parsing vocabulary matches `business_state` and `input_mode`.
- [ ] 4.3 Run focused validation for `shadow_only` parsing and runtime flows, then capture any follow-on quiescence work as a separate change if still needed.
