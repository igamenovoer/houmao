## Context

`houmao-mgr` already has a clean Click-facing error path for `click.ClickException` and a narrow compatibility bridge for `SessionManifestError`, but local managed-agent commands also depend on the broader realm-controller runtime error family during registry-first target resolution. When a shared-registry record still looks fresh but its tmux session has already disappeared, resuming the local controller can raise a runtime-domain error before the command reaches its normal action path.

That mismatch currently leaks through `houmao-mgr` as a Python traceback even though the underlying condition is operator-facing and recoverable: the selected local managed agent no longer has a live tmux authority. The problem crosses the native CLI wrapper, the managed-agent resume helper, and the tmux-backed runtime resume path.

## Goals / Non-Goals

**Goals:**

- Ensure native `houmao-mgr` renders stale tmux-backed local managed-agent failures as normal CLI error text.
- Preserve the managed-agent context in the rendered error so operators can tell which target failed and why.
- Keep the command non-zero on failure; this is an error-reporting fix, not a silent success path.
- Add regression coverage at the helper and top-level CLI layers.

**Non-Goals:**

- Redefining `agents stop` as idempotent success when the tmux session is already gone.
- Changing shared-registry freshness semantics or forcing tmux liveness probes into every discovery lookup.
- Reworking the full realm-controller error taxonomy.
- Introducing new server APIs, registry formats, or tmux cleanup workflows.

## Decisions

### Decision: Broaden the native CLI runtime error boundary to the realm-controller base error family

`houmao-mgr` should treat realm-controller domain/runtime failures the same way the lower-level runtime CLI already does: render explicit error text and exit non-zero without a traceback. Catching the shared `BrainLaunchRuntimeError` base at the top-level wrapper keeps future runtime-domain failures from escaping as raw Python exceptions.

Alternative considered:
- Keep the top-level wrapper narrow and only patch the one known stale-session error site.
- Rejected because it leaves the same traceback leak pattern available through other runtime-domain failures.

### Decision: Wrap local controller resume failures with managed-agent context in the registry-backed helper

The local resume helper should convert runtime-domain resume failures into `click.ClickException` with a message that identifies the affected managed agent and states that its local runtime authority is unusable. This keeps command-specific context close to the source instead of relying on the top-level wrapper to explain a raw backend message.

Alternative considered:
- Let `resume_runtime_session()` messages flow directly to the top-level wrapper.
- Rejected because the raw message usually lacks the resolved managed-agent identity and does not explain that the failure came from shared-registry-backed local control.

### Decision: Keep stale local stop semantics as explicit failure for this change

If the operator targets a local managed agent whose tmux session has already disappeared, the command should fail clearly rather than pretending it successfully stopped a still-live session. The operator-facing fix is to report the stale target cleanly, not to silently redefine lifecycle semantics.

Alternative considered:
- Treat stale local `agents stop` as an idempotent "already stopped" success and opportunistically clean registry state.
- Rejected for this change because it is a larger lifecycle contract decision that should be handled separately if desired.

### Decision: Do not move tmux liveness probing into ordinary discovery for this change

Registry cleanup already has explicit stale-record probing, and normal discovery intentionally resolves "fresh" records by lease rather than by eager tmux probing. This change should make stale post-discovery failures safe and comprehensible without expanding the discovery contract itself.

Alternative considered:
- Make every registry-backed local resolve probe tmux liveness before returning a record.
- Rejected because it changes discovery behavior broadly and could have latency or authority implications beyond the traceback bug.

## Risks / Trade-offs

- [Catching the base runtime error family hides programmer bugs that accidentally use that family] → Preserve non-runtime exceptions as uncaught so true unexpected errors still surface during development.
- [Different command paths may still format stale-target errors differently] → Centralize the local resume wrapping in the managed-agent helper so registry-backed commands share one message pattern.
- [Operators may expect `agents stop` to succeed when the session is already gone] → Keep the message explicit about the tmux session no longer being live and leave idempotent-success semantics for a later change.
- [A future runtime refactor could raise a different exception class before the helper wraps it] → The broadened top-level CLI boundary still prevents traceback leakage for all realm-controller runtime-domain errors.

## Migration Plan

1. Broaden the native `houmao-mgr` top-level wrapper from `SessionManifestError` to the realm-controller runtime base error family.
2. Extend the local managed-agent resume helper to wrap stale local resume failures with managed-agent context.
3. Add regression tests for stale tmux-backed `agents stop` resolution and for traceback-free native CLI rendering.
4. Verify that successful command behavior and non-zero exit semantics for operator-facing failures remain unchanged.

Rollback is straightforward: revert the broadened CLI catch and resume-helper wrapping. No stored data or runtime-state migration is required.

## Open Questions

- Whether a later change should treat stale local `agents stop` as idempotent success plus registry cleanup instead of explicit failure.
- Whether the same managed-agent contextual wrapping should be applied to additional non-registry current-session resolution paths for perfect message consistency.
