# Supervisor And Lifecycle

The server-owned tracker runs as one supervisor thread plus one watch worker per live known session. This logic lives in [`../../../../../src/houmao/server/tui/supervisor.py`](../../../../../src/houmao/server/tui/supervisor.py).

## Runtime Contract

The supervisor depends on a `TrackingRuntime` protocol implemented by `HoumaoServerService`.

The important runtime hooks are:

- `watch_poll_interval_seconds()`
- `load_live_known_sessions()`
- `ensure_known_session(record)`
- `poll_known_session(tracked_session_id)`
- `handle_poll_exception(tracked_session_id, exc)`
- `release_known_session(tracked_session_id)`

This keeps the thread orchestration in `tui/supervisor.py` while the actual registry, tracking, and route authority stay in `service.py`.

## Reconcile Loop

`TuiTrackingSupervisor._run()` repeatedly calls `_reconcile_once()` and then waits for either:

- the normal poll interval, or
- an out-of-band wakeup from `request_reconcile()`

The reconcile pass does four things:

1. Load the current live known-session map from `KnownSessionRegistry`.
2. Stop workers whose `tracked_session_id` is no longer present in the live set.
3. Stop dead workers for sessions that are still live so they can be recreated on the same pass.
4. Ensure tracker state exists for every live record and start workers that are missing.

When a tracked session leaves the live set, the supervisor also calls `release_known_session(tracked_session_id)`. In `HoumaoServerService`, that maps to `_forget_tracker(...)`, which evicts both the live tracker and any terminal alias bound to it.

That eviction step is what keeps `GET /houmao/terminals/{terminal_id}/state` from continuing to resolve through stale in-memory residue after tmux or registry authority has gone away.

## Worker Loop

`SessionWatchWorker` owns one background thread for one `tracked_session_id`.

Its loop is simple:

1. Call `poll_known_session(tracked_session_id)`.
2. If the runtime says `False`, exit.
3. Otherwise sleep until the next poll interval or until stop is requested.

In the current implementation, `poll_known_session()` returns `False` only when the tracked tmux session no longer exists. That means:

- TUI-down sessions remain eligible for future polling
- parse failures remain eligible for future polling
- unsupported-tool sessions remain eligible for future polling
- tmux loss ends the worker, and the next reconcile pass releases the stale in-memory authority if the session is no longer rediscovered

## Alias And Tracker Lifecycle

`HoumaoServerService` keeps two in-memory maps:

- `m_trackers`: `tracked_session_id -> LiveSessionTracker`
- `m_terminal_aliases`: `terminal_id -> tracked_session_id`

`ensure_known_session(record)` is responsible for keeping those maps coherent:

- create a new tracker if the session has not been seen before
- refresh tracker identity if the session already has a tracker
- remove stale aliases that still point at the same tracked session under an older terminal id
- bind the current terminal id alias to the tracked session

`release_known_session()` and the explicit delete handlers remove those mappings again.

The explicit delete flows are:

- `handle_deleted_terminal(terminal_id)`
- `handle_deleted_session(session_name)`

Both remove the registration directory, forget the in-memory tracker state, and wake the supervisor.

## Exception Hardening

The review hardening change made both thread layers resilient to unexpected exceptions.

### Worker-side failures

`SessionWatchWorker._run()` now catches any unexpected exception raised by `poll_known_session()`.

The recovery path is:

1. call `handle_poll_exception(tracked_session_id, exc)`
2. if that handler also fails, log the failure defensively
3. keep the worker alive for later polling

`HoumaoServerService.handle_poll_exception()` logs the exception and records an explicit probe/runtime error state into the tracker with:

- `transport_state="probe_error"`
- `process_state="probe_error"`
- `parse_status="probe_error"`
- `probe_error.kind="tracking_runtime_error"`

This keeps the failure visible in the live-state route instead of silently killing the worker.

### Supervisor-side failures

`TuiTrackingSupervisor._run()` also wraps `_reconcile_once()` in a catch-all guard. An unexpected reconcile failure is logged and the supervisor continues to the next wait/retry cycle instead of dying permanently.

This is important because reconcile is the mechanism that:

- admits new registrations
- releases dead sessions
- recreates dead workers

Without the guard, one unexpected exception could stall the whole watch plane until the server process restarted.

## Related Sources

- [`../../../../../src/houmao/server/tui/supervisor.py`](../../../../../src/houmao/server/tui/supervisor.py)
- [`../../../../../src/houmao/server/service.py`](../../../../../src/houmao/server/service.py)
- [`../../../../../src/houmao/server/tui/registry.py`](../../../../../src/houmao/server/tui/registry.py)
- [`../../../../../src/houmao/server/tui/tracking.py`](../../../../../src/houmao/server/tui/tracking.py)
