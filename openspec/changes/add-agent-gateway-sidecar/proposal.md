## Why

Current multi-agent control in this project is centered on direct runtime commands, direct tmux interaction, and backend-specific status surfaces. That is workable for simple operator-driven flows, but it does not give each live agent a durable per-agent control plane for admission, queueing, wakeups, heartbeats, and crash recovery.

We need that control plane now because agent sessions are becoming longer-lived and more collaborative. A per-agent gateway lets the system add policy, scheduling, and recovery without making CAO the architectural center, while still preserving a key feature of this system: humans can interact with the live TUI directly and the system remains coherent.

## What Changes

- Add a per-agent gateway sidecar that runs as a background process in the same tmux window and terminal lifecycle as the managed agent TUI, rather than in a separate visible tmux window.
- Define a local gateway protocol for status queries, queued work submission, permission checks, priority ordering, wakeup triggers, timer-driven work, and recovery actions.
- Add a durable gateway state and queue store under the runtime root so concurrent senders can interact with one managed agent without racing through raw tmux input.
- Normalize backend-specific readiness and health signals into gateway-owned status axes such as gateway health, agent state, active work, queue depth, last heartbeat, and recovery state.
- Define gateway behavior so direct human interaction with the managed TUI remains a supported feature rather than a protocol violation; the gateway must tolerate and reconcile operator-driven TUI changes instead of assuming exclusive terminal ownership.
- Add recovery expectations for agent crash, stalled work, blocked-input states, and gateway restart, while explicitly scoping full tmux-session loss to an outer supervisor layer rather than the in-window sidecar itself.
- Keep the initial implementation localhost-only and transport-neutral enough that future cross-host discovery or distributed coordination can layer on later without redefining the per-agent gateway contract.

## Capabilities

### New Capabilities
- `agent-gateway`: Per-agent same-window gateway sidecar protocol, durable queueing and logging, normalized status reporting, permission and priority policy, wakeup and timer handling, and recovery behavior that tolerates direct human TUI interaction.

### Modified Capabilities
- `brain-launch-runtime`: Session startup, resume, and control flows gain gateway-sidecar launch and shutdown behavior, gateway runtime-root storage, gateway-related env publication, and runtime surfaces for interacting with a managed agent through the gateway instead of raw concurrent tmux mutation.
- `agent-identity`: Tmux-backed agent identity resolution gains gateway-related tmux environment pointers so control tooling can discover the active gateway state and storage root for a named live session.

## Impact

This change is expected to affect runtime session startup and shutdown, tmux session environment publication, persisted runtime state under the runtime root, agent control surfaces, operator workflows, and local recovery behavior. It will likely introduce gateway-local SQLite or equivalent durable queue state plus append-only event logging, new gateway env bindings in tmux-backed sessions, backend-to-gateway status normalization over CAO and headless runtime signals, and new documentation describing the supported boundary between gateway-mediated control and direct human TUI interaction.
