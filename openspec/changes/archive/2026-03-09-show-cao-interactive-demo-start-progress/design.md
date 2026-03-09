## Context

The interactive CAO demo `start` path performs several meaningful stages before the operator can interact with Claude Code: workspace preparation, optional worktree provisioning, CAO server checks/startup, brain build, and the final `brain_launch_runtime start-session` launch that blocks until the CAO-backed Claude terminal is ready for input. Today the demo prints nothing during that blocking period because the demo layer wraps the subprocess with `subprocess.run(...)` and only emits the final JSON payload after the subprocess exits.

That silence is especially confusing because the long wait happens at the exact point where the operator expects visible motion: Claude is being launched, tmux is being initialized, and readiness checks are running. A tutorial workflow that looks dead during startup undermines trust even when it is functioning correctly.

This change is intentionally scoped to operator feedback for the interactive demo startup path. The existing success payload and persisted artifacts remain the source of truth; the goal is to make the wait understandable rather than to redesign startup semantics.

## Goals / Non-Goals

**Goals:**
- Show visible progress during `run_demo.sh start` so operators can tell the command is still active.
- Preserve the existing machine-readable success JSON contract for `start`.
- Provide especially clear waiting feedback during the long-running `start-session` phase.
- Keep the implementation local to the interactive demo layer unless a shared runtime change becomes clearly necessary.

**Non-Goals:**
- Redesigning the shared `brain_launch_runtime start-session` CLI output contract for all callers.
- Streaming internal CAO or Claude logs directly to the user during startup.
- Turning startup progress into a detailed event protocol with dozens of stage transitions.

## Decisions

### 1. Emit startup progress on stderr and preserve final structured success output on stdout

The demo startup flow will print human-oriented progress breadcrumbs and wait heartbeats to stderr, while the final success JSON remains on stdout exactly as the current command expects.

Rationale:
- The current `start` payload is machine-readable JSON and should stay safe for wrappers or manual scripting.
- Stderr is the conventional place for progress/status messages that should not corrupt stdout payloads.
- This keeps the UX improvement isolated from downstream consumers of the final structured result.

Alternatives considered:
- Print progress to stdout before the final JSON. Rejected because it would break the current stdout contract and make the command harder to script.
- Replace the final JSON with human-readable text. Rejected because the demo already has a useful structured success payload.

### 2. Keep progress orchestration in the demo layer

The interactive demo module will own the startup breadcrumbs and heartbeat loop instead of requiring a new shared `brain_launch_runtime start-session` progress API.

Rationale:
- The pain point is specific to the demo wrapper experience, not to every runtime caller.
- The demo layer already knows its own operator-facing stages such as workspace prep, CAO preflight, brain build, and session launch.
- A local implementation reduces scope and avoids widening shared runtime contracts for a tutorial UX problem.

Alternatives considered:
- Add shared progress/event streaming to `brain_launch_runtime start-session`. Rejected for now because it is broader than necessary for this targeted operator experience fix.

### 3. Provide stage breadcrumbs plus a heartbeat for the long-running readiness wait

Startup progress will have two levels:

1. short stage breadcrumbs emitted when the demo enters major startup phases, and
2. periodic elapsed-time heartbeat messages while the blocking `start-session` subprocess is still running.

The long-running wait message should clearly say that the demo is waiting for the interactive Claude session to launch and become ready for input.

Rationale:
- Stage breadcrumbs tell the user where startup currently is.
- Heartbeats solve the “is this dead?” problem during the longest silent phase.
- A small number of clear messages is more valuable than verbose low-level tracing.

Alternatives considered:
- Emit only one static “starting...” line. Rejected because it still feels dead during multi-second or multi-minute waits.
- Emit raw child-process output continuously. Rejected because it is noisy, may be unstable across runtime changes, and would be harder to keep operator-friendly.

### 4. Implement the wait heartbeat by polling the child process rather than by changing the success payload shape

The blocking `start-session` launch will move from a fire-and-forget `subprocess.run(...)` call to a child-process polling loop in the demo runner for that command path, allowing the demo to emit elapsed-time updates until the child exits. The captured stdout/stderr logs and returned `CommandResult` shape remain unchanged.

Rationale:
- The current runner already owns process execution and log capture; extending it is the smallest implementation hook.
- Polling the child process allows progress updates without requiring the child CLI to cooperate.
- Keeping the returned `CommandResult` stable minimizes downstream churn in the demo module and tests.

Alternatives considered:
- Spawn a parallel timer thread while still using `subprocess.run(...)`. Rejected because polling a live child is simpler to reason about and easier to test deterministically.
- Special-case progress printing outside the runner with no child visibility. Rejected because the runner is the component that actually knows whether the child is still alive.

## Risks / Trade-offs

- [Risk] Progress messages could become overly chatty or noisy for fast startups. -> Mitigation: keep stage messages short and only emit periodic heartbeats during longer waits.
- [Risk] Mixing progress with machine-readable output could break callers. -> Mitigation: keep progress on stderr and preserve the final JSON payload on stdout.
- [Risk] A demo-local solution may not help other runtime callers that also want startup progress. -> Mitigation: keep the implementation isolated first; if the pattern proves useful, it can inform a later shared-runtime proposal.

## Migration Plan

1. Add a startup progress helper in the interactive demo module that can emit short phase breadcrumbs.
2. Update the long-running `start-session` subprocess execution path so it can print heartbeat updates while the child is still running and still return the same captured logs/result shape.
3. Hook the startup phases into `start_demo` so the operator sees meaningful messages before and during the readiness wait.
4. Update README/examples and unit tests to cover the stderr progress contract and stdout JSON stability.
5. Validate that startup still returns the same final JSON and that long-running starts now visibly report progress.

Rollback is straightforward: revert the demo-layer progress helper and runner changes to restore the previous silent startup behavior.

## Open Questions

- The exact heartbeat interval can remain an implementation detail as long as long-running waits produce recurring visible feedback before timeout.
