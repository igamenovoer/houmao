# Shared Registry Resolution And Ownership

This page explains the dynamic rules around the shared registry: how canonical names relate to authoritative ids, what makes a record fresh, how duplicate publishers are handled, and when registry state is treated as stale versus as a hard error.

## Mental Model

The registry resolves in two stages:

1. storage-level lookup decides whether there is a fresh usable record for a logical name,
2. runtime-level control validation decides whether the pointed-to manifest and agent-definition data are still safe to trust.

That distinction is why some failures collapse into “stale” while others still fail fast.

## Canonical Names and Agent IDs

Registry-facing input accepts either:

- canonical `HOUMAO-gpu`, or
- unprefixed `gpu`.

Canonical names provide friendly lookup metadata. The immutable `agent_id` is the authoritative directory key and direct lookup surface. Distinct agents can share a name, so convenience lookup can report ambiguity. Prefixed and unprefixed selectors normalize to the same name lookup, which does not by itself establish logical ownership.

New agents generate UUIDs by default. Explicit `--agent-id-mode name-hash` retains deterministic name-derived IDs for callers that guarantee unique names. Supplied opaque IDs remain valid. Identical ID values denote the same logical agent worldwide; Houmao does not detect accidental collisions. Registry publication, resume, and refresh preserve the selected ID instead of deriving it from names or mail addresses. See [Agent Identity](../../run-phase/agent-identity.md) for creation and reuse examples.

## Freshness And Lease Semantics

Freshness is lease-based, not directory-based.

- v1 uses a 24-hour soft lease,
- `lease_expires_at >= now` means the record is fresh,
- expired records are treated as stale even if the directory still exists,
- stale directories are expected after crashes and are cleaned later by `houmao-mgr admin cleanup registry`.

Timezone matters:

- `published_at` and `lease_expires_at` must include timezone information,
- naive timestamps are rejected rather than interpreted relative to the local machine timezone.

## Generation Ownership

`generation_id` answers “which live session instance currently owns this logical name?”

Rules:

- a new tmux-backed live session gets one `generation_id`,
- a successful relaunch rotates the live generation even when it reuses the tmux envelope,
- refreshes keep the same `generation_id`,
- resume reuses the persisted `generation_id` when the same live session is being reclaimed,
- a replacement publisher must use a different `generation_id`,
- ownership conflicts are enforced on `agent_id`, not on canonical name alone.

Fresh duplicate ownership is not allowed.

An explicit relaunch can replace its captured old generation only when logical identity, backend identity, runtime pointers, execution binding, and tmux socket still match. Atomic publication runs under the logical owner's lock. Execution-bound controllers check the saved generation before control, and manifest writes compare the captured generation while holding the manifest lock. Manifest generation checks also block stale registry publication or teardown during the interval between committing the new manifest and replacing the registry projection.

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
- published under a different canonical name than the requested name lookup,
- ambiguous because more than one fresh `agent_id` matches the requested canonical name.

Those cases are treated as not-found or stale discovery state rather than as a live result.

### Runtime-level hard validation outcomes

After a fresh record is found, name-based control still validates the pointers it is about to trust.

That path still fails explicitly when:

- `runtime.manifest_path` is not absolute,
- the manifest file no longer exists,
- the resolved manifest backend is not tmux-backed,
- the persisted tmux session handle in the manifest does not match the addressed tmux session,
- the canonical agent name must be learned from manifest or registry metadata rather than inferred from tmux session naming alone,
- `runtime.agent_def_dir` is required but missing, non-absolute, or stale and no explicit `--agent-def-dir` override was supplied.

That split is intentional:

- malformed or expired registry state should not block recovery forever,
- but a fresh record that points at the wrong session should not silently recover to some other target.

## Known-Name Resolution Flow

Owner-local lifecycle records and `executor_agents/` locators form the managed discovery tier. A selector matching an execution locator enters its saved owner route before any local tmux probe or manifest reconstruction. Equivalent IDs/bindings deduplicate; different IDs sharing a friendly name, or different bindings claiming one ID, require explicit disambiguation or conflict repair. Existing local tmux aliases do not select a foreign owner. Communication-only imports remain a later tier, and explicit `--port` continues to bypass registry discovery.

A known execution route is a control boundary even when its owner is unavailable. Authorization failure, context mismatch, or lost transport does not authorize caller-local/default-server fallback. Listing queries owner state through the route; lifecycle-inclusive output preserves unreachable identities as unavailable with unknown transport/lifecycle, rather than claiming stopped state. The execution context qualifies returned native homes, runtime pointers, and gateway-loopback coordinates.

At the registry-storage layer, two lookup modes exist:

1. direct lookup by authoritative `agent_id` using `live_agents/<agent-id>/record.json`,
2. convenience lookup by canonical agent name by scanning live records and returning one unique fresh match.

Name-based lookup can therefore report ambiguity when multiple live `agent_id`s share one canonical name.

`houmao-mgr agents single --target-tmux-session <session> gateway status` matches the exact session name against fresh local registry records. A unique match selects its saved owner and socket even if the caller is in another tmux server. If more than one record matches, use the `--agent-id` from the diagnostic to select the intended peer. Use an agent ID or friendly name when selecting an explicit pair authority or delegated owner.

## Remove And Cleanup Ownership Boundaries

`admin executors forget --agent-id <id>` removes only a lexical operator execution locator. It does not stop the agent, remove owner files, or revoke independent communication imports. Local stale-presence cleanup does not apply local leases or tmux liveness to execution locators. Use owner-routed lifecycle operations for the agent itself.

When owner birth succeeds but operator locator publication fails, retain the admitted identity and inspect/reconcile that owner explicitly. `admin executors reconcile --executor <name> --agent-id <id>` verifies owner admission and binding before publishing the locator; it does not repeat birth or retarget an existing locator. See [execution context recovery](../../run-phase/execution-contexts.md#locators-and-recovery).

Two cleanup paths exist:

- targeted removal during authoritative runtime teardown,
- stale-directory cleanup through `houmao-mgr admin cleanup registry`.

Targeted teardown removal is guarded by `generation_id`:

- if the stored record still belongs to another generation, the caller does not remove it.

Stale cleanup is broader:

- missing `record.json`,
- malformed records,
- expired records beyond the cleanup grace period

are removal candidates regardless of who originally created them.

## Current Implementation Notes

- Publication serializes competing logical owners through a stable lock file and atomically replaces the registry projection. External systems and nonparticipating writers can still change independently, so every later control operation must revalidate its captured authority.
- Storage-level resolution returning `None` does not mean name-based runtime control will always succeed when a record exists; manifest and agent-definition validation still happens after record lookup.
- Explicit `--agent-def-dir` overrides beat registry-published `runtime.agent_def_dir`.

## Source References

- [`src/houmao/agents/realm_controller/registry_models.py`](../../../../src/houmao/agents/realm_controller/registry_models.py)
- [`src/houmao/agents/realm_controller/registry_storage.py`](../../../../src/houmao/agents/realm_controller/registry_storage.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../../../src/houmao/agents/realm_controller/runtime.py)
- [`tests/unit/agents/realm_controller/test_registry_storage.py`](../../../../tests/unit/agents/realm_controller/test_registry_storage.py)
- [`tests/unit/agents/realm_controller/test_runtime_agent_identity.py`](../../../../tests/unit/agents/realm_controller/test_runtime_agent_identity.py)
