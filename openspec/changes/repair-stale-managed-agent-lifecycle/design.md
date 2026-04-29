## Context

`houmao-mgr agents stop` and `houmao-mgr agents relaunch` already classify local tmux-backed active registry records as healthy, degraded, or stale before dispatch. Degraded means the recorded tmux session exists but the contractual primary surface is missing; stale means the recorded tmux session no longer exists.

The current stale/degraded recovery paths reconstruct a stopped-session controller and then publish through normal registry publication. That reconstruction can allocate a new registry generation before the old active record has been transitioned out of `active`, so the registry correctly rejects the write with an ownership conflict. Operators then see an internal conflict message and must discover cleanup commands manually.

## Goals / Non-Goals

**Goals:**

- Make verified stale/degraded active local records recoverable through `agents stop` without shared-registry ownership conflicts.
- Make `agents relaunch` revive the same logical managed-agent identity after verified stale/degraded local authority when preserved relaunch metadata is usable.
- Ensure unexpected `agents stop` failures include actionable guidance: known state, unknown state, artifact paths, and exact supported follow-up commands.
- Keep destructive cleanup guarded by Houmao-owned authority checks and explicit operator intent.

**Non-Goals:**

- Do not preserve legacy broken publish behavior.
- Do not kill tmux sessions based only on `HOUMAO-<agent-name>` prefix matching.
- Do not add a broad registry overwrite mode that bypasses ownership checks for healthy active records.
- Do not route relaunch through build-time `agents launch`.

## Decisions

1. Use a common broken-active recovery transition before stop or relaunch.

   Introduce a helper in the native managed-agent control layer that takes the currently resolved active registry record, revalidates it is still the expected generation, re-probes local tmux authority, and transitions only verified stale/degraded local records out of `active`.

   For stop, the helper publishes a stopped lifecycle record with the existing generation id when preserved relaunch authority remains readable. If the manifest or agent-definition authority is gone, it retires or removes the record through the existing cleanup semantics.

   For relaunch, the command first performs that same active-to-stopped transition, then uses the existing stopped-session revival path to create a new live generation. If revival fails after the transition, the record remains stopped/relaunchable instead of staying stuck as active.

   Alternative considered: let normal `publish_managed_agent_record` replace the active generation when a caller passes a force flag. Rejected because the registry layer cannot safely infer that the active owner is broken; the control path has the local tmux evidence.

2. Keep registry ownership checks strict by default.

   Normal publish continues rejecting writes over a fresh active generation. Any takeover helper must require an expected existing generation id and must only run after local stale/degraded authority has been verified immediately before mutation.

   Alternative considered: remove the conflicting record before every stale relaunch. Rejected because a failed revival would erase continuity unnecessarily. Transitioning to stopped keeps the identity recoverable.

3. Make stop failure output structured and command-oriented.

   `agents stop` should map unexpected failures into guidance text that states what completed and what did not complete. When a manifest path or session root is available, guidance should prefer exact cleanup selectors such as:

   ```text
   houmao-mgr agents cleanup session --manifest-path <path> --purge-registry --dry-run
   ```

   When only an identity is available, guidance should fall back to `--agent-id` or `--agent-name`. For destructive recovery, the first suggested command should be a dry run unless the operator already requested destructive cleanup.

   Alternative considered: emit only the raw exception and rely on docs. Rejected because lifecycle recovery happens during operational incidents, and the CLI already has enough context to provide the next supported command.

4. Treat leftover tmux reaping as authority-based cleanup.

   If stop guidance or future stop-integrated reaping mentions leftover tmux sessions, the implementation must identify Houmao-owned sessions through durable authority such as `HOUMAO_AGENT_ID` or `HOUMAO_MANIFEST_PATH`. Friendly-name or `HOUMAO-` prefix matching can be used for diagnostics but must not be the sole basis for killing sessions.

## Risks / Trade-offs

- [Race between probe and registry write] -> Re-read the registry record and compare the expected generation immediately before mutation; abort with guided output if the generation changed.
- [False stale/degraded classification] -> Re-probe tmux authority in the recovery helper instead of trusting an earlier resolver result.
- [Revival succeeds locally but registry publish fails] -> Preserve existing rollback cleanup for failed stopped-session revival and report exact recovery commands.
- [Guidance suggests a destructive command too eagerly] -> Suggest `--dry-run` first for purge/reap actions and include exact artifact selectors when known.
- [Additional recovery helper duplicates cleanup logic] -> Keep lifecycle mutation focused in one helper and reuse existing cleanup command behavior for full artifact deletion.

## Migration Plan

No stored data migration is required. Existing active records that are already stale or degraded can be recovered the next time an operator runs `houmao-mgr agents stop`, `houmao-mgr agents relaunch`, or the supported cleanup command.

Existing stopped records remain compatible with the current stopped-session revival path.

## Open Questions

- Should `agents stop` grow an explicit `--reap-leftovers` flag now, or should this change limit stop to correct lifecycle recovery plus exact cleanup guidance while keeping destructive artifact deletion under `agents cleanup session --purge-registry`?
