# TUI Parsing Developer Guide

This guide documents the runtime-owned TUI parsing stack used for CAO `shadow_only` sessions.

It is the maintainer-oriented companion to the shorter reference and troubleshooting pages under `docs/reference/`. Use this guide when you need to understand why the parser stack is structured the way it is, how the runtime lifecycle works, or how to safely change provider-specific parsing rules.

## What This Guide Covers

The TUI parsing stack turns CAO `mode=full` tmux snapshots into stable runtime artifacts without pretending that raw terminal scrollback can always prove “the answer for the current prompt.” The current contract is built around these layers:

- provider parsers classify one snapshot into `SurfaceAssessment` and `DialogProjection`
- runtime `TurnMonitor` interprets ordered snapshots before and after submit
- callers may optionally layer answer association on top of projected dialog

## Reading Order

| Page | Use it for |
|------|------------|
| [Architecture](architecture.md) | Understand the layered design, major modules, and end-to-end data flow |
| [Shared Contracts](shared-contracts.md) | Learn the shared models, payload fields, anomalies, and result surface |
| [Runtime Lifecycle](runtime-lifecycle.md) | Understand `TurnMonitor`, lifecycle states, transition events, and success terminality |
| [Claude](claude.md) | Review Claude-specific state vocabulary, detection signals, preset/version behavior, and projection rules |
| [Codex](codex.md) | Review Codex-specific state vocabulary, supported output families, preset/version behavior, and projection rules |
| [Maintenance](maintenance.md) | See the update checklist for parser drift, docs/spec alignment, and fixture/test refreshes |

## Source Of Truth Map

This doc set summarizes the active runtime contract from these sources:

- active specs in `openspec/specs/`
- runtime modules under `src/gig_agents/agents/realm_controller/backends/`
- the archived originating design and contract notes in `openspec/changes/archive/2026-03-09-decouple-shadow-state-from-answer-association/`

The most important implementation files are:

- `backends/shadow_parser_core.py`
- `backends/cao_rest.py`
- `backends/claude_code_shadow.py`
- `backends/codex_shadow.py`
- `backends/shadow_answer_association.py`

All of those paths are relative to `src/gig_agents/agents/realm_controller/`.

## Relationship To Reference Docs

The shorter reference pages remain useful for operators and quick lookups:

- [CAO Claude Code Shadow Parsing](../../reference/cao_claude_shadow_parsing.md)
- [CAO Shadow Parser Troubleshooting](../../reference/cao_shadow_parser_troubleshooting.md)

Those pages now point back to this guide for design-level detail. If you are changing contracts, state transitions, or parser responsibilities, treat this developer guide as the place where the deep explanation should live.
