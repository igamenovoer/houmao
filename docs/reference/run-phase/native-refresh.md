# Native Home and Common-Plugin Refresh

Houmao exposes the native home of an active managed agent and supports read-only inspection and native refresh of skills and MCP. These resources form the `common-plugin` view. Agent-specific extensions are `native-special-plugin`; users inspect those through native facilities. A refresh can reload those extensions as a normal native side effect without promising their freshness or atomic application.

## Workflow

Select the agent explicitly, inspect its native home, complete external updates, and check or refresh:

```sh
houmao-mgr agents single --agent-id <id> home
houmao-mgr agents single --agent-id <id> refresh --check
houmao-mgr agents single --agent-id <id> refresh
```

A managed agent can use `agents self home`, `agents self refresh --check`, and `agents self refresh`. Single scope never infers the current tmux session. Self scope requires the current registered managed session. Global and external scopes do not expose these controls.

The default `home` output is the authoritative native configuration path, not the caller's OS home, project directory, or runtime artifact directory. Root `--print-json` returns the typed descriptor or refresh observation/result. Home inspection reads no configuration contents. Common observation excludes skill bodies, raw native configuration, credentials, and credential-derived fingerprints.

Houmao does not install packages or accept replacement definitions through refresh. Use an editor, package manager, native tool, or other external updater to change the native material. Native precedence still applies: a project/scoped skill or captured launch override can mask an edited file.

## Freshness and Native Boundaries

Check mode observes without forced rescans, invalidation, reload, provider workers, or model turns. Native watchers can independently apply updates before or during a query. The result does not require a Houmao update receipt.

| State | Meaning |
| --- | --- |
| `current` | The reported scope is confirmed current at its stated native boundary. |
| `pending` | A known input change has not taken effect. |
| `unknown` | Runtime/source evidence or coverage is insufficient. |

Read resource components and boundaries as well as aggregate freshness. Skills can have a current catalog for the next step and current body availability for the next load. Previously loaded instructions remain in conversation history. Refresh does not force the model to reread them.

MCP declaration application, negotiated tools, and server implementation revision are distinct. A connected server does not prove it loaded a newly installed package. DSH reports unavailable implementation revision evidence as an explicit optional unknown component; aggregate current covers the required declaration/tool scope and does not promise the latest remote server implementation. Connection health remains separate from declaration freshness.

Manual refresh first observes common state. Complete current evidence permits `method=noop`, `outcome=already_current` without native mutation. Qualified automatic discovery reports its future `next_step`, `next_turn`, or `next_load` boundary. Otherwise an admitted native operation reloads resources and produces another observation. Unknown state cannot justify an already-current claim.

Check mode exits zero only for complete confirmed common freshness. Refresh exits zero for verified already-current, confirmed common refresh, or qualified automatic coverage with explicit future boundaries. Busy, partial/unverified, restart-required, unsupported, unavailable, failed, and uncertain results exit nonzero while preserving typed evidence in JSON output.

## Refresh and Relaunch

Refresh preserves the running harness process and bound conversation. Internal plugin resources or MCP subprocesses can reload. Pending native-special-plugin or host-module updates do not invalidate confirmed current skills/MCP unless they impair those resources or native readiness. Partial application is retained; no rollback is claimed.

Refresh never invokes agent restart, a host-exit hook, cold activation, or relaunch. It rejects force/restart/install options. A common resource known to require restart produces `restart_required`, preserving any already-applied changes. The operator can separately invoke:

```sh
houmao-mgr agents single --agent-id <id> relaunch
```

Relaunch remains manifest-backed and can regenerate launch-derived material. Its existing stored/default conversation policy applies, which is not exact continuation by default. Refresh neither resolves edited Houmao launch profiles nor regenerates system prompts, brain configuration, or installed skills. It does not repair missing native files from a saved launch snapshot.

## Gateway and Failure Handling

The owning gateway exposes `GET /v1/native-home`, read-only `GET /v1/control/refresh`, and observe-first `POST /v1/control/refresh`. The passive server mirrors them under `/houmao/agents/{agent_ref}/gateway/`. GET returns a normal typed observation when freshness is pending or unknown. POST preserves typed action statuses and partial effects; the proxy adds no activation, retry, or freshness evaluation.

Without an attached gateway, qualified local inspection and no-op/automatic results remain available. Mutating refresh requires explicit gateway attachment. An attached but unavailable gateway is not permission to bypass its authority.

The manager and passive server verify that the reached gateway belongs to the selected native execution. Later requests carry a captured identity precondition, so port reuse or agent replacement cannot silently retarget refresh. Authentication and preflight consume the original refresh deadline; expiry prevents a later native handoff.

Live manual reload requires immediate native admission. Busy agents, pending input/interactions, or shared active execution produce a refusal instead of waiting inside a calling agent's own tool invocation. Native automatic updates remain allowed independently.

A lost response can leave a native operation active. Report uncertainty and inspect state; do not automatically replay it. Managed ordinary work stays blocked while native settlement/readiness is uncertain. Unknown freshness alone does not keep an otherwise settled valid runtime blocked. Status, interruption, and explicit relaunch remain available.

## Execution Owner Routing

For an executor-managed agent, `home`, `refresh --check`, and refresh enter the recorded owner context before reading manifests or contacting native/gateway endpoints. The returned home descriptor's `identity` includes `execution_context_id`, `execution_host_id`, and owner UID/GID/account metadata. The path belongs to that context. Check/inspection creates no caller-local home or repaired runtime state.

Owner routing retains the refresh/relaunch boundary described above. It does not restart the harness, regenerate launch-profile-derived material, or alter another same-user agent's credential selection. An unavailable owner or a failed binding/generation check produces an explicit result without trying a caller-local manifest, similarly named tmux session, or loopback port. A lost refresh response remains indeterminate until owner inspection establishes current state; it is not replayed automatically. See [execution contexts](execution-contexts.md).

## Qualification

DSH headless and Web are the primary targets. The current Web path qualifies configuration/resource reconciliation, not arbitrary hot-code HMR. ACP loads current materialized inputs on the next ordinary invocation without a refresh-created worker. Kimi Code, Codex, and Claude Code are best effort; native capabilities outside maintained owned transports remain explicit limitations.

See [Compatibility](native-refresh-compatibility.md), [DSH Headless](dsh-headless.md), [DSH Web Control](dsh-web-control.md), and [Gateway Operations](../gateway/operations/native-refresh.md) for executed evidence and interface details.
