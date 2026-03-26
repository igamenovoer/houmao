# Terminal Recorder Developer Guide

This guide documents the maintainer-facing design of the tmux-backed terminal recorder used to capture agent TUI sessions for parser and lifecycle testing.

It is the deep companion to the shorter operator/reference page in `docs/reference/terminal-record/index.md`. Use this guide when you need to change recorder lifecycle behavior, artifact contracts, active/passive semantics, or the managed `send-keys` integration.

## What This Guide Covers

The terminal recorder exists to solve a specific problem: we need replay-grade artifacts for TUI state tracking without pretending that an `asciinema` cast alone is the machine source of truth.

The maintained contract is built around these layers:

- the recorder targets an already-running tmux session or explicit pane instead of launching a new agent
- `asciinema` captures the operator-facing visual session
- `tmux capture-pane` produces the machine-readable pane snapshot stream used for replay and validation
- active mode publishes recorder state back into tmux so repo-managed `send-keys` calls can append structured managed-input events
- analyze and label flows derive parser/state observations from pane snapshots after the live run has ended, with replay/state analysis now driven through the standalone shared tracker session rather than a recorder-local reducer

## Reading Order

| Page | Use it for |
|------|------------|
| [Architecture](architecture.md) | Understand active/passive mode semantics, recorder lifecycle, artifact authority boundaries, and runtime integration points |
| [Maintenance](maintenance.md) | See the change checklist for lifecycle edits, send-keys integration, replay semantics, tests, and documentation updates |

## Source Of Truth Map

This doc set summarizes the active terminal-recorder contract from these sources:

- the `add-terminal-record-tooling` OpenSpec change under `openspec/changes/`
- the recorder package under `src/houmao/terminal_record/`
- tmux shared primitives under `src/houmao/agents/realm_controller/backends/tmux_runtime.py`
- managed control-input integration under `src/houmao/agents/realm_controller/backends/`
- recorder lifecycle and integration tests under `tests/unit/terminal_record/` and `tests/integration/agents/realm_controller/`

The most important implementation files are:

- `src/houmao/terminal_record/service.py`
- `src/houmao/terminal_record/models.py`
- `src/houmao/terminal_record/runtime_bridge.py`
- `src/houmao/agents/realm_controller/backends/tmux_runtime.py`
- `src/houmao/agents/realm_controller/backends/` (managed control-input integration)
- `tools/terminal_record/cli.py`
- `tests/unit/terminal_record/test_service.py`
- `tests/integration/agents/realm_controller/test_cao_control_input_runtime_contract.py`

## Relationship To Reference Docs

The shorter reference page remains the right entry point for command examples and artifact names:

- [Terminal Recorder Reference](../../reference/terminal-record/index.md)

If you are changing lifecycle guarantees, capture-authority semantics, or replay behavior, treat this developer guide as the place where the design-level explanation should live.
