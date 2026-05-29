# Shared Registry

This page is the centralized filesystem reference for the shared managed-agent lifecycle registry: where the registry root lives, which directories Houmao creates there, and how that filesystem stays pointer-oriented instead of becoming a second runtime state store.

## Registry Layout

Representative default layout:

```text
~/.houmao/registry/
  live_agents/
    <agent-id>/
      record.json
  external_agents/
    <external-agent-id>/
      record.json
```

The registry root is independent from the runtime root. The published runtime session root can live anywhere else on disk; the registry stores pointers to that state rather than moving the session under the registry root.

External communication-only records are also registry-owned, but they are not local runtime pointers. They store a remote passive-server URL, a remote agent reference, verification timestamps, and cached identity data so local listing works without polling the remote host.

## Artifact Inventory

| Path pattern | Created by | Later written by | Purpose | Contract level | Cleanup notes |
| --- | --- | --- | --- | --- | --- |
| `<registry-root>/` | registry publication and cleanup helpers | whichever launcher, stopper, relauncher, or cleanup command owns the record action | Shared per-user registry root | Stable path family | Durable while registry-backed lifecycle discovery is in use |
| `<registry-root>/live_agents/` | registry publication and cleanup helpers | whichever launcher, stopper, relauncher, or cleanup command owns the record action | Parent directory for one directory per authoritative managed `agent_id` | Stable path family | Durable |
| `<registry-root>/live_agents/<agent-id>/` | launcher creating the lifecycle record | launcher refresh flows, stop/relaunch flows, or later cleanup actor | One managed-agent lifecycle directory keyed by authoritative `agent_id` | Stable path family | Remove only when stale or when cleanup explicitly purges the lifecycle record |
| `<registry-root>/live_agents/<agent-id>/record.json` | launcher creating the lifecycle record | launcher refresh flows, stop/relaunch flows, or later cleanup actor | Strict secret-free lifecycle record for one managed-agent identity; active records carry liveness and optional gateway metadata, while stopped or retired records preserve durable runtime pointers and last-known tmux identity | Stable operator-facing artifact | Durable across stop/relaunch until cleanup retires or purges it |
| `<registry-root>/external_agents/` | `houmao-mgr agents external register` | external register, verify, and remove commands | Parent directory for communication-only imports of remotely owned managed agents | Stable path family | Durable until explicitly removed |
| `<registry-root>/external_agents/<external-agent-id>/record.json` | `houmao-mgr agents external register` | external register and verify commands | Strict secret-free remote locator record with local alias, remote pair API base URL, remote agent ref, gateway expectation, timestamps, lifecycle owner `remote`, and cached identity | Stable operator-facing artifact | Preserved by stale local lifecycle cleanup; remove only with `agents external remove` |

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

The external import schema is `external_managed_agent_registry_record.v1.schema.json`, and the typed boundary is `ExternalManagedAgentRegistryRecordV1`. These records are locator metadata only: they never imply local ownership of the remote runtime, gateway sidecar, mailbox root, tmux session, manifest, or cleanup boundary.

For maintained tmux-backed managed sessions, the registry publishes pointers back to the Houmao-owned runtime manifest and session root rather than copying runtime state into the registry record. Legacy `houmao_server_rest` records may still be recognized as old artifacts, but new public launches do not create them.

## Ownership Notes

- Shared-registry creation follows launch authority. Whoever launches the live agent creates the record.
- Shared-registry lifecycle updates follow termination and cleanup authority. Authoritative stop for relaunchable tmux-backed local sessions publishes a stopped record; later session cleanup retires that record by default or purges it when the operator explicitly asks.
- Discovery by `houmao-passive-server` does not, by itself, transfer registry ownership or trigger republishing of an already valid external record.
- External records are owned by the local registry operator who imported them, but the managed-agent lifecycle owner remains the remote passive server. Local cleanup of `live_agents/` does not remove valid external records.
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
- [`src/houmao/agents/realm_controller/schemas/external_managed_agent_registry_record.v1.schema.json`](../../../src/houmao/agents/realm_controller/schemas/external_managed_agent_registry_record.v1.schema.json)
