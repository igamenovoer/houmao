## Why

Current TUI state tracking for CAO-backed agents is short-lived and request-scoped. The runtime only polls continuously while waiting for readiness or completion, and the dual shadow-watch demo has its own separate always-on monitor loop. That leaves no persistent Houmao-owned control plane behind a live Claude Code or Codex session for continuous state tracking, stable operator-facing status, or durable local control.

We need that control plane now, but we do not want to fork or patch CAO just to get it. A shallow Houmao-managed per-session supervisor lets us add continuous watching, persisted state, and our own session authority on top of CAO today, while creating the adapter boundary needed to replace CAO later instead of keeping CAO as the architectural center.

## What Changes

- Add a Houmao-managed per-session supervisor sidecar that continuously watches one live agent session, owns its persisted local state, and provides a local control surface for status, prompt submission, control input, interrupt, and stop.
- Define the v1 supervisor as adapter-based so it can manage existing CAO-backed Claude Code and Codex sessions without modifying CAO source code.
- Separate supervisor-owned state into raw observed TUI snapshots, owned-turn lifecycle state for supervisor-submitted work, and a smoothed operator-facing state that can tolerate transient snapshot flicker.
- Persist supervisor attach metadata, current state, sample history, and transition history under the session root so other Houmao tools can inspect or build UI on top of the session without scraping CAO directly.
- Extend runtime launch and control flows so sessions can opt into supervisor-backed management while leaving upstream launch, tmux/terminal hosting, and provider-specific behavior delegated to the current CAO adapter in v1.

## Capabilities

### New Capabilities
- `managed-agent-supervisor`: A persistent per-session Houmao-owned supervisor sidecar with continuous TUI observation, durable local state, explicit upstream-adapter boundaries, and local control surfaces for supervised live agent sessions.

### Modified Capabilities
- `brain-launch-runtime`: Runtime session startup and control gain an optional supervisor-backed management mode that launches, discovers, and routes session control through the Houmao supervisor instead of talking only to the upstream backend directly.

## Impact

- New supervisor runtime and models under `src/houmao/agents/realm_controller/` for sidecar lifecycle, current-state persistence, watch loops, and adapter contracts
- New CAO-backed supervisor adapter that consumes CAO REST terminal inspection and control without requiring CAO source modifications
- Runtime launch/control entrypoints, session manifests, and status surfaces for supervised session start, inspect, send, interrupt, and stop behavior
- Session-root storage layout for supervisor state, histories, and attach metadata
- Tests for supervisor lifecycle, persistence, observation reduction, and CAO-backed adapter behavior
- Reference docs describing the new Houmao-managed supervisor model and its relationship to CAO and the existing gateway sidecar
