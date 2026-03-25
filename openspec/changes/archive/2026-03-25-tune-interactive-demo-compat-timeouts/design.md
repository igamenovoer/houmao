## Context

The Houmao-server interactive full-pipeline demo starts its own `houmao-server`, installs the tracked compatibility profile, and then launches a detached interactive session through `houmao-mgr cao launch --headless`. That detached launch is still synchronous on `POST /cao/sessions`, so the demo can fail before startup completes if it relies on the generic pair timeout defaults instead of a demo-owned startup budget.

The pair already has the right tuning seams:

- `houmao-server serve` exposes compatibility startup timing options for shell readiness, provider readiness, polling intervals, and Codex warmup.
- `houmao-mgr cao launch` exposes a separate compatibility create timeout budget for long-running `POST /cao/sessions`.

This change is only about the interactive demo pack. It should make that demo robust under automation and real provider latency without raising the product-wide defaults for unrelated operators.

## Goals / Non-Goals

**Goals:**

- Give the interactive demo explicit generous compatibility startup budgets instead of relying on generic pair defaults.
- Keep the generous values demo-owned so they apply only to this demo pack.
- Expose a narrow demo-side override surface so automation can tune the budgets without patching repository code.
- Document the relationship between the demo's server-side compatibility waits and the detached launch create timeout.

**Non-Goals:**

- Change the product-wide defaults for `houmao-server` or `houmao-mgr`.
- Rework the detached compatibility launch into a native headless route.
- Fix separate startup hygiene bugs from the same hacktest report, such as stale git worktree registration or orphaned tmux cleanup.
- Change post-launch request-settle polling or managed-agent follow-up flow unless required as a direct consequence of the startup-budget tuning.

## Decisions

### Decision: Use demo-specific generous compatibility defaults

The demo will start its demo-owned `houmao-server` with explicit compatibility startup overrides and will launch the detached session with an explicit create-timeout override.

The proposed demo defaults are:

- compatibility shell-ready timeout: `20s`
- compatibility provider-ready timeout: `120s`
- compatibility Codex warmup: `10s`
- compatibility create timeout: `180s`

The general compatibility HTTP timeout used for lightweight requests will stay on the existing short budget instead of becoming part of the demo's generous startup profile.

Why this over changing the pair-wide defaults:

- the failure was observed in this demo's automation path, not as a proven product-wide regression for every compatibility launch
- `10s` Codex warmup is too expensive to justify as a global default
- the demo owns both the server process and the detached launch wrapper, so it can budget them together locally

Alternatives considered:

- raise the global `houmao-server` Codex warmup and provider-ready defaults
  Rejected because it would slow every compatibility launch rather than only the demo pack that needs extra headroom.
- change only the detached launch create timeout
  Rejected because the demo also owns the server startup waits; if those remain at product defaults, the client and server budgets can still drift apart.

### Decision: Surface the tuning through the demo CLI and shell wrapper

The demo should not bury these values as patch-only literals. It already exposes demo-owned timeout controls such as `--server-start-timeout-seconds`, so the new compatibility startup budgets should follow the same pattern.

The demo CLI will add flags for the server-side compatibility startup waits and the detached launch create timeout. The shell wrapper will forward matching environment variables for automation workflows.

Why this over hardcoding only:

- the hacktest harness already drives the demo through `run_demo.sh`
- CI or local automation may need to raise or lower the values by environment without editing tracked scripts
- it keeps the demo's startup contract inspectable and explicit

Alternatives considered:

- hardcode the demo values and document them only in README
  Rejected because it removes a useful automation seam now that the pair supports supported overrides.
- expose every pair timing knob, including polling intervals and ordinary HTTP timeout
  Rejected because the demo only needs a small operator surface for the known startup problem.

### Decision: Keep the generous budget tied to detached compatibility startup only

The new demo values will be used only in:

- `_start_server_process()` for `houmao-server serve`
- `_launch_pair_session()` for `houmao-mgr cao launch --headless`

Post-launch inspection, request submission, interrupt, and stop will keep their existing small client budgets and follow-up logic.

Why:

- the observed blocker is startup, not steady-state inspection or stop behavior
- widening all demo HTTP calls would make later failures slower without improving the start path materially

## Risks / Trade-offs

- [Demo startup becomes slower on failing Codex runs] → Keep the `10s` Codex warmup override scoped to this demo and expose it as a demo override instead of changing product defaults.
- [Client and server demo budgets could drift if only one side is overridden] → Document that the detached launch create timeout must remain larger than the demo-owned server compatibility startup chain.
- [More demo CLI flags increase surface area] → Limit the new override surface to the startup-relevant compatibility budgets rather than exposing every pair timing option.
- [Automation may still hit separate startup hygiene bugs] → Keep this change scoped to Finding 1 and leave worktree/tmux cleanup for a separate follow-up.

## Migration Plan

1. Add demo-owned startup timing fields and defaults to the interactive demo environment model.
2. Pass those values into `houmao-server serve` and `houmao-mgr cao launch --headless` during startup.
3. Expose matching demo CLI flags and shell-wrapper environment forwarding for automation.
4. Update the interactive demo README and regression tests to reflect the new startup budgeting.

Rollback is simple because the change is local to the demo pack. Reverting the demo-specific overrides restores the previous behavior without affecting the pair-wide compatibility contract.

## Open Questions

None. The change intentionally keeps the scope to the interactive demo pack and the startup timeout problem already observed in automation.
