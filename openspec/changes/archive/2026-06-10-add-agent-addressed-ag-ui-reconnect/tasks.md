## 1. Registry and Passive Resolution

- [x] 1.1 Add or expose secret-free known-agent address resolution by `agent_id` and friendly `agent_name`, distinct from live gateway presence.
- [x] 1.2 Preserve current live-agent listing behavior while adding known/offline, ambiguous, live-without-gateway, and live-with-gateway resolution outcomes.
- [x] 1.3 Add passive-server response models and read-only route coverage for agent-address AG-UI resolution.
- [x] 1.4 Add tests for known offline agent resolution, ambiguous name resolution, and live gateway coordinate resolution.

## 2. Gateway Replay Contract

- [x] 2.1 Add durable SSE event id assignment for replayable AG-UI events, scoped to agent and thread.
- [x] 2.2 Add bounded per-thread event storage for accepted `/v1/ag-ui/events` batches under gateway-owned state.
- [x] 2.3 Update `/v1/ag-ui/connect` to honor valid `lastSeenEventId` cursors and replay retained events before live fanout.
- [x] 2.4 Update cursor fallback behavior for expired, malformed, unknown, or mismatched cursors to emit a fresh state snapshot without claiming full replay.
- [x] 2.5 Update capabilities and Houmao metadata to advertise resumable replay only when event-log replay is enabled.
- [x] 2.6 Update publish responses and client models to include accepted, stored, and delivered counts.
- [x] 2.7 Add gateway unit and integration tests for replay, storage without live subscribers, live fanout, cursor fallback, and secret-free diagnostics.

## 3. Workbench Target Model

- [x] 3.1 Extend workbench target storage so discovered targets persist durable agent address metadata and treat latest gateway URL as volatile.
- [x] 3.2 Update the agent picker to retarget panes to known offline agents as waiting targets, while preserving errors for unknown or ambiguous agent references.
- [x] 3.3 Keep manual AG-UI URL targets first-class and prevent manual targets from silently switching into agent-address resolution.
- [x] 3.4 Add storage migration or tolerant loading for existing discovered targets that only have a persisted direct gateway URL.

## 4. Workbench Reconnect Runtime

- [x] 4.1 Implement the discovered-pane resolve/connect/reconnect state machine with bounded backoff and visible offline, waiting, reconnecting, and connected states.
- [x] 4.2 Re-resolve current gateway coordinates before each discovered-pane connect attempt and after stream failure.
- [x] 4.3 Track latest applied SSE event id per pane/thread and send `lastSeenEventId` when reconnecting to a resumable gateway.
- [x] 4.4 Deduplicate replayed SSE frames by event id while preserving existing AG-UI reducer behavior for streams without ids.
- [x] 4.5 Ensure reconnect, disconnect, pane close, and retarget operations never send Houmao lifecycle control requests.

## 5. Agent Guidance and Documentation

- [x] 5.1 Update the `houmao-agent-ag-ui` system skill to explain durable agent addressing and volatile gateway coordinates.
- [x] 5.2 Update publish guidance so agents interpret `accepted_count`, `stored_count`, and `delivered_count` correctly.
- [x] 5.3 Update workbench documentation to describe GUI-first, agent-first, gateway-restart, and manual direct-URL validation flows.

## 6. Verification

- [x] 6.1 Run `pixi run test` for Python unit coverage touched by registry, passive server, gateway, and AG-UI models.
- [x] 6.2 Run focused integration tests for per-agent AG-UI gateway replay and passive-server resolution.
- [x] 6.3 Run `bun run typecheck` and `bun run build` in `apps/ag-ui-workbench`.
- [x] 6.4 Run workbench Playwright E2E covering GUI-first wait, agent gateway restart, cursor replay, and manual direct target fallback.
- [x] 6.5 Run `openspec validate add-agent-addressed-ag-ui-reconnect --strict`.
