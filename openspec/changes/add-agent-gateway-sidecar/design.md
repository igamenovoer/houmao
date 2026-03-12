## Context

This repo already has strong building blocks for live agent sessions: tmux-backed agent identities, persisted session manifests, runtime-managed environment publication, CAO-backed interactive terminals, and mailbox-oriented asynchronous content exchange. What it does not yet have is a per-agent control plane that sits close to one live session and arbitrates competing requests, normalizes backend status, schedules follow-up work, and records recovery decisions.

The user-facing constraint for this change is unusually specific and should drive the architecture: the gateway must not appear as a separate tmux window or pane. It must live in the same tmux window as the managed agent TUI, run silently as a background process, and avoid turning the session into a two-surface operator experience. At the same time, direct human interaction with the agent TUI remains a supported feature of the system, not an error case. That means the gateway cannot assume exclusive ownership of the terminal surface and must be designed to observe, tolerate, and reconcile human-driven TUI changes.

The first implementation only needs to cover localhost workflows. CAO remains a useful lower-level backend adapter, but the gateway contract should not be CAO-specific so it can survive backend replacement later.

```mermaid
flowchart LR
  A[Other agents or operator tools] --> B[Gateway submit or status surface]
  B --> C[Per-agent gateway root]
  C --> D[Gateway event loop]
  D --> E[Backend adapter]
  E --> F[Managed agent TUI]
  F --> G[Human direct interaction]
  D --> H[Queue and events]
  D --> I[State and heartbeats]
```

## Goals / Non-Goals

**Goals:**

- Add a per-agent gateway sidecar that runs in the same tmux window lifecycle as the managed agent TUI without introducing a separate visible tmux surface.
- Give each managed agent one durable local control plane for request admission, permission policy, priority ordering, queueing, timer-driven wakeups, health observation, and recovery.
- Preserve direct human TUI interaction as a supported workflow by treating it as concurrent operator activity that the gateway must tolerate rather than forbid.
- Normalize backend-specific state into gateway-owned status records that external tools can query without scraping raw tmux output directly.
- Store queued work and gateway events durably so gateway restart or transient failures do not lose outstanding requests.
- Keep the gateway contract transport-neutral and localhost-oriented so future distributed coordination can build on it later without redefining the per-agent model.

**Non-Goals:**

- Hard security isolation against a human with direct tmux access on the same host.
- Recovering a full tmux-session or tmux-server loss from inside the in-window sidecar itself.
- Distributed agent discovery, remote queue replication, or cross-host request delivery in v1.
- Replacing mailbox content transport; the gateway is a control plane, not a replacement for mailbox message storage.
- Requiring exclusive gateway ownership of the TUI surface or treating human direct interaction as protocol corruption.
- Designing a generic cluster-wide scheduler in this change.

## Decisions

### 1) The gateway runs as a silent same-window sidecar process launched before the foreground TUI

The gateway will be started in the same tmux window as the managed agent by a wrapper-style launch contract that backgrounds the gateway and then `exec`s the foreground TUI command. The steady-state operator experience remains a single visible TUI surface.

Conceptually, the launch shape is:

```sh
gatewayd --config /abs/path/gateway-bootstrap.json >>/abs/path/logs/gateway.log 2>&1 &
exec <managed-agent-foreground-command>
```

This structure matters for two reasons:

- there is no second visible tmux window or pane for operators to accidentally enter, and
- there is no idle shell prompt left behind during normal execution.

The sidecar must not read from stdin, print to the terminal, or rely on an interactive terminal UI of its own. All stdout and stderr are redirected to log files under the gateway root.

For CAO-backed sessions, the runtime-owned bootstrap path should wrap the provider launch so the gateway starts in the same tmux window before the provider TUI takes over. For other tmux-backed interactive surfaces, the same wrapper contract should be used when the runtime owns a persistent foreground command.

Rationale: this satisfies the operator UX constraint directly while preserving the shared lifecycle between the gateway and the managed terminal surface.

Alternatives considered:

- Separate tmux window or pane. Rejected because it creates an operator-visible surface the user explicitly does not want.
- Central broker process per runtime root. Rejected because it weakens per-agent locality and recovery independence.
- In-process gateway inside the agent TUI binary. Rejected because it couples policy and recovery to tool-specific internals and makes backend replacement harder.

### 2) Each gateway gets a durable per-agent root under the runtime root plus live tmux env pointers

The gateway state should live in a deterministic per-agent directory such as:

```text
<runtime_root>/gateways/<canonical-agent-identity>/
  protocol-version.txt
  bootstrap.json
  state.json
  queue.sqlite
  events.jsonl
  logs/
    gateway.log
  locks/
    gateway.lock
  run/
    gateway.pid
```

`state.json` is the current read-optimized status snapshot for external readers. `queue.sqlite` is the durable source of truth for queued requests, timers, execution leases, and completion records. `events.jsonl` is append-only audit history. `bootstrap.json` captures the runtime-provided launch configuration the sidecar needs after restart.

The runtime should publish live tmux session environment pointers for the addressed session, including at minimum:

- `AGENTSYS_GATEWAY_ROOT`
- `AGENTSYS_GATEWAY_STATE_PATH`
- `AGENTSYS_GATEWAY_PROTOCOL_VERSION`

The persisted session manifest should also record the gateway launch mode and root path so a resumed control path can discover the expected gateway layout even if live tmux env needs validation or refresh.

Rationale: external tooling needs a stable discovery path, and the gateway needs durable queue state that survives process restart.

Alternatives considered:

- Purely in-memory queue and status. Rejected because recovery and audit would be too weak.
- Tmux environment as the only source of gateway state. Rejected because env variables are useful pointers, not a durable event store.
- One shared runtime-wide gateway database. Rejected because it creates unnecessary coupling between otherwise independent agent sessions.

### 3) External callers interact through package-owned gateway commands, while SQLite is the internal persistence layer

The gateway protocol should be local and filesystem-backed, but external callers should not mutate `queue.sqlite` directly. Instead, the repo should expose package-owned submit and query surfaces that validate and serialize requests into the gateway store.

Requests should be stored as structured records with fields such as:

- `request_id`
- `sender_principal_id`
- `target_agent_identity`
- `kind`
- `priority`
- `not_before_utc`
- `expires_at_utc`
- `payload_json`
- `requires_submit_ready`
- `coalescing_key`
- `status`

Informational queries, such as gateway status inspection, should read `state.json` or a validated query path and should not enter the execution queue. Terminal-mutating work should always flow through the durable queue so the gateway can serialize it.

Rationale: the gateway needs a stable contract for multiple local writers without turning SQLite schema details into a public interface.

Alternatives considered:

- Raw file-drop request directories. Rejected because ordering, de-duplication, and update semantics become harder once priorities and retries are involved.
- Raw SQLite writes by any caller. Rejected because it freezes low-level schema details into the public control contract.
- Direct tmux or CAO calls from all orchestrators. Rejected because it reintroduces the race conditions this change exists to remove.

### 4) The status model separates gateway health, agent state, terminal surface state, and execution state

The gateway should publish a structured status snapshot that keeps these concerns separate:

- `gateway_state`: `booting | online | degraded | recovering | offline`
- `agent_state`: `idle | busy | waiting_input | awaiting_operator | error | unknown`
- `surface_state`: `submit_ready | modal | blocked | disconnected | unknown`
- `execution_state`: `idle | running | backoff | blocked`

It should also include supporting fields such as:

- `active_request_id`
- `queue_depth`
- `last_gateway_heartbeat_utc`
- `last_agent_observation_utc`
- `recovery_attempt_count`
- `last_error`

This separation is important because human interaction changes the surface frequently without necessarily implying that the gateway or agent is broken. For example, a human opening a slash-command menu should move `surface_state` out of `submit_ready` and pause queued injection, but it should not mark the gateway unhealthy.

Backend adapters should map CAO-native or shadow-parser evidence, headless runtime state, and tmux availability into this normalized status model. When the gateway cannot classify the surface safely, it should prefer `unknown` and avoid injection rather than guessing that the prompt is free.

Rationale: explicit separation makes the gateway robust to non-exclusive control of the TUI surface.

Alternatives considered:

- One flat `status` field like `busy` or `idle`. Rejected because it collapses health, control eligibility, and operator state into one ambiguous label.
- Treating any manual surface deviation as `error`. Rejected because direct human interaction is a supported feature, not misuse.

### 5) The gateway scheduler owns a single terminal-mutation slot and treats human activity as a first-class scheduling signal

Only one queued request at a time may hold the terminal-mutation lease for a given agent. The scheduler should order pending work by policy, priority, age, and eligibility while preserving single-writer semantics for terminal input.

Requests should divide into two broad classes:

- non-mutating reads, which can be served from gateway state without terminal injection, and
- terminal-mutating actions, which require the single active execution slot.

Low-value repeated work such as periodic `mail.check` should support coalescing so multiple pending checks collapse into one effective queued action. Timer-driven work should become ordinary queued requests rather than bypassing policy.

Human direct TUI interaction should not invalidate the queue. Instead:

- when the surface is not safely submit-ready, queued injection waits,
- when a human changes the surface mid-request, the gateway records the observation and reevaluates completion or retry policy,
- when the human resolves the blocking surface and the gateway sees a safe ready state again, queued work may continue.

The gateway should never assume that it may inject text merely because a request exists. Injection is allowed only when the backend adapter says the surface is eligible for that specific action.

Rationale: this keeps queue semantics stable while making human interaction a feature the scheduler understands rather than a source of silent corruption.

Alternatives considered:

- Optimistic concurrent sends with “last writer wins.” Rejected because it recreates the raw tmux race problem.
- Automatic interruption of human activity for high-priority gateway work. Rejected for v1 because it would make the operator experience brittle and surprising.

### 6) Recovery is conservative, backend-adapter-driven, and explicitly scoped below whole-session supervision

The gateway should own a bounded recovery ladder for failures inside the live agent surface:

1. refresh status and re-validate the latest observation,
2. wait or back off if the surface is merely non-ready or manually occupied,
3. attempt backend-native interruption or wakeup when policy allows,
4. restart the managed TUI using the runtime-owned backend adapter when the agent process is gone or unrecoverable,
5. move to `degraded` after the retry budget is exhausted.

Recovery must remain conservative because human interaction is allowed. The gateway should not forcibly inject control sequences into an unknown or operator-blocked surface unless the request type and policy explicitly permit that behavior.

Full tmux-session or tmux-server loss is out of scope for the same-window sidecar. If the whole tmux container disappears, an outer launcher or supervisor layer is responsible for re-establishing the session and then starting a fresh gateway from persisted runtime state.

Rationale: the sidecar can recover many agent-local failures, but it cannot be the recovery authority for the container it lives inside.

Alternatives considered:

- Aggressive automatic control-input recovery on any stall. Rejected because it would fight with valid human interaction and increase unintended terminal mutation.
- Making the gateway responsible for tmux-server resurrection. Rejected because that violates the failure-domain boundary created by same-window colocation.

### 7) Runtime integration is additive and should preserve non-gateway sessions

The runtime should treat gateway support as an additive session feature. New tmux-backed sessions that enable the gateway publish gateway pointers and launch the sidecar. Existing sessions without gateway support remain valid and resumable without backfilling a gateway requirement.

This design implies three integration points:

- session startup creates the gateway root, writes `bootstrap.json`, publishes tmux env pointers, and launches the same-window wrapper,
- session resume validates and republishes gateway pointers and consults gateway state when the session is gateway-enabled,
- control commands targeting a gateway-enabled session prefer gateway-mediated request submission over raw concurrent tmux mutation.

Rationale: this reduces rollout risk and keeps older manifests and sessions from becoming invalid immediately.

Alternatives considered:

- Make the gateway mandatory for all existing tmux-backed sessions immediately. Rejected because it complicates rollout and recovery for sessions created before the new contract exists.
- Hide the gateway entirely from runtime/session metadata. Rejected because discovery and debugging would be unnecessarily difficult.

## Risks / Trade-offs

- [Background sidecar accidentally writes into the visible terminal] -> Redirect all gateway stdout and stderr to log files, forbid stdin reads, and keep all terminal interaction behind backend adapters or tmux control primitives rather than direct console writes.
- [Human operators can bypass gateway policy by typing directly into the TUI] -> Define the gateway as the supported automation path rather than a hard local security boundary, observe surface changes explicitly, and log when direct interaction changes queue eligibility or request outcomes.
- [Same-window colocation prevents the gateway from surviving full tmux-session loss] -> Persist queue and status on disk, keep recovery of whole-session loss in an outer supervisor layer, and scope the gateway to agent-local recovery only.
- [Readiness classification may be wrong on complex terminal surfaces] -> Normalize backend signals conservatively, publish `unknown` when confidence is low, and refuse automatic injection on uncertain surfaces.
- [Durable queue storage adds schema and compatibility burden] -> Keep the external protocol at the package-owned command layer, version the gateway root with `protocol-version.txt`, and treat SQLite as an internal implementation detail.
- [Gateway restart can leave stale active-request state] -> Store execution leases durably with heartbeat timestamps, reconcile incomplete leases on startup, and move abandoned work back to pending or failed according to policy.

## Migration Plan

1. Add gateway-aware manifest and tmux environment publication in an additive way so older sessions remain valid.
2. Introduce gateway startup only for new tmux-backed sessions that opt into the feature or meet the rollout criteria chosen during implementation.
3. Keep existing direct runtime control paths available for sessions that are not gateway-enabled.
4. On rollback, stop launching the sidecar for new sessions and ignore gateway-specific metadata for existing sessions; preserved gateway roots remain inspectable and can be cleaned up out of band.
5. Defer any default-on rollout until status normalization and recovery behavior have been validated against real human-plus-automation interaction patterns.

## Open Questions

- Should the first implemented backend integration target only CAO-backed interactive sessions, or should it also cover other tmux-backed sessions that maintain a persistent foreground TUI?
- Do we want an explicit operator-facing “pause gateway queue” control in v1, or is observed surface state sufficient for the initial design?
- Which gateway request kinds should be first-class in v1 beyond generic prompt turns and mailbox-triggered work, and which should wait for follow-up changes?
