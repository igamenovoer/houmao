## 1. Publish Stable Gateway Attachability For Runtime-Owned Sessions

- [ ] 1.1 Extend runtime-owned tmux-backed session startup and resume flows to publish a stable secret-free gateway attach contract and expose it through `AGENTSYS_GATEWAY_ATTACH_PATH` plus `AGENTSYS_GATEWAY_ROOT`.
- [ ] 1.2 Extend blueprint loading and validation so optional `gateway.host` and `gateway.port` defaults are parsed and validated as attach-time listener defaults without turning blueprint presence into implicit gateway startup.
- [ ] 1.3 Persist the stable gateway attach metadata needed to rediscover the same gateway root and attach contract on resume.
- [ ] 1.4 Keep legacy non-gateway sessions valid, including sessions that publish no attach metadata at all.
- [ ] 1.5 Add unit coverage for attach-metadata publication, blueprint-default dormancy, stale or invalid attach pointers, and legacy-session compatibility.

## 2. Define The Versioned Gateway Protocol And Stable Versus Live Metadata Split

- [ ] 2.1 Add typed gateway boundary models for `GET /health`, `GET /v1/status`, and `POST /v1/requests`, with v1 public request kinds limited to `submit_prompt` and `interrupt`.
- [ ] 2.2 Define the stable protocol-versioned `state.json` schema, keep it aligned with `GET /v1/status`, and ensure state snapshots are written atomically.
- [ ] 2.3 Implement gateway-root bootstrap and durable storage layout for `protocol-version.txt`, `attach.json`, `desired-config.json`, `state.json`, `queue.sqlite`, `events.jsonl`, logs, and live-instance run state.
- [ ] 2.4 Distinguish stable attachability metadata from live gateway bindings, including lifecycle rules for publishing and clearing active host, port, state-path, and protocol-version pointers.
- [ ] 2.5 Add unit coverage for request-model validation, protocol-version handling, stable status-model reads, live-binding invalidation, and durable recovery of accepted queued work after gateway restart.

## 3. Add Independent Gateway Attach And Detach Lifecycle Control

- [ ] 3.1 Add explicit runtime lifecycle surfaces for launch-time auto-attach, attach-later, and detach of a gateway instance for a live session.
- [ ] 3.2 Resolve gateway host and port when a gateway instance is started, fail attach explicitly on bind conflict, and do not silently reselect a listener.
- [ ] 3.3 Ensure attach-later starts a gateway for a running session without restarting the managed agent and ensure detach stops the gateway without stopping the agent.
- [ ] 3.4 Add integration coverage for launch-time auto-attach, attach-later on an already-running session, graceful detach, bind-conflict failure, and stale-live-binding cleanup.

## 4. Implement The First Live Attach Backend And Gateway-Aware Control

- [ ] 4.1 Implement the first live gateway attach adapter for runtime-owned `cao_rest` sessions, while making unsupported-backend attach failures explicit for other tmux-backed backends.
- [ ] 4.2 Implement package-owned runtime gateway clients for `GET /health`, `GET /v1/status`, and `POST /v1/requests`, and use them for gateway-aware prompt-submission and interrupt flows when a live gateway instance is attached.
- [ ] 4.3 Keep legacy direct control paths working unchanged for sessions with no live gateway instance, including name-based resolution that finds attach metadata but no active gateway bindings.
- [ ] 4.4 Add unit and integration coverage for gateway attach discovery, live-binding publication, gateway-aware prompt submission, gateway-aware interrupt submission, unsupported-backend attach errors, and legacy direct-control fallback.

## 5. Align Docs And Verify The Change

- [ ] 5.1 Update proposal-aligned operator and developer docs so they describe stable attach metadata, launch-time auto-attach, attach-later or detach lifecycle flows, the distinction between gateway-capable and gateway-running sessions, stable status inspection via `state.json` or `GET /v1/status`, and v1 request submission through `POST /v1/requests`.
- [ ] 5.2 Run the relevant `pixi run format`, `pixi run lint`, `pixi run typecheck`, `pixi run test`, and `pixi run test-runtime` commands, then capture any follow-up artifact or implementation adjustments needed before the change is considered ready.
