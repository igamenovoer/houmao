# Shared Registry Reference

This section explains the shared managed-agent lifecycle registry: why it exists, what it publishes, and how it helps the runtime recover name-addressed sessions across different runtime roots.

If you are new to the subsystem, start with the mental model and the operations page. If you need exact record fields and on-disk layout, go to the contract pages. If you are debugging publication hooks or warning behavior, use the internals page.

For the broader Houmao filesystem map and operator-preparation guidance, use [System Files Reference](../system-files/index.md) and [System Files / Shared Registry](../system-files/shared-registry.md).

## Mental Model

The selected registry has two authorities. Lifecycle records locate runtime-owned sessions. Its configured filesystem mail store owns durable offline membership, address allocation, and mailbox history.

- Runtime-owned tmux-backed sessions publish one secret-free lifecycle record per authoritative `agent_id`, with canonical agent name kept as lookup metadata.
- Remotely owned communication-only agents can be imported into a separate `external_agents/` collection with local locator metadata and cached remote identity.
- Active records carry liveness metadata plus optional live gateway details; stopped and retired records preserve last-known tmux identity and runtime pointers for relaunch, cleanup, and diagnostics.
- Tmux-local discovery is still the first same-host lookup path when its pointers are present and valid.
- The registry provides same-host lifecycle discovery when tmux-local discovery is missing or stale.
- The selected offline store persists membership separately from lifecycle presence. A stopped body or expired lease does not release an address. Remote members use the narrow registry API without shared runtime paths.
- `manifest.json`, session-root artifacts, gateway files, and mailbox state remain authoritative.

The registry configuration associates one selected mail store with that authority. Membership mutations reject a different store instead of creating another implicit group. Runtime manifests remain the binding authority, and lifecycle JSON records contain only safe dual-channel mail projections.

For live gateway recovery, that means:

- the registry points callers at `runtime.manifest_path`,
- the manifest remains the durable stable authority,
- `<session-root>/gateway/run/current-instance.json` is the authoritative local live-gateway record once the session root is known.

## Key Terms

- `shared registry`: The per-user filesystem tree rooted at `<platformdirs user config>/registry` by default, or at `HOUMAO_GLOBAL_REGISTRY_DIR` when that override is set.
- `managed-agent lifecycle record`: The strict `record.json` payload stored for one managed-agent identity, whether the lifecycle state is active, stopped, relaunching, or retired.
- `external communication-only record`: A strict `record.json` payload for a remotely owned agent imported through `houmao-mgr agents external`; lifecycle owner is always remote.
- `canonical agent name`: The reserved-prefix form such as `HOUMAO-gpu`; registry-facing input also accepts unprefixed names such as `gpu`.
- `agent_id`: The authoritative runtime-wide agent identifier used as the live-agent directory name.
- `generation id`: The stable identifier for one live session instance; refreshes reuse it, replacement publishers do not.
- `lease freshness`: The active-only liveness rule based on `liveness.lease_expires_at`, not on whether the directory happens to exist.
- `locator layer`: A metadata layer that points to runtime-owned artifacts without replacing their authority.

## Read by Goal

### Start Here

- [Discovery And Cleanup](operations/discovery-and-cleanup.md): How name-based resolution falls back from tmux-local discovery to the registry, plus how `houmao-mgr admin cleanup registry` classifies stale state.

### Contracts

- [Record And Layout](contracts/record-and-layout.md): Effective root resolution, on-disk layout, record shape, and what is intentionally excluded from the registry.
- [Resolution And Ownership](contracts/resolution-and-ownership.md): Canonical naming, freshness, `generation_id`, duplicate-publisher conflicts, and the difference between stale and hard-invalid state.

### Internals

- [Runtime Integration](internals/runtime-integration.md): Where the runtime publishes, refreshes, persists, and clears registry state across session lifecycle actions.

## Current Scope

The current implementation documents what exists today:

- publication is for runtime-managed tmux-backed sessions,
- external imports are stored separately under `external_agents/` and are not local lifecycle records,
- records are validated through strict Pydantic models and the shipped v4 standalone JSON Schema,
- unsupported older lifecycle projections fail validation and require explicit backup and rebootstrap,
- lookup treats malformed or expired records as unusable stale state,
- the current typed boundary is `ManagedAgentRegistryRecordV3`.

## Migration Notes

The dual-mail format intentionally replaces the former single mailbox union. Back up unsupported application state and rebootstrap it with the current runtime. Reads do not generate missing IDs, upgrade old bindings, or reset retained mailbox stores. UUID generation applies to fresh agent creation; persisted explicit agent IDs remain opaque stable identities.

See [Offline Registry Setup](../mailbox/operations/offline-registry.md) for local store association, narrow server startup, private credentials, remote enrollment, and reconnect behavior. No cluster identifier is required.

## Related References

- [System Files / Shared Registry](../system-files/shared-registry.md): Centralized filesystem layout and ownership boundary for the registry root.
- [Session Lifecycle](../run-phase/session-lifecycle.md): The broader runtime session model that uses registry-backed discovery.
- [Agent Gateway Reference](../gateway/index.md): Stable and live gateway data that can be pointed to from registry records.
- [Mailbox Reference](../mailbox/index.md): Mailbox identity and binding metadata that may appear in registry records.
- [Realm Controller](../realm_controller.md): Broad runtime overview and CLI entry points.

## Source References

- [`src/houmao/agents/realm_controller/registry_models.py`](../../../src/houmao/agents/realm_controller/registry_models.py)
- [`src/houmao/agents/realm_controller/registry_storage.py`](../../../src/houmao/agents/realm_controller/registry_storage.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../../src/houmao/agents/realm_controller/runtime.py)
- [`tests/unit/agents/realm_controller/test_registry_storage.py`](../../../tests/unit/agents/realm_controller/test_registry_storage.py)
- [`tests/unit/agents/realm_controller/test_runtime_agent_identity.py`](../../../tests/unit/agents/realm_controller/test_runtime_agent_identity.py)
