# Gateway Plugin Author and Operator Guide

This page is for Python package authors who want to add an HTTP or external-service integration to a Houmao gateway, and operators who enable those packages. Plugins run as trusted Python code in the gateway process. Install them in the same Python environment as Houmao; changing Houmao's source code is unnecessary.

The public SDK is `houmao.gateway.plugins`, contract version `1`. A plugin owns a relative FastAPI router and an asynchronous resource lifespan. The gateway owns discovery, route admission, credentials, worker supervision, status, and dispatch to its single managed agent.

## Install and Enable a Package

The [independent notification example](https://github.com/igamenovoer/houmao/tree/main/examples/gateway-plugin) is a complete distribution. Its source imports only the public SDK and declares both a Houmao dependency range and an entry point:

```toml
[project]
name = "houmao-example-notifications"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["houmao>=2.4,<3"]

[project.entry-points."houmao.gateway_plugins"]
example-notifications = "houmao_example_plugin:definition"
```

Install a built wheel with the Python interpreter that runs Houmao:

```bash
python -m pip install houmao_example_notifications-0.1.0-py3-none-any.whl
```

Installation makes an implementation discoverable. It does not enable it. Create a YAML or JSON selection file:

```yaml
schema_version: 1
gateway:
  plugins:
    team-chat:
      implementation: example-notifications
      config:
        account: team-chat
        require_credentials: false
  max_event_bytes: 65536
  dispatch_timeout_seconds: 10.0
  startup_timeout_seconds: 10.0
  shutdown_timeout_seconds: 5.0
```

Enable the complete set when attaching the owner's gateway:

```bash
houmao-mgr agents single --agent-id AGENT_ID gateway attach --plugins-config /absolute/path/plugins.yaml
```

Instance IDs match `[a-z][a-z0-9-]{0,62}`. Here, `team-chat` is an operator-selected instance ID; `example-notifications` is the installed implementation's entry-point name. Multiple instances can select one implementation with different accounts. Entry-point discovery inspects metadata, then imports only selected implementations. Ambiguous selected names, unsupported SDK versions, invalid settings, or import failures fail the affected instance with sanitized status.

The file is a complete replacement selection, rather than a patch. Omitting `--plugins-config` reuses the persisted selection. An explicit empty `plugins: {}` clears it on the next gateway start. Attaching with an identical effective selection can reuse a live gateway. A changed selection requires detaching and reattaching the gateway; the managed agent body can keep running. Code upgrades also require a gateway restart. The host does not replace live plugins in place.

## Implement the Public Contract

Return a `PluginDefinition` from the selected entry point:

```python
definition = PluginDefinition(
    config_model=NotificationConfiguration,
    binding_identity=lambda config: "example-account:" + config.account,
    create=NotificationPlugin.from_config,
    sdk_version=1,
)
```

Use a strict Pydantic configuration model that rejects unknown fields. `binding_identity` is a pure, deterministic function of the intended service account. It must not depend on credentials, passwords, or token contents. The host derives an opaque owner-specific binding ID from it.

The factory accepts `(context, validated_config)` and returns an object with `router: APIRouter` and `lifespan() -> AsyncContextManager[None]`. Construction prepares routes and immutable settings. Read credentials, open connections, and start workers inside the lifespan. The host starts that lifespan only after listener binding and route validation succeed.

| Context Capability | Purpose |
| --- | --- |
| `owner` | Immutable `agent_id`, `runtime_session_id`, and optional `agent_name` for the gateway owner. |
| `instance_id`, `binding_id` | Host-selected instance and stable owner/account binding identities. |
| `listener` | Optional resolved host, port, and base URL supplied during post-bind activation. |
| `events.dispatch(event)` | Await immediate confirmed handoff of one ordinary notification, or receive `PluginDispatchError`. |
| `workers.start_soon(name, worker)` | Start an asynchronous zero-argument worker under instance supervision. |
| `credentials.read()` | Reopen the selected private credential document during the active lifespan. |
| `state.path(relative_path)` | Resolve contained owner/binding-specific non-message state; reject escapes and symlinks. |
| `report_connection(state, retry_at=...)` | Publish `connected`, `unattached`, `reconnecting`, `degraded`, or `disconnected` without a health callback. |
| `log(event_code, fields=...)` | Report safe operational metadata; exclude messages, tokens, and credential values. |

Workers must await cooperatively and close connections when cancelled. Worker or lifespan failure marks the instance failed and disables its custom routes. The host cancels and drains workers on shutdown, within the configured deadline. A broken plugin does not stop core gateway routes or an unrelated healthy plugin.

These deadlines require cooperative code. A plugin that blocks the event loop or suppresses cancellation can prevent timely shutdown. Use asynchronous service clients, preserve cancellation, and repair a failed instance by restarting the gateway after correcting its package or configuration.

Connection health and lifecycle state are separate. For example, a running reconnect loop may report `reconnecting`. Status reads use host snapshots and do not call service APIs or plugin health callbacks.

The host converts untyped custom-handler failures before response emission into safe `503` errors. For streaming responses, catch provider exceptions inside the iterator and finish with a safe protocol error. After headers or chunks have been sent, the client has already received them. Streaming privacy and cleanup therefore require cooperative handling inside the plugin iterator.

## Keep Routes Inside the Instance

Declare paths relative to the instance, such as `/notify`. The host publishes them below `/v1/plugins/team-chat`. A plugin cannot replace `/health`, `/v1/control/prompt`, another instance's routes, or the host-owned `/_status` suffix.

Before activation, the host stages the complete candidate set. It checks HTTP methods and effective paths, including parameter-name aliases, static/dynamic overlaps, catchalls, and trailing-slash aliases. Every participant in a conflict fails; registration order does not choose a winner. Core and unrelated valid plugin routes remain available.

Do not mutate the application router, install global exception handlers, or expose another ASGI application. The supported extension surface is the staged instance router.

## Bind Credentials to the Owner and Account

A no-auth plugin can omit `credential_ref`. An authenticated integration selects one preprovisioned private JSON document:

```yaml
schema_version: 1
gateway:
  plugins:
    team-chat:
      implementation: example-notifications
      credential_ref:
        file: /absolute/private/path/team-chat.json
      config:
        account: team-chat
        require_credentials: true
```

Keep this credential document outside the checkout and project tree, owned by the current user, with mode `0600`. Do not put keys in tracked files, CLI arguments, logs, status, or the immutable plugin configuration. The selected path must be explicit and absolute. The reader rejects symlinks and unsafe ownership or permissions, and does not scan the filesystem or use ambient environment authentication.

The example checks that the selected document's `account` matches its configured account. Credential rotation updates that same selected file. Its `POST /refresh-credentials` endpoint accepts only `{}` and rereads that reference. It cannot select a new file, owner, account, or sender. Services that support owner-authorized joining can follow the same narrow rule; broader account administration belongs outside plugin routes.

Plugin state is scoped by logical owner, instance, and binding. Rebinding to another account creates a different state scope. Store cursors, connection metadata, or other non-message state there. Persisting an event payload to retry it later violates the immediate-dispatch contract.

## Dispatch Now or Return an Error

An inbound HTTP handler can use this pattern:

```python
@router.post("/notify", response_model=PluginDispatchResult)
async def notify(event: PluginEvent) -> PluginDispatchResult:
    try:
        return await context.events.dispatch(event)
    except PluginDispatchError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
```

`PluginEvent` contains a source correlation ID, plain text, and optional JSON metadata:

```json
{"source_event_id":"message-42","text":"Please inspect the latest build.","metadata":{}}
```

The owner comes from the context. Event input cannot override its agent ID, runtime session, sender account, target route, or credentials. The gateway bounds the entire event envelope before dispatch and applies ordinary readiness admission to the current agent body.

| Outcome | Sender Observation | Sender Action |
| --- | --- | --- |
| Confirmed handoff to the same observed body | HTTP `200`, `{"disposition":"dispatched","source_event_id":"message-42"}` | Advance the source cursor or acknowledge the upstream event. |
| Body busy, not ready, or readiness uncertain | Retryable HTTP `409` | Retain the source event and make a new request later. |
| Plugin/body unavailable, dispatch timeout, or body death/replacement during the request | Retryable HTTP `503` | Retain the source event and make a new request later. |
| Invalid or unsupported input | Permanent HTTP `422` | Correct the request. |
| Gateway absent, process death, or connection loss | Connection failure or timeout | Apply the sender's retry policy. |

Success confirms handoff, rather than completion of the agent's work. Starting a worker or admitting work to an internal queue does not establish success. If the body dies or restarts after admission and before response finalization, the request fails and its payload is discarded. The gateway must not deliver a late result to a replacement body.

The gateway does not cache, queue, spool, or automatically resend plugin notifications. A plugin must preserve the same rule. Each retry is a fresh sender request evaluated against current readiness. Reconnecting a service client or restarting the gateway restores connection configuration, not undelivered payloads.

Adapters that cannot confirm actual handoff fail with `503`. Native headless execution uses a request-scoped launch fence and observes the provider child. Managed headless execution uses the same guarded synchronous execution boundary, bounded by the request deadline. The fence checks expiry, body generation, and the originating gateway process before a delayed launch; it contains no event payload.

`source_event_id` provides correlation, not a durable exactly-once guarantee. If the body accepted an event but the success response was lost, a sender retry may dispatch it again. A crash after a completed success response cannot change that response retroactively. The sender and service protocol must account for that ambiguity.

## Inspect and Operate the Host

Read the resolved listener from gateway status, then inspect:

```bash
curl "$GATEWAY_URL/v1/plugins"
curl "$GATEWAY_URL/v1/plugins/team-chat/_status"
curl "$GATEWAY_URL/v1/plugins/team-chat/owner"
```

Status exposes implementation/distribution versions, SDK version, lifecycle, connection state, binding identity, worker names, and safe failure/conflict details. It excludes configuration contents, selected credential paths, and event bodies.

Plugins activate only on loopback listeners. Binding the gateway to `0.0.0.0` disables plugin activation before implementation import, credential access, or worker startup. Sanitized host status remains readable; custom plugin routes remain unavailable.

For package upgrades or changed selection, detach the live gateway, install the package or update the configuration, and attach again. This restarts the sidecar without relaunching the managed agent. Detaching a gateway does not imply that the agent body has stopped.

## Qualification

The repository's [gateway plugin qualification tools](../../../scripts/qualification/gateway-plugins/) build independently installable fixture wheels and run installed Houmao from an external working directory. They check import isolation, explicit selection, owner/account isolation, route conflicts, lifecycle failures, immediate errors, and sender-owned retries. Dependency wheels must be provisioned before the offline run; missing dependencies are setup failures.

The example's [recorded installed wheel qualification](https://github.com/igamenovoer/houmao/blob/main/examples/gateway-plugin/qualification.md) includes sanitized artifact hashes, environment facts, gateway loss/recovery, cursor continuity, possible duplication after a discarded reply, and completed cleanup.

The example is a small notification integration, not an implementation of CCCC. Private upstream state, credentials, and participant administration do not become gateway-owned stores.
