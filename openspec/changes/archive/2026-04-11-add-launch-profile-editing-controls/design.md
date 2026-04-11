## Context

Project-local launch profiles share one catalog-backed object family with two user-facing lanes:

- easy profiles: `profile_lane=easy_profile`, `source_kind=specialist`, managed through `houmao-mgr project easy profile ...`
- explicit launch profiles: `profile_lane=launch_profile`, `source_kind=recipe`, managed through `houmao-mgr project agents launch-profiles ...`

The explicit lane already exposes `set`, and the shared CLI helper `_store_launch_profile_from_cli()` already knows how to patch an existing launch-profile row while preserving unspecified fields. The easy lane only exposes `create/list/get/remove`, so operators must manually remove and recreate an easy profile to change stored defaults. The catalog `store_launch_profile()` method is already an upsert, but the CLI helper deliberately rejects same-name creation before reaching that upsert.

## Goals / Non-Goals

**Goals:**

- Add a maintained easy-profile patch surface with the same stored-field coverage as explicit launch-profile `set`.
- Add an intentional, confirmation-gated same-lane replacement path for both easy-profile create and explicit launch-profile add.
- Preserve the distinction between patch and replace:
  - patch starts from the existing stored profile and changes only requested fields,
  - replace starts from empty create defaults and writes the supplied fields as the new complete profile.
- Prevent accidental cross-lane replacement even though the underlying catalog upsert can overwrite the `profile_lane` column.
- Rematerialize the compatibility projection after stored profile mutation.
- Keep live instances and already-written runtime manifests unchanged.

**Non-Goals:**

- No new persistent catalog schema or data migration.
- No ability to rename a launch profile in this change.
- No `project easy profile set --specialist ...`; source changes use replacement through `create --yes`.
- No interactive editor or direct YAML editing workflow.
- No change to launch-time one-shot overrides; they remain non-persistent.

## Decisions

### Decision 1: Add `project easy profile set` as a patch command

The easy-profile `set` command will accept the same categories of update and clear flags as explicit `launch-profiles set`: managed-agent identity, workdir, auth, memory binding, model, reasoning, prompt mode, env records, mailbox, launch posture, managed-header policy, and prompt overlay.

Rationale: the easy and explicit lanes share the same catalog model and reusable defaults. Having a smaller easy create surface is useful, but once a user has an easy profile, patching one stored field should not require manual remove/recreate.

Alternative considered: tell users to use `project agents launch-profiles set` against the projected profile. That would blur the lane boundary and risks treating specialist-backed profiles as recipe-backed explicit profiles. Keeping a dedicated easy command makes lane intent explicit.

### Decision 2: Model helper behavior as create, patch, or replace

The shared CLI storage helper should be extended with an operation mode instead of overloading `existing_name` alone:

- `create`: reject any existing profile name,
- `patch`: require an existing profile in the expected lane and preserve unspecified fields,
- `replace`: require an existing profile in the expected lane and start from empty create defaults.

Rationale: replacement is not the same as patch. If `project easy profile create --name alice --specialist reviewer-v2 --yes --workdir /repo` preserves an old prompt overlay only because the prior `alice` had one, the command would not behave like recreate. The operation mode keeps the data-flow obvious and testable.

Alternative considered: implement `--yes` by removing the old profile before calling the existing create path. That would work but creates a transient delete/write window and duplicates error handling. It also makes it easier to lose the stable catalog row semantics if later code starts depending on the row identity.

### Decision 3: Use `--yes`, not `--force`, for stored profile replacement

Same-name creation will use the repository's existing destructive authoring confirmation flag, `--yes`, on:

- `project easy profile create`,
- `project agents launch-profiles add`.

Rationale: `--force` already means managed launch takeover in this CLI family. Stored-profile replacement is an authoring overwrite, and `project easy specialist create` already uses `--yes` for non-interactive replacement confirmation.

Alternative considered: add `--force` to create/add. This would be shorter but would overload the force vocabulary with a different risk model.

### Decision 4: Enforce same-lane replacement before catalog upsert

When a create/add command sees an existing name:

- if the existing profile lane differs from the requested lane, fail even with `--yes`,
- if the lane matches and `--yes` is absent, prompt on interactive terminals or fail in non-interactive contexts with a rerun-with-`--yes` message,
- if the lane matches and `--yes` is present, perform replacement.

Rationale: the catalog table uses `name` as the unique key and its upsert can change `profile_lane`. The CLI must keep easy and explicit lanes from accidentally stealing the same profile name.

Alternative considered: permit cross-lane replacement with `--yes`. That would be surprising because the two lanes have different source semantics and different launch entry points.

## Risks / Trade-offs

- [Duplicated Click option lists between easy `set` and explicit `set`] → Prefer a small shared option decorator or helper only if it reduces real duplication without obscuring the CLI. Keep behavior tests as the primary guard.
- [Replacement unexpectedly preserving old optional fields] → Add tests that create a profile with optional advanced blocks, replace it with fewer fields, and verify omitted blocks are cleared.
- [Cross-lane overwrite through catalog upsert] → Check the existing row and expected lane in the CLI helper before calling `store_launch_profile()`.
- [Prompt overlay content ref staleness after replacement clears overlay] → Verify `get` and the projected YAML show no prompt overlay after replacement without overlay flags.
- [Operator confusion between launch-time override and stored edit] → Update docs to state that `instance launch ... --workdir` and `agents launch ... --workdir` stay one-shot, while `profile set` and `launch-profiles set` mutate future defaults.

## Migration Plan

No catalog migration is required. Existing profiles remain valid. Rollout is code and documentation only:

1. Add the new command and replacement mode.
2. Update docs and system-skill guidance.
3. Run focused unit tests for project profile CRUD and projection behavior.

Rollback is code rollback only. Profiles replaced while the change is active remain ordinary launch-profile catalog rows.

## Open Questions

None.
