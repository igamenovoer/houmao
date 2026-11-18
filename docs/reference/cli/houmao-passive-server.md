# houmao-passive-server

Registry-first passive server for distributed agent coordination.

`houmao-passive-server` is the maintained server/API binary for Houmao. It discovers running agents from the shared registry, observes local tmux-backed agents, proxies requests to live agent gateways, exposes mailbox and memory proxy routes, and can own managed headless agents with durable turn records. It does not provide the retired standalone server compatibility surface and does not expose `/cao/*`.

## Synopsis

```bash
houmao-passive-server [OPTIONS] COMMAND [ARGS]...
```

## When to Use It

Use `houmao-passive-server` when you need a global HTTP authority for collecting, observing, or managing running Houmao agents from the shared registry. Typical operators still launch local agents through `houmao-mgr project agents launch` or adopt the current tmux session through `houmao-mgr agents self join`; passive-server then provides API-based discovery, observation, gateway proxying, mailbox proxying, and managed-headless turn handling.

Passive-server is not a Houmao project-bound command. It can start from any directory without a `.houmao` project overlay, and its durable state and registry target come from explicit root configuration, environment variables, or global defaults.

The packaged server/API command is `houmao-passive-server`. Historical standalone `houmao-server`, `houmao-cli`, and `/cao/*` workflows are removed from the maintained CLI/API surface.

## Commands

### `serve`

Start the passive server.

```bash
houmao-passive-server serve [OPTIONS]
```

| Option | Default | Description |
|---|---:|---|
| `--host TEXT` | `127.0.0.1` | Host address to bind. |
| `--port INTEGER` | `9891` | Port to listen on. |
| `--runtime-root PATH` | Global default | Runtime root for passive-server process state and passive-server-owned headless records. Precedence is `--runtime-root`, then `HOUMAO_GLOBAL_RUNTIME_DIR`, then the global default runtime root. |
| `--registry-root PATH` | Global default | Shared registry root used for discovery and passive-server-owned registry publish/remove calls. Precedence is `--registry-root`, then `HOUMAO_GLOBAL_REGISTRY_DIR`, then the global default registry root. |

Example:

```bash
houmao-passive-server serve --host 127.0.0.1 --port 9891
```

Isolated CI or demo state usually sets both roots:

```bash
HOUMAO_GLOBAL_RUNTIME_DIR=/tmp/houmao-runtime \
HOUMAO_GLOBAL_REGISTRY_DIR=/tmp/houmao-registry \
houmao-passive-server serve
```

### `offline-registry`

Start the separate authenticated offline membership, mail, and attachment service on the host that owns the filesystem store:

```bash
houmao-passive-server offline-registry \
  --config "$HOME/.local/state/houmao/offline-registry/service.json" \
  --host 127.0.0.1 --port 9892
```

`--config` is required and selects an owner-private configuration file. The listener defaults to `127.0.0.1:9892`. The configuration selects `registry_root`, `mailbox_root`, `admin_credential_file`, and `public_url`; see [Offline Registry Setup and Remote Access](../mailbox/operations/offline-registry.md) for initialization and private credential preparation. This service mode exposes no agent body lifecycle, gateway control, or shutdown routes. Remote agents use its configured API endpoint rather than mounting the host's store. Keep this configuration and all credentials outside the checkout.

## Root Resolution

Passive-server runtime state and shared-registry state are separate roots.

Runtime root precedence is:

1. `--runtime-root`
2. `HOUMAO_GLOBAL_RUNTIME_DIR`
3. the global default runtime root under the Houmao platform config home

Registry root precedence is:

1. `--registry-root`
2. `HOUMAO_GLOBAL_REGISTRY_DIR`
3. the global default registry root under the Houmao platform config home

Use `--runtime-root` or `HOUMAO_GLOBAL_RUNTIME_DIR` when you need to isolate passive-server process metadata and passive-server-owned headless state. Use `--registry-root` or `HOUMAO_GLOBAL_REGISTRY_DIR` when you need to isolate the shared registry that passive-server scans and mutates.

## Discovery Model

Passive-server is registry-driven. It scans the configured shared registry root for agents launched, joined, or managed by Houmao, then resolves those records into API targets. A discovered agent may expose local tmux authority, a live gateway, mailbox bindings, managed memory, or passive-server-owned headless authority depending on how that agent was created.

Agents are discoverable only when their launching authority and passive-server use the same shared registry root. For example, an agent launched with `HOUMAO_GLOBAL_REGISTRY_DIR=/tmp/a` will not appear in a passive-server that uses `--registry-root /tmp/b`.

Agent routes use `{agent_ref}` for either an exact agent id or an unambiguous agent name. Missing agents return `404`; ambiguous names return `409`.

## Selected-Agent Access

The passive server resolves the agent's retained owner policy before it reads a protected operation's body or uses the runtime. This applies to managed headless agents with no discovery entry and to known agents after gateway detach. An unavailable owner policy returns `503`. Discovery shows whether a gateway is available and can lag behind policy changes.

| Access | Operations | Caller requirement |
|---|---|---|
| Public | Discovery and challenge issuance | Network access to the passive service |
| Private | Detailed gateway status, usage, managed state summary, memory, and routine mail | Current self or listed admin proof |
| Admin | Native observation, direct turns and artifacts, prompt control, interrupt, stop, gateway lifecycle, reminders, notifier control, operator mail post, and mailbox binding | Anonymous access while the stored admin list is empty, followed by listed admin proof after first enrollment |

For signed requests, send `POST /houmao/agents/{agent_ref}/auth/challenge` with `purpose` set to `self` or `admin` and `request` containing the intended HTTP `method`, escaped `path`, raw `query` without the leading `?`, and `body_sha256` of the exact body bytes. For `admin` include `key_id`. Use the same agent reference in both paths. Check the returned issuer, agent and execution context, incarnation, purpose, key, and request binding before signing. Send the challenge ID in `Houmao-Challenge` and the encoded signature in `Houmao-Signature`. The per-agent gateway reference specifies the signing encoding and namespace. [Gateway access and enrollment](../gateway/operations/access.md)

Python callers can pass a `GatewayClientBinding` to `PassiveServerClient` to handle this exchange. Bind it to the passive server's base URL and the expected agent and execution context. The client signs selected protected routes and uses unsigned discovery and readiness calls.

The passive server consumes the signature and relays the admitted principal only through the owner-local path. The receiving gateway verifies the translated method, path, query, and body and checks whether the grant still applies. An unsigned admin request remains anonymous, so first enrollment can close access between the passive ingress and gateway. A `401` response includes the passive challenge location. A `403` response means the caller lacks authority. Either response ends the operation. After admission, gateway attach and detach return `501` and point to the scoped manager commands. Operations that require an attached gateway return `502` when it is unavailable.

For a server-managed gateway, passive launch provisions owner service authority for the current target's backing inspection, prompt handoff, and interrupt. This authority survives admin enrollment and is restricted to those backing operations on the selected managed controller. Keep the global passive listener on an owner-only interface or network, including its launch and shutdown routes. Publish the per-agent gateway through a verified HTTPS proxy for remote access. [Gateway deployment and trust](../gateway/operations/access.md)

## API Route Families

All maintained agent routes live under `/houmao/`. Root health is available at `/health` and identifies the service as `houmao-passive-server`.

### Health and Instance

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health and service identity. |
| `GET` | `/houmao/server/current-instance` | Current passive-server process metadata, API URL, runtime root, and server root. |
| `POST` | `/houmao/server/shutdown` | Request graceful passive-server shutdown. |

### Agent Discovery

| Method | Path | Description |
|---|---|---|
| `GET` | `/houmao/agents` | List discovered registry-backed agents. |
| `GET` | `/houmao/agents/{agent_ref}` | Resolve one discovered agent by id or unambiguous name. |

### Passive TUI Observation

These routes expose passive-server's local observer for discovered tmux-backed agents.

| Method | Path | Description |
|---|---|---|
| `GET` | `/houmao/agents/{agent_ref}/state` | Compact passive TUI state. |
| `GET` | `/houmao/agents/{agent_ref}/state/detail` | Detailed passive TUI state with diagnostics and parsed surface data. |
| `GET` | `/houmao/agents/{agent_ref}/history` | Recent passive TUI state history. |
| `GET` | `/houmao/agents/{agent_ref}/managed-state` | Managed-agent-compatible state projection. |
| `GET` | `/houmao/agents/{agent_ref}/managed-state/detail` | Managed-agent-compatible detailed state projection. |
| `GET` | `/houmao/agents/{agent_ref}/managed-history` | Managed-agent-compatible history projection. |

### Gateway Proxy

Gateway routes proxy to the agent-owned gateway when one is attached. Gateway attach and detach are intentionally same-host operations and are not performed remotely by passive-server.

| Method | Path | Description |
|---|---|---|
| `GET` | `/houmao/agents/{agent_ref}/gateway` | Gateway status. |
| `GET` | `/houmao/agents/{agent_ref}/gateway/native-home` | Authoritative native-home descriptor from the agent gateway. |
| `GET` | `/houmao/agents/{agent_ref}/gateway/control/refresh` | Passive skill/MCP capabilities, freshness, native boundaries, and health. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/control/refresh` | One observe-first refresh through the agent-owned gateway. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/requests` | Create a gateway request. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/control/prompt` | Submit a prompt through live-gateway control. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/control/send-keys` | Send raw gateway control input. |
| `GET` | `/houmao/agents/{agent_ref}/gateway/control/headless/state` | Inspect live headless control posture through the gateway. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session` | Set the next headless prompt-session selector through the gateway. |
| `GET` | `/houmao/agents/{agent_ref}/gateway/tui/state` | Gateway-owned TUI state. |
| `GET` | `/houmao/agents/{agent_ref}/gateway/tui/history` | Gateway-owned TUI state history. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/tui/note-prompt` | Record explicit prompt provenance on the gateway tracker. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/attach` | Returns not implemented; run local `houmao-mgr agents single --agent-id <id> gateway attach` or `houmao-mgr agents self gateway attach` on the host that owns the agent. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/detach` | Returns not implemented; run local gateway detach on the host that owns the agent. |

Native-home and refresh projections use the shared [native refresh contracts](../gateway/operations/native-refresh.md). GET preserves normal pending/unknown observations as HTTP 200. POST preserves typed no-op, automatic, confirmed, busy, restart-required, unsupported, partial, and uncertain outcomes, including already-applied effects and native-only diagnostics. It accepts only `schema_version` and an optional finite positive `timeout_seconds` up to 120 seconds (default 30). A missing or unreachable gateway returns HTTP 502. The passive server makes no local freshness decision, reads no native home material, and performs no automatic attachment, relaunch, replacement process, or retry.

`PassiveServerClient.refresh_managed_agent_gateway_native()` returns typed non-success refresh outcomes. Its HTTP timeout adds ten seconds to the requested native budget for the gateway and passive-server hops. Transport, invalid-response, and scoped resolution errors remain exceptions with safe diagnostics.

### Gateway Memory Proxy

| Method | Path | Description |
|---|---|---|
| `GET` | `/houmao/agents/{agent_ref}/gateway/memory` | Managed memory summary. |
| `GET` | `/houmao/agents/{agent_ref}/gateway/memory/memo` | Read the agent memo. |
| `PUT` | `/houmao/agents/{agent_ref}/gateway/memory/memo` | Replace the agent memo. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/memory/memo/append` | Append text to the agent memo. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/memory/pages/tree` | List page-tree entries. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/memory/pages/resolve` | Resolve a page path. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/memory/pages/read` | Read a page. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/memory/pages/write` | Write a page. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/memory/pages/append` | Append text to a page. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/memory/pages/delete` | Delete a page. |

### Mail Notifier and Reminders

| Method | Path | Description |
|---|---|---|
| `GET` | `/houmao/agents/{agent_ref}/gateway/mail-notifier/{channel}` | Mail-notifier status. |
| `PUT` | `/houmao/agents/{agent_ref}/gateway/mail-notifier/{channel}` | Enable or reconfigure the mail notifier. |
| `DELETE` | `/houmao/agents/{agent_ref}/gateway/mail-notifier/{channel}` | Disable the mail notifier. |
| `GET` | `/houmao/agents/{agent_ref}/gateway/reminders` | List gateway reminders. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/reminders` | Create reminders. |
| `GET` | `/houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}` | Read one reminder. |
| `PUT` | `/houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}` | Replace or update one reminder. |
| `DELETE` | `/houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}` | Delete one reminder. |

### Mail Proxy

Mail lifecycle routes preserve the explicit channel and `expected_binding_id` while proxying through the agent gateway. Summary status reports both configured slots and canonical identity. An upstream binding or scope conflict ends the request with a safe `502` response. Remote offline membership and storage access use the separate registry-only service.

| Method | Path | Description |
|---|---|---|
| `GET` | `/houmao/agents/{agent_ref}/mail/status` | Mailbox status. |
| `POST` | `/houmao/agents/{agent_ref}/mail/{channel}/list` | List mailbox messages. |
| `POST` | `/houmao/agents/{agent_ref}/mail/{channel}/peek` | Peek at one message. |
| `POST` | `/houmao/agents/{agent_ref}/mail/{channel}/read` | Read one message. |
| `POST` | `/houmao/agents/{agent_ref}/mail/{channel}/send` | Send a message. |
| `POST` | `/houmao/agents/{agent_ref}/mail/{channel}/post` | Post an operator-origin message. |
| `POST` | `/houmao/agents/{agent_ref}/mail/{channel}/reply` | Reply to a message. |
| `POST` | `/houmao/agents/{agent_ref}/mail/{channel}/mark` | Mark messages. |
| `POST` | `/houmao/agents/{agent_ref}/mail/{channel}/move` | Move messages. |
| `POST` | `/houmao/agents/{agent_ref}/mail/{channel}/archive` | Archive messages. |

### Managed-Agent Requests

| Method | Path | Description |
|---|---|---|
| `POST` | `/houmao/agents/{agent_ref}/requests` | Submit a passive-server managed-agent prompt request. |
| `POST` | `/houmao/agents/{agent_ref}/interrupt` | Interrupt a target agent. |
| `POST` | `/houmao/agents/{agent_ref}/stop` | Stop a target agent when the resolved authority supports it. |

### Passive-Server-Owned Headless Agents


| Method | Path | Description |
|---|---|---|
| `POST` | `/houmao/agents/headless/launches` | Launch a passive-server-owned headless agent. |
| `POST` | `/houmao/agents/{agent_ref}/turns` | Submit a headless turn. |
| `GET` | `/houmao/agents/{agent_ref}/turns/{turn_id}` | Inspect turn status. |
| `GET` | `/houmao/agents/{agent_ref}/turns/{turn_id}/events` | Read structured turn events. |
| `GET` | `/houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/{name}` | Read a turn artifact such as stdout or stderr. |

## houmao-mgr Compatibility

`houmao-mgr` commands that accept pair-authority options can target passive-server. When no explicit port is supplied for a server-backed pair authority, manager code defaults to passive-server port `9891`.

Common examples:

```bash
houmao-mgr agents global list --port 9891
houmao-mgr agents single --agent-name <name> state --port 9891
houmao-mgr agents single --agent-name <name> prompt --port 9891 --prompt "Summarize your status."
houmao-mgr agents single --agent-name <name> gateway status --port 9891
houmao-mgr agents single --agent-name <name> mail list --channel offline --port 9891 --read-state unread
houmao-mgr agents single --agent-name <name> turn submit --port 9891 --prompt "Run the next step."
```

Use local `houmao-mgr agents single --agent-id <id> gateway attach|detach` or `houmao-mgr agents self gateway attach|detach` on the host that owns the tmux session; passive-server does not remotely spawn or tear down gateway processes.

## Runtime Layout

Passive-server stores listener metadata and server-owned headless state under the selected runtime root:

```text
<runtime-root>/
  houmao_servers/
    <host>-<port>/
      run/
        current-instance.json
      managed_agents/
        <tracked-agent-id>/
          authority.json
          turns/
            <turn-id>/
              record.json
              stdout.jsonl
              stderr.txt
```

Passive-server reads and writes shared registry records under the selected registry root:

```text
<registry-root>/
  live_agents/
    <agent-id>/
      record.json
```

## See Also

- [houmao-mgr](houmao-mgr.md) — primary management CLI
- [Shared Registry Reference](../registry/index.md) — filesystem registry read by passive-server
- [Agent Gateway Reference](../gateway/index.md) — gateway subsystem proxied by passive-server
- [Managed Agent API](../managed_agent_api.md) — HTTP payload reference shared by manager-compatible routes
