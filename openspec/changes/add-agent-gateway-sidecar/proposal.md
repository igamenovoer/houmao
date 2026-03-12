## Why

Current multi-agent control in this project is centered on direct runtime commands, direct tmux interaction, and backend-specific status surfaces. That is workable for simple operator-driven flows, but it does not give each live agent a durable per-agent control plane for admission, queueing, wakeups, heartbeats, and crash recovery.

We need that control plane now because agent sessions are becoming longer-lived and more collaborative. A per-agent gateway lets the system add policy, scheduling, and recovery without making CAO the architectural center, while still preserving a key feature of this system: humans can interact with the live TUI directly and the system remains coherent.

## What Changes

- Add a per-agent gateway sidecar that runs as a background process in the same tmux window and terminal lifecycle as the managed agent TUI, rather than in a separate visible tmux window.
- Resolve one effective gateway listener host and port at agent launch, with the host defaulting to `127.0.0.1` and optionally switching to `0.0.0.0` when explicitly configured, and with the port resolved from `--gateway-port`, `AGENTSYS_AGENT_GATEWAY_PORT`, optional blueprint configuration, or a system-selected free port when no explicit setting is supplied.
- Define an HTTP gateway API, implemented by a FastAPI sidecar bound by default on `127.0.0.1:<port>` and optionally on `0.0.0.0:<port>` when explicitly configured, for status queries, queued work submission, permission checks, priority ordering, wakeup triggers, timer-driven work, and recovery actions.
- Add a durable gateway state and queue store under the runtime root so concurrent senders can interact with one managed agent without racing through raw tmux input.
- Normalize backend-specific readiness and health signals into gateway-owned status axes such as gateway health, agent state, active work, queue depth, last heartbeat, and recovery state.
- Define gateway behavior so direct human interaction with the managed TUI remains a supported feature rather than a protocol violation; the gateway must tolerate and reconcile operator-driven TUI changes instead of assuming exclusive terminal ownership.
- Add recovery expectations for agent crash, stalled work, blocked-input states, and gateway restart, while explicitly scoping full tmux-session loss to an outer supervisor layer rather than the in-window sidecar itself.
- Fail fast when the resolved gateway port cannot be bound; port conflicts do not trigger silent port reselection and instead prevent the agent session from launching.
- Keep gateway v1 independent from the mailbox system; mailbox-triggered submission, mailbox-aware policy, and mailbox-specific bindings are deferred until the mailbox contract is mature enough for a follow-up integration.
- Keep the initial implementation backend-neutral and single-port-per-session, with default loopback binding and explicit all-interface opt-in, so future discovery, access control, or distributed coordination can layer on later without redefining the per-agent gateway contract.

## Capabilities

### New Capabilities
- `agent-gateway`: Per-agent same-window FastAPI HTTP gateway sidecar with resolved bind host and port, defaulting to `127.0.0.1:<resolved-port>` and optionally binding `0.0.0.0:<resolved-port>` when requested, plus durable queueing and logging, normalized status reporting, permission and priority policy, wakeup and timer handling, and recovery behavior that tolerates direct human TUI interaction.

### Modified Capabilities
- `brain-launch-runtime`: Session startup, resume, and control flows gain gateway-sidecar launch and shutdown behavior, launch-time gateway-host and gateway-port resolution from CLI, env, blueprint, or safe defaults, gateway runtime-root storage, gateway-related env publication, and runtime surfaces for interacting with a managed agent through the gateway instead of raw concurrent tmux mutation.
- `agent-identity`: Tmux-backed agent identity resolution gains gateway-related tmux environment pointers so control tooling can discover the active gateway host, port, state, and storage root for a named live session.
- `component-agent-construction`: Optional agent blueprints gain a secret-free gateway configuration surface that can declare default gateway host and port values for sessions launched from that blueprint.

## Impact

This change is expected to affect runtime session startup and shutdown, tmux session environment publication, persisted runtime state under the runtime root, agent control surfaces, operator workflows, optional blueprint configuration, and local recovery behavior. It will likely introduce a FastAPI HTTP gateway service per managed session with resolved bind host and port, defaulting to `127.0.0.1:<resolved-port>` and optionally exposing `0.0.0.0:<resolved-port>` when configured, gateway-local SQLite or equivalent durable queue state plus append-only event logging, launch-time `--gateway-host` and `--gateway-port` overrides, `AGENTSYS_AGENT_GATEWAY_HOST` and `AGENTSYS_AGENT_GATEWAY_PORT` env handling, optional blueprint-declared gateway host and port defaults, new gateway env bindings in tmux-backed sessions, backend-to-gateway status normalization over CAO and headless runtime signals, and explicit startup failure when the resolved gateway listener conflicts with another process. This revision does not require mailbox enablement, mailbox env bindings, or mailbox-triggered workflows for gateway-managed sessions.
