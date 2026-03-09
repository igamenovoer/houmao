## 1. Parser Surface Classification

- [x] 1.1 Update Claude shadow slash-command classification so it follows the active input surface instead of whole-scrollback slash matches.
- [x] 1.2 Apply the same active-surface slash-command rule to the Codex shadow parser so provider behavior stays aligned.
- [x] 1.3 Refresh/add parser fixtures and unit tests that distinguish active slash-command prompts from historical slash-command output followed by a recovered normal prompt.

## 2. Runtime And Demo Regression Coverage

- [x] 2.1 Update CAO `shadow_only` runtime tests to verify historical slash-command output no longer blocks readiness while truly active slash-command surfaces still block prompt submission.
- [x] 2.2 Add or update interactive CAO full-pipeline demo tests to cover `send-turn` after manual slash-command/model-switch interaction in the same session.
- [x] 2.3 Adjust any demo/runtime diagnostics or expectations that assumed slash-command context could remain sticky after the prompt recovered.

## 3. Validation

- [x] 3.1 Run the affected parser and CAO runtime unit tests with `pixi run`.
- [x] 3.2 Run the affected demo test coverage with `pixi run`.
- [x] 3.3 Manually sanity-check the change notes against the investigated `/model` failure so implementation preserves the intended recovered-prompt behavior.
