# TUI Parsing Developer Guide

This guide documents the runtime-owned TUI parsing stack used for tracking interactive and headless agent sessions.

It is the maintainer-oriented companion to the shorter reference and troubleshooting pages under `docs/reference/`. Use this guide when you need to understand why the parser stack is structured the way it is, how the runtime lifecycle works, or how to safely change provider-specific parsing rules.

## What This Guide Covers

The TUI parsing stack turns raw tmux pane snapshots (for `local_interactive` sessions) or headless stdout (for headless sessions) into stable runtime artifacts without pretending that raw terminal scrollback can always prove “the answer for the current prompt.” The current contract is built around these layers:

- provider parsers classify one snapshot into `SurfaceAssessment` and `DialogProjection`
- the `shared_tui_tracking/` package provides `StreamStateReducer`, detector profiles, and `TuiTrackerSession` for raw-snapshot reduction and turn lifecycle tracking
- callers may optionally layer answer association on top of projected dialog

## Reading Order

| Page | Use it for |
|------|------------|
| [Architecture](architecture.md) | Understand the layered design, major modules, and end-to-end data flow |
| [Shared Contracts](shared-contracts.md) | Learn the shared models, payload fields, anomalies, and result surface |
| [Runtime Lifecycle](runtime-lifecycle.md) | Understand readiness/completion monitor semantics, completion stability, stalled recovery, and success terminality |
| [Claude](claude.md) | Review Claude-specific state vocabulary, detection signals, preset/version behavior, and projection rules |
| [Claude Signals](claude-signals.md) | See the concrete on-screen Claude cues currently used for reliable tracking and fixture authoring |
| [Codex](codex.md) | Review Codex-specific state vocabulary, supported output families, preset/version behavior, and projection rules |
| [Codex Signals](codex-signals.md) | See the concrete on-screen Codex cues currently used for reliable tracking and fixture authoring |
| [Maintenance](maintenance.md) | See the update checklist for parser drift, docs/spec alignment, and fixture/test refreshes |

> **Gemini note:** Gemini is intentionally unsupported for TUI tracking. Gemini agents run on the `gemini_headless` backend only and do not have a shadow TUI parser. All TUI parsing documentation in this guide covers Claude and Codex exclusively.

## Source Of Truth Map

This doc set summarizes the active runtime contract from these sources:

- active specs in `openspec/specs/`
- runtime modules under `src/houmao/agents/realm_controller/backends/`
- the completed `openspec/changes/rx-shadow-turn-monitor/` change for the current monitor design and terminology
- the archived originating design and contract notes in `openspec/changes/archive/2026-03-09-decouple-shadow-state-from-answer-association/`

The most important implementation files are:

- `backends/shadow_parser_core.py`
- `shared_tui_tracking/session.py`
- `shared_tui_tracking/reducer.py`
- `shared_tui_tracking/detectors.py`
- `shared_tui_tracking/apps/`
- `backends/cao_rx_monitor.py`
- `backends/cao_rest.py`
- `backends/claude_code_shadow.py`
- `backends/codex_shadow.py`
- `backends/shadow_answer_association.py`
- `tests/unit/agents/realm_controller/test_cao_rx_monitor.py`

All of those paths are relative to `src/houmao/agents/realm_controller/` except `shared_tui_tracking/` paths which are relative to `src/houmao/`.

## Relationship To Reference Docs

If you are changing contracts, state transitions, or parser responsibilities, treat this developer guide as the place where the deep explanation should live.

The existing [Architecture](architecture.md) and [Runtime Lifecycle](runtime-lifecycle.md) pages are the maintained home for the runtime monitor explanation. This guide intentionally does not split that material into a separate Rx-only page unless the lifecycle story becomes too large to keep readable.
