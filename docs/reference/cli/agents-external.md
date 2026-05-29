# houmao-mgr agents external

Local imports for remotely owned, communication-only managed agents.

External records let one local `houmao-mgr` address an agent that is owned by another `houmao-passive-server`. The local registry stores only locator metadata and a cached identity snapshot; stop, relaunch, cleanup, attach, detach, and tmux/current-session workflows remain owned by the remote host.

```
houmao-mgr agents external [OPTIONS] COMMAND [ARGS]...
```

## Commands

| Command | Purpose |
| --- | --- |
| `register` | Verify a remote passive server and create or replace one local external import. |
| `list` | List local external records from the registry without polling remote servers. |
| `get` | Show one local external record and cached identity. |
| `verify` | Contact the remote authority, refresh cached identity, and update `verified_at_utc`. |
| `remove` | Delete only the local external import. The remote agent is not stopped or detached. |

## register

```
houmao-mgr agents external register --name <local-name> --api-base-url <url> --agent-ref <remote-ref> [--gateway-enabled] [--replace]
```

| Option | Description |
| --- | --- |
| `--name TEXT` | Local unprefixed alias for the external import. Must not collide with a local lifecycle record. |
| `--api-base-url TEXT` | Remote `houmao-passive-server` base URL, for example `http://127.0.0.1:9899`. |
| `--agent-ref TEXT` | Remote managed-agent id or name as understood by the remote authority. |
| `--gateway-enabled / --no-gateway-enabled` | Require gateway status to be reachable during register and verify. Defaults to disabled. |
| `--replace` | Replace an existing external import with the same local name. Without this flag, an existing external import is rejected. |

Example:

```bash
houmao-mgr agents external register \
  --name teammate-coder \
  --api-base-url http://127.0.0.1:9899 \
  --agent-ref remote-coder \
  --gateway-enabled
```

## list

```
houmao-mgr agents external list
```

`list` reads `<registry-root>/external_agents/*/record.json` locally. It does not contact remote authorities, so it remains useful when a remote host is offline.

## get, verify, remove

```
houmao-mgr agents external get --agent-name <local-name>
houmao-mgr agents external verify --agent-id <external-agent-id>
houmao-mgr agents external remove --agent-name <local-name>
```

`get`, `verify`, and `remove` accept exactly one of `--agent-id` or `--agent-name`. For this command family, `--agent-id` means the local `external_agent_id` stored in the external registry collection.

## Normal Command Support

After registration, the same selector can be used with these communication-safe commands:

| Supported command | Routing |
| --- | --- |
| `agents list` | Uses cached local external records. |
| `agents state` | Calls the stored remote pair API and annotates the response as external. |
| `agents prompt` | Calls the stored remote pair API with the stored remote agent ref. |
| `agents interrupt` | Calls the stored remote pair API with the stored remote agent ref. |
| `agents gateway status` | Calls the stored remote pair API. |
| `agents gateway prompt` | Calls the stored remote pair API. |
| `agents gateway interrupt` | Calls the stored remote pair API. |
| `agents mail ...` | Calls the stored remote pair API for supported mail operations. |

Unsupported local-owner operations fail clearly and leave the external record untouched: `agents stop`, `agents relaunch`, `agents cleanup ...`, `agents gateway attach`, `agents gateway detach`, `agents gateway send-keys`, gateway TUI/reminder/mail-notifier mutation, and selector flows based on the current local tmux session.

## Secure Exposure

Do not expose `houmao-passive-server` directly on an untrusted network. Prefer a trusted channel such as SSH local forwarding, VPN, Tailscale, or a secured reverse proxy with access control. The external registry record stores the base URL you provide, so use a URL whose trust boundary is stable for every local operator that can read the registry.
