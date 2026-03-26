# Code Review: `passive-server-requests-and-headless`

Reviewed change:
- `openspec/changes/passive-server-requests-and-headless`

Reviewed implementation:
- `src/houmao/passive_server/headless.py`
- `src/houmao/passive_server/service.py`
- `src/houmao/passive_server/app.py`
- `src/houmao/passive_server/models.py`

Review basis:
- OpenSpec artifacts under `openspec/changes/passive-server-requests-and-headless/`
- Existing runtime/server implementations in `src/houmao/agents/realm_controller/` and `src/houmao/server/`
- No external web references used

## Summary

The implementation gets the route scaffolding in place, but several core Tier 7 behaviors are still broken or incomplete. The biggest issue is that launched headless agents are never published to the shared registry, so the follow-up `/turns`, `/interrupt`, and `/stop` routes cannot reliably address the agents that `/headless/launches` creates. Restart recovery and artifact/event persistence are also incomplete relative to the spec and the old server behavior.

## Findings

### 1. Launched headless agents are never published to the shared registry, so follow-up routes cannot address them

**Severity:** High

**Why this matters**

The Step 5 flow depends on a launched headless agent becoming discoverable so later calls like `POST /houmao/agents/{agent_ref}/turns`, `POST /interrupt`, and `POST /stop` can resolve `agent_ref`. The current implementation starts a runtime session and persists local authority, but never publishes a `LiveAgentRegistryRecordV2`.

**Evidence**

- `src/houmao/passive_server/headless.py:151-165` starts the session with `registry_launch_authority="external"`.
- `src/houmao/passive_server/headless.py:172-189` writes authority and stores the in-memory handle, but there is no explicit registry publication step afterward.
- `src/houmao/agents/realm_controller/runtime.py:589-613` shows `refresh_shared_registry_record()` only publishes when `registry_launch_authority == "runtime"`.
- `src/houmao/agents/realm_controller/runtime.py:842-856` shows `start_runtime_session()` itself does not override that authority here.
- `openspec/changes/passive-server-requests-and-headless/specs/passive-server-headless-management/spec.md:8-17` requires the launch endpoint to publish a shared-registry record.
- The old server explicitly does this extra step in `src/houmao/server/service.py:832-845`.

**Impact**

`POST /houmao/agents/headless/launches` can return `200`, but the returned agent will not be discoverable by the passive server’s own `_resolve_agent_or_error()` flow. In practice, the subsequent management routes can fail with `404` even though launch appeared successful.

**Suggestion**

After `start_runtime_session()`, explicitly publish the shared-registry record, equivalent to the old server’s `_publish_server_launched_registry_record()` path.

---

### 2. Managed-headless routing keys are inconsistent: handles are stored by `tracked_agent_id`, but service lookups use registry `agent_id`

**Severity:** High

**Why this matters**

Even if registry publication is added, the passive server still uses the wrong key when deciding whether an agent is server-managed headless. That makes `/interrupt`, `/stop`, and `/turns` fail for launches that provide a custom `agent_id`.

**Evidence**

- `src/houmao/passive_server/headless.py:181-189` stores the handle in `self.m_handles[tracked_agent_id]`.
- `src/houmao/passive_server/headless.py:476-488` shows `is_managed()` and `_require_handle()` expect a `tracked_agent_id`.
- `src/houmao/passive_server/service.py:317-321`, `357-361`, and `406-410` resolve the registry record, then pass `resolved.record.agent_id` into `is_managed()` / headless operations.
- `src/houmao/passive_server/headless.py:181` explicitly allows `agent_id` to differ from `tracked_agent_id`.

**Impact**

If launch is called with an explicit `agent_id`, the later service methods will look up the wrong key and treat the agent as non-managed, returning `400`/`502` or taking the wrong code path.

**Suggestion**

Normalize on one authoritative lookup key for server-managed headless agents. The safest option is to maintain a mapping from published registry `agent_id` back to `tracked_agent_id`, then route all managed operations through that mapping.

---

### 3. Restart rebuild does not resume `RuntimeSessionController`, so live agents lose turn submission and interrupt capability after server restart

**Severity:** High

**Why this matters**

The spec requires restart recovery for live headless agents. The current rebuild path only recreates a lightweight handle with `controller=None`, which leaves the live session unusable for turn submission and direct interrupt after restart.

**Evidence**

- `src/houmao/passive_server/headless.py:490-503` scans authorities and rebuilds handles.
- `src/houmao/passive_server/headless.py:499-501` explicitly says it does not resume the controller and stores `controller=None`.
- `src/houmao/passive_server/headless.py:217-221` makes `submit_turn()` return `503` when `controller is None`.
- `src/houmao/passive_server/headless.py:404-408` makes `interrupt_managed()` return `503` when `controller is None`.
- `openspec/changes/passive-server-requests-and-headless/specs/passive-server-headless-management/spec.md:100-115` requires live authorities to be resumed and remain available for turn submission.
- `src/houmao/agents/realm_controller/runtime.py:927-1009` already provides `resume_runtime_session()`.

**Impact**

After a passive-server restart, a still-live headless tmux session becomes effectively read-only: status may remain inspectable from files, but new turns and interrupts stop working.

**Suggestion**

Use `resume_runtime_session()` during rebuild for live authorities, mirroring the old server’s resumable-controller pattern.

---

### 4. Completed turns never persist `stdout_path` / `stderr_path`, so artifact and event endpoints break

**Severity:** High

**Why this matters**

The artifact and event endpoints depend on file paths stored in `ManagedHeadlessTurnRecord`. The current worker marks turns completed, but never records the generated artifact paths or completion metadata from the headless backend.

**Evidence**

- `src/houmao/passive_server/headless.py:522-538` updates the turn record after `send_prompt()` completes, but only sets `status`, `completed_at_utc`, `returncode`, and `completion_source`.
- `src/houmao/passive_server/headless.py:324-358` reads events only from `record.stdout_path`.
- `src/houmao/passive_server/headless.py:377-391` serves artifacts only from `record.stdout_path` / `record.stderr_path`.
- `src/houmao/agents/realm_controller/backends/headless_base.py:151-170` shows `send_prompt()` returns a final `"done"` event payload containing `stdout_path`, `stderr_path`, and `completion_source`.
- The old server’s refresh logic explicitly computes and persists those paths in `src/houmao/server/service.py:3485-3565`.

**Impact**

A turn can complete successfully, but `GET /turns/{turn_id}/events` returns an empty list and `GET /turns/{turn_id}/artifacts/stdout|stderr` returns `404` because the record was never updated with artifact locations.

**Suggestion**

On completion, reconcile the turn record from the turn artifact directory, at minimum persisting `stdout_path`, `stderr_path`, `status_path`, and the real `completion_source`. Reusing the old server’s refresh pattern would be the safest route.

---

### 5. Launch validation and mailbox handling do not meet the OpenSpec contract

**Severity:** Medium

**Why this matters**

The spec requires stricter launch validation and support for the full mailbox option set. The current implementation only does a subset of that work.

**Evidence**

- `src/houmao/passive_server/headless.py:111-130` validates path existence and backend kind, but does not validate that `tool` matches the manifest’s `inputs.tool`.
- The same block returns `400`, while the spec requires `422` for invalid working directory, tool mismatch, and unsupported backend (`openspec/.../passive-server-headless-management/spec.md:19-30`).
- `src/houmao/passive_server/headless.py:154-168` passes `role_name` directly into `start_runtime_session()` and turns any resulting exception into a generic `500`, instead of surfacing launch validation errors as client errors.
- `src/houmao/passive_server/headless.py:136-148` extracts only filesystem mailbox fields.
- `src/houmao/agents/realm_controller/runtime.py:657-664` accepts additional Stalwart mailbox fields, but `src/houmao/passive_server/headless.py:151-165` never forwards them.

**Impact**

Invalid launch requests can produce the wrong status code, tool/manifest mismatches are not rejected up front, and Stalwart mailbox launches cannot be fully configured through the passive server endpoint.

**Suggestion**

Before calling `start_runtime_session()`:

- load the brain manifest and verify `request.tool == manifest.inputs.tool`
- validate `role_name` if present
- return `422` for request-validation failures
- forward the full mailbox option set, including Stalwart fields

## Suggested next steps

1. Fix launch publication first; without it, the main Tier 7 workflow is not operational.
2. Normalize managed-agent lookup keys (`tracked_agent_id` vs `agent_id`).
3. Restore restart resumability with `resume_runtime_session()`.
4. Reconcile turn records from actual artifact files after completion.
5. Tighten launch validation/status codes and forward the full mailbox config.
