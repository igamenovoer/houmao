# Issue: Tracking Semantics Are Duplicated Across Server, Replay, and Demo Layers

## Priority
P1 - The repository has no single authoritative owner for tracked TUI semantics, which creates drift risk, inverted dependencies, and recurring integration bugs such as circular imports.

## Status
Known and unfixed as of 2026-03-20.

## Summary

The repository currently implements tracked TUI semantics in multiple places, but not all of that duplication is a bug.

There are two different roles:

1. An intentionally independent reference/demo tracker in the now-retired CAO dual shadow-watch demo, used to present and validate what correct state tracking should look like.
2. The official/runtime tracking path, which is currently fragmented across:
   - `houmao.server.tui.tracking`
   - `houmao.terminal_record.service`
   - `houmao.explore.claude_code_state_tracking`

The design flaw is not that the demo tracker exists independently. That independence is intentional and useful. The flaw is that generic/runtime tooling currently depends on the demo tracker and that the official/runtime path still lacks a single authoritative tracking core of its own.

## Why This Matters

- A generic subsystem (`terminal_record`) currently depends upward on demo-owned tracking code.
- Replay and live tracking can drift semantically even when both consume the same pane evidence.
- The explore harness duplicates public turn semantics again, increasing the number of places that must evolve together.
- Eager package-root imports can turn this ownership confusion into real import cycles, as happened with the `terminal_record.service -> demo -> runtime -> server -> service` path.

## Concrete Symptoms

### 1. Generic recorder depends on the independent demo tracker

Runtime-adjacent tooling and tests historically imported:

- the retired dual-watch demo `AgentSessionState`
- the retired dual-watch demo `MonitorObservation`
- the retired dual-watch demo `AgentStateTracker`

That coupling let replay-oriented validation reuse demo tracker fields such as `readiness_state` and `completion_state`.

### 2. Official live contract already moved to a different vocabulary

`src/houmao/server/tui/tracking.py` and `src/houmao/server/models.py` now define the public tracked-state contract around:

- `surface.accepting_input`
- `surface.editing_input`
- `surface.ready_posture`
- `turn.phase`
- `last_turn.result`
- `last_turn.source`

That contract is the official OpenSpec direction and is no longer centered on public readiness/completion states.

### 3. Explore replay duplicates the simplified contract again

`src/houmao/explore/claude_code_state_tracking/models.py` explicitly says it mirrors the simplified tracked-state vocabulary from OpenSpec without importing the `houmao-server` tracker implementation. Its `state_reducer.py` then re-implements a separate replay reducer.

## Root Cause

The repository lacks a shared official/runtime tracking core that sits below:

- live server observation and transport diagnostics,
- offline recorder replay,
- explore-harness replay and comparison tooling, and
- official runtime-facing presentation layers.

At the same time, generic/runtime tooling reaches upward into the intentionally independent demo tracker instead of depending on an official/runtime-owned core.

## Affected Code

- `src/houmao/terminal_record/service.py`
- the retired CAO dual-watch demo tracker module
- `src/houmao/server/tui/tracking.py`
- `src/houmao/server/models.py`
- `src/houmao/explore/claude_code_state_tracking/models.py`
- `src/houmao/explore/claude_code_state_tracking/state_reducer.py`
- `src/houmao/server/__init__.py`
- the retired CAO dual-watch demo package export surface

## Design Direction

Extract a shared official/runtime tracked-state core and make the current official/runtime layers depend on that core rather than on each other.

The target layering should look like:

- parser output + optional runtime/input evidence
- shared official/runtime tracking core
- adapters:
  - live server tracker
  - terminal-record replay analyzer
  - explore replay/comparison harness
  - runtime-facing dashboards and tools

The independent demo tracker remains separate and does not need to consume this shared core.

The shared official/runtime core should own:

- lifecycle timing over `LifecycleObservation`,
- turn-anchor semantics,
- turn-signal interpretation and public `surface` / `turn` / `last_turn` reduction,
- offline-compatible degraded behavior when explicit input authority is unavailable.

The live server layer should remain responsible for:

- tmux/process/probe diagnostics,
- explicit prompt-submission events,
- server-owned registration and session identity,
- route-facing response shaping.

## Fix Direction

1. Stop importing demo tracking code from `terminal_record`.
2. Extract neutral tracked-state models and reduction logic for the official/runtime path below `houmao.server.tui`.
3. Rework recorder replay to emit the official tracked-state vocabulary or a mechanically derived replay form of it.
4. Rework the explore harness to consume the shared official/runtime tracking core instead of mirroring semantics independently.
5. Preserve the boundary between independent reference tracking and the official/runtime core rather than folding the two together.
6. Keep lazy package exports as hygiene, but treat them as a symptom fix rather than the architectural fix.

## Related Specs

- `openspec/specs/official-tui-state-tracking/spec.md`
- `openspec/specs/terminal-record-replay/spec.md`
- `openspec/specs/terminal-record-artifacts/spec.md`

## Notes

The recently fixed circular import during pytest collection should be treated as supporting evidence for this issue, not as the whole issue. Lazy package exports removed the import-time failure, but they did not remove the underlying dependency inversion from official/runtime code into the independent demo tracker.
