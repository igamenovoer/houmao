## 1. Gateway Live-Only Publish

- [x] 1.1 Update AG-UI capabilities so Houmao-published GUI events report non-resumable live-only delivery and client-owned caching responsibility.
- [x] 1.2 Change `POST /v1/ag-ui/connect` handling so `lastSeenEventId` is ignored for gateway replay while current state snapshot and future live events still work.
- [x] 1.3 Remove or bypass retained replay writes and reads for `/v1/ag-ui/events` published GUI batches.
- [x] 1.4 Update publish fanout responses so Houmao gateway publish reports `stored_count = 0` and `delivered_count` counts only live stream deliveries.
- [x] 1.5 Keep event validation, sequencing checks, size limits, and safe diagnostics for published event batches.
- [x] 1.6 Update gateway unit tests for live subscriber delivery, no-subscriber loss, non-resumable capabilities, and absence of replay after reconnect.

## 2. Workbench Watchers and Client Cache

- [x] 2.1 Add a watched-target registry keyed by durable discovered-agent address or manual AG-UI URL plus thread id.
- [x] 2.2 Add a watcher manager that owns background AG-UI connect streams independently from Dockview panes.
- [x] 2.3 Add a browser-owned AG-UI event cache with bounded retention for received watched-target events.
- [x] 2.4 Store target key, thread id, receive timestamp, local sequence, optional non-durable SSE frame id, and raw AG-UI event object for watched events.
- [x] 2.5 Exclude request bodies, forwarded props, credentials, passive-server response bodies, mailbox content, memory content, and raw terminal content from cached metadata.
- [x] 2.6 Rework pane rendering so panes initialize from cached events and subscribe to watcher live updates for the selected target.
- [x] 2.7 Remove pane-level `lastSeenEventId` replay behavior and reconnect watchers without gateway replay cursors.
- [x] 2.8 Add cache status and clear-cache behavior for global or per-target cache removal.

## 3. Workbench UI and Discovery

- [x] 3.1 Add watch, unwatch, and open-pane actions to the agent picker without coupling watch to pane creation.
- [x] 3.2 Display watched, connected, reconnecting, offline, and unwatched states in the picker or target controls.
- [x] 3.3 Preserve watched listeners when panes are closed, and stop listeners only through explicit unwatch or disconnect actions.
- [x] 3.4 Persist safe watched-target metadata across browser reload while keeping stream events out of localStorage.
- [x] 3.5 Ensure discovered-agent watchers resolve current gateways by agent id or unambiguous agent name through the passive server.
- [x] 3.6 Keep manual targets direct and prevent manual URL watchers from inferring Houmao agent identity.

## 4. Skills and Documentation

- [x] 4.1 Update `houmao-agent-ag-ui` skill guidance for live-only publish results, `stored_count = 0`, and `delivered_count = 0` retry guidance.
- [x] 4.2 Update `houmao-mgr internals ag-ui` publish helper output and help text so it does not claim durable delivery or GUI visibility when no stream receives the batch.
- [x] 4.3 Update workbench README and gateway AG-UI reference docs with watch/unwatch, client cache, and missed-event loss semantics.
- [x] 4.4 Update debug-agent documentation to state whether debug relay publishing follows live-only behavior or an explicit lab-only replay mode.

## 5. Verification

- [x] 5.1 Run focused gateway tests for AG-UI capabilities, connect, publish validation, live fanout, and no replay.
- [x] 5.2 Run workbench unit or component tests for watched-target registry, event cache retention, reducer replay from cache, and cache clearing.
- [x] 5.3 Run Playwright E2E proving a chart received while watched remains visible after pane close/reopen from client cache.
- [x] 5.4 Run Playwright E2E proving a chart published while unwatched is not recovered after reconnect.
- [x] 5.5 Run formatting, linting, typecheck, and the relevant unit test suite before marking the change complete.
