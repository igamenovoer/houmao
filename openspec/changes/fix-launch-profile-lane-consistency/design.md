## Context

Issue `#24` is not a storage-model bug. The project catalog already records both easy profiles and explicit launch profiles with `profile_lane`, and the docs already describe them as two user-facing lanes over one shared launch-profile object family. The inconsistency lives in the command layer: explicit `list` filters correctly to `launch_profile`, explicit `get` does not enforce lane ownership, both remove surfaces delete by name without lane validation, and the current error path does not redirect the operator to the correct lane.

That means the repository is already carrying the right semantic distinction in the data model, but the public CLI contract leaks the shared storage shape in confusing ways. The fix should therefore tighten lane ownership at the maintained command surfaces instead of changing catalog schema, projection layout, or the shared launch-profile resolution model.

## Goals / Non-Goals

**Goals:**

- Make `project agents launch-profiles` consistently operate on explicit `launch_profile` entries only.
- Make `project easy profile` consistently operate on easy `easy_profile` entries only.
- Replace generic wrong-lane failures with clear redirect guidance to the correct command family.
- Preserve the current shared catalog and shared projection-path model while making command ownership explicit.
- Add regression coverage for wrong-lane `get`, `set`, and `remove`, plus lane-aware empty-list guidance.

**Non-Goals:**

- Unifying the easy and explicit lanes into one new launch-profile management surface.
- Changing the project catalog schema, projection tree layout, or launch-profile storage format.
- Making `project agents launch-profiles list` return easy profiles or making `project easy profile list` return explicit profiles.
- Reworking specialist-backed versus recipe-backed launch behavior outside the lane-consistency contract.

## Decisions

### 1. Keep the lane split and make command ownership strict

The fix should preserve the existing operator model: easy profiles belong to `project easy profile ...`, and explicit launch profiles belong to `project agents launch-profiles ...`.

This matches the current docs and spec posture better than introducing a unified CRUD surface after the fact. It also avoids broadening the scope from "make the existing split consistent" into "redesign launch-profile discovery."

Alternatives considered:

- Unify the CRUD surfaces and let either lane manage either stored profile. Rejected because it would collapse a documented ownership model and force a larger UX redesign than issue `#24` needs.
- Keep today's mixed behavior and only document it better. Rejected because cross-lane `get` and `remove` are surprising enough to look like bugs and can mutate the wrong resource.

### 2. Centralize wrong-lane detection and redirect messaging in shared command helpers

The current `_load_launch_profile_or_click()` helper in `project_common.py` already knows both the requested lane and the actual stored lane. It should become the shared place that raises action-aware wrong-lane errors with redirect guidance.

The helper should accept enough context to produce the correct redirect for verbs such as `get`, `set`, and `remove`, for example:

- explicit lane targeting an easy profile should redirect to `houmao-mgr project easy profile <verb> --name <name>`
- easy lane targeting an explicit profile should redirect to `houmao-mgr project agents launch-profiles <verb> --name <name>`

This lets all public command handlers share one error contract instead of embedding slightly different messages or forgetting lane checks.

Alternatives considered:

- Patch each command independently with handwritten error text. Rejected because the bug already exists due to uneven checks, and scattered fixes would drift again.
- Push lane validation into the catalog layer. Rejected because the catalog intentionally models the shared object family and should stay lane-agnostic.

### 3. Treat lane-specific remove helpers as lane-owning surfaces, not name-only pass-throughs

`project easy profile remove` currently reaches `remove_profile_metadata()`, which delegates straight to catalog removal by name. That helper lives in the easy-profile module, so it should enforce easy-lane ownership before deletion instead of behaving like a generic catalog shortcut.

Likewise, explicit remove should resolve and validate the stored profile against `launch_profile` before calling catalog deletion.

This keeps lane guarantees true even when a future caller reuses the lane-specific helper outside the CLI entrypoint.

Alternatives considered:

- Enforce lane checks only in the command functions and leave helper modules loose. Rejected because the helper naming already implies lane-specific semantics and the current pass-through behavior is what created the easy remove bug.

### 4. Keep list payloads stable and add an optional note when only the other lane has results

The list commands should remain lane-bounded and continue returning their current primary arrays (`launch_profiles` for explicit, `profiles` for easy). To address the discovery confusion without inventing a new mixed listing shape, each command should add an optional `note` field only when:

- the current lane returns zero matches, and
- one or more profiles exist in the other lane.

The note should be operator-facing and action-oriented, for example:

`No explicit launch profiles found. Found 3 easy profiles instead; use 'houmao-mgr project easy profile list'.`

This preserves current machine-facing shapes while adding enough guidance to turn an apparently empty result into an understandable lane boundary.

Alternatives considered:

- Include the other lane's profiles in the same list output. Rejected because it would blur ownership and make the lane-specific commands partially interchangeable again.
- Return no extra information on empty results. Rejected because that preserves the original issue's operator confusion.

### 5. Treat the change as a CLI contract fix with no data migration

No catalog migration or projection rewrite is needed. All required information already exists in `profile_lane`, and the shared projection path can remain unchanged.

The change is still behaviorally breaking for callers that relied on wrong-lane `get` or `remove`, so the docs and tests should describe that explicitly, but rollout remains a code-and-docs update rather than a storage migration.

Alternatives considered:

- Add a compatibility toggle that preserves old wrong-lane access. Rejected because the repository is explicitly willing to take breaking cleanup changes and this behavior is actively misleading.

## Risks / Trade-offs

- [Scripts may rely on wrong-lane `get` or `remove`] → Mitigation: keep the failure mode clear and redirecting, and document the behavioral break in the change artifacts and docs.
- [Adding a `note` field changes structured list output] → Mitigation: keep the existing array keys unchanged and make `note` purely additive and optional.
- [Action-aware redirect messaging could drift between lanes] → Mitigation: generate messages through one shared helper instead of duplicating strings in each command handler.
- [Future helper reuse could bypass lane enforcement again] → Mitigation: make lane-specific helper modules such as `project/easy.py` enforce their own lane semantics before delegating to catalog deletion.

## Migration Plan

1. Update shared command helpers to produce lane-aware redirect errors and optional cross-lane list notes.
2. Tighten explicit `get` and `remove` to validate `launch_profile` ownership before returning or deleting a resource.
3. Tighten easy remove helper and command flow to validate `easy_profile` ownership before deletion.
4. Add CLI regression tests for wrong-lane `get`, `set`, and `remove`, plus empty-list note behavior in both directions.
5. Update launch-profile documentation to explain that both lanes share storage and projection paths while still remaining lane-bounded management surfaces.

No persisted data migration or rollback plan is required beyond reverting the command-layer change if necessary, because stored project state remains unchanged.

## Open Questions

None at the proposal stage. The remaining work is choosing the exact redirect wording and optional note text while keeping the lane model unchanged.
