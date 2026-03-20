# Houmao Server Developer Guide

This guide documents the server-owned live terminal tracking contract implemented by `houmao-server`.

It is the maintainer-oriented companion to the shorter reference pages under `docs/reference/`. Use this guide when you need to understand how the server builds `HoumaoTerminalStateResponse`, how turn anchors and lifecycle authority work, or how to safely change state reduction logic without drifting from the public API.

## What This Guide Covers

The server tracker is built around one core rule: `houmao-server` is the source of truth for live tracked terminal state. The server owns:

- tmux pane capture and transport health
- process inspection for supported TUIs
- parser invocation and parsed-surface normalization
- readiness and completion timing through the shared ReactiveX lifecycle kernel
- turn-anchor authority, visible-state stability, and bounded recent transition history

## Reading Order

| Page | Use it for |
|------|------------|
| [State Tracking](state-tracking.md) | Understand the end-to-end poll/reduce/publish pipeline, exact state transition rules, turn-anchor behavior, stability timing, and worked examples |

## Source Of Truth Map

This doc set summarizes the active contract from these sources:

- `src/houmao/server/tui/tracking.py`
- `src/houmao/server/service.py`
- `src/houmao/server/app.py`
- `src/houmao/server/models.py`
- `src/houmao/lifecycle/rx_lifecycle_kernel.py`
- `tests/unit/server/test_tui_parser_and_tracking.py`
- `tests/unit/server/test_service.py`
- `tests/unit/server/test_app_contracts.py`

The most important implementation file is `src/houmao/server/tui/tracking.py`, where `LiveSessionTracker` owns the current state, the turn-anchor lifecycle, stability timing, and transition publication.

## Relationship To Reference Docs

The shorter reference pages remain useful for quick lookups and operator workflows:

- [Houmao Server Pair](../../reference/houmao_server_pair.md)

Those pages intentionally stay higher level. If you are changing tracker semantics, state transitions, or the public live-state payload, treat this developer guide as the maintained home for the detailed explanation.
