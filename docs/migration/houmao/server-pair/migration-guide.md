# Migration Guide

This guide is for operators and developers moving from:

- `cao-server`
- `cao`

to the supported Houmao-managed pair:

- `houmao-server`
- `houmao-mgr`

## 1. Understand The Support Boundary

The supported migration target is:

```text
houmao-server + houmao-mgr
```

Do not plan around mixed deployments such as:

- `houmao-server + cao`
- `cao-server + houmao-mgr`

Those combinations are outside the supported contract.

## 2. Stop Depending On Installed `cao`

The supported pair no longer requires the standalone `cao` executable or the explicit `houmao-mgr cao ...` namespace.

The supported path is now Houmao-owned end to end:

- `houmao-mgr server ...` manages server lifecycle
- `houmao-mgr agents launch ...` performs local launch
- `houmao-mgr agents ...` handles post-launch control

The pinned CAO source remains a compatibility oracle for preserved HTTP behavior, not a runtime dependency.

## 3. Start `houmao-server`

Typical local start:

```bash
pixi run houmao-mgr server start --api-base-url http://127.0.0.1:9889
```

Optional controls:

```bash
pixi run houmao-mgr server start \
  --api-base-url http://127.0.0.1:9889 \
  --runtime-root /tmp/houmao-runtime \
  --watch-poll-interval-seconds 1.0 \
  --recent-transition-limit 24
```

What changes when you do this:

- `houmao-server` becomes the public HTTP authority
- root `/health` keeps `service="cli-agent-orchestrator"` and adds `houmao_service="houmao-server"`, without `child_cao`
- the preserved `/cao/*` route family is served locally by `houmao-server`
- live terminal tracking remains server-owned and runs from direct tmux/process observation
- session-backed launch resolves native selectors at launch time from the effective agent-definition root
- server-owned state is written under `<runtime-root>/houmao_servers/<host>-<port>/`

## 4. Switch Service-Management Commands To `houmao-mgr`

Replace direct `cao` usage with `houmao-mgr server ...` for server lifecycle and `houmao-mgr agents ...` for managed-agent lifecycle.

Examples:

```bash
pixi run houmao-mgr server status
pixi run houmao-mgr agents launch --agents gpu-kernel-coder --provider codex
pixi run houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --headless
pixi run houmao-mgr agents prompt AGENTSYS-gpu --prompt "Summarize the current state."
pixi run houmao-mgr agents gateway attach AGENTSYS-gpu
pixi run houmao-mgr brains build --tool codex --skill skills/mailbox --config-profile dev --cred-profile openai
pixi run houmao-mgr admin cleanup-registry --grace-seconds 0
pixi run houmao-mgr server sessions shutdown --all
```

## 5. Use Houmao Inspection Commands

After switching, inspect state through `houmao-server` instead of reading raw CAO state or child-process artifacts.

Examples:

```bash
pixi run houmao-server health
pixi run houmao-server current-instance
pixi run houmao-server sessions list
pixi run houmao-server sessions get cao-gpu
pixi run houmao-server terminals state abcd1234
pixi run houmao-server terminals history --limit 20 abcd1234
```

These commands expose Houmao-owned views such as:

- root health with preserved compatibility identity fields
- current server instance details
- explicit transport/process/parse state for tracked sessions
- derived operator-facing live state and stability metadata
- bounded in-memory recent transitions

For managed agents, use `/houmao/agents/*` instead of treating headless agents as fake CAO terminals.

History retention is intentionally split:

- TUI-backed managed-agent history is bounded in memory and disappears when the server forgets or loses the live tracker state
- headless managed-agent history is still coarse, but it is derived from persisted server-owned turn records and remains inspectable across server restarts
- durable headless stdout, stderr, event logs, and return codes stay on `/houmao/agents/{agent_ref}/turns/*`

## 6. Understand What `launch` Does Differently Now

`houmao-mgr` now exposes one supported native tree:

- `server ...`
- `agents ...`
- `brains build`
- `admin cleanup-registry`

`houmao-mgr agents launch` now builds the brain locally, starts the runtime directly, and publishes the shared-registry record without routing through `houmao-server`.

Successful local launches:

- materialize a runtime-owned session root
- write a manifest backed by a native headless runtime backend
- publish stable gateway attachability through the shared runtime seam
- publish the live agent into the shared registry for later discovery

Pair-managed gateway attach remains post-launch:

- explicit attach: `pixi run houmao-mgr agents gateway attach <agent-ref> --port <public-port>`
- current-session attach: run `pixi run houmao-mgr agents gateway attach` from inside the target tmux session
- tmux window `0` remains the contractual agent surface for that pair-managed session

For follow-up operator control after launch, treat the native `agents` tree as the default pair surface:

- `agents prompt` is the default documented prompt path
- `agents gateway prompt` is the explicit live-gateway queue path
- `agents mail status|check|send|reply` covers pair-owned mailbox follow-up when the managed agent exposes mailbox capability
- `agents turn ...` is headless-only and rejects TUI-backed agents explicitly

## 7. Runtime Sessions Persist As `houmao_server_rest`

When a terminal-backed session is launched through the pair and runtime artifacts are materialized, the persisted identity remains:

```text
backend = "houmao_server_rest"
```

That means:

- the manifest points at `houmao-server`
- runtime follow-up control should use the persisted Houmao server identity
- the session should not be modeled as a supported standalone `cao_rest` session anymore
- same-session gateway lifecycle still resolves from the persisted attach contract and tmux-published pointers

## 8. Deprecated Standalone CAO Surfaces Are Retired

The supported operator path is now the pair.

The following standalone CAO-facing surfaces are retired:

- `houmao-cao-server`
- `python -m houmao.cao.tools.cao_server_launcher`
- `houmao-cli start-session --backend cao_rest`
- resumed `houmao-cli` control flows against standalone raw `cao_rest` sessions

Those entrypoints now fail fast with migration guidance to `houmao-server` and `houmao-mgr`.

## 9. Roll Out In A Safe Sequence

Recommended migration order:

1. Start `houmao-server` on the public base URL you want to own.
2. Replace operator command usage from `cao` to `houmao-mgr server ...` and `houmao-mgr agents ...`.
3. Verify `houmao-server health` and `houmao-mgr server status`.
4. Launch one agent through `houmao-mgr agents launch`.
5. Inspect server-owned sessions through `houmao-server sessions` and `houmao-mgr server sessions`, and inspect launched agents through `houmao-mgr agents ...` or `/houmao/agents/*`.
6. Move follow-up tooling toward the shared registry, runtime manifests, and `/houmao/agents/*` instead of standalone CAO endpoints.

## 10. Roll Back If Needed

Rollback remains pairwise:

- stop `houmao-server`
- stop using `houmao-mgr`
- return operators to `cao-server + cao`

Do not keep one side on Houmao and the other side on raw CAO. The supported story is pairwise in both directions:

- adopt the pair together
- roll back from the pair together

## Related References

- [Houmao Server Pair](../../../reference/houmao_server_pair.md)
- [Houmao Server Filesystem Reference](../../../reference/system-files/houmao-server.md)
- [What We Tested](tested.md)
