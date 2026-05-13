## 1. Reference And Design Guidance

- [x] 1.1 Invoke the local `skill-creator` guidance before substantially updating the packaged system skill assets.
- [x] 1.2 Update v5 developer design notes to describe generated `<loop-slug>-operator-control`, separate `run_state` and `execution_mode`, and auto/manual mode semantics.
- [x] 1.3 Update reference execplan examples to use `<loop-slug>-operator-control` instead of older operator runbook naming.
- [x] 1.4 Update generated contract defaults so controllable loops include control state, operator intent events, and mode-aware runtime defaults.

## 2. Authoring Stage Guidance

- [x] 2.1 Update `execplan-specs-process` guidance so generated process docs model auto/manual mode when mail-driven loops support manual operation.
- [x] 2.2 Update `execplan-specs-contract` guidance to derive control contracts, mode state, operator intent records, and notifier posture requirements.
- [x] 2.3 Update `execplan-harness` guidance to require control status, get-mode, set-mode, pause/resume/stop, and manual-context command surfaces when applicable.
- [x] 2.4 Update `execplan-skills` guidance to require a generated `<loop-slug>-operator-control` skill for loop-local lifecycle control and mode switching.
- [x] 2.5 Update `execplan-agent-bindings` guidance so auto mode is notifier-prompt-driven and manual mode is operator-prompted.
- [x] 2.6 Update `execplan-finalize` guidance so generated support docs summarize operator-control and auto/manual wakeup behavior without introducing new authority.

## 3. Execution And Validation Guidance

- [x] 3.1 Update `validate-execplan` guidance to check operator-control skill shape, harness mode lookup, manual-context output, mode-aware tick behavior, and notifier/manual boundaries.
- [x] 3.2 Update execution pages for status, start, pause, resume, recover, and stop to prefer generated operator-control or harness control surfaces when present.
- [x] 3.3 Ensure generated on-tick skill guidance requires a harness control-context query and bounded behavior in both auto and manual mode.
- [x] 3.4 Ensure manual mode guidance never asks agents to sleep, poll, tail logs, wait in-chat, or rely on an external periodic tick driver.

## 4. Verification

- [x] 4.1 Run `openspec verify change add-v5-operator-control-skill` or the repository-supported equivalent.
- [x] 4.2 Run Markdown or formatting checks that are appropriate for changed documentation assets.
- [x] 4.3 Inspect the final diff for stale `<loop-slug>-operator-runbook` examples, category skill directories, duplicated platform mechanics, and accidental hardcoded loop domains.
