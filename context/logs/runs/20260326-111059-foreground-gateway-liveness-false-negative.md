# Run: Foreground gateway liveness false-negative for same-session attach

Date: 2026-03-26 UTC
Agent under test: `james`
Session root: `/home/huangzhe/.houmao/runtime/sessions/local_interactive/local_interactive-20260326-101307Z-d5209044`

## Summary

The foreground gateway prompt failure is caused by a false-negative liveness probe in the same-session tmux path, not by the gateway process spontaneously disappearing first.

The runtime liveness check looks up the recorded gateway pane through `list_tmux_panes(session_name=...)`. That helper currently runs:

```bash
tmux list-panes -t <session_name> ...
```

In tmux, `list-panes -t <session>` only lists panes from the current window of that session. It does not enumerate panes from the auxiliary gateway window unless that window is current.

As a result, once window `0` (`agent`) remains current, the liveness probe cannot see the gateway pane on window `1`, concludes the gateway is stale, and clears the runtime state. That cleanup then tears down the foreground gateway and causes `GatewayNoLiveInstanceError` on the prompt path.

## Repro evidence

Foreground attach succeeded and reported a live gateway window/pane:

```json
{
  "gateway_health": "healthy",
  "execution_mode": "tmux_auxiliary_window",
  "gateway_tmux_window_id": "@629",
  "gateway_tmux_window_index": "1",
  "gateway_tmux_pane_id": "%633"
}
```

Manual tmux inspection immediately after attach showed the gateway window still existed:

```bash
tmux list-windows -t james -F '#{window_index}\t#{window_id}\t#{window_name}\t#{window_active}\t#{window_panes}'
```

Observed:

```text
0    @622    agent    1    1
1    @629    gateway  0    1
```

But the pane-listing form used by the shared helper only returned the current window pane:

```bash
tmux list-panes -t james -F '#{pane_id}\t#{session_name}\t#{window_id}\t#{window_index}\t#{window_name}\t#{pane_index}\t#{pane_active}\t#{pane_dead}\t#{pane_pid}'
```

Observed:

```text
%625  james  @622  0  agent  0  1  0  12176
```

The session-wide form does show both panes:

```bash
tmux list-panes -s -t james -F '#{pane_id}\t#{session_name}\t#{window_id}\t#{window_index}\t#{window_name}\t#{pane_index}\t#{pane_active}\t#{pane_dead}\t#{pane_pid}'
```

Observed:

```text
%625  james  @622  0  agent    0  1  0  12176
%633  james  @629  1  gateway  0  1  0  424918
```

## Code path

- `src/houmao/agents/realm_controller/backends/tmux_runtime.py:281`
  - `list_tmux_panes()` uses `tmux list-panes -t session_name`
- `src/houmao/agents/realm_controller/runtime.py:3091`
  - `_same_session_gateway_is_alive()` calls `_find_tmux_pane(...)`
- `src/houmao/agents/realm_controller/runtime.py:3085`
  - `_find_tmux_pane()` searches only the panes returned by `list_tmux_panes_shared(session_name=...)`
- `src/houmao/agents/realm_controller/runtime.py:2919`
  - false-negative liveness triggers `_clear_stale_gateway_runtime_state(...)`

## Gateway log correlation

The gateway log shows the gateway starting normally, and the earlier failure timestamp lines line up with runtime-side stale cleanup:

```text
2026-03-26T11:05:38Z [gateway-runtime-debug] same-session liveness check failed ... pane_summary=[%625 ... window=0/'agent' ...]
2026-03-26T11:05:38Z [gateway-shell] exit code=0
```

Inference:
The prompt path misclassified the live foreground gateway as missing, then stale cleanup killed the auxiliary tmux window, which produced the shell exit line in the same second.

## Fix direction

The shared tmux pane enumeration used for session-wide discovery must use a session-wide listing mode, for example `tmux list-panes -s -t <session_name>`, or an equivalent implementation that truly enumerates all panes in the addressed session.

The same-session gateway liveness probe should continue to rely on the recorded pane id, but it must search against all panes in the session rather than only the current window.
