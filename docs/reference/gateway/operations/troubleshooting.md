# Gateway Troubleshooting

This page covers the current operator-facing failure modes for pair-managed `houmao_server_rest` gateway attach and same-session gateway lifecycle.

## `houmao-srv-ctrl agents gateway attach` Reports Missing Stable Tmux Metadata

If current-session attach says the tmux session does not publish `AGENTSYS_GATEWAY_ATTACH_PATH` or `AGENTSYS_GATEWAY_ROOT`, the command is not running against a session that has published stable gateway capability yet.

Check:

- you are inside the target tmux session, not another shell or another tmux session
- the session was launched through the current pair flow that seeds gateway capability
- the session is not an older launch that predates the shared capability-publication seam

If you need to attach before current-session metadata is available, use explicit pair attach instead:

```bash
houmao-srv-ctrl agents gateway attach <agent-ref> --port <public-port>
```

## Current-Session Attach Reports Stale Metadata

Current-session attach fails closed when the tmux-published pointers no longer match the runtime-owned gateway subtree or when the persisted attach contract belongs to another tmux session.

Typical causes:

- the session was recreated and tmux still exposes older env
- the runtime root or session root moved
- the gateway subtree was deleted or partially cleaned up under a still-live tmux session

Operator guidance:

- treat the session as stale rather than trying to patch the env by hand
- relaunch the pair-managed session or use explicit `<agent-ref>` attach against the server if the managed-agent registration is still valid

## Current-Session Attach Returns Unknown Managed Agent

Current-session pair attach uses the persisted `backend_metadata.api_base_url` plus `backend_metadata.session_name` from `attach.json` as its only managed-agent route target.

That means a seeded `attach.json` alone is not enough. Current-session attach becomes valid only after the matching delegated launch has completed managed-agent registration on that same server.

If the server returns unknown managed agent:

- wait for the delegated launch registration step to finish
- verify that the persisted `api_base_url` still addresses the intended `houmao-server`
- do not try to override the server target with `--port`; current-session mode does not support retargeting

## Detach Or Cleanup Refuses To Stop Window `0`

For pair-managed `houmao_server_rest`, tmux window `0` is the reserved agent surface. The gateway lifecycle never intentionally kills it.

If detach or cleanup reports that it refused to stop window `0`, inspect:

- `<session-root>/gateway/run/current-instance.json`
- `<session-root>/gateway/logs/gateway.log`

This usually means the recorded execution handle is corrupt or stale. The safe response is to fix or recreate the session state, not to force-kill window `0`.

## Multiple Non-Zero Windows Exist

This is not automatically a problem.

Current pair-managed rules:

- non-zero windows are auxiliary and intentionally non-contractual
- window names, counts, and ordering are not stable API
- only the exact tmux window and pane handle recorded in `gateway/run/current-instance.json` is authoritative for the live gateway

If the wrong auxiliary window appears to be live, compare the current tmux layout with the recorded `tmux_window_id`, `tmux_window_index`, and `tmux_pane_id` in `current-instance.json` before taking action
