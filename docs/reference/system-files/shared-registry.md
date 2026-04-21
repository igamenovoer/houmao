# Shared Registry

This page is the centralized filesystem reference for the shared managed-agent lifecycle registry: where the registry root lives, which directories Houmao creates there, and how that filesystem stays pointer-oriented instead of becoming a second runtime state store.

## Registry Layout

Representative default layout:

```text
~/.houmao/registry/
  live_agents/
    <agent-id>/
      record.json
```

The registry root is independent from the runtime root. The published runtime session root can live anywhere else on disk; the registry stores pointers to that state rather than moving the session under the registry root.

## Artifact Inventory

| Path pattern | Created by | Later written by | Purpose | Contract level | Cleanup notes |
| --- | --- | --- | --- | --- | --- |
| `<registry-root>/` | registry publication and cleanup helpers | whichever launcher, stopper, relauncher, or cleanup command owns the record action | Shared per-user registry root | Stable path family | Durable while registry-backed lifecycle discovery is in use |
| `<registry-root>/live_agents/` | registry publication and cleanup helpers | whichever launcher, stopper, relauncher, or cleanup command owns the record action | Parent directory for one directory per authoritative managed `agent_id` | Stable path family | Durable |
| `<registry-root>/live_agents/<agent-id>/` | launcher creating the lifecycle record | launcher refresh flows, stop/relaunch flows, or later cleanup actor | One managed-agent lifecycle directory keyed by authoritative `agent_id` | Stable path family | Remove only when stale or when cleanup explicitly purges the lifecycle record |
| `<registry-root>/live_agents/<agent-id>/record.json` | launcher creating the lifecycle record | launcher refresh flows, stop/relaunch flows, or later cleanup actor | Strict secret-free lifecycle record for one managed-agent identity; active records carry liveness and optional gateway metadata, while stopped or retired records preserve durable runtime pointers and last-known tmux identity | Stable operator-facing artifact | Durable across stop/relaunch until cleanup retires or purges it |

Temporary sibling files may appear briefly during atomic rewrites, but they are implementation details rather than part of the durable registry contract.

## Record Contract Boundary

`record.json` is intentionally pointer-oriented. It may point to:

- the runtime `manifest.json`,
- the runtime session root,
- gateway attach or status files,
- mailbox identity metadata when mailbox bindings exist.

It does not copy:

- the full session manifest payload,
- gateway queue state,
- mailbox contents,
- secrets.

The current active standalone schema for this artifact is `managed_agent_registry_record.v3.schema.json`, and the current typed boundary in live code is `ManagedAgentRegistryRecordV3`. Legacy v2 live records are still accepted on load and are upgraded to active lifecycle records in memory.

For `houmao_server_rest` sessions, including server-backed managed-session flows, the registry continues to publish pointers back to the Houmao-owned runtime manifest and session root rather than copying runtime state into the registry record.

## Ownership Notes

- Shared-registry creation follows launch authority. Whoever launches the live agent creates the record.
- Shared-registry lifecycle updates follow termination and cleanup authority. Authoritative stop for relaunchable tmux-backed local sessions publishes a stopped record; later session cleanup retires that record by default or purges it when the operator explicitly asks.
- Discovery by `houmao-server` does not, by itself, transfer registry ownership or trigger republishing of an already valid external record.
- Runtime-managed manifests, tmux bindings, gateway metadata, and mailbox pointers remain available regardless of who created the registry record, so another launcher can publish a pointer-oriented record without copying runtime state.
- The registry directory key is authoritative `agent_id`, not the retired `agent_key`.
- Canonical agent name remains persisted metadata inside the record and remains part of lookup semantics, but it is not the on-disk directory key.
- Malformed or expired records are treated as stale discovery state rather than as authoritative runtime state.

Legacy `live_agents/<agent-key>/` directories left over from pre-cutover versions are historical cleanup artifacts, not part of the active lookup contract.

## Related References

- [Shared Registry Reference](../registry/index.md): Discovery, cleanup, and publication semantics.
- [Operator Preparation](operator-preparation.md): Registry-root permissions, relocation, and cleanup guidance.

## Source References

- [`src/houmao/owned_paths.py`](../../../src/houmao/owned_paths.py)
- [`src/houmao/agents/realm_controller/registry_storage.py`](../../../src/houmao/agents/realm_controller/registry_storage.py)
- [`src/houmao/agents/realm_controller/registry_models.py`](../../../src/houmao/agents/realm_controller/registry_models.py)
- [`src/houmao/agents/realm_controller/schemas/managed_agent_registry_record.v3.schema.json`](../../../src/houmao/agents/realm_controller/schemas/managed_agent_registry_record.v3.schema.json)
