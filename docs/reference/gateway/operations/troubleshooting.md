# Gateway Troubleshooting

This page covers the current operator-facing failure modes for gateway attach, live readiness, and same-session gateway lifecycle.

## Attach Times Out Waiting For Health Readiness

If attach reports `Timed out waiting for gateway health readiness on 127.0.0.1:<port>.`, the runtime started a gateway surface and discovered the intended listener, but repeated `GET /health` probes did not return a valid gateway health payload before the readiness deadline.

Current attach errors include `Last health probe error: ...` when the readiness loop observed a gateway HTTP client failure. Use that suffix first because it points at the client-side reason the health check could not complete.

Common readings:

- `Connection refused`, timeout text, or socket errors usually mean the sidecar did not keep serving on the discovered listener; inspect `<session-root>/gateway/logs/gateway.log` and `<session-root>/gateway/run/current-instance.json`.
- `gateway returned invalid JSON` usually means the port answered, but not with the Houmao gateway health contract; check for a listener collision or stale desired-port reuse.
- proxy-related wording, proxy refusal, or a non-loopback proxy endpoint usually means ambient proxy variables captured loopback readiness traffic.

Gateway client calls are local control-plane calls. By default, Houmao bypasses ambient proxy variables such as `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, and lowercase variants for live gateway calls, and it does not mutate process-wide `NO_PROXY` or `no_proxy`. Set `HOUMAO_GATEWAY_RESPECT_PROXY_ENV=1` only when you intentionally want `GatewayClient` to use normal Python environment proxy handling for live gateway HTTP.

Useful first checks:

```bash
houmao-mgr agents gateway status --agent-name <friendly-name>
```

```bash
env | grep -Ei '^(http_proxy|https_proxy|all_proxy|no_proxy)='
```

If you are debugging an older build that still routes gateway readiness through proxy envs, temporarily remove proxy variables or set loopback bypass while attaching:

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    -u http_proxy -u https_proxy -u all_proxy \
    NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost \
    houmao-mgr agents gateway attach --agent-name <friendly-name>
```

## `houmao-mgr agents gateway attach` Reports Missing Manifest Tmux Metadata

If current-session attach says the tmux session does not publish `HOUMAO_MANIFEST_PATH` or a usable `HOUMAO_AGENT_ID`, the command is not running against a session that has published supported managed-agent discovery metadata yet.

Check:

- you are inside the target tmux session, not another shell or another tmux session
- the session was launched through the current pair flow that seeds gateway capability
- the session is not an older launch that predates the shared capability-publication seam

If you need to attach before current-session metadata is available, use explicit pair attach instead:

```bash
houmao-mgr agents gateway attach --agent-name <friendly-name> --pair-port <pair-port>
```

## Current-Session Attach Reports Stale Metadata

Current-session attach fails closed when the tmux-published manifest or registry fallback no longer matches the current tmux session, or when the persisted manifest authority belongs to another managed agent.

Typical causes:

- the session was recreated and tmux still exposes older env
- the runtime root or session root moved
- the gateway subtree was deleted or partially cleaned up under a still-live tmux session

Operator guidance:

- treat the session as stale rather than trying to patch the env by hand
- relaunch the pair-managed session, use `--target-tmux-session <tmux-session-name>` if the live local tmux handle is known, or use explicit `--agent-name` or exact `--agent-id` attach against the server if the managed-agent registration is still valid

## Current-Session Attach Returns Unknown Managed Agent

Current-session pair attach uses the persisted manifest authority `gateway_authority.attach.api_base_url` plus `gateway_authority.attach.managed_agent_ref` as its only managed-agent route target.

That means a seeded manifest alone is not enough. Current-session attach becomes valid only after the matching delegated launch has completed managed-agent registration on that same server.

If the server returns unknown managed agent:

- wait for the delegated launch registration step to finish
- verify that the persisted `api_base_url` still addresses the intended `houmao-server`
- do not try to override the server target with `--pair-port`; current-session and `--target-tmux-session` modes do not support retargeting

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
