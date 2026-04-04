# System Files Reference

This subtree is the centralized reference for filesystem paths that Houmao creates, selects, or relies on during normal runtime, registry, and server lifecycles.

Use it when you need to answer questions like:

- which directories Houmao will create,
- which files are durable contracts versus current implementation details,
- which roots can be redirected,
- which paths should be writable before launch,
- which directories are safe to treat as scratch.

Mailbox is intentionally out of scope here because it is a separate filesystem subsystem with its own reference tree. Use [Mailbox Reference](../mailbox/index.md) for mailbox-owned roots and contracts.

## Quick Map

Representative Houmao-owned roots for maintained local-state command flows:

```text
<active-overlay>/
  runtime/
  jobs/
  mailbox/                  # documented separately

~/.houmao/
  registry/
```

Representative runtime-owned layout:

```text
<active-overlay>/runtime/
  homes/<home-id>/
  manifests/<home-id>.yaml
  sessions/<backend>/<session-id>/
  houmao_servers/<host>-<port>/
```

Representative registry-owned layout:

```text
~/.houmao/registry/
  live_agents/<agent-id>/record.json
```

Representative launcher-owned layout:

```text
<runtime-root>/cao_servers/<host>-<port>/
  launcher/
  home/
```

## Read By Goal

For maintained local-state command surfaces, `runtime/`, `jobs/`, and `mailbox/` now default from one active project overlay. The shared `~/.houmao/` anchor remains the default home for registry state and the explicit legacy-root target for operators who intentionally override runtime or mailbox placement.

- [Roots And Ownership](roots-and-ownership.md): Default roots, override precedence, ownership categories, and the mailbox boundary.
- [Agents And Runtime](agents-and-runtime.md): Generated homes, generated manifests, runtime session roots, nested gateway files, and overlay-local job directories.
- [Legacy CAO Server](cao-server.md): Historical reference for the retired standalone CAO launcher layout.
- [Houmao Server](houmao-server.md): Server-owned listener roots, registration bridges, and memory-primary live tracking.
- [Shared Registry](shared-registry.md): Registry root placement, `live_agents/<agent-id>/record.json`, and the registry’s pointer-oriented scope.
- [Operator Preparation](operator-preparation.md): Pre-creation, permissions, redirection surfaces, ignore rules, and cleanup expectations.

## Related References

- [Runtime-Managed Agents Reference](../agents/index.md): Session lifecycle, targeting, and recovery behavior.
- [Shared Registry Reference](../registry/index.md): Registry semantics, discovery, and cleanup behavior.
- [Agent Gateway Reference](../gateway/index.md): Gateway protocol, queue behavior, and lifecycle handling.
- [Houmao Server Pair](../houmao_server_pair.md): Supported pair boundary and backend identity.

## Source References

- [`src/houmao/owned_paths.py`](../../../src/houmao/owned_paths.py)
- [`src/houmao/agents/brain_builder.py`](../../../src/houmao/agents/brain_builder.py)
- [`src/houmao/agents/realm_controller/manifest.py`](../../../src/houmao/agents/realm_controller/manifest.py)
- [`src/houmao/agents/realm_controller/gateway_storage.py`](../../../src/houmao/agents/realm_controller/gateway_storage.py)
- [`src/houmao/agents/realm_controller/registry_storage.py`](../../../src/houmao/agents/realm_controller/registry_storage.py)
- [`src/houmao/cao/server_launcher.py`](../../../src/houmao/cao/server_launcher.py)
