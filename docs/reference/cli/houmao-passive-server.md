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
| `GET` | `/houmao/agents/{agent_ref}/gateway/mail-notifier` | Mail-notifier status. |
| `PUT` | `/houmao/agents/{agent_ref}/gateway/mail-notifier` | Enable or reconfigure the mail notifier. |
| `DELETE` | `/houmao/agents/{agent_ref}/gateway/mail-notifier` | Disable the mail notifier. |
| `GET` | `/houmao/agents/{agent_ref}/gateway/reminders` | List gateway reminders. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/reminders` | Create reminders. |
| `GET` | `/houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}` | Read one reminder. |
| `PUT` | `/houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}` | Replace or update one reminder. |
| `DELETE` | `/houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}` | Delete one reminder. |

### Mail Proxy

Mail routes proxy through the agent gateway.

| Method | Path | Description |
|---|---|---|
| `GET` | `/houmao/agents/{agent_ref}/mail/status` | Mailbox status. |
| `POST` | `/houmao/agents/{agent_ref}/mail/list` | List mailbox messages. |
| `POST` | `/houmao/agents/{agent_ref}/mail/peek` | Peek at one message. |
| `POST` | `/houmao/agents/{agent_ref}/mail/read` | Read one message. |
| `POST` | `/houmao/agents/{agent_ref}/mail/send` | Send a message. |
| `POST` | `/houmao/agents/{agent_ref}/mail/post` | Post an operator-origin message. |
| `POST` | `/houmao/agents/{agent_ref}/mail/reply` | Reply to a message. |
| `POST` | `/houmao/agents/{agent_ref}/mail/mark` | Mark messages. |
| `POST` | `/houmao/agents/{agent_ref}/mail/move` | Move messages. |
| `POST` | `/houmao/agents/{agent_ref}/mail/archive` | Archive messages. |

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
houmao-mgr agents single --agent-name <name> mail list --port 9891 --read-state unread
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
