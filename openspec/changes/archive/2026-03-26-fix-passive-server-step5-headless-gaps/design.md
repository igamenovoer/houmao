## Context

The first Step 5 passive-server change established the route surface for request submission and headless management, but the implementation stopped short of a few runtime-critical behaviors. Review showed that launched headless agents are not explicitly published to the shared registry, managed lookups use inconsistent identifiers, restart rebuild recreates non-resumable handles, and completed turns do not persist the artifact metadata needed by status, event, and artifact endpoints.

The passive server already has the right building blocks: `start_runtime_session()` and `resume_runtime_session()` in the runtime layer, `publish_live_agent_record()` / `remove_live_agent_record()` in registry storage, and the old server’s managed-headless reconciliation logic in `src/houmao/server/service.py`. This follow-up should reuse those existing control-plane patterns instead of keeping a divergent partial implementation in `src/houmao/passive_server/headless.py`.

## Goals / Non-Goals

**Goals:**
- Make launched passive-server headless agents immediately discoverable through the shared registry.
- Ensure managed follow-up routes (`/turns`, `/interrupt`, `/stop`) can resolve server-managed headless agents even when callers use a published `agent_id` that differs from `tracked_agent_id`.
- Restore restart recovery by resuming authoritative `RuntimeSessionController` handles for live persisted headless agents.
- Persist completed-turn artifact metadata so status, events, and artifact endpoints are durable and correct.
- Bring launch validation and status codes back in line with the intended Step 5 contract, including full mailbox passthrough.

**Non-Goals:**
- Adding new Step 5 endpoints or changing the external route layout.
- Replacing `ManagedHeadlessStore` or moving it out of the old server package in this follow-up.
- Reworking the passive server into a generic managed-agent service beyond the reviewed gaps.
- Introducing direct tmux prompt delivery for non-gateway agents.

## Decisions

### Decision 1: Publish the shared-registry record explicitly after launch

The passive server will keep `registry_launch_authority="external"` when calling `start_runtime_session()`, then explicitly publish the runtime-built shared-registry record after launch succeeds. This mirrors the old server’s pattern and makes publication an intentional passive-server responsibility rather than an implicit side effect.

This preserves the design intent that the passive server owns publication for its server-managed launches while still reusing the runtime controller’s record-building logic.

**Alternatives considered:**
- Switch launch to `registry_launch_authority="runtime"` and rely on implicit runtime publication. Rejected because it hides the passive server’s contractual responsibility and makes rollback/error handling less explicit.
- Continue without explicit publication. Rejected because it leaves Step 5 launches undiscoverable.

### Decision 2: Normalize managed-headless resolution through tracked ids plus a secondary published-agent lookup

`HeadlessAgentService` will remain authoritative by `tracked_agent_id`, but it will also maintain enough information to resolve a server-managed headless agent from the published shared-registry `agent_id`. `PassiveServerService` will use a dedicated helper to translate a resolved discovered agent or direct agent reference into the correct managed `tracked_agent_id` before invoking managed operations.

This keeps the persisted authority model unchanged while making caller-visible routing robust for both default and custom launch identities.

**Alternatives considered:**
- Re-key all in-memory handles by `agent_id`. Rejected because `tracked_agent_id` remains the durable local authority key in `ManagedHeadlessStore`.
- Require callers to always use `tracked_agent_id`. Rejected because the launch flow intentionally publishes an external shared-registry identity and the server already accepts generic `{agent_ref}` values.

### Decision 3: Rebuild live headless authorities by resuming `RuntimeSessionController`

On startup, the passive server will scan persisted authorities, verify tmux liveness, and call `resume_runtime_session()` for live records. If resume succeeds, the in-memory handle becomes fully authoritative again. If resume fails or the tmux session is gone, the server will log the failure and clean up stale authority state.

This matches the Step 5 contract that restart recovery restores operable managed agents rather than read-only placeholders.

**Alternatives considered:**
- Keep `controller=None` after restart and treat the passive server as read-only until relaunch. Rejected because it breaks turn submission and interrupt after restart.
- Auto-stop any live tmux session that cannot be resumed. Rejected because resume failures should not silently destroy potentially salvageable sessions.

### Decision 4: Reconcile completed turns from durable artifact evidence

After `send_prompt()` returns, the passive server will refresh the persisted turn record from the turn artifact directory and/or the final `done` event payload. The refreshed record must include `stdout_path`, `stderr_path`, `status_path` when present, `completion_source`, and the final status/return code. Artifact and event endpoints will consume this durable record instead of guessing from partially populated state.

This follows the old server’s managed-headless refresh approach while keeping the passive-server implementation smaller.

**Alternatives considered:**
- Parse artifacts ad hoc inside each endpoint. Rejected because it duplicates logic and leaves persistent state incomplete.
- Store only the artifact directory and derive file paths on every request. Rejected because the contract already expects path fields in turn status and the refresh step is the authoritative place to finalize turn state.

### Decision 5: Restore launch-time validation and full mailbox passthrough

Before launch, the passive server will validate:
- `working_directory` is an existing directory
- `agent_def_dir` is an existing directory
- `brain_manifest_path` is an existing file
- `tool` matches the manifest’s `inputs.tool`
- `role_name`, when present, resolves successfully from the agent definition

Validation failures will return contract-matching client errors. The launch path will also forward the full mailbox option set, including Stalwart-specific fields, to `start_runtime_session()`.

**Alternatives considered:**
- Let `start_runtime_session()` surface all launch errors generically. Rejected because it produces the wrong status codes and hides contract-specific validation semantics.

## Risks / Trade-offs

- **[Risk] Resume logic can fail for partially corrupted persisted authorities** → Mitigation: treat resume as best effort, log the failure, and clean stale authority only when the session is clearly unusable.
- **[Risk] Adding a second managed-id lookup path can drift from persisted authority state** → Mitigation: derive the published-id mapping from persisted authority and/or the resumed controller rather than maintaining an unrelated cache.
- **[Risk] Turn refresh logic may still diverge from old server behavior if reimplemented loosely** → Mitigation: copy the old server’s artifact reconciliation shape closely instead of inventing a simplified variant.
- **[Trade-off] Explicit publication keeps passive-server logic slightly more verbose than pure runtime delegation** → Accepted because the lifecycle boundary remains clearer and easier to test.

## Migration Plan

1. Update `HeadlessAgentService.launch()` to perform explicit publication and persist the authoritative published identity mapping.
2. Add a managed-agent resolution helper used by `submit_turn()`, `interrupt_agent()`, and `stop_agent()`.
3. Replace rebuild placeholders with `resume_runtime_session()` for live authorities.
4. Refresh completed turn records from durable artifacts and update route tests around events/artifacts.
5. Tighten launch validation and mailbox forwarding, then rerun passive-server tests, lint, and typecheck.

Rollback is straightforward: the change is internal to passive-server Step 5 behavior and can be reverted without affecting the existing Step 1–4 route surface.

## Open Questions

- None. The review findings already give enough direction for a focused corrective change.
