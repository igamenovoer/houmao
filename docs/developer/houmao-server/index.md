# Houmao Server Developer Guide

This guide documents the server-owned live terminal tracking contract implemented by `houmao-server`. It covers TUI state tracking, turn lifecycle, and the public state API exposed via `GET /houmao/terminals/{terminal_id}/state`.

## Reading Paths

| Path | Start here if you need to... | Document |
|------|------------------------------|----------|
| **State Reference** | Look up what a specific state value means, its derivation, and what operations are safe | [state-reference.md](state-reference.md) |
| **Transitions & Operations** | Understand how states change, see the statechart diagrams, learn what operations are acceptable in each state | [state-transitions.md](state-transitions.md) |
| **Pipeline Architecture** | Understand the end-to-end poll/reduce/publish pipeline, turn-anchor behavior, and stability timing | [state-tracking.md](state-tracking.md) |
| **TUI Module Map** | Understand what `src/houmao/server/tui/` owns, how it relates to `shared_tui_tracking`, and which file to change | [internals/tui_tracking_module.md](internals/tui_tracking_module.md) |
| **Internals** | Understand registration, probe/parse pipeline, supervisor lifecycle, and live state model implementation details | [internals/README.md](internals/README.md) |

## What This Guide Covers

The server tracker is built around one core rule: `houmao-server` is the source of truth for live tracked terminal state, but it now expresses that ownership through a dedicated `src/houmao/server/tui/` watch-plane module that hosts the shared reducer rather than reimplementing it locally. The server owns:

- tmux pane capture and transport health
- process inspection for supported TUIs
- parser invocation and parsed-surface normalization
- registration-backed session discovery and watch-worker lifecycle
- the host adapter that merges shared tracker state with server-owned diagnostics, lifecycle timing, visible-state stability, and bounded recent transition history

Native headless managed agents now sit beside that tracker rather than inside it. They use the shared `/houmao/agents/*` read API, persist server-owned admission state under `state/managed_agents/<tracked_agent_id>/`, and expose durable per-turn inspection under `/houmao/agents/{agent_ref}/turns/*`. That headless control plane is implemented in the same service, but it is intentionally separate from the terminal-tracking reducer documented by this guide.

## Source Of Truth Map

Core state type definitions and tracker reduction logic live in the shared TUI tracking module, not in the server module:

| Module | Role |
|--------|------|
| `src/houmao/shared_tui_tracking/models.py` | Canonical type definitions: `Tristate`, `TrackedDiagnosticsAvailability`, `TurnPhase`, `TrackedLastTurnResult`, `TrackedLastTurnSource`, `TransportState`, `ProcessState`, `ParseStatus` |
| `src/houmao/shared_tui_tracking/session.py` | `TuiTrackerSession` — standalone raw-snapshot tracker with internal Rx timers and thread-safe live API |
| `src/houmao/shared_tui_tracking/registry.py` | App/profile registry and closest-compatible semver-floor detector resolution |
| `src/houmao/shared_tui_tracking/detectors.py` | Shared detector/profile contracts plus compatibility exports |
| `src/houmao/shared_tui_tracking/apps/claude_code/` | Claude Code raw-text detector/profile implementations |
| `src/houmao/shared_tui_tracking/apps/codex_tui/` | Codex interactive TUI detector/profile implementations, including temporal hint logic |
| `src/houmao/shared_tui_tracking/apps/unsupported_tool/` | Conservative fallback detector/profile implementation |
| `src/houmao/shared_tui_tracking/reducer.py` | Compatibility replay wrappers over the standalone tracker session |
| `src/houmao/server/tui/registry.py` | Registration-backed session admission plus manifest/version enrichment before tracking starts |
| `src/houmao/server/tui/transport.py` | tmux target resolution and raw pane capture |
| `src/houmao/server/tui/process.py` | Supported-TUI process inspection |
| `src/houmao/server/tui/parser.py` | Official parser sidecar over the shared shadow parser stack |
| `src/houmao/server/tui/tracking.py` | `LiveSessionTracker` — live server polling tracker |
| `src/houmao/server/tui/supervisor.py` | Supervisor and per-session worker lifecycle for the watch plane |
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
