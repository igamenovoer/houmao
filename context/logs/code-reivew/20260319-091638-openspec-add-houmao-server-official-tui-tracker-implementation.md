# Code Review: `add-houmao-server-official-tui-tracker` implementation

- Scope: implementation under `src/houmao/server/`, `src/houmao/server/tui/`, and the related `tmux_runtime` changes
- Change artifact: `openspec/changes/add-houmao-server-official-tui-tracker`
- Review mode: read-only
- Online references used: none

## Summary

The main architecture is in the right direction: the watch path is now server-owned, the CAO dependency is removed from parse/state tracking, and the targeted tests cover the happy path well.

The important problems are around lifecycle hardening and trust boundaries rather than parser logic:

1. `session_name` is used as a filesystem path without containment checks.
2. Background tracking threads die on the first unexpected exception.
3. Dead sessions are not evicted from the in-memory alias/tracker maps.
4. The immediate post-registration tracker drops tmux window identity and can watch the wrong pane.

## Findings

### 1. High: `register_launch()` allows path traversal outside the server-owned `sessions/` root

The registration route accepts raw `session_name` input from `/houmao/launches/register` and only validates that it is non-blank. It is then used to build a filesystem path with `.resolve()` and no containment check before `mkdir()` and `write_text()`. The delete path uses the same pattern with `shutil.rmtree()`.

- Entry point: `src/houmao/server/app.py:201`
- Missing validation: `src/houmao/server/models.py:250`
- Unsafe write path: `src/houmao/server/service.py:326`
- Unsafe delete path: `src/houmao/server/service.py:629`

Concrete reproduction I verified locally:

```python
service.register_launch(
    HoumaoRegisterLaunchRequest(
        session_name="../../escaped",
        terminal_id="abcd1234",
        tool="codex",
    )
)
```

This created `registration.json` at:

```text
/tmp/houmao-review-path/houmao_servers/escaped/registration.json
```

instead of staying under:

```text
/tmp/houmao-review-path/houmao_servers/127.0.0.1-9889/sessions/
```

That is a straightforward containment bug. At minimum, `session_name` needs path-safe validation and the resolved target must be checked to remain under `sessions_dir` before writing or deleting.

### 2. High: one unexpected exception permanently kills either a watch worker or the supervisor

Both background loops run without any exception guard:

- Worker loop: `src/houmao/server/tui/supervisor.py:59`
- Supervisor loop: `src/houmao/server/tui/supervisor.py:109`

The supervisor immediately calls `load_live_known_sessions()` with no protection:

- `src/houmao/server/tui/supervisor.py:115`
- `src/houmao/server/tui/registry.py:63`

That means a transient tmux failure, registry I/O problem, or any bug thrown out of `poll_known_session()` tears down the thread permanently. I verified both failure modes with small repros: after one raised exception, `m_thread.is_alive()` becomes `False`.

This is especially risky here because the design promises continuous background tracking. With the current implementation, one bad cycle can silently disable tracking for one session or for the whole server lifetime.

The fix should be operational rather than architectural:

- catch and record/log unexpected exceptions inside both loops
- keep the supervisor alive across reconcile failures
- decide whether worker failures should retry, back off, or mark state as `probe_error`

### 3. Medium: dead sessions are removed from `m_workers`, but not from `m_trackers` or `m_terminal_aliases`

When tmux disappears, `poll_known_session()` records `tmux_missing` and returns `False`:

- `src/houmao/server/service.py:401`

The supervisor then drops only the worker object:

- `src/houmao/server/tui/supervisor.py:120`

But the service keeps the tracker and alias mapping unless an explicit delete route is later called:

- alias lookup short-circuits on stale memory: `src/houmao/server/service.py:591`
- eviction helper exists but is not used in this path: `src/houmao/server/service.py:620`

I verified the effect locally: after reconcile with no live tmux session, `m_terminal_aliases` still contained `{"abcd1234": "cao-gpu"}`, `m_trackers` still contained `cao-gpu`, and `terminal_state("abcd1234")` still returned the cached state.

That creates two problems:

- stale terminal ids remain queryable even though the session is no longer in the live known-session registry
- memory grows with session churn until restart or explicit delete

If the intended contract is “live tmux-backed sessions only,” tracker/alias eviction needs to be tied to the same lifecycle that stops the worker.

### 4. Medium: the immediate registration path drops tmux window identity and may watch the wrong pane

The design calls out tracked tmux session identity with optional window coordinates, and the registry loader can recover `tmux_window_name` from manifest metadata:

- manifest enrichment: `src/houmao/server/tui/registry.py:120`

But the registration request model has no `tmux_window_name` field:

- `src/houmao/server/models.py:250`

and the immediate dormant-tracker creation hardcodes `tmux_window_name=None`:

- `src/houmao/server/service.py:658`

Once that happens, pane resolution falls back to “prefer the active pane” for the whole session:

- `src/houmao/server/tui/transport.py:25`

So a newly registered live session can be tracked against whichever pane happens to be active, not the intended tool pane, until a later reconcile happens to enrich it from the manifest. In a multi-window or multi-pane tmux session, that is enough to parse the wrong surface.

The current tests do not cover this case.

## Verification

I ran:

```text
pixi run pytest tests/unit/server/test_service.py tests/unit/server/test_tui_parser_and_tracking.py tests/unit/server/test_tui_process.py tests/unit/server/test_tui_supervisor.py tests/unit/server/test_app_contracts.py
pixi run mypy src/houmao/server src/houmao/agents/realm_controller/backends/tmux_runtime.py
pixi run ruff check src/houmao/server src/houmao/agents/realm_controller/backends/tmux_runtime.py tests/unit/server
```

All of those passed.

I also used small one-off `pixi run python - <<'PY' ... PY` repros to confirm:

- the `session_name='../../escaped'` path traversal write
- supervisor death after a raised exception in `load_live_known_sessions()`
- worker death after a raised exception in `poll_known_session()`
- stale alias/tracker retention after reconcile removes the worker

## Assumptions

- I am assuming `/houmao/launches/register` is not guaranteed to be callable only by fully trusted in-process code. If it is strictly internal and never exposed to less-trusted callers, the path-traversal issue becomes an operational-hardening issue rather than an externally reachable security issue, but it is still a real bug.
- I am assuming the intended authority is “live known sessions,” not “keep dead sessions queryable forever after tmux exit.” If the latter is intentional, it should be documented explicitly because it diverges from how the supervisor and registry lifecycle are currently described.
