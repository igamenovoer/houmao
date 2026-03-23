## Context

Tmux-backed headless sessions currently start by creating a detached tmux session, leaving the default bootstrap shell in window 0, and then launching each controlled turn in a separate `turn-N` window. That shape makes the session topology encode turn lifecycle and forces operators or test harnesses to chase transient windows in order to watch the real agent output.

This is misaligned with the intended headless model in two ways:

- headless execution is controller-owned and serialized rather than concurrent, so there is no architectural need for separate per-turn windows; and
- operators expect one stable attach surface per headless agent, with auxiliary windows treated as optional extras rather than as the primary agent surface.

The repository already enforces the no-overlapping-turn rule for server-managed headless agents. The missing piece is making the tmux surface reflect that contract instead of exposing a bootstrap shell in window 0 and the actual agent turn in a later window.

## Goals / Non-Goals

**Goals:**
- Make tmux-backed headless sessions use a stable primary agent surface in window 0.
- Reuse window 0 for all runtime-controlled turns of the same headless agent.
- Preserve the existing serialized-execution contract so one headless agent never runs overlapping controlled turns.
- Allow auxiliary tmux windows in the same session for gateway, logs, or operator diagnostics without redefining which window is the agent.
- Keep controller-owned turn truth based on process/result evidence rather than tmux topology.

**Non-Goals:**
- Reintroduce tmux watching as authority for headless lifecycle state.
- Allow concurrent runtime-controlled prompt execution on the same headless session.
- Require gateway to move into tmux if it does not already need a window.
- Redesign the public managed-agent APIs beyond what is needed to reflect the stable primary surface.

## Decisions

### Decision: Window 0 is the canonical headless agent surface

For every tmux-backed headless session, window 0 is reserved for the agent itself. The runtime should treat that window as the stable primary surface for operator attach, capture, and best-effort control.

For operator clarity, the runtime should rename window 0 to a stable name such as `agent`, but the index contract is the authority: the headless agent is always in window 0.

Additional windows may exist in the same session, but they are auxiliary. They do not replace the agent surface and they must not change where runtime or server code expects the headless agent to be visible.

Rationale:

- It matches the intended mental model: attach to the session, look at window 0.
- It keeps test harnesses and demos deterministic.
- It avoids exposing an idle bootstrap shell as the canonical agent surface.

Alternatives considered:

- Keep window 0 as bootstrap shell and continue using `turn-N` windows: rejected because it encodes execution into tmux topology without need.
- Put the agent in some other stable window and leave window 0 unused or auxiliary: rejected because it weakens the simplest operator rule.

### Decision: Headless execution remains serialized and reuses the same tmux surface

One headless session runs at most one runtime-controlled turn at a time. This is already true for managed headless agents and should remain true across all runtime-controlled headless paths.

Because execution is serialized, the runtime should reuse the same window-0 surface for every turn instead of allocating a new tmux window per turn. Turn identity remains a controller-owned concept represented by per-turn records and durable artifacts on disk, not by tmux window names.

Rationale:

- There is no concurrency requirement that justifies per-turn windows.
- Reuse makes the session surface stable while keeping per-turn stdout/stderr/status artifacts unchanged.
- It lines up the tmux layout with the controller-owned lifecycle model.

Alternatives considered:

- Keep serialized execution but still allocate per-turn windows for convenience: rejected because it preserves the wrong operator-facing topology.
- Support overlapping turns in separate windows: rejected because it conflicts with the headless control model and complicates recovery and interrupt semantics.

### Decision: Turn execution is injected into the stable window-0 shell instead of spawning a new tmux window

The runtime should keep a persistent shell or equivalent control surface in window 0 and inject one bounded runner command into that surface for each turn. That injected command may still:

- write per-turn `stdout`, `stderr`, `exitcode`, and `process.json` artifacts,
- tee rolling output back into the visible pane,
- publish completion through `tmux wait-for`, and
- return control to the stable window-0 shell when the turn ends.

This preserves the recent execution-evidence contract while removing the dependency on `tmux new-window` for each turn.

Rationale:

- It keeps the visible surface stable without losing durable per-turn evidence.
- It preserves rolling console output in the same pane operators are already watching.
- It avoids coupling turn identity to tmux window allocation.

Alternatives considered:

- Replace the shell with `respawn-window` or `respawn-pane` per turn: rejected because it makes the stable surface harder to reason about after a turn exits and complicates prompt visibility.
- Run headless turns completely detached from tmux: rejected because live console visibility is still useful.

### Decision: Control and inspectability target the stable agent surface, not transient windows

Managed-headless diagnostics, demos, and best-effort tmux fallbacks should treat the stable agent surface as `session:0` rather than a per-turn `turn-N` window.

This means:

- tmux-facing inspect helpers and demos should capture window 0 when they want the agent surface;
- detailed state should describe the stable headless attach surface rather than implying transient turn windows; and
- last-resort interrupt should prefer live process identity first, then persisted process identity, then a control-input fallback aimed at window 0 rather than `kill-window` of a per-turn target.

Auxiliary windows may still exist for gateway or debugging, but they remain non-authoritative for both state and control.

Rationale:

- It keeps public inspectability aligned with the real agent surface.
- It prevents stable agent sessions from being torn down by a fallback that assumes turns own their own windows.

Alternatives considered:

- Continue storing per-turn tmux window names only for diagnostics: rejected because it perpetuates the wrong public mental model and keeps fallback control pointed at disposable windows.

## Risks / Trade-offs

- [Injected commands can collide with manual typing in window 0] → Mitigation: keep headless sessions controller-owned, document manual typing as unsupported, and treat resulting failure as ordinary execution/control failure.
- [A persistent shell can remain in a surprising state after a failed turn wrapper] → Mitigation: make the injected runner command self-contained, preserve durable artifacts, and keep server-side diagnostics explicit when the surface must be reset.
- [Legacy records and helpers may still assume `turn-N` windows] → Mitigation: migrate inspect helpers, detailed-state projection, and fallback control together; fail cleanly for older persisted state rather than preserving mixed assumptions.
- [Auxiliary windows may tempt future features to overload tmux topology again] → Mitigation: keep the rule explicit that auxiliary windows are non-authoritative and window 0 remains the canonical agent surface.

## Migration Plan

1. Update tmux-backed headless session bootstrap so window 0 is the stable agent surface and is named consistently for operators.
2. Replace per-turn `tmux new-window` execution with window-0 command injection that preserves the existing durable artifact contract and rolling pane output.
3. Update managed-headless active-turn metadata, interrupt fallback, and inspect/report surfaces to reference the stable agent surface rather than `turn-N` windows.
4. Update demos and autotest helpers to capture and attach to the agent surface in window 0 while tolerating auxiliary windows in the same session.
5. Add regression coverage for stable window-0 reuse, absence of per-turn windows, preserved rolling output, and continued single-active-turn enforcement.

Rollback strategy:

- If the stable-window execution path proves unreliable, keep the controller-owned artifact and process-evidence model but revert to the previous launch primitive temporarily.
- Do not relax the single-active-turn contract during rollback.

## Open Questions

- Should the public detailed-state payload expose an explicit stable attach target such as `session:0`, or is it sufficient to keep that stable target as an internal convention used by demos and diagnostics?
