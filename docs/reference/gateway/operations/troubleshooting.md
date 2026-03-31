# Gateway Troubleshooting

This page covers the current operator-facing failure modes for pair-managed `houmao_server_rest` gateway attach and same-session gateway lifecycle.

## `houmao-mgr agents gateway attach` Reports Missing Manifest Tmux Metadata

If current-session attach says the tmux session does not publish `HOUMAO_MANIFEST_PATH` or a usable `HOUMAO_AGENT_ID`, the command is not running against a session that has published supported managed-agent discovery metadata yet.

Check:

- you are inside the target tmux session, not another shell or another tmux session
- the session was launched through the current pair flow that seeds gateway capability
- the session is not an older launch that predates the shared capability-publication seam

If you need to attach before current-session metadata is available, use explicit pair attach instead:

```bash
houmao-mgr agents gateway attach --agent-name <friendly-name> --port <public-port>
```

## Current-Session Attach Reports Stale Metadata

Current-session attach fails closed when the tmux-published manifest or registry fallback no longer matches the current tmux session, or when the persisted manifest authority belongs to another managed agent.

Typical causes:

- the session was recreated and tmux still exposes older env
- the runtime root or session root moved
- the gateway subtree was deleted or partially cleaned up under a still-live tmux session

Operator guidance:

- treat the session as stale rather than trying to patch the env by hand
- relaunch the pair-managed session or use explicit `--agent-name` or exact `--agent-id` attach against the server if the managed-agent registration is still valid

## Current-Session Attach Returns Unknown Managed Agent

Current-session pair attach uses the persisted manifest authority `gateway_authority.attach.api_base_url` plus `gateway_authority.attach.managed_agent_ref` as its only managed-agent route target.

That means a seeded manifest alone is not enough. Current-session attach becomes valid only after the matching delegated launch has completed managed-agent registration on that same server.

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
