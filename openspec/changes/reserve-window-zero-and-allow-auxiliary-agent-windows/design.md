## Context

The current repo draws a hard line between the agent TUI surface and the gateway sidecar. The live gateway service is launched as a detached subprocess with stdout and stderr redirected into `gateway.log`, while the main `agent-gateway` spec still says the gateway must not create a visible tmux pane or window. That protects the primary agent surface, but it also prevents a useful operator mode where gateway, monitoring, or other support processes stay visible in their own windows for debugging and observability.

The repository already has part of the desired topology for tmux-backed headless sessions: window `0` is the primary agent surface, auxiliary windows are allowed in principle, and server-managed headless APIs already treat auxiliary windows as non-authoritative. The gaps are elsewhere:

- gateway attach still launches one detached out-of-band process for every backend;
- headless window preparation still selects window `0`, which steals foreground focus back from any auxiliary window;
- `cao_rest` startup only reasons about bootstrap-window pruning and current-window selection, not about a later same-session auxiliary-window topology; and
- some repo-owned helper flows still capture the session's active pane instead of an explicit agent surface.

This change needs to relax the old "gateway must stay invisible" rule without weakening the more important rule: the agent process keeps one stable primary surface, and support processes must not redefine it.

## Goals / Non-Goals

**Goals:**

- Allow supported tmux-backed sessions to host gateway, monitoring, or similar support processes in auxiliary tmux windows in the same session.
- Keep window `0` as the only contractual agent surface for same-session tmux layouts.
- Preserve the existing headless `agent` window-0 contract.
- Extend the same-session auxiliary-window topology to `cao_rest` sessions without forcing `houmao_server_rest` into a tmux-session model it does not need.
- Ensure attach, detach, crash cleanup, and later agent relaunch preserve or restore the reserved agent window `0`.
- Keep durable gateway artifacts and on-disk logs intact even when gateway logs are also visible in an auxiliary tmux window.
- Harden repo-owned tracking and demo helpers so they keep following the agent surface when auxiliary windows are selected in the foreground.

**Non-Goals:**

- Make non-zero window names, counts, or indices part of the public runtime contract.
- Move `houmao_server_rest` server or gateway processes into the agent's tmux session.
- Redesign managed-agent HTTP payloads solely to expose auxiliary-window topology.
- Replace durable gateway log files with tmux-only observability.
- Guarantee same-session auxiliary-window support for sessions whose primary agent surface cannot be identified safely.

## Decisions

### Decision 1: Same-session auxiliary-window topology is backend-specific

Same-session auxiliary windows will be supported for tmux-backed headless backends (`claude_headless`, `codex_headless`, `gemini_headless`) and for `cao_rest`. `houmao_server_rest` remains out-of-session: the server process and any gateway or monitoring companions continue to run outside the agent's tmux session.

Rationale:

- Headless and `cao_rest` already have a runtime-owned tmux session that operators attach to directly.
- `houmao_server_rest` is a different topology: the server is not the agent and does not need to share the agent's tmux container.
- Making this split explicit keeps the new same-session behavior from leaking into backends where it would be artificial or misleading.

Alternatives considered:

- Use the same same-session tmux-window model for every gateway-capable backend. Rejected because `houmao_server_rest` does not need a session-local tmux companion and the user explicitly excluded it.
- Keep every backend on the detached out-of-band launcher. Rejected because it preserves the current observability limitation.

### Decision 2: Window `0` is the only contractual slot; auxiliary windows stay non-contractual

Window `0` is the only stable tmux-location contract in same-session layouts. The agent process must occupy window `0`, and all control, attach guidance, and recovery logic must continue to treat that surface as canonical. Non-zero windows remain implementation-owned: their names, indices, and counts are not part of the public contract.

For headless sessions, the stable public window name remains `agent`. For `cao_rest`, the runtime will preserve the CAO terminal's existing tmux window name for compatibility where practical, but the stronger invariant is process placement in window `0`, not a renamed CAO window.

Rationale:

- The user only wants one tmux-slot contract: window `0` is the agent.
- Leaving auxiliary windows non-contractual keeps future debugging and monitoring layouts flexible.
- Preserving CAO terminal naming avoids needless churn in CAO-specific compatibility paths that already use `terminal.name` and persisted `tmux_window_name`.

Alternatives considered:

- Standardize both index and name for every backend, including `cao_rest -> agent`. Rejected because CAO compatibility paths already use CAO-owned window naming and do not need that extra breakage.
- Publish a second contract for gateway-window name or index. Rejected because the requested behavior explicitly avoids making non-zero windows contractual.

### Decision 3: Gateway attach will gain two launcher modes

The runtime will support two gateway-launcher modes:

- same-session auxiliary-window launcher for tmux-backed headless backends and `cao_rest`;
- existing detached subprocess launcher for `houmao_server_rest` and any fallback paths that do not support same-session windows safely.

The same-session launcher will create or reuse an auxiliary tmux window, run `gateway_service` in the foreground there, and keep the existing durable log and state artifacts under `<session-root>/gateway/`. Visible console logs become additive observability, not a replacement for `gateway.log`.

For same-session mode, the runtime will treat the auxiliary tmux window and pane as the authoritative local execution surface for the gateway. Local liveness will come from tmux-owned pane state such as `pane_pid` or `pane_dead`, readiness will still require successful gateway health responses, and teardown will target the auxiliary tmux surface rather than pretending the gateway is backed by the detached `Popen` lifecycle used by `houmao_server_rest`.

Rationale:

- The gateway process already writes human-readable log lines both to disk and to stdout, so a foreground auxiliary window fits the current service behavior well.
- A launcher split is simpler than trying to force one process model across incompatible backends.
- Keeping the detached launcher for `houmao_server_rest` avoids coupling the server lifecycle to an unnecessary tmux surface.

Alternatives considered:

- Replace the detached launcher entirely. Rejected because `houmao_server_rest` still needs it.
- Run the gateway in the primary agent window. Rejected because it would reintroduce output corruption risk on the agent surface.

### Decision 4: Headless window preparation must stop stealing foreground selection

Headless runtime helpers will keep ensuring that window `0` exists and is named `agent`, but they will stop assuming that window `0` must also be the currently selected window before each turn. Runtime-controlled turns will continue to execute on the pane in window `0`, even when an auxiliary window is currently selected.

The implementation may split "ensure and name the stable agent surface" from "select that surface in the foreground" so initial session creation and pre-turn preparation do not have to share one always-selecting helper.

Rationale:

- The user's requested observability mode requires auxiliary windows to be able to stay in the foreground.
- The contractual requirement is "agent process remains in window `0`," not "window `0` must always be selected."
- This change is local to tmux helper behavior and does not require any public API expansion.

Alternatives considered:

- Keep selecting window `0` before every headless turn. Rejected because it defeats the new foreground-observability workflow.
- Let the active selected window determine the execution surface. Rejected because that would make auxiliary windows authoritative by accident.

### Decision 5: `cao_rest` same-session auxiliary windows require explicit primary-surface normalization

`cao_rest` startup today only guarantees best-effort selection of the CAO terminal window and bootstrap pruning. For same-session auxiliary windows, that is not enough. Before the runtime creates or treats another window as an auxiliary same-session process window, it must first identify the CAO terminal window explicitly and normalize the session so the agent process occupies window `0`.

The v1 normalization sequence will be explicit: when the bootstrap window and resolved CAO terminal window are distinct, the runtime will first prune the bootstrap window, then move the resolved CAO terminal window into tmux window `0`. If prune or move cannot safely establish the CAO terminal as window `0`, the runtime will leave ordinary CAO startup intact but will refuse same-session auxiliary-window topology for that session.

The normalization path will preserve CAO terminal identity semantics where possible, but it will refuse to guess. If the runtime cannot safely determine or preserve the CAO primary surface, it should not create a same-session auxiliary window for that session.

Rationale:

- The repo already treats CAO window resolution as bounded and explicit rather than inferred from active selection.
- Same-session auxiliary windows are only safe if the agent surface is known first.
- Refusing unsafe same-session topology is better than silently reintroducing the raw-TUI corruption risk that motivated the original restriction.

Alternatives considered:

- Allow same-session auxiliary windows for `cao_rest` without normalizing the CAO terminal into window `0`. Rejected because the user explicitly wants window `0` reserved for the agent process.
- Rename and rebuild all CAO window identity contracts around `agent`. Rejected because that creates extra compatibility churn with little benefit.
- Use `swap-window` or whole-session renumbering as the primary v1 normalization primitive. Rejected because prune-then-move fits the existing CAO startup sequence more directly and keeps the fail-closed decision point obvious.

### Decision 6: Attach, detach, crash cleanup, and later relaunch preserve window `0`

Window `0` belongs to the agent surface, not to the gateway lifecycle. Gateway attach, detach, crash cleanup, or auxiliary-window recreation must only affect the auxiliary process window. They must not kill the primary agent window as part of routine sidecar lifecycle handling.

If the agent process later dies and the runtime relaunches it inside the same tmux session, the recovery path must restore the relaunched agent process to window `0` before the session is treated as recovered or ready again.

This is new recovery work rather than a reuse of an existing tmux relaunch path. The runtime will need explicit primitives to detect agent loss, re-establish window-`0` ownership, and only then mark the session as recovered.

Rationale:

- The user explicitly wants the framework to preserve the agent window even when sidecars come and go.
- Treating window `0` as agent-owned keeps lifecycle semantics simple and predictable.
- Recovery should re-anchor the agent process to the same canonical slot rather than silently drifting to a non-zero window.

Alternatives considered:

- Treat window `0` as disposable during gateway detach or recovery. Rejected because it breaks the new contract immediately.
- Allow relaunch into any available window and update metadata afterward. Rejected because it would turn non-zero windows into accidental contract surface.

### Decision 7: Repo-owned tmux observers must resolve the agent surface explicitly

Repo-owned demo, explore, and tracking helpers that currently follow the session's active pane will be updated to target an explicit agent surface when they are used with runtime-managed same-session tmux layouts. For headless sessions, that means window `0` / `agent`. For `cao_rest`, that means the resolved CAO agent window rather than whichever auxiliary window happens to be selected.

That explicit agent-surface resolution will be centralized in one shared tmux helper rather than re-implemented independently at each demo or explore call site.

Rationale:

- Without this change, foreground auxiliary windows will make repo-owned helpers capture the wrong surface.
- The repo already has richer transport resolvers in some paths; this change makes the remaining ad hoc helpers follow the same rule.

Alternatives considered:

- Leave helper behavior unchanged and document the limitation. Rejected because it would make the new observability mode unreliable in demos and debugging workflows.

## Risks / Trade-offs

- [CAO window normalization may be fragile when tmux or CAO window discovery races] → Mitigation: keep the normalization path explicit, bounded, and test-covered, and refuse unsafe same-session auxiliary-window creation instead of guessing.
- [Foreground auxiliary windows can make operators forget which window is contractual] → Mitigation: document that only window `0` is authoritative and keep attach or control fallbacks pinned to the agent surface.
- [Headless helpers that stop selecting window `0` may expose hidden assumptions in tests or tooling] → Mitigation: update helper tests and add regression coverage for foreground auxiliary-window selection.
- [Auxiliary-window identity is intentionally non-contractual, which reduces discoverability for those windows] → Mitigation: keep that trade-off explicit in docs and rely on tmux-native operator workflows for non-zero windows.
- [Mixed launcher modes add implementation complexity] → Mitigation: isolate the launcher split at the gateway attach layer and keep status, artifacts, and durable contracts unchanged.

## Migration Plan

1. Update the behavior contracts in `agent-gateway` and `brain-launch-runtime` to distinguish the new same-session auxiliary-window topology from the existing detached topology.
2. Implement the launcher split and the window-`0` preservation rules, keeping `houmao_server_rest` on the existing detached gateway path.
3. Refactor headless tmux helpers so they preserve window `0` without forcing it into the foreground, including a split between rename-only and explicitly selecting variants when needed.
4. Add same-session gateway liveness and teardown handling that uses tmux-owned pane state for local execution tracking and gateway health for readiness.
5. Add `cao_rest` same-session normalization logic for auxiliary-window support using the explicit prune-then-move sequence, while preserving CAO naming compatibility and failing closed when normalization cannot safely establish window `0`.
6. Update repo-owned helper flows, tests, and docs to capture the agent surface through one shared resolver and to describe the new non-contractual nature of non-zero windows.

Rollback strategy:

- Revert the same-session auxiliary-window launcher and keep the existing detached launcher everywhere.
- Preserve the strengthened "window `0` is the agent surface" logic where it is already correct for headless sessions.
- Do not add fallback behavior that allows gateway lifecycle to destroy the agent surface during rollback.

## Open Questions

None at proposal time. The user has already fixed the intended backend scope, non-contractual nature of non-zero windows, and window-`0` preservation rule for attach, detach, and relaunch behavior.
