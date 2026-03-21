# Houmao Server Developer Guide

This guide documents the server-owned live terminal tracking contract implemented by `houmao-server`. It covers TUI state tracking, turn lifecycle, and the public state API exposed via `GET /houmao/terminals/{terminal_id}/state`.

## Reading Paths

| Path | Start here if you need to... | Document |
|------|------------------------------|----------|
| **State Reference** | Look up what a specific state value means, its derivation, and what operations are safe | [state-reference.md](state-reference.md) |
| **Transitions & Operations** | Understand how states change, see the statechart diagrams, learn what operations are acceptable in each state | [state-transitions.md](state-transitions.md) |
| **Pipeline Architecture** | Understand the end-to-end poll/reduce/publish pipeline, turn-anchor behavior, and stability timing | [state-tracking.md](state-tracking.md) |
| **Internals** | Understand registration, probe/parse pipeline, supervisor lifecycle, and live state model implementation details | [internals/README.md](internals/README.md) |

## What This Guide Covers

The server tracker is built around one core rule: `houmao-server` is the source of truth for live tracked terminal state. The server owns:

- tmux pane capture and transport health
- process inspection for supported TUIs
- parser invocation and parsed-surface normalization
- readiness and completion timing through the shared ReactiveX lifecycle kernel
- turn-anchor authority, visible-state stability, and bounded recent transition history

Native headless managed agents now sit beside that tracker rather than inside it. They use the shared `/houmao/agents/*` read API, persist server-owned admission state under `state/managed_agents/<tracked_agent_id>/`, and expose durable per-turn inspection under `/houmao/agents/{agent_ref}/turns/*`. That headless control plane is implemented in the same service, but it is intentionally separate from the terminal-tracking reducer documented by this guide.

## Source Of Truth Map

Core state type definitions and mapping logic live in the shared TUI tracking module, not in the server module:

| Module | Role |
|--------|------|
| `src/houmao/shared_tui_tracking/models.py` | Canonical type definitions: `Tristate`, `TrackedDiagnosticsAvailability`, `TurnPhase`, `TrackedLastTurnResult`, `TrackedLastTurnSource`, `TransportState`, `ProcessState`, `ParseStatus` |
| `src/houmao/shared_tui_tracking/public_state.py` | Canonical mapping functions: `diagnostics_availability()`, `turn_phase_from_signals()`, `tracked_last_turn_source_from_anchor_source()` |
| `src/houmao/shared_tui_tracking/detectors.py` | Tool-specific signal detectors: `ClaudeCodeSignalDetectorV2_1_X`, `CodexTrackedTurnSignalDetector`, `FallbackTrackedTurnSignalDetector` |
| `src/houmao/shared_tui_tracking/reducer.py` | `StreamStateReducer` — shared replay/offline reducer implementing the same public state contract |
| `src/houmao/server/tui/tracking.py` | `LiveSessionTracker` — live server polling tracker |
| `src/houmao/server/service.py` | Top-level wiring, registration, alias maps, poll cycle |
| `src/houmao/server/app.py` | HTTP route definitions |
| `src/houmao/server/models.py` | Pydantic response models (re-exports shared types) |
| `src/houmao/lifecycle/rx_lifecycle_kernel.py` | ReactiveX settle/timing kernel |

Test sources:

| Module | Coverage |
|--------|----------|
| `tests/unit/server/test_tui_parser_and_tracking.py` | Parser and tracking integration |
| `tests/unit/server/test_service.py` | Service-level behavior |
| `tests/unit/server/test_app_contracts.py` | HTTP route contracts |

## Relationship To Reference Docs

The shorter reference pages remain useful for quick lookups and operator workflows:

- [Houmao Server Pair](../../reference/houmao_server_pair.md)

Those pages intentionally stay higher level. If you are changing tracker semantics, state transitions, or the public live-state payload, treat this developer guide as the maintained home for the detailed explanation.

If you are changing native headless lifecycle, authority persistence, or managed-agent alias resolution, start in:

- `src/houmao/server/service.py`
- `src/houmao/server/managed_agents.py`
- `src/houmao/server/models.py`
- `src/houmao/server/app.py`
