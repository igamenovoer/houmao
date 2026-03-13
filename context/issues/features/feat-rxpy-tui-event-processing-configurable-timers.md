# Feature Request: RxPY-Based TUI Event Processing With Configurable Timers

## Status
Proposed

## Summary
Introduce a reactive TUI event processing pipeline using ReactiveX for Python (`reactivex` / RxPY) so runtime event handling is cleaner, easier to extend, and does not depend on scattered hardcoded timing constants.

The goal is to replace ad-hoc read/poll loops with composable observables and make timing behavior explicitly configurable.

## Why
Current TUI/event handling paths rely on fixed timing values spread across backend loops. This makes behavior harder to reason about and harder to tune per environment (local dev, CI, slower remote hosts, etc.).

Examples in current implementation include:
- fixed short read windows in Codex app-server event loops (`0.25s`) and interrupt timeout (`3.0s`) in `src/gig_agents/agents/realm_controller/backends/codex_app_server.py`
- default CAO polling/time budget values (`poll_interval_seconds=0.4`, `timeout_seconds=120.0`) in `src/gig_agents/agents/realm_controller/backends/cao_rest.py`
- headless tmux completion polling defaults in `src/gig_agents/agents/realm_controller/backends/headless_runner.py`

## Requested Scope
1. Add an internal RxPY-based event pipeline abstraction for TUI/event streams (stdio JSON-RPC messages, CAO terminal output polling, and related completion/status signals).
2. Move timing controls (poll interval, read window, response timeout, completion timeout, retry intervals, debounce/quiet windows if used) into explicit runtime configuration instead of hardcoded literals.
3. Define one shared timing config contract used by all relevant backends, with validation and clear defaults.
4. Thread timing config from launch/runtime config to backend constructors so callers can override values without code changes.
5. Keep behavior parity by default, but allow environment-specific tuning through config.

## Acceptance Criteria
1. No backend TUI/event loop depends on inline hardcoded timing literals for operational timing decisions.
2. Timing values are discoverable in a documented config schema and validated (for example: positive floats, minimum bounds where needed).
3. Codex app-server and CAO shadow/event paths consume the new config contract.
4. Tests cover default behavior and at least one non-default override path per backend.
5. Developer docs explain how to tune timing values and when to adjust them.

## Non-Goals
- No immediate change to parser semantics or output schema beyond what is needed to support reactive processing.
- No mandatory behavioral changes for existing users when defaults are unchanged.

## Suggested Follow-Up
- Create an OpenSpec change dedicated to reactive runtime event orchestration and timing configuration.
- Include migration notes that map old implicit constants to new config keys.

## Review Notes

### Problem validation

The identified pain point is real and well-scoped. There are ~8 timing literals across three backends (`codex_app_server`, `cao_rest`, `headless_runner`) that are either fully hardcoded or declared as constructor parameters but never wired through from `runtime.py::_create_backend_session()`. The examples cited in the proposal are accurate.

### Recommendation: accept configurable timers (scope 2–5), reject RxPY pipeline (scope 1)

**Scope items 2–5** (extract timing to config, shared contract, validation, threading config to backends, docs) are a clean, low-risk improvement that directly addresses the stated problem.

**Scope item 1** (RxPY-based event pipeline) is over-engineered for the current architecture and should be deferred or dropped. Reasons:

1. **Architecture mismatch.** The entire runtime is synchronous, single-threaded, blocking I/O — `time.sleep()` loops with `time.monotonic()` deadlines, `select.select()` for reads. There is no async foundation. Grafting reactive observables onto this requires rearchitecting every backend's control flow, not just extracting constants. The blast radius far exceeds what the proposal implies.

2. **Dead dependency signal.** `reactivex>=4.1.0` is already declared in `pyproject.toml` but has zero imports anywhere in `src/`. The library was added and never adopted — this suggests the team previously considered and deferred reactive patterns. Re-proposing the same direction should address why the earlier attempt stalled.

3. **Existing config pattern is sufficient.** `launch_plan.py` already implements `configured_cao_shadow_policy()`, which extracts validated timing config from `LaunchPlan.metadata` and threads it to the CAO backend. Extending this proven pattern to all backends (and wiring the existing but unused constructor parameters through `_create_backend_session()`) solves the configurable-timers problem with ~50 lines of incremental change — no new abstractions required.

### Suggested revised scope

- Extract all backend timing literals into named constants with clear defaults.
- Define a shared `BackendTimingConfig` (Pydantic model or frozen dataclass) covering poll intervals, read windows, response/completion timeouts, and interrupt timeouts.
- Add a `LaunchPlan.metadata` key (e.g., `backend_timing_config`) with validated extraction, following the `configured_cao_shadow_policy()` pattern.
- Wire timing config from `_create_backend_session()` to each backend constructor.
- Add tests for default behavior and at least one override path per backend.
- Document tunable timing keys and when to adjust them.
- Defer RxPY event pipeline to a future proposal if/when the runtime moves to async I/O.
