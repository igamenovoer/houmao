# Native Home and Common-Plugin Refresh

The gateway exposes the native configuration home of its bound agent and observes whether that agent's skills and MCP resources are current. Installation and file updates remain external operations. Refresh asks the running agent body to pick up current native materials; restarting the agent remains a separate explicit relaunch operation.

## Read Home and Common State

| Method | Route | Result |
| --- | --- | --- |
| GET | `/v1/native-home` | Authoritative native-home descriptor for the bound active agent. |
| GET | `/v1/control/refresh` | Common-plugin capabilities, observed coverage, freshness, native boundaries, and health. |
| POST | `/v1/control/refresh` | Observe-first no-op, qualified automatic discovery, or bounded native reload. |

Read operations do not invalidate caches, force a rescan, reload resources, start a worker, or submit a model turn. Native watchers can continue independently while the gateway reads their results. A completed common observation returns HTTP 200 even when some freshness is pending or unknown.

The home descriptor identifies the native configuration home rather than the caller's OS home, project worktree, or runtime artifact directory. It does not include configuration contents or credentials. A missing authoritative mapping fails explicitly instead of selecting an ambient home.

`common-plugin` means skills and MCP. The observation does not provide a common inventory or freshness API for the body's other extensions, called `native-special-plugin`. A native extension can contribute a skill or MCP server that participates in the common view without making the extension package itself part of that view. Houmao gateway plugins remain a separate extension system.

## Interpret Freshness

Common observations distinguish these states for each resource:

| State | Meaning |
| --- | --- |
| `current` | Qualified evidence establishes availability under the stated native boundary. |
| `pending` | A known change has not taken effect at that boundary. |
| `unknown` | Input comparison, runtime evidence, or observation coverage is insufficient. |

The complete common scope is current only when all required components are confirmed current. A cached skill list or a connected MCP server alone cannot establish that the latest external edits took effect. An unobservable inventory cannot be treated as an empty one.

Freshness and health describe different facts. An MCP declaration can be applied while its endpoint is unreachable. An unchanged server command does not prove that a running subprocess loaded an externally upgraded implementation. The observation preserves each limitation instead of claiming a universal applied revision.

Skill changes can become available at the next catalog update, model step, turn, or skill load. These boundaries remain explicit. Refresh preserves conversation history and does not rewrite earlier skill tool results or claim that the model has already reread the new body.

## Request Refresh

POST accepts only `schema_version` (currently `1`) and `timeout_seconds`. The timeout defaults to 30 seconds and must be finite, positive, and no greater than 120 seconds. It accepts no agent/home override, package source, replacement content, arbitrary command, force flag, or restart instruction.

One absolute deadline covers initial observation, authentication, admission, and native handoff. A late read cannot schedule a later mutation. Native work already admitted can settle after the caller stops waiting; subsequent managed resource mutations cannot start after expiry.

```json
{"schema_version": 1, "timeout_seconds": 30.0}
```

The gateway observes common state first. If complete common freshness is already confirmed, including after a native automatic update, it returns `method=noop` and `outcome=already_current`. Missing freshness evidence cannot justify that no-op. Qualified next-use discovery can instead return an automatic result with the future native boundary, without starting provider work.

When a native reload is needed, the gateway reserves managed admission and the backend claims a native boundary. Busy or uncertain targets are refused immediately. An agent cannot wait inside its own active tool call for the same turn to finish; it receives a busy result instead. The gateway does not enqueue a refresh, interrupt work, or retry a failed mutation.

The native operation may reload other extensions or native configuration. It need not affect common-plugin exclusively or apply atomically. Pending native-special-plugin code does not invalidate confirmed current skills/MCP by itself. A native failure that impairs common resources or leaves readiness uncertain remains an actionable failure, with safe diagnostics and partial-effect evidence.

## Admission and Recovery

Managed prompts, ordinary plugin notifications, reminders, and notifier commits observe the refresh reservation. The general gateway mutex is released during native work so core controls can remain responsive. Explicit interruption and recovery remain separate from ordinary input. The reservation does not claim to govern every native watcher or external edit.

Lost confirmation can leave native work active after the caller stops waiting. In that case, the gateway retains the admission guard until native settlement and valid readiness can be established. It does not replay refresh or start a replacement process. Unknown freshness alone does not keep an otherwise settled valid runtime blocked indefinitely.

Native replacement can stop a plugin before its replacement fails. Results preserve that partial effect; restoring a file is not proof of runtime rollback. A common resource requiring restart remains pending until the operator explicitly chooses relaunch. Refresh itself never invokes relaunch, process respawn, native host exit, or a replacement conversation.

## HTTP Outcomes

| Status | Refresh POST Meaning |
| --- | --- |
| 200 | Already-current no-op, confirmed common refresh, or qualified automatic discovery with an explicit future boundary. |
| 409 | Busy admission or a known common restart requirement, including any already-applied effects. |
| 412 | The captured native execution changed before the request could use it. |
| 422 | Invalid request fields or timeout. |
| 501 | No qualified managed control path. |
| 503 | Unavailable, failed, partial/unverified, or uncertain execution. |

Typed results preserve common state separately from native operation diagnostics and effects. A partial native update is not described as an untouched refusal, and a successful common result does not claim that every native extension refreshed. `GatewayClient.refresh_native()` returns these typed results for successful and non-successful HTTP outcomes. Its HTTP wait budget includes the requested native timeout plus five seconds of transport overhead, and it never retries the mutation.

The passive server projects these routes under `/houmao/agents/{agent_ref}/gateway/`, preserving typed upstream statuses and evidence. A missing or unreachable gateway remains HTTP 502. The proxy performs no additional refresh, freshness evaluation, or retry.

Scoped manager and passive-server calls verify the gateway's native identity against their selected authority before refresh. `GatewayClient.bind_native_home()` carries an `If-Match` precondition on later native-home/common-state/refresh requests and verifies returned identities. A reused port or changed incarnation fails explicitly instead of selecting another agent. Direct endpoint clients can bind the descriptor returned by `get_native_home()` before issuing their next request; the precondition supplies no replacement identity or launch authority.

Local manager inspection can operate from qualified active local authority without a live gateway. Mutating native reload requires explicit gateway attachment. Neither local inspection nor a missing-gateway refusal implicitly starts a gateway or repairs the agent.
