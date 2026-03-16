# Shared Registry Record And Layout

This page explains the static contract around the shared registry: where it lives, how live-agent directories are named, what `record.json` contains, and what the registry intentionally does not store.

For the broader Houmao filesystem map and operator-facing preparation guidance, use [System Files / Shared Registry](../../system-files/shared-registry.md) and [Operator Preparation](../../system-files/operator-preparation.md).

## Mental Model

The registry layout is deliberately small.

- one per-user root,
- one directory per authoritative live `agent_id`,
- one authoritative `record.json` file per directory.

That keeps cross-process coordination simple and avoids central hot files such as `index.json` or SQLite.

## Effective Registry Root

The runtime resolves the shared-registry root in this order:

1. `AGENTSYS_GLOBAL_REGISTRY_DIR` when it is set to a non-empty absolute path,
2. otherwise `<resolved-user-home>/.houmao/registry`.

Current implementation notes:

- the override is mainly for CI, tests, and similarly controlled environments,
- relative override paths are rejected,
- the default home anchor is derived through `platformdirs`-aware logic rather than a hardcoded Linux-only `/home/<user>` assumption.

## On-Disk Layout

Representative layout:

```text
~/.houmao/registry/
  live_agents/
    <agent-id>/
      record.json
```

Rules:

- `live_agents/` holds the set of directories that are candidates for currently live logical agent ids,
- `<agent-id>` is the authoritative runtime-wide agent identifier,
- the only durable file the runtime expects inside that directory is `record.json`,
- temporary files may appear briefly during atomic writes but are cleaned on replace failure.

The runtime session root itself can live anywhere else on disk. The registry stores pointers to that runtime-owned state rather than moving it under the registry root.

## Record Shape

The strict persisted contract is now shipped in two complementary forms:

- a packaged JSON Schema at `src/houmao/agents/realm_controller/schemas/live_agent_registry_record.v2.schema.json` for the structural disk contract, and
- strict Pydantic models in `registry_models.py` for typed construction, load validation, and semantic invariants.

Representative record with optional gateway and mailbox metadata present:

```json
{
  "schema_version": 2,
  "agent_name": "AGENTSYS-gpu",
  "agent_id": "270b8738f2f97092e572b73d19e6f923",
  "generation_id": "98cc9a0d-d1fd-4c56-b49c-871274e28f98",
  "published_at": "2026-03-13T12:00:00+00:00",
  "lease_expires_at": "2026-03-14T12:00:00+00:00",
  "identity": {
    "backend": "cao_rest",
    "tool": "codex"
  },
  "runtime": {
    "manifest_path": "/abs/path/runtime/sessions/cao_rest/cao-rest-1/manifest.json",
    "session_root": "/abs/path/runtime/sessions/cao_rest/cao-rest-1",
    "agent_def_dir": "/abs/path/repo/.agentsys/agents"
  },
  "terminal": {
    "kind": "tmux",
    "session_name": "AGENTSYS-gpu"
  },
  "gateway": {
    "gateway_root": "/abs/path/runtime/sessions/cao_rest/cao-rest-1/gateway",
    "attach_path": "/abs/path/runtime/sessions/cao_rest/cao-rest-1/gateway/attach.json",
    "host": "127.0.0.1",
    "port": 43123,
    "state_path": "/abs/path/runtime/sessions/cao_rest/cao-rest-1/gateway/state.json",
    "protocol_version": "v1"
  },
  "mailbox": {
    "transport": "filesystem",
    "principal_id": "AGENTSYS-research",
    "address": "AGENTSYS-research@agents.localhost",
    "filesystem_root": "/abs/path/shared-mail",
    "bindings_version": "2026-03-13T12:00:00.123456+00:00"
  }
}
```

## Field Groups

### Identity

`identity` tells readers what kind of live session they are looking at.

- `backend`: runtime backend kind such as `cao_rest` or `claude_headless`
- `tool`: non-empty tool identifier string

### Runtime

`runtime` points back to authoritative runtime-owned artifacts.

- `manifest_path`: required absolute path to the persisted session manifest
- `session_root`: optional runtime-owned session root
- `agent_def_dir`: optional agent-definition root that name-based fallback can reuse

### Terminal

`terminal` is the terminal-container hint for the published session.

Current implementation scope:

- `kind` is `tmux`,
- `terminal.session_name` is the actual tmux session handle and does not need to equal the canonical `agent_name`.

### Gateway

`gateway` appears only when stable or live gateway metadata exists.

- `gateway_root` and `attach_path` are the stable pointers,
- `host`, `port`, `state_path`, and `protocol_version` appear together as one complete live-binding group when a live gateway is attached,
- detached sessions can still publish stable gateway pointers without live host and port data.

### Mailbox

`mailbox` appears only when mailbox bindings exist for the session.

- `transport`
- `principal_id`
- `address`
- `filesystem_root`
- `bindings_version`

## What The Registry Does Not Store

The registry is intentionally secret-free and pointer-oriented.

It does not copy:

- full `manifest.json` payloads,
- gateway queue state,
- mailbox contents or mailbox SQLite data,
- environment snapshots,
- secrets.

That boundary is the main reason the registry can stay small and safe to inspect.

## Current Implementation Notes

- `published_at` and `lease_expires_at` must be timezone-aware ISO-8601 timestamps.
- `agent_name` must already be in canonical `AGENTSYS-...` form inside the stored record.
- `agent_id` must be a non-empty path-safe identifier and is the on-disk directory key.
- Runtime-managed publish and refresh flows validate serialized payloads against the packaged schema before atomically replacing `record.json`.
- Cross-field invariants such as canonical-name enforcement, lease ordering, and complete live gateway field grouping remain model-enforced rather than schema-only.
- Older `agent_key`-keyed registry directories are not part of a compatibility path in this change and remain manual cleanup.

## Source References

- [`src/houmao/agents/realm_controller/registry_models.py`](../../../../src/houmao/agents/realm_controller/registry_models.py)
- [`src/houmao/agents/realm_controller/registry_storage.py`](../../../../src/houmao/agents/realm_controller/registry_storage.py)
- [`src/houmao/agents/realm_controller/schemas/live_agent_registry_record.v2.schema.json`](../../../../src/houmao/agents/realm_controller/schemas/live_agent_registry_record.v2.schema.json)
- [`docs/reference/system-files/shared-registry.md`](../../system-files/shared-registry.md)
- [`tests/unit/agents/realm_controller/test_registry_storage.py`](../../../../tests/unit/agents/realm_controller/test_registry_storage.py)
