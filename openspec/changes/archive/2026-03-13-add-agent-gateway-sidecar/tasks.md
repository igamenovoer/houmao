## 1. Publish Stable Gateway Attachability For Runtime-Owned Sessions

- [x] 1.1 Extend runtime-owned tmux-backed session startup and resume flows so newly started runtime-owned tmux sessions publish gateway capability by default through one strict versioned secret-free gateway attach contract exposed via both `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`, with required shared core fields plus optional runtime-owned fields and the gateway rooted under the session's own runtime directory.
- [x] 1.2 Extend blueprint loading and validation so optional `gateway.host` and `gateway.port` defaults are parsed through a strict typed schema, reject unknown top-level and nested gateway fields explicitly, and do not turn blueprint presence into implicit gateway startup.
- [x] 1.3 Reshape runtime-owned session storage to `<runtime_root>/sessions/<backend>/<session_id>/manifest.json` plus a nested `<session-root>/gateway/` directory, and persist the stable gateway attach metadata needed to rediscover that session-owned gateway root and attach contract on resume.
- [x] 1.4 Keep legacy non-gateway sessions valid, including sessions that publish no attach metadata at all.
- [x] 1.5 Add unit coverage for attach-metadata publication, strict attach-contract validation, blueprint-default dormancy, rejection of unknown blueprint fields, stale or invalid attach pointers, and legacy-session compatibility.

## 2. Define The Versioned Gateway Protocol And Stable Versus Live Metadata Split

- [x] 2.1 Add typed gateway boundary models for `GET /health`, `GET /v1/status`, and `POST /v1/requests`, with v1 public request kinds limited to `submit_prompt` and `interrupt`, `/health` staying gateway-local, and status explicitly separating gateway health from managed-agent connectivity, recovery, and request-admission state.
- [x] 2.2 Define the stable protocol-versioned `state.json` schema, keep it aligned with `GET /v1/status`, ensure state snapshots are written atomically, seed offline or not-attached state during capability publication plus graceful detach, and carry stable session identity plus current managed-agent instance epoch when a gateway is attached.
- [x] 2.3 Implement gateway-root bootstrap and durable storage layout for `protocol-version.txt`, `attach.json`, `desired-config.json`, `state.json`, `queue.sqlite`, `events.jsonl`, logs, and live-instance run state, with runtime-owned gateway assets living under the nested `gateway/` directory inside each session root and `attach.json` living under `AGENTSYS_GATEWAY_ROOT`.
- [x] 2.4 Distinguish stable attachability metadata from live gateway bindings, including lifecycle rules for publishing and clearing active host, port, state-path, and protocol-version pointers.
- [x] 2.5 Add unit coverage for request-model validation, protocol-version handling, health-versus-upstream-availability separation, stable status-model reads, live-binding invalidation, durable recovery of accepted queued work after gateway restart, and non-replay behavior when a managed-agent instance is replaced.

## 3. Add Independent Gateway Attach And Detach Lifecycle Control

- [x] 3.1 Add explicit runtime lifecycle surfaces for launch-time auto-attach, attach-later, and detach of a gateway instance for a live session, with launch-time auto-attach returning a structured partial-start failure while keeping the agent session running if the gateway attach step fails after session startup.
- [x] 3.2 Resolve gateway host and port when a gateway instance is started, fail attach explicitly on bind conflict, do not silently reselect a listener, and persist the first successful resolved listener as the desired listener reused on later restarts unless explicitly overridden.
- [x] 3.3 Ensure attach-later starts a gateway for a running session without restarting the managed agent, ensure detach stops the gateway without stopping the agent, and ensure runtime-owned `stop-session` also stops any live attached gateway while restoring offline or not-attached gateway state.
- [x] 3.4 Add integration coverage for launch-time auto-attach partial-start failure, attach-later on an already-running session, graceful detach, runtime-owned stop-session teardown of a live gateway, bind-conflict failure, and stale-live-binding cleanup.

## 4. Implement The First Live Attach Backend And Gateway-Aware Control

- [x] 4.1 Implement the first live gateway attach adapter for runtime-owned `cao_rest` sessions, while making unsupported-backend attach failures explicit for other tmux-backed backends.
- [x] 4.2 Implement package-owned runtime gateway clients for `GET /health`, `GET /v1/status`, and `POST /v1/requests`, validate live gateway bindings structurally with `GET /health` as the authoritative liveness check, surface explicit `409` or `503` recovery or admission-blocking outcomes, and use those clients for gateway-aware prompt-submission and interrupt flows when a live gateway instance is attached.
- [x] 4.3 Keep legacy direct control paths working unchanged for sessions with no live gateway instance, including name-based resolution that finds attach metadata but no active gateway bindings, while making gateway-aware control commands fail explicitly instead of auto-attaching a gateway implicitly.
- [x] 4.4 Add unit and integration coverage for gateway attach discovery, live-binding publication, gateway-aware prompt submission, gateway-aware interrupt submission, unsupported-backend attach errors, bounded managed-agent recovery, replacement-instance admission blocking, and legacy direct-control fallback.

## 5. Align Docs And Verify The Change

- [x] 5.1 Update proposal-aligned operator and developer docs so they describe default attachability publication for new runtime-owned tmux sessions, the session-root-first runtime layout with a nested `gateway/` subdirectory, required stable attach pointers, launch-time auto-attach, attach-later or detach lifecycle flows, offline seeded status inspection via `state.json` or `GET /v1/status`, the distinction between gateway health and managed-agent recovery state, no implicit auto-attach from gateway-aware control commands, and v1 request submission through `POST /v1/requests`.
- [x] 5.2 Run the relevant `pixi run format`, `pixi run lint`, `pixi run typecheck`, `pixi run test`, and `pixi run test-runtime` commands, then capture any follow-up artifact or implementation adjustments needed before the change is considered ready.
