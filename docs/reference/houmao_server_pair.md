# Retired Houmao Server Pair

This page is historical reference only. The former `houmao-server` + `houmao-mgr server ...` pair is retired as a public operator workflow, and the package no longer installs a standalone `houmao-server` executable.

Use the maintained surfaces instead:

```bash
houmao-mgr --help
houmao-passive-server serve --port 9891
```

## What Replaced It

`houmao-mgr` remains the primary local management CLI for project overlays, agent launch and join, gateway attach, mailbox workflows, credentials, cleanup, and system-skill installation.

`houmao-passive-server` is the maintained server/API authority. It discovers running agents from the shared registry, observes local tmux-backed agents, proxies to attached gateways, exposes mailbox and memory proxy routes, and can own native headless agents with durable turn records.

## Retired Surfaces

The following old surfaces are no longer maintained public workflows:

- `houmao-server` as a packaged executable
- `houmao-mgr server start|status|stop|sessions ...`
- `houmao-cli`
- `houmao-cao-server`
- standalone `/cao/*` compatibility routes
- new runtime manifests with `backend = "houmao_server_rest"`

Some Python modules under `src/houmao/server/` remain importable because maintained manager and passive-server code still use shared models, compatibility records, TUI helpers, or managed-headless storage shapes. That module location is internal support only and does not imply a supported standalone server product.

## Migration Guide

Use these replacements for current workflows:

| Old intent | Maintained path |
|---|---|
| Start the server API | `houmao-passive-server serve --port 9891` |
| Launch a local managed agent | `houmao-mgr agents launch ...` |
| Adopt an existing tmux agent | `houmao-mgr agents join ...` |
| Attach or inspect a gateway on the owning host | `houmao-mgr agents gateway ...` |
| Inspect or prompt through a server API authority | `houmao-mgr agents state|prompt|mail|turn ... --port 9891` or passive-server `/houmao/agents/*` routes |
| Manage passive-server-owned headless turns | `houmao-mgr agents turn ... --port 9891` or `/houmao/agents/{agent_ref}/turns` |
| Recognize old server filesystem artifacts | [Retired Houmao Server Filesystem Notes](system-files/houmao-server.md) |

## Current References

- [houmao-mgr CLI](cli/houmao-mgr.md)
- [houmao-passive-server CLI and API](cli/houmao-passive-server.md)
- [Managed-Agent API](managed_agent_api.md)
- [Agent Gateway Reference](gateway/index.md)
- [System Files Reference](system-files/index.md)
