# Use Cases

This directory contains use cases for two complementary TUI state-tracking qualification suites, short-to-medium state/transition tests and long-horizon pressure tests, plus end-to-end prompt-admission qualification over the tracked state.

## Index

| ID | Use Case | Status |
| --- | --- | --- |
| [UC-01](uc-01-qualify-focused-tui-state-transitions.md) | Qualify Focused TUI State and Transition Tracking | Codex 0.144.x and Kimi 0.23.x detector profiles qualified; remaining focused coverage is pending |
| [UC-02](uc-02-pressure-test-long-horizon-tui-state-tracking.md) | Pressure-Test Long-Horizon TUI State Tracking | Exact Boltons prompts and actions designed; five sessions with at least 20 user operations each are pending |
| [UC-03](uc-03-qualify-prompt-admission-readiness.md) | Qualify Prompt Admission Readiness | Exact direct-prompt and mail-notifier procedures designed; Claude, Codex, and Kimi execution is pending |
| [UC-04](uc-04-verify-kimi-ready-busy-ready-transition.md) | Verify Kimi Code Ready-Busy-Ready Transition | Designed and executed for Kimi Code 0.23.6 |
| [UC-05](uc-05-detect-pending-instruction-state.md) | Detect Pending Instruction State | Designed; execution for Claude, Codex, and Kimi is pending |
| [UC-06](uc-06-guard-houmao-mgr-prompt-submission-against-pending-instructions.md) | Guard houmao-mgr Prompt Submission Against Pending Instructions | Designed; implementation and execution are pending |

## Notes

- UC-01 owns focused detector-state and transition correctness. Its short-to-medium cases normally use one to four user interactions in one provider session. Existing `PS-*` and `MS-*` cases belong to this use case.
- UC-02 owns accumulated-history and robustness pressure. Each `ST-*` session uses a fresh run-local copy of the vendored Boltons fixture and records at least 20 exact user operations. The five-session use case collectively covers every in-scope state-transition family.
- UC-03 owns the behavioral admission boundary. It proves that a new independent prompt is accepted only when the provider will process it immediately, that false-busy tracking clears within a bounded deadline, and that mail-notifier wakeups remain outside the provider CLI while busy and release promptly after ready.
- UC-04 isolates the `ready -> busy -> ready` transition family for Kimi Code. It deliberately widens the ready gap between two prompts so that a detector which never reports `ready_immediate` cannot hide behind a fast recording.
- UC-05 adds a new tracker posture, `busy_pending_input`, for spans where the provider CLI visibly retains user text for the next turn. It calibrates provider-specific signatures and proves the detector can distinguish `busy_active` from `busy_pending_input` for both gateway-submitted and natively typed input.
- UC-06 wires the UC-05 detector output into the `houmao-mgr agents single ... gateway prompt` path. It requires the command to refuse submission with `error_code=pending_input` when `turn_phase=busy_pending_input`, and it introduces `--force-if-no-pending` as a bypass that still blocks when a pending instruction exists. The existing `--force` flag continues to bypass every guard for calibration and recovery.
- The long-horizon suite does not replace focused cases. Focused cases localize transition defects; long-horizon cases detect stale-state leakage, drift, oscillation, duplicated outcomes, lost authority, and downstream-consumer failures after many operations.
- The plan targets the maintained Claude Code, Codex, and Kimi Code tracker profiles.
- Provider-visible network and LLM API failures are excluded from live scenario coverage because they cannot be induced reliably. Every live provider session uses the maintained `unattended` launch posture. Avoidable confirmation, approval, permission, trust, update, login, session-picker, browser, and user-question prompts are forbidden test outcomes rather than required stimuli.
- A prompt may receive scripted intervention only when provider/version-specific evidence proves that the CLI hard-codes it and exposes no CLI argument, configuration key, environment variable, prepared state, or other supported bypass. Such exceptions are declared before execution in an intervention allowlist and receive a distinct `pass_with_unavoidable_intervention` verdict.
- Locally controllable transport, process, parser, interruption, terminal-failure, and unknown-to-stalled states remain in scope. Approval and waiting-for-operator states are covered by negative live assertions and synthetic/replay fixtures unless an allowlisted unavoidable prompt makes them reachable under `unattended` mode.
- Canonical recordings use approximately 20 fps capture. Lower and irregular replay cadences use semantic transition contracts when exact sample equality is no longer meaningful.
