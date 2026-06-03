# Shared Registry Record And Layout

This page explains the static contract around the shared registry: where it lives, how lifecycle-record directories are named, what `record.json` contains, and what the registry intentionally does not store.

For the broader Houmao filesystem map and operator-facing preparation guidance, use [System Files / Shared Registry](../../system-files/shared-registry.md) and [Operator Preparation](../../system-files/operator-preparation.md).

## Mental Model

The registry layout is deliberately small.

- one per-user root,
- one directory per authoritative local lifecycle `agent_id`,
- one directory per local external communication-only `external_agent_id`,
- one authoritative `record.json` file per directory.

That keeps cross-process coordination simple and avoids central hot files such as `index.json` or SQLite.

## Effective Registry Root

The runtime resolves the shared-registry root in this order:

1. `HOUMAO_GLOBAL_REGISTRY_DIR` when it is set to a non-empty absolute path,
2. otherwise `<platformdirs user config>/registry`, where the anchor is `platformdirs.user_config_path(appname="houmao", appauthor=False)`.

Current implementation notes:

- the override is mainly for CI, tests, and similarly controlled environments,
- relative override paths are rejected,
- the default home anchor is derived through `platformdirs`-aware logic rather than a hardcoded Linux-only `/home/<user>` assumption.

## On-Disk Layout

Representative layout:

```text
<platformdirs user config>/registry/
  live_agents/
    <agent-id>/
      record.json
  external_agents/
    <external-agent-id>/
      record.json
```

Rules:

- `live_agents/` holds the set of lifecycle-record directories keyed by authoritative logical `agent_id`,
- `external_agents/` holds communication-only imports for remotely owned agents, keyed by local `external_agent_id`,
- `<agent-id>` is the authoritative runtime-wide agent identifier,
- the only durable file the runtime expects inside that directory is `record.json`,
- temporary files may appear briefly during atomic writes but are cleaned on replace failure.

The runtime session root itself can live anywhere else on disk. The registry stores pointers to that runtime-owned state rather than moving it under the registry root.

External records are different: they do not point to local runtime session roots. They store local locator metadata for a remote `houmao-passive-server` plus a cached identity snapshot for offline listing.

## Record Shape

The strict persisted contract is now shipped in two complementary forms:

- a packaged JSON Schema at `src/houmao/agents/realm_controller/schemas/managed_agent_registry_record.v3.schema.json` for the structural disk contract, and
- strict Pydantic models in `registry_models.py` for typed construction, load validation, semantic invariants, and compatibility upgrades from legacy v2 live records.

Representative active record with optional gateway and mailbox metadata present:

```json
{
  "schema_version": 3,
  "agent_name": "HOUMAO-gpu",
  "agent_id": "270b8738f2f97092e572b73d19e6f923",
  "generation_id": "98cc9a0d-d1fd-4c56-b49c-871274e28f98",
  "lifecycle": {
    "state": "active",
    "relaunchable": true,
    "state_updated_at": "2026-03-13T12:00:00+00:00",
    "stopped_at": null,
    "stop_reason": null
  },
  "identity": {
    "backend": "codex_headless",
    "tool": "codex"
  },
  "runtime": {
    "manifest_path": "/abs/path/runtime/sessions/codex_headless/codex-1/manifest.json",
    "session_root": "/abs/path/runtime/sessions/codex_headless/codex-1",
    "agent_def_dir": "/abs/path/repo/.houmao/agents"
  },
  "terminal": {
    "kind": "tmux",
    "current_session_name": "HOUMAO-gpu-1741867200000",
    "last_session_name": "HOUMAO-gpu-1741867200000"
  },
  "liveness": {
    "published_at": "2026-03-13T12:00:00+00:00",
    "lease_expires_at": "2026-03-14T12:00:00+00:00"
  },
  "gateway": {
    "host": "127.0.0.1",
    "port": 43123,
    "state_path": "/abs/path/runtime/sessions/codex_headless/codex-1/gateway/state.json",
    "protocol_version": "v1"
  },
  "mailbox": {
    "transport": "filesystem",
    "principal_id": "HOUMAO-research",
    "address": "HOUMAO-research@agents.localhost",
    "filesystem_root": "/abs/path/shared-mail",
    "bindings_version": "2026-03-13T12:00:00.123456+00:00"
  }
}
```

## Field Groups

### Identity

`identity` tells readers what kind of managed session they are looking at.

- `backend`: runtime backend kind such as `cao_rest` or `claude_headless`
- `tool`: non-empty tool identifier string

### Lifecycle

`lifecycle` describes whether the record is actively routable, stopped but still relaunchable or cleanable, transiently relaunching, or retired after destructive cleanup.

- `state`: one of `active`, `stopped`, `relaunching`, or `retired`
- `relaunchable`: whether the runtime can honestly relaunch the preserved session
- `state_updated_at`: timestamp for the current lifecycle transition
- `stopped_at`: required for `stopped` and `retired`
- `stop_reason`: optional stop/retirement provenance for `stopped` and `retired`

### Runtime

`runtime` points back to authoritative runtime-owned artifacts.

- `manifest_path`: required absolute path to the persisted session manifest
- `session_root`: optional runtime-owned session root
- `agent_def_dir`: optional agent-definition root that name-based fallback can reuse

### Terminal

`terminal` is the terminal-container hint for the published session.

Current implementation scope:

- `kind` is `tmux`,
- `terminal.current_session_name` is present only for active or relaunching records,
- `terminal.last_session_name` is always preserved and remains the durable last-known tmux handle even after stop,
- the convenience view `terminal.session_name` resolves to `current_session_name` first and `last_session_name` second.

### Liveness

`liveness` appears only for active or relaunching records.

- `published_at` and `lease_expires_at` are active-only freshness metadata,
- stopped and retired records clear `liveness` entirely.

### Gateway

`gateway` appears only when live gateway connect metadata exists on an active or relaunching record.

- `host`, `port`, `state_path`, and `protocol_version` appear together as one complete live-binding group when a live gateway is attached.
- detached or stopped sessions omit `gateway` entirely.
- This field group is locator metadata for fresh discovery and diagnostics. It does not replace the durable manifest authority, and once the session root is known the authoritative local live-gateway record is `<session-root>/gateway/run/current-instance.json`.

### Mailbox

`mailbox` appears only when mailbox bindings exist for the session.

- `transport`
- `principal_id`
- `address`
- `filesystem_root`
- `bindings_version`

### External Communication-Only Records

External records use the separate schema `external_managed_agent_registry_record.v1.schema.json` and the model `ExternalManagedAgentRegistryRecordV1`.

Representative record:

```json
{
  "schema_version": 1,
  "kind": "external_communication_only",
  "local_name": "teammate-coder",
  "external_agent_id": "external-9e6dd9a4c8b54f0492741f033b9b7f1a",
  "generation_id": "42d1f894-ea2f-4f49-a4e3-e472c266857b",
  "pair_api_base_url": "http://127.0.0.1:9899",
  "remote_agent_ref": "remote-coder",
  "gateway_expected": true,
  "lifecycle_owner": "remote",
  "created_at_utc": "2026-05-29T00:00:00+00:00",
  "updated_at_utc": "2026-05-29T00:00:00+00:00",
  "verified_at_utc": "2026-05-29T00:00:00+00:00",
  "cached_identity": {
    "tracked_agent_id": "remote-coder",
    "transport": "headless",
    "tool": "codex",
    "agent_name": "remote-coder",
    "agent_id": "remote-agent-id",
    "lifecycle_state": "active"
  }
}
```

Field semantics:

- `local_name`: local unprefixed alias used by `--agent-name`.
- `external_agent_id`: local id used by `--agent-id` for this external collection.
- `pair_api_base_url`: normalized remote `houmao-passive-server` URL.
- `remote_agent_ref`: id or name sent to the remote pair authority.
- `gateway_expected`: whether register and verify require remote gateway status to be reachable.
- `lifecycle_owner`: always `remote`; local commands must not stop, relaunch, clean, attach, or detach the remote lifecycle.
- `cached_identity`: remote identity snapshot used for local listing without remote polling.

Registration and verification contact the remote passive server, resolve `remote_agent_ref`, and refresh `cached_identity` plus `verified_at_utc`. Cleanup of stale local lifecycle records only scans `live_agents/`; valid external records are preserved until `houmao-mgr agents external remove` deletes the local import.

## What The Registry Does Not Store

The registry is intentionally secret-free and pointer-oriented.

It does not copy:

- full `manifest.json` payloads,
- gateway queue state,
- mailbox contents or mailbox SQLite data,
- environment snapshots,
- secrets.

External records also do not copy remote runtime-owned state. They store only a base URL, remote ref, timestamps, gateway expectation, and cached identity.

That boundary is the main reason the registry can stay small and safe to inspect.

## Migration Notes

- Legacy `live_agent_registry_record.v2` payloads are still accepted on load. They are upgraded to `ManagedAgentRegistryRecordV3` with `lifecycle.state=active`, `terminal.current_session_name == terminal.last_session_name == <legacy session_name>`, and legacy freshness fields mapped into active-only `liveness`.
- Pre-change stopped sessions that never published a lifecycle-aware record are still reachable only through bounded runtime-root scans used by `agents single ... relaunch` and `agents single ... cleanup`. Once such a session is revived or cleaned, the lifecycle registry becomes authoritative again.

## Current Implementation Notes

- `lifecycle.state_updated_at`, `lifecycle.stopped_at`, and active `liveness` timestamps must be timezone-aware ISO-8601 timestamps.
- `agent_name` must already be in canonical `HOUMAO-...` form inside the stored record.
- `agent_id` must be a non-empty path-safe identifier and is the on-disk directory key.
- `terminal.last_session_name` is always required for tmux-backed lifecycle records.
- Active and relaunching records require `liveness` and `terminal.current_session_name`.
- Stopped and retired records must clear `liveness`, `gateway`, and `terminal.current_session_name`.
- Runtime-managed publish and refresh flows validate serialized payloads against the packaged schema before atomically replacing `record.json`.
- External publish and verify flows validate serialized payloads against `external_managed_agent_registry_record.v1.schema.json` before atomically replacing `record.json`.
- Cross-field invariants such as canonical-name enforcement, lifecycle-state requirements, active lease ordering, and complete live gateway field grouping remain model-enforced rather than schema-only.
- Older `agent_key`-keyed registry directories are not part of a compatibility path in this change and remain manual cleanup.

## Source References

- [`src/houmao/agents/realm_controller/registry_models.py`](../../../../src/houmao/agents/realm_controller/registry_models.py)
- [`src/houmao/agents/realm_controller/registry_storage.py`](../../../../src/houmao/agents/realm_controller/registry_storage.py)
- [`src/houmao/agents/realm_controller/schemas/managed_agent_registry_record.v3.schema.json`](../../../../src/houmao/agents/realm_controller/schemas/managed_agent_registry_record.v3.schema.json)
- [`src/houmao/agents/realm_controller/schemas/external_managed_agent_registry_record.v1.schema.json`](../../../../src/houmao/agents/realm_controller/schemas/external_managed_agent_registry_record.v1.schema.json)
- [`docs/reference/system-files/shared-registry.md`](../../system-files/shared-registry.md)
- [`tests/unit/agents/realm_controller/test_registry_storage.py`](../../../../tests/unit/agents/realm_controller/test_registry_storage.py)
