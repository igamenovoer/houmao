# Shared Registry Resolution And Ownership

This page explains the dynamic rules around the shared registry: how names become keys, what makes a record fresh, how duplicate publishers are handled, and when registry state is treated as stale versus as a hard error.

## Mental Model

The registry resolves in two stages:

1. storage-level lookup decides whether there is a fresh usable record for a logical name,
2. runtime-level control validation decides whether the pointed-to manifest and agent-definition data are still safe to trust.

That distinction is why some failures collapse into “stale” while others still fail fast.

## Canonical Names And Agent Keys

Registry-facing input accepts either:

- canonical `AGENTSYS-gpu`, or
- unprefixed `gpu`.

The runtime canonicalizes both to `AGENTSYS-gpu` before:

- hashing,
- reading a record,
- publishing a record,
- comparing logical ownership.

`agent_key` is always:

```text
sha256(canonical agent_name).hexdigest()
```

Important consequences:

- prefixed and unprefixed input refer to the same logical identity,
- there is no second on-disk copy for the unprefixed form,
- readers can compute the directory path directly without scanning a shared index.

## Freshness And Lease Semantics

Freshness is lease-based, not directory-based.

- v1 uses a 24-hour soft lease,
- `lease_expires_at >= now` means the record is fresh,
- expired records are treated as stale even if the directory still exists,
- stale directories are expected after crashes and are cleaned later by `cleanup-registry`.

Timezone matters:

- `published_at` and `lease_expires_at` must include timezone information,
- naive timestamps are rejected rather than interpreted relative to the local machine timezone.

## Generation Ownership

`generation_id` answers “which live session instance currently owns this logical name?”

Rules:

- a new tmux-backed live session gets one `generation_id`,
- refreshes keep the same `generation_id`,
- resume reuses the persisted `generation_id` when the same live session is being reclaimed,
- a replacement publisher must use a different `generation_id`.

Fresh duplicate ownership is not allowed.

If a fresh record already exists for the same canonical `agent_name` with a different `generation_id`:

- the new publish attempt is rejected,
- later refreshes also re-check ownership so a losing publisher can stand down instead of quietly coexisting.

## Stale Versus Hard-Invalid Outcomes

The registry intentionally distinguishes “unusable stale state” from “this would target the wrong session.”

### Storage-level stale outcomes

`resolve_live_agent_record()` returns no live record when the stored `record.json` is:

- missing,
- malformed JSON,
- schema-invalid under the strict model,
- expired,
- published under a different canonical name than the requested key.

Those cases are treated as not-found or stale discovery state rather than as a live result.

### Runtime-level hard validation outcomes

After a fresh record is found, name-based control still validates the pointers it is about to trust.

That path still fails explicitly when:

- `runtime.manifest_path` is not absolute,
- the manifest file no longer exists,
- the resolved manifest backend is not tmux-backed,
- the persisted tmux session identity in the manifest does not match the addressed agent name,
- `runtime.agent_def_dir` is required but missing, non-absolute, or stale and no explicit `--agent-def-dir` override was supplied.

That split is intentional:

- malformed or expired registry state should not block recovery forever,
- but a fresh record that points at the wrong session should not silently recover to some other target.

## Known-Name Resolution Flow

At the registry-storage layer, known-name resolution is deterministic:

1. canonicalize the input name,
2. derive the full SHA-256 `agent_key`,
3. load `live_agents/<agent-key>/record.json`,
4. validate the strict record model,
5. reject stale records,
6. return the fresh record.

This means the common “find agent X” path does not require a shared index file or a full scan of `live_agents/`.

## Remove And Cleanup Ownership Boundaries

Two cleanup paths exist:

- targeted removal during authoritative runtime teardown,
- stale-directory cleanup through `cleanup-registry`.

Targeted teardown removal is guarded by `generation_id`:

- if the stored record still belongs to another generation, the caller does not remove it.

Stale cleanup is broader:

- missing `record.json`,
- malformed records,
- expired records beyond the cleanup grace period

are removal candidates regardless of who originally created them.

## Current Implementation Notes

- Publication is lock-free and uses compare-then-replace semantics, so the design tolerates a narrow race window while still requiring the losing generation to stand down later.
- Storage-level resolution returning `None` does not mean name-based runtime control will always succeed when a record exists; manifest and agent-definition validation still happens after record lookup.
- Explicit `--agent-def-dir` overrides beat registry-published `runtime.agent_def_dir`.

## Source References

- [`src/houmao/agents/realm_controller/registry_models.py`](../../../../src/houmao/agents/realm_controller/registry_models.py)
- [`src/houmao/agents/realm_controller/registry_storage.py`](../../../../src/houmao/agents/realm_controller/registry_storage.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../../../src/houmao/agents/realm_controller/runtime.py)
- [`tests/unit/agents/realm_controller/test_registry_storage.py`](../../../../tests/unit/agents/realm_controller/test_registry_storage.py)
- [`tests/unit/agents/realm_controller/test_runtime_agent_identity.py`](../../../../tests/unit/agents/realm_controller/test_runtime_agent_identity.py)
