# TUI Parsing Maintenance Guide

This page is the checklist for keeping the TUI parsing docs, specs, and runtime implementation aligned when provider UI drift or contract changes occur.

## Source Of Truth Inputs

When you update the parser stack, review these inputs together:

- active specs in `openspec/specs/`
- runtime modules under `src/houmao/agents/realm_controller/backends/`
- parser fixtures under `tests/fixtures/shadow_parser/`
- parser/runtime tests under `tests/unit/agents/realm_controller/`
- this developer doc set under `docs/developer/tui-parsing/`
- short reference and troubleshooting pages under `docs/reference/`

The archived design inputs under `openspec/changes/archive/2026-03-09-decouple-shadow-state-from-answer-association/` are useful historical context, but the maintained explanation should live in the main docs tree once this guide exists.

## When To Update This Doc Set

Update these docs whenever one of these changes lands:

- a provider adds or removes supported output families
- a provider gains new `ui_context` meanings or blocking states
- success terminality or stall policy changes in `TurnMonitor`
- result payload fields change for `shadow_only`
- new anomalies, metadata fields, or association helpers are introduced

If the change affects contract semantics rather than only implementation details, it should also go through OpenSpec and then feed back into this guide.

## Drift Investigation Workflow

When a provider UI drifts:

1. reproduce under `parsing_mode=shadow_only`
2. capture `mode=full` output for the failing turn
3. inspect parser metadata, anomalies, `surface_assessment`, and `dialog_projection`
4. determine whether the break is:
   - unsupported output family
   - version-floor fallback problem
   - projection-boundary bug
   - lifecycle/terminality issue
5. add or refresh fixtures and tests before or alongside parser changes
6. update docs if the contract, supported variants, or troubleshooting guidance changed

The operational steps for capture and troubleshooting remain in [CAO Shadow Parser Troubleshooting](../../reference/cao_shadow_parser_troubleshooting.md).

## Coordinated Update Checklist

Use this checklist when changing parser behavior:

- update parser code in `shadow_parser_core.py`, `claude_code_shadow.py`, `codex_shadow.py`, or `cao_rest.py` as needed
- refresh or add fixtures in `tests/fixtures/shadow_parser/`
- update unit or integration tests that validate state/projection/result payload behavior
- update active OpenSpec specs if the contract changed
- update this developer doc set, especially:
  - `shared-contracts.md`
  - `runtime-lifecycle.md`
  - `claude.md`
  - `codex.md`
- update the short reference/troubleshooting pages if their quick guidance changed

## Diagram Maintenance

If lifecycle states or transitions change, update both:

- the Mermaid `stateDiagram-v2` in [Runtime Lifecycle](runtime-lifecycle.md)
- the prose tables that define states and events

The diagram should stay readable and reflect the same vocabulary used in code and specs. Do not update one without the other.

## Navigation Expectations

The developer guide is the deep-dive home for architecture and contract explanation. The shorter pages should stay concise and point here for design-level details.

When adding new pages or reorganizing topics:

- keep `index.md` as the reading-order entry point
- update `docs/index.md` so the guide remains discoverable
- keep reference pages focused on quick lookup and troubleshooting rather than duplicating long-form design narrative
