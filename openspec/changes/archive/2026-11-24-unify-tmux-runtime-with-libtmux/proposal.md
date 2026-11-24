# Proposal

## Why

Houmao resolves tmux ownership in several places and mixes live terminal observations with saved launch state. A shared libtmux runtime makes terminal targeting and failure handling consistent before agent discovery and messaging start relying more heavily on saved records across tmux servers.

## What Changes

- Route maintained Python tmux operations through a shared libtmux adapter. Centralize direct process calls for operations that need capabilities libtmux lacks.
- Make the session manifest's tmux section the authority for the managed agent's terminal binding. Derive copies of that binding in provider state and registry records from the same source.
- Use one checked view of the session's panes to resolve the managed primary terminal. Give owner-authorized runtime operations a separate path to repair stale handles.
- Distinguish a confirmed missing target from a failed or inconclusive tmux observation. Keep server selection explicit through lookup, capture, input, and lifecycle operations.

## Capabilities

### New Capabilities

### Modified Capabilities

- `tmux-integration-runtime` covers shared libtmux execution, manifest-backed terminal ownership, checked observations, and authorized primary-handle repair.

## Impact

The change affects the Python execution layer, managed terminal backends, manifest and registry persistence, gateway terminal lifecycle, server compatibility controller, and maintained terminal tools and fixtures. It uses the existing libtmux dependency. `prefer-record-backed-agent-operations` builds on the resulting terminal operations and evidence model.
