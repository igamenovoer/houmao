## Context

`houmao-mgr agents gateway ...` is already the supported operator surface for live gateway lifecycle, prompt admission, raw control input, and notifier control, but the raw gateway-owned TUI tracking routes remain effectively HTTP-only. Operators can read curated managed-agent detail through `agents show`, but that is a different abstraction: it is transport-neutral and intentionally not the exact raw gateway tracking surface.

Today the direct gateway exposes `GET /v1/control/tui/state`, `GET /v1/control/tui/history`, and `POST /v1/control/tui/note-prompt`, but the pair-owned managed-agent API and passive-server proxy family do not expose corresponding `/houmao/agents/{agent_ref}/gateway/tui/*` routes. That forces any CLI surface that wants exact gateway-owned tracking state to either discover the gateway listener directly or special-case local-only control paths, both of which cut across the current pair boundary.

The shared tracker already keeps bounded in-memory transition history, but that is not the same thing as a recent snapshot history suitable for exact TUI-state inspection. For the new CLI surface we want recent raw tracked snapshots, held only in memory, capped at 1000 entries, and configured internally in Python rather than as a user-facing knob.

## Goals / Non-Goals

**Goals:**
- Expose raw gateway-owned TUI tracking through `houmao-mgr agents gateway tui ...`.
- Preserve the existing meaning of `agents gateway status` as gateway lifecycle and health, not parser state.
- Support the new TUI commands through the same pair-authority boundary as the rest of `agents gateway`, without requiring direct gateway host or port discovery.
- Add a bounded in-memory snapshot history with a maximum retained length of 1000 entries per tracked session.
- Keep local resumed-controller and pair-managed flows coherent under the same CLI subtree.

**Non-Goals:**
- Introduce durable on-disk TUI snapshot history.
- Replace coarse managed-agent `/history` or terminal `/history` contracts.
- Add server-push, websocket, or streaming watch transport in this change.
- Expose retention tuning as a public CLI flag, environment variable, or API field.

## Decisions

### 1. Add a dedicated `agents gateway tui` CLI subtree

The CLI will grow a new subgroup:

- `houmao-mgr agents gateway tui state`
- `houmao-mgr agents gateway tui history`
- `houmao-mgr agents gateway tui watch`
- `houmao-mgr agents gateway tui note-prompt`

Each command will reuse the same managed-agent selector and current-session targeting rules as the rest of `agents gateway`.

Rationale:
- This keeps raw gateway-owned TUI inspection grouped under the gateway namespace instead of overloading transport-neutral `agents state` or `agents show`.
- It preserves the current meaning of `agents gateway status`.
- It provides a stable place to grow raw gateway-owned inspection without mixing it with mailbox or request-admission commands.

Alternatives considered:
- Extend `agents gateway status` with parser fields. Rejected because it mixes gateway process health with raw tracked TUI state.
- Add more fields to `agents show`. Rejected because `show` is a curated managed-agent view, not the raw gateway-owned tracker surface.
- Flatten commands as `agents gateway tui-state` and `tui-history`. Rejected because a nested subtree matches the existing command organization better.

### 2. Add pair-owned managed-agent gateway TUI proxy routes

`houmao-server` and `houmao-passive-server` will gain managed-agent proxy routes for:

- `GET /houmao/agents/{agent_ref}/gateway/tui/state`
- `GET /houmao/agents/{agent_ref}/gateway/tui/history`
- `POST /houmao/agents/{agent_ref}/gateway/tui/note-prompt`

The CLI will call those pair-owned routes whenever it is operating through a pair client. Local resumed-controller paths will continue to resolve the attached gateway locally and call the direct gateway client.

Rationale:
- This preserves the current pair boundary: callers address managed-agent identities, not gateway listener coordinates.
- It keeps active/passive pair authorities symmetric with the rest of the `agents gateway` surface.
- It avoids inventing a second direct tmux-backed tracker path inside the CLI.

Alternatives considered:
- Discover the gateway host and port from `gateway status` and call the listener directly. Rejected because it leaks transport-private topology into the CLI and breaks the pair-owned model.
- Restrict the new CLI commands to local-only resumed controller paths. Rejected because that would make pair-managed sessions second-class and inconsistent with the rest of `agents gateway`.

### 3. Make `tui history` a bounded snapshot-history surface

The gateway-owned TUI history surface will return recent tracked snapshots, not only coarse transition summaries. The implementation will add a dedicated in-memory ring buffer owned by the active tracker. The buffer will retain at most 1000 snapshots per tracked session, controlled by an internal Python constant or constructor argument and not exposed to users yet.

The existing `recent_transitions` data remains useful and stays part of current-state diagnostics, but it is not sufficient for exact historical tracker inspection. Snapshot history and transition history therefore serve different purposes:

- `recent_transitions`: compact change summaries attached to current state
- `tui history`: recent raw tracked snapshots for inspection

To avoid compounding memory growth, the stored history entries will use a dedicated lightweight snapshot-entry model rather than recursively storing full state objects that themselves embed the entire recent-transition list.

Rationale:
- The user-facing need is to inspect recent exact tracked states, not only human summaries of changes.
- Keeping the buffer in memory only matches the existing TUI tracking posture and avoids inventing another durable artifact family.
- A hard cap of 1000 entries keeps memory bounded while leaving enough room for short-horizon debugging.

Alternatives considered:
- Reuse transition history for `tui history`. Rejected because it loses the actual tracked-surface payloads that operators want to inspect.
- Persist snapshot history to SQLite or JSONL. Rejected because the request explicitly prefers a bounded in-memory buffer and the system does not need another durable audit surface here.
- Reuse full `HoumaoTerminalStateResponse` objects in the ring buffer. Rejected because nested `recent_transitions` duplication would inflate memory unnecessarily.

### 4. Implement `watch` as CLI-side polling over `tui state`

`houmao-mgr agents gateway tui watch` will be a client-side polling command. It will repeatedly call the same state path used by `tui state` on a configurable polling interval, with the initial default encoded in the CLI implementation.

Rationale:
- This is the smallest additive change and does not require a streaming server protocol.
- It keeps the gateway and pair APIs synchronous and simple.
- It aligns with the existing operational model where live tracked state is already polled.

Alternatives considered:
- Add websocket or SSE streaming routes. Rejected as unnecessary complexity for the current need.
- Make `watch` consume history deltas instead of state polling. Rejected because state polling is simpler and yields the exact current surface each cycle.

## Risks / Trade-offs

- [Memory growth from snapshot history] → Keep a strict per-session cap of 1000 entries and use lightweight snapshot-entry models rather than full recursive state objects.
- [Terminology collision with existing `/history` surfaces] → Document clearly that `agents gateway tui history` is raw gateway-owned snapshot history, not coarse managed-agent `/history` and not terminal transition history.
- [Route-family sprawl across gateway, server, and passive-server layers] → Reuse existing gateway proxy patterns and shared client abstractions instead of inventing custom control paths.
- [Watch output may be noisy for humans] → Keep `watch` as a thin polling surface first; richer rendering can be added later without changing the transport model.
- [Changing direct gateway `tui history` semantics may surprise existing internal consumers] → Treat this as an intentional unstable-development contract update and update the shared client/model layer together.

## Migration Plan

1. Add shared models for gateway TUI snapshot-history responses and tracker snapshot entries.
2. Extend the active tracker implementation to retain bounded recent snapshots with an internal default max of 1000.
3. Update direct gateway routes and client methods for TUI state, history, and prompt-note calls.
4. Add managed-agent gateway TUI proxy routes and pair-client methods in `houmao-server`.
5. Add matching passive-server proxy routes and client methods.
6. Add the `houmao-mgr agents gateway tui ...` command subtree and wire local and pair-backed execution paths.
7. Update docs and tests for CLI help, pair proxies, local current-session targeting, and bounded snapshot retention.

Rollback is straightforward because the change is additive at the CLI and route-family level. If necessary, the new CLI subgroup and proxy routes can be removed without data migration because no durable snapshot store is introduced.

## Open Questions

None for the proposal phase. The history cap is fixed at 1000 for now and remains an internal implementation setting until a later change chooses to expose retention tuning publicly.
