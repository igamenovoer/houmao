# Tasks

## 1. Shared Execution and Observation

- [x] 1.1 Build the socket-bound libtmux adapter under `houmao.execution`. Extend the execution-scope tests to verify exact session selection on isolated servers with overlapping IDs, nested and concurrent scopes, and unchanged caller environment.
- [x] 1.2 Add checked observations and one immutable pane record for session-wide enumeration. Verify that an auxiliary window remains visible when inactive and that a missing target, an invalid row, and an inaccessible socket produce distinct results.
- [x] 1.3 Add the checked capture, buffer, and key operations used by the first slice. Verify literal text, bracketed paste, a separate Enter, scoped buffer cleanup, and a silent nonzero mutation result with no replay. Document the stdin-backed loader where it is implemented and test that prompt text stays out of arguments and diagnostics.

## 2. Managed Primary Binding and TUI Prompt Submission

- [x] 2.1 Normalize managed terminal binding on restore and persist it through the existing manifest and registry shapes. Verify that conflicting projections cannot override the saved binding, existing populated bindings resume, and missing socket authority cannot select an ambient server. Document the binding in the registry runtime integration reference.
- [x] 2.2 Unify primary pane selection for live observations and add the owner-authorized repair path. Verify nonzero pane defaults for owned launches, adopted window names and pane-zero rules for joins, and explicit outcomes for missing, dead, and ambiguous surfaces. Assert that observation leaves saved state unchanged and that same-generation binding changes or newer generations defeat stale repair attempts without losing unrelated state.
- [x] 2.3 Route the normal local TUI prompt and capture path through the checked binding and adapter. Exercise readiness, capture, buffer paste, and Enter on the same pane with the gateway detached, a different tmux window focused, and a same-name session on a second isolated socket. Verify that a paste failure prevents Enter and leaves the other pane untouched.

## 3. Runtime Lifecycle and Control

- [x] 3.1 Move fresh session and primary window setup, session options, and launch environment publication to the shared operations. Document the sanitized startup exception. Through isolated launches, verify one-based window defaults, color injection and opt-out, credential exclusion in new and existing server environments, required publication failure blocking provider startup, and relaunch masking of expired values.
- [x] 3.2 Move Headless and Service startup, liveness, input, restart, and teardown to the shared binding and terminal operations. Verify that a confirmed handle is used for control even when another window is active, failed observation cannot trigger retargeting or teardown, and deadline-bounded native waits still work on the owning socket. Document the wait and delegated child-process exceptions at the adapter boundary.
- [x] 3.3 Move DSH and Kimi Web supervisor terminal operations and the gateway's window lifecycle to the adapter. Verify checked supervisor restart and liveness, exact gateway window and pane receipts, and cleanup of a gateway window while a different window is current. Assert that gateway lifecycle preserves the agent's primary binding.
- [x] 3.4 Move the remaining manager and runtime tmux calls for join, self lookup, client inspection, gateway inspection, and terminal handoff behind shared operations. Verify exact owner socket routing, nested launcher isolation, and manual attach coordinates for non-interactive callers. Keep the documented operator commands aligned with the existing handoff behavior.

## 4. Compatibility, Recorder, and Tooling

- [x] 4.1 Replace the compatibility controller's separate transport with shared operations. Exercise its window lifecycle and key delivery through compatibility tests. Verify exact capture output, including trailing blank rows, and document a native exact-output operation if the pinned libtmux commands cannot preserve that contract.
- [x] 4.2 Migrate recorder lookup, dimensions, capture, and window operations to the adapter. Use its explicit socket and target for delegated PTY attach. Cover existing recording output, exact pane selection, and recorder-owned cleanup in recorder tests and document the PTY handoff where it is implemented.
- [x] 4.3 Migrate maintained fixture launch, demo, exploration, and qualification helpers that drive tmux. Exercise the fixture executable on `PATH`, an allowed owned-socket operation, and a silent foreign-socket refusal. Check that command denial is surfaced as an observation failure and that the adapter honors the shim's routing rules.
- [x] 4.4 Remove superseded runners, duplicate pane records, per-field binding fallbacks, and textual retargeting paths. Audit maintained Python call sites for direct tmux invocation and document each remaining process exception with its use and verification. Check that all surviving terminal operations bind an explicit selector or intentionally implement native entry-point selection.

## 5. Integrated Verification

- [x] 5.1 Run `pixi run lint`, `pixi run typecheck`, `pixi run test`, and the focused integration suites for execution scope, fixture boundaries, and managed gateway control. Run live tmux checks on uniquely selected isolated servers with `TMUX` and `TMUX_PANE` cleared at setup and clean up only those servers.
- [x] 5.2 Exercise the managed TUI path across isolated sockets from an enclosing agent session, then check Headless, Service, Web, and gateway lifecycle against the same terminal binding contract. Verify the manifest and registry projections after restart and the failure evidence that `prefer-record-backed-agent-operations` will consume.
