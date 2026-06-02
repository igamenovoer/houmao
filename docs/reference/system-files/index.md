# System Files Reference

This subtree is the centralized reference for filesystem paths that Houmao creates, selects, or relies on during normal runtime, registry, and maintained passive-server lifecycles.

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
  memory/
  mailbox/                  # documented separately

<platformdirs user config>/
  registry/
```

Representative runtime-owned layout:

```text
<active-overlay>/runtime/
  homes/<home-id>/
  manifests/<home-id>.yaml
  loop-runs/pairwise-v2/<run-id>/   # legacy retained runtime-family reference
  sessions/<backend>/<session-id>/
  houmao_servers/<host>-<port>/       # passive-server listener/headless state
```

Representative registry-owned layout:

```text
<platformdirs user config>/registry/
  live_agents/<agent-id>/record.json
```

## Read By Goal

For maintained local-state command surfaces, `runtime/`, managed-agent memory state under `memory/`, and `mailbox/` now default from one active project overlay. The shared `<platformdirs user config>/` anchor remains the default home for registry state and the explicit legacy-root target for operators who intentionally override runtime or mailbox placement.

- [Roots And Ownership](roots-and-ownership.md): Default roots, override precedence, ownership categories, and the mailbox boundary.
- [Agents And Runtime](agents-and-runtime.md): Generated homes, generated manifests, runtime-owned loop-run recovery records, runtime session roots, nested gateway files, and per-agent memory directories.
- [Legacy CAO Server](cao-server.md): Historical reference for the retired standalone CAO launcher layout.
- [Retired Houmao Server](houmao-server.md): Historical/internal notes for retained old-server state shapes; not a maintained executable.
- [Shared Registry](shared-registry.md): Registry root placement, `live_agents/<agent-id>/record.json`, and the registry’s pointer-oriented scope.
- [Operator Preparation](operator-preparation.md): Pre-creation, permissions, redirection surfaces, ignore rules, and cleanup expectations.

## Related References

- [Session Lifecycle](../run-phase/session-lifecycle.md): Session lifecycle, targeting, and recovery behavior.
- [Shared Registry Reference](../registry/index.md): Registry semantics, discovery, and cleanup behavior.
- [Agent Gateway Reference](../gateway/index.md): Gateway protocol, queue behavior, and lifecycle handling.
- [Passive Server API](../cli/houmao-passive-server.md): Maintained server API surface and passive-server runtime layout.

## Source References

- [`src/houmao/owned_paths.py`](../../../src/houmao/owned_paths.py)
- [`src/houmao/agents/brain_builder.py`](../../../src/houmao/agents/brain_builder.py)
- [`src/houmao/agents/realm_controller/manifest.py`](../../../src/houmao/agents/realm_controller/manifest.py)
- [`src/houmao/agents/realm_controller/gateway_storage.py`](../../../src/houmao/agents/realm_controller/gateway_storage.py)
- [`src/houmao/agents/realm_controller/registry_storage.py`](../../../src/houmao/agents/realm_controller/registry_storage.py)
