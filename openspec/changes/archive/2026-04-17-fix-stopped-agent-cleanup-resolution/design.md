## Context

`houmao-mgr agents stop` resolves a live managed agent through the shared registry, stops the backend, persists the manifest, and then clears the live-registry record. That is correct for a live locator: the stopped agent should no longer appear in `agents list` or route prompt/control actions.

The cleanup command family currently accepts `--agent-id`, `--agent-name`, `--manifest-path`, and `--session-root`. The path forms remain usable after stop, but the name/id forms require a fresh shared-registry record. This creates an operator trap: the system removes the convenient locator before post-stop cleanup, and neither `agents stop` nor `project easy instance stop` currently echoes the durable manifest/session-root locator needed for cleanup.

## Goals / Non-Goals

**Goals:**

- Make successful stop responses carry the durable cleanup locators that the runtime already knows.
- Let selector-based cleanup recover stopped sessions by scanning the effective runtime root when the live registry no longer has a fresh record.
- Keep fallback cleanup local, bounded, deterministic, and explicit on ambiguity.
- Update packaged agent-instance guidance so agents prefer durable path selectors after stop.

**Non-Goals:**

- Do not add stopped-session tombstones, a stopped-agent index, or any new registry state store.
- Do not make stopped sessions appear in ordinary `agents list` or live-control discovery.
- Do not let cleanup scan arbitrary filesystem roots outside Houmao-owned runtime roots.
- Do not change live prompt, interrupt, state, gateway, or mail targeting semantics.

## Decisions

1. Stop responses carry cleanup locators.

   Local `RuntimeSessionController` targets and pair-managed targets already have identity metadata before teardown. The stop path should capture `manifest_path` and `session_root` from the resolved target before clearing registry state and include those fields in the structured action response when known. This is simpler and more explicit than trying to reconstruct the locator from logs or registry state later.

   Alternative considered: rely on launch output. Rejected because cleanup is normally a follow-up to stop, and the system should not require the operator or a system-skill agent to preserve old launch output manually.

2. Runtime-root scanning is a cleanup-only fallback.

   When `agents cleanup session|logs|mailbox --agent-id` or `--agent-name` finds no fresh local registry record, cleanup should inspect the effective runtime root's session envelopes and match stopped or malformed manifests by persisted `agent_id` or `agent_name`. If exactly one stopped target matches, cleanup proceeds as if the caller had provided that session root. If multiple matches exist, the command fails with candidate metadata. If no match exists, the command fails with guidance to pass `--manifest-path`, `--session-root`, or a runtime-root override if supported.

   Alternative considered: extend general managed-agent discovery. Rejected because live-control commands should not address stopped sessions.

3. Do not introduce tombstones.

   A tombstone/index would create another lifecycle artifact with freshness, cleanup, migration, and ambiguity semantics. The chosen design uses already-authoritative runtime manifests plus explicit stop-returned locators. Runtime scanning is slower than an index, but it only runs for cleanup fallback after live-registry miss, which is not a hot path.

4. Preserve project-aware root behavior.

   The cleanup fallback should use the same project-aware runtime-root resolution rules as existing `admin cleanup runtime ...` commands unless the command grows or already has an explicit runtime-root override. This avoids scanning the wrong root when a repository has an active `.houmao/` overlay.

5. Guidance prefers path selectors after stop.

   `houmao-agent-instance` should teach agents to capture `manifest_path` or `session_root` from stop output and use those for post-stop cleanup. Name/id cleanup remains valid, but guidance should not present it as the primary post-stop route because it depends on fallback scanning once the live registry is gone.

## Risks / Trade-offs

- Ambiguous stopped sessions with the same friendly name -> fail closed and list candidate `agent_id`, `agent_name`, `manifest_path`, and `session_root` so the operator can choose a path selector.
- Runtime-root scan misses sessions in a non-default runtime root -> keep error messaging explicit and document the appropriate runtime-root override path where supported.
- Stop response models are shared across clients -> add optional fields so existing consumers continue to parse older responses.
- Malformed manifests may not expose `agent_id` or `agent_name` -> selector fallback cannot recover those by name/id; path selectors remain the supported authority for malformed envelopes.
- Extra filesystem scanning cost -> only run after fresh registry lookup fails for cleanup selectors, and limit the search to runtime-owned session envelopes.

## Migration Plan

No stored data migration is required. Existing stopped sessions become cleanup-addressable by path immediately and by name/id only when their persisted manifest still carries matching identity metadata under the effective runtime root. Existing clients that ignore additional stop-response fields continue to work.

Rollback is straightforward: stop responses can keep the optional locator fields harmlessly, while cleanup fallback logic can be removed without changing manifest format or registry format.

## Open Questions

None for the selected scope. The user explicitly excluded a stopped-session tombstone/index.
