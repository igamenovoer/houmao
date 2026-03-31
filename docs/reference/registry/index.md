# Shared Registry Reference

This section explains the shared live-agent registry: why it exists, what it publishes, and how it helps the runtime recover name-addressed sessions across different runtime roots.

If you are new to the subsystem, start with the mental model and the operations page. If you need exact record fields and on-disk layout, go to the contract pages. If you are debugging publication hooks or warning behavior, use the internals page.

For the broader Houmao filesystem map and operator-preparation guidance, use [System Files Reference](../system-files/index.md) and [System Files / Shared Registry](../system-files/shared-registry.md).

## Mental Model

The shared registry is a locator layer, not a replacement state store.

- Runtime-owned tmux-backed sessions publish one secret-free live record per authoritative `agent_id`, with canonical agent name kept as lookup metadata.
- Tmux-local discovery is still the first same-host lookup path when its pointers are present and valid.
- The registry is the fallback when tmux-local discovery is missing or stale.
- `manifest.json`, session-root artifacts, gateway files, and mailbox state remain authoritative.

Think of it as a per-user phonebook for live sessions:

- it tells the runtime where to look,
- it does not become the source of truth for the session itself.

For live gateway recovery, that means:

- the registry points callers at `runtime.manifest_path`,
- the manifest remains the durable stable authority,
- `<session-root>/gateway/run/current-instance.json` is the authoritative local live-gateway record once the session root is known.

## Key Terms

- `shared registry`: The per-user filesystem tree rooted at `~/.houmao/registry` by default, or at `HOUMAO_GLOBAL_REGISTRY_DIR` when that override is set.
- `live-agent record`: The strict `record.json` payload stored for one currently published logical agent.
- `canonical agent name`: The reserved-prefix form such as `HOUMAO-gpu`; registry-facing input also accepts unprefixed names such as `gpu`.
- `agent_id`: The authoritative runtime-wide agent identifier used as the live-agent directory name.
- `generation id`: The stable identifier for one live session instance; refreshes reuse it, replacement publishers do not.
- `lease freshness`: The v1 liveness rule based on `lease_expires_at`, not on whether the directory happens to exist.
- `locator layer`: A metadata layer that points to runtime-owned artifacts without replacing their authority.

## Read By Goal

### Start here

- [Discovery And Cleanup](operations/discovery-and-cleanup.md): How name-based resolution falls back from tmux-local discovery to the registry, plus how `houmao-mgr admin cleanup registry` classifies stale state.

### Contracts

- [Record And Layout](contracts/record-and-layout.md): Effective root resolution, on-disk layout, record shape, and what is intentionally excluded from the registry.
- [Resolution And Ownership](contracts/resolution-and-ownership.md): Canonical naming, freshness, `generation_id`, duplicate-publisher conflicts, and the difference between stale and hard-invalid state.

### Internals

- [Runtime Integration](internals/runtime-integration.md): Where the runtime publishes, refreshes, persists, and clears registry state across session lifecycle actions.

## Current Scope

The current implementation documents what exists today:

- publication is for runtime-managed tmux-backed sessions,
- records are validated through strict Pydantic models and the shipped v2 standalone JSON Schema,
- lookup treats malformed or expired records as unusable stale state,
- the current typed boundary is `LiveAgentRegistryRecordV2`.

## Related References

- [System Files / Shared Registry](../system-files/shared-registry.md): Centralized filesystem layout and ownership boundary for the registry root.
- [Runtime-Managed Agents Reference](../agents/index.md): The broader runtime session model that uses registry-backed discovery.
- [Agent Gateway Reference](../gateway/index.md): Stable and live gateway data that can be pointed to from registry records.
- [Mailbox Reference](../mailbox/index.md): Mailbox identity and binding metadata that may appear in registry records.
- [Realm Controller](../realm_controller.md): Broad runtime overview and CLI entry points.

## Source References

- [`src/houmao/agents/realm_controller/registry_models.py`](../../../src/houmao/agents/realm_controller/registry_models.py)
- [`src/houmao/agents/realm_controller/registry_storage.py`](../../../src/houmao/agents/realm_controller/registry_storage.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../../src/houmao/agents/realm_controller/runtime.py)
- [`tests/unit/agents/realm_controller/test_registry_storage.py`](../../../tests/unit/agents/realm_controller/test_registry_storage.py)
- [`tests/unit/agents/realm_controller/test_runtime_agent_identity.py`](../../../tests/unit/agents/realm_controller/test_runtime_agent_identity.py)
