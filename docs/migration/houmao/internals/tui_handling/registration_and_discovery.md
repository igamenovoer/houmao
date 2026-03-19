# Registration And Discovery

`houmao-server` does not discover arbitrary tmux sessions. The watch plane is seeded from server-owned registration records and then filtered against current tmux liveness.

## Registration Route

The entrypoint is `POST /houmao/launches/register` in [`../../../../../src/houmao/server/app.py`](../../../../../src/houmao/server/app.py). The payload model is `HoumaoRegisterLaunchRequest` in [`../../../../../src/houmao/server/models.py`](../../../../../src/houmao/server/models.py).

Important request fields are:

- `session_name`: the server-owned tracked session key
- `tool`: parser/process selection key
- `terminal_id`: optional compatibility terminal id; if absent, the server resolves it from the child CAO session view
- `manifest_path` and `session_root`: optional runtime-owned artifact references
- `agent_name` and `agent_id`: optional compatibility metadata
- `tmux_session_name`: optional explicit tmux session name; defaults to `session_name` later if omitted
- `tmux_window_name`: optional explicit tmux window identity

`register_launch()` in [`../../../../../src/houmao/server/service.py`](../../../../../src/houmao/server/service.py) performs the following steps:

1. Validate `session_name` with `_validated_registration_session_name()`.
2. If `terminal_id` is absent, query the child CAO-compatible surface for `/sessions/{session_name}/terminals` and take the first returned terminal id.
3. Validate that `/terminals/{terminal_id}` returns a valid CAO terminal payload.
4. Resolve the registration storage directory with `_registration_dir_for_session_name(..., strict=True)`.
5. Persist the normalized request as `registration.json`.
6. Create or refresh an in-memory dormant tracker immediately with `_ensure_tracker_for_registered_launch()`.
7. Wake the supervisor so the background reconcile pass can admit or refresh the worker set.

## Registration Storage And Containment

Registration records are stored under the server-owned sessions root:

```text
<server-root>/sessions/<session_name>/registration.json
```

The hardening change made `session_name` a validated storage key rather than a raw path fragment.

The current safety rules are:

- the identifier must be non-empty after trimming
- the identifier cannot be `.` or `..`
- the identifier cannot contain `/`, `\\`, or NUL
- the resolved registration directory must still be under the configured `sessions/` root

That same containment logic is used for both writes and cleanup paths, so registration creation and later deletion use the same server-owned namespace rules.

## Immediate Admission Versus Rediscovery

There are two closely related admission paths.

### Immediate registration-seeded admission

`_ensure_tracker_for_registered_launch()` converts the just-persisted request into a `KnownSessionRecord` by calling `known_session_record_from_registration(..., allow_shared_registry_enrichment=False)`.

This path is intentionally narrow:

- it does not consult the shared live-agent registry
- it does use manifest enrichment when `manifest_path` is present
- it preserves `tmux_window_name` immediately so the first poll can target the intended tmux window instead of defaulting to whichever pane is active

This is the path that removed the old wrong-pane race during the first polling cycles after registration.

### Supervisor rediscovery

`KnownSessionRegistry.load_live_sessions()` in [`../../../../../src/houmao/server/tui/registry.py`](../../../../../src/houmao/server/tui/registry.py) rebuilds the live known-session set by scanning:

```text
<sessions-dir>/*/registration.json
```

For each file it:

1. parses the JSON into `HoumaoRegisterLaunchRequest`
2. normalizes the record with `known_session_record_from_registration(...)`
3. drops the record if required identity is missing or if the tmux session is not currently live

This means the watch plane is rebuilt from current server-owned registrations plus current tmux existence, not from historical tracker output files.

## Metadata Enrichment Rules

`known_session_record_from_registration()` is the main normalization step. Its output is `KnownSessionRecord`, which later converts to `HoumaoTrackedSessionIdentity`.

Normalization and enrichment rules are:

- `tracked_session_id` is the registration `session_name`
- `tmux_session_name` defaults to `registration.tmux_session_name` or `registration.session_name`
- `terminal_id` is required by the time admission finishes
- when `allow_shared_registry_enrichment=True`, shared live-agent registry records may fill missing `manifest_path`, `session_root`, `agent_name`, `agent_id`, and `tmux_session_name`
- when `manifest_path` points to a readable manifest, manifest metadata may fill `terminal_id`, `tmux_window_name`, `tmux_session_name`, `tool`, and `session_root`

Manifest enrichment currently looks in the runtime payload for:

- `backend_state.tmux_session_name`
- `houmao_server.terminal_id`
- `houmao_server.tmux_window_name`
- `houmao_server.session_name`
- `cao.terminal_id`
- `cao.tmux_window_name`
- `cao.session_name`

The manifest is also used to recover the runtime-owned session root from the manifest path.

## Live-Admission Rules

A normalized registration is admitted into the live known-session set only when:

- `terminal_id` is known and non-blank
- the tmux session is currently live when rediscovery is running with a live tmux set

This is why a registration can exist on disk but still not appear in the active worker set: the registration seed is durable enough to rebuild from later, but live admission still requires the tmux-backed session to exist now.

## Related Sources

- [`../../../../../src/houmao/server/app.py`](../../../../../src/houmao/server/app.py)
- [`../../../../../src/houmao/server/service.py`](../../../../../src/houmao/server/service.py)
- [`../../../../../src/houmao/server/tui/registry.py`](../../../../../src/houmao/server/tui/registry.py)
- [`../../../../../src/houmao/server/models.py`](../../../../../src/houmao/server/models.py)
