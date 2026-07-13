## Why

UC-03 (Qualify Prompt Admission Readiness) defines the CAL-01, AR-01, and AR-02 procedures needed to prove that gateway direct-control prompts and mail-notifier wakeups are admitted only when the provider TUI will process them as a new independent turn. The procedures are documented, but no execution plan or harness exists yet. We already have a large corpus of long-horizon tmux recordings under `tmp/tui-state-tracking-long-horizon/2026-07-13-all-providers/` that includes the same providers, Boltons fixture, unattended posture, and 20 fps capture format UC-03 requires. This change plans how to execute UC-03 by reusing that corpus for harness development, calibration, and partial replay evidence while defining the remaining live capture work.

## What Changes

- Define a concrete UC-03 execution plan that maps CAL-01, AR-01, and AR-02 to the existing long-horizon recording infrastructure and the `houmao-mgr gateway prompt` / `gateway mail-notifier` control surfaces.
- Specify how to derive an **admission-consumer simulator** from the existing recorded-validation replay harness so it can replay recorded state through the current non-forced admission predicate and emit `would_admit` plus blocking reasons per sample.
- Specify how to reuse existing tmux recordings as development fixtures for the simulator and as partial behavioral ground-truth for the ready/busy/draft/overlay labels, while keeping independent human labels authoritative for qualification.
- Identify the exact new live capture sessions still required (CAL-01 per provider, AR-01 per provider, AR-02 per provider) and the reusable harness artifacts that make those sessions tractable.
- Produce a tasks list that can be implemented incrementally without blocking on full UC-02 qualification completion.

## Capabilities

### New Capabilities
- `tui-prompt-admission-qualification`: Defines the UC-03 CAL-01/AR-01/AR-02 test procedures, the admission-consumer simulator contract, reuse of existing tmux recordings as development fixtures, and the remaining live capture requirements for Claude, Codex, and Kimi.

### Modified Capabilities
- (none — this change is test-planning and harness-only; it does not change product requirements in existing specs)

## Impact

- Affects `scripts/demo/shared-tui-tracking-demo-pack/` and any new `scripts/qualification/tui-prompt-admission/` harness location.
- Reuses `terminal-record-artifacts`, `terminal-record-replay`, `shared-tui-tracking-recorded-validation`, `agent-gateway`, and `agent-gateway-mail-notifier` specs as dependencies.
- Does not change gateway control APIs or tracker public state schema; it only consumes them.
