# houmao-passive-server

Registry-first passive server for distributed agent coordination.

`houmao-passive-server` is a lightweight FastAPI application that discovers agents from the shared filesystem registry and provides coordination, observation, and proxy services on top of them. Unlike `houmao-server`, this server has no legacy compatibility layer, no child process supervision, and no registration-backed session admission.

## Synopsis

```
houmao-passive-server [OPTIONS] COMMAND [ARGS]...
```

## When to Use: Passive Server vs houmao-server

| Concern | `houmao-passive-server` | `houmao-server` |
|---|---|---|
| Architecture | Stateless, registry-driven discovery | Stateful, registration-backed session management |
| Agent launch | Headless agents only (via `/houmao/agents/headless/launches`) | Full managed lifecycle: build, launch, stop, relaunch |
| TUI agents | Observes existing TUI agents via registry + tmux polling | Owns and supervises TUI agent processes |
| Child processes | None — does not spawn or supervise agent processes for TUI agents | Spawns and monitors child CAO processes |
| Gateway interaction | Proxies requests to agent-owned gateways | Owns gateways directly |
| CAO compatibility | None | Full CAO compatibility layer |
| Default port | 9891 | 9889 |
| Ideal for | Distributed coordination of independently launched agents | Centralized agent lifecycle management |

Use `houmao-passive-server` when agents are launched independently (via `houmao-mgr agents launch` or `houmao-mgr agents join`) and you need a coordination layer for discovery, observation, and gateway proxying without centralized process ownership.

## Commands

### `serve`

Start the passive server.

```
houmao-passive-server serve [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--host TEXT` | `127.0.0.1` | Host address to bind the server to. |
| `--port INT` | `9891` | Port to listen on. |
| `--runtime-root PATH` | Project-aware default | Root directory for runtime state and the shared agent registry. Falls back to `HOUMAO_GLOBAL_RUNTIME_DIR` or the active project overlay's runtime root. |

## API Routes

All routes are served under the `/houmao/` prefix. Agent-scoped routes use `{agent_ref}` which accepts either an agent ID or agent name.

### Health and Metadata

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check. Returns `{"status": "ok"}`. |
| `GET` | `/houmao/server/current-instance` | Server metadata: PID, API URL, runtime root, start timestamp. |
| `POST` | `/houmao/server/shutdown` | Request graceful server shutdown. |

### Agent Discovery

| Method | Path | Description |
|---|---|---|
| `GET` | `/houmao/agents` | List all discovered agents from the shared registry. |
| `GET` | `/houmao/agents/{agent_ref}` | Resolve one agent by ID or name. Returns 404 if not found, 409 on ambiguous name match. |

Discovery works by periodically scanning the shared filesystem registry (default: every 5 seconds). An agent is considered live when its registry record exists, its lease is fresh, and its tmux session is running.

### TUI Observation

These routes expose the passive server's own TUI tracking for discovered agents. The server polls tmux panes, parses terminal output, and tracks state transitions independently.

| Method | Path | Description |
|---|---|---|
| `GET` | `/houmao/agents/{agent_ref}/state` | Compact TUI state: diagnostics, surface summary, turn phase, stability. |
| `GET` | `/houmao/agents/{agent_ref}/state/detail` | Full TUI state with probe snapshot and parsed surface. |
| `GET` | `/houmao/agents/{agent_ref}/history` | Recent state transitions (default limit: 50). |
| `GET` | `/houmao/agents/{agent_ref}/managed-state` | TUI state projected into managed-agent compatible format. |
| `GET` | `/houmao/agents/{agent_ref}/managed-state/detail` | Managed-agent compatible detail with diagnostics. |
| `GET` | `/houmao/agents/{agent_ref}/managed-history` | Managed-agent compatible history (default limit: 50). |

### Gateway Proxy

These routes proxy to the agent's own gateway process. They return 502 if no gateway is attached to the target agent.

| Method | Path | Description |
|---|---|---|
| `GET` | `/houmao/agents/{agent_ref}/gateway` | Gateway status for one agent. |
| `GET` | `/houmao/agents/{agent_ref}/gateway/tui/state` | Gateway-owned TUI tracking state. |
| `GET` | `/houmao/agents/{agent_ref}/gateway/tui/history` | Gateway-owned TUI snapshot history. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/tui/note-prompt` | Record prompt-note provenance in the gateway tracker. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/requests` | Create a gateway request (prompt, interrupt, etc.). |
| `POST` | `/houmao/agents/{agent_ref}/gateway/control/prompt` | Submit prompt through the gateway. |
| `POST` | `/houmao/agents/{agent_ref}/gateway/control/send-keys` | Send raw control input through the gateway. |
| `GET` | `/houmao/agents/{agent_ref}/gateway/mail-notifier` | Mail-notifier status, including effective `appendix_text`, `context_error_policy`, and `pre_notification_context_action`. |
| `PUT` | `/houmao/agents/{agent_ref}/gateway/mail-notifier` | Enable or reconfigure mail-notifier. Omitted `appendix_text` is preserved, non-empty text replaces it, and `""` clears it. Optional `context_error_policy` and `pre_notification_context_action` select degraded-context handling and pre-notification compaction. |
| `DELETE` | `/houmao/agents/{agent_ref}/gateway/mail-notifier` | Disable mail-notifier without clearing stored appendix text. |

Gateway attach and detach are local-only operations (`POST .../gateway/attach` and `.../gateway/detach` return 501 Not Implemented). Use `houmao-mgr agents gateway attach` directly on the host where the agent runs.

### Mail Proxy

Mail routes also proxy through the agent's gateway.

| Method | Path | Description |
|---|---|---|
| `GET` | `/houmao/agents/{agent_ref}/mail/status` | Mailbox status. |
| `POST` | `/houmao/agents/{agent_ref}/mail/list` | List mailbox messages. |
| `POST` | `/houmao/agents/{agent_ref}/mail/peek` | Peek at one mailbox message without marking it read. |
| `POST` | `/houmao/agents/{agent_ref}/mail/read` | Read one mailbox message and mark it read. |
| `POST` | `/houmao/agents/{agent_ref}/mail/send` | Send a mail message. |
| `POST` | `/houmao/agents/{agent_ref}/mail/post` | Post an operator-origin mailbox note. |
| `POST` | `/houmao/agents/{agent_ref}/mail/reply` | Reply to a mail message. |
| `POST` | `/houmao/agents/{agent_ref}/mail/mark` | Mark selected mailbox messages. |
| `POST` | `/houmao/agents/{agent_ref}/mail/move` | Move selected mailbox messages. |
| `POST` | `/houmao/agents/{agent_ref}/mail/archive` | Archive selected mailbox messages. |

### Request Submission

| Method | Path | Description |
|---|---|---|
| `POST` | `/houmao/agents/{agent_ref}/requests` | Submit prompt request to the agent's gateway. |
| `POST` | `/houmao/agents/{agent_ref}/interrupt` | Interrupt the agent. |
| `POST` | `/houmao/agents/{agent_ref}/stop` | Stop the agent. |

### Headless Agent Management

The passive server can launch and manage headless agents with durable turn tracking. These are server-owned agents with persistent state.

| Method | Path | Description |
|---|---|---|
| `POST` | `/houmao/agents/headless/launches` | Launch a new headless agent. |
| `POST` | `/houmao/agents/{agent_ref}/turns` | Submit a turn to a headless agent. |
| `GET` | `/houmao/agents/{agent_ref}/turns/{turn_id}` | Get turn status. |
| `GET` | `/houmao/agents/{agent_ref}/turns/{turn_id}/events` | Get structured events from a turn. |
| `GET` | `/houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/{name}` | Get a turn artifact (stdout or stderr). |

Headless agents launched by the passive server are recovered on server restart: persisted authority records are replayed and surviving agents are re-registered in the shared registry.

## houmao-mgr Compatibility

Most `houmao-mgr` commands work with the passive server when targeting it via `--port 9891`:

- `houmao-mgr agents list --port 9891` — lists discovered agents
- `houmao-mgr agents state --port 9891 --agent-name <name>` — shows agent state
- `houmao-mgr agents prompt --port 9891 --agent-name <name>` — submits prompt via gateway proxy
- `houmao-mgr agents gateway status --port 9891 --agent-name <name>` — shows gateway status
- `houmao-mgr agents mail list --port 9891 --agent-name <name> --read-state unread` — lists unread mailbox items via gateway proxy
- `houmao-mgr agents turn submit --port 9891 --agent-name <name>` — submits headless turn

Gateway attach/detach are local-only and must be run directly on the agent's host, not through the passive server.

## Runtime Layout

The passive server stores its state under the runtime root:

```
<runtime-root>/
  houmao_servers/
    <host>-<port>/
      run/
        current-instance.json    # server PID and metadata marker
      managed_agents/
        <tracked-agent-id>/      # per headless agent state
          authority.json
          turns/
            <turn-id>/
              record.json
              stdout.jsonl
              stderr.txt
```

## See Also

- [houmao-server](houmao-server.md) — stateful server with full agent lifecycle management
- [houmao-mgr](houmao-mgr.md) — primary management CLI
- [Shared Registry Reference](../registry/index.md) — the filesystem registry that the passive server reads
- [Agent Gateway Reference](../gateway/index.md) — gateway subsystem that the passive server proxies
