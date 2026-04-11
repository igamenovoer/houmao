## 1. Storage Helper Semantics

- [x] 1.1 Extend the launch-profile CLI storage helper to distinguish create, patch, and replace operations.
- [x] 1.2 Add same-lane conflict checks before catalog upsert so easy-profile and explicit-launch-profile names cannot replace each other.
- [x] 1.3 Add confirmation handling for replacement using the existing `--yes` destructive authoring pattern.
- [x] 1.4 Ensure replacement starts from empty create defaults while patch preserves unspecified existing fields.

## 2. Easy Profile CLI

- [x] 2.1 Add `houmao-mgr project easy profile set --name <profile>` with stored-field update and clear options matching the explicit launch-profile patch surface.
- [x] 2.2 Route easy-profile `set` through patch mode with `profile_lane=easy_profile` and `source_kind=specialist`.
- [x] 2.3 Add `--yes` to `project easy profile create` and route same-name same-lane replacement through replace mode.
- [x] 2.4 Keep easy-profile source changes out of `set`; use `create --yes` for replacing the source specialist.

## 3. Explicit Launch Profile CLI

- [x] 3.1 Add `--yes` to `project agents launch-profiles add`.
- [x] 3.2 Route same-name same-lane explicit launch-profile replacement through replace mode.
- [x] 3.3 Preserve the existing `project agents launch-profiles set` patch behavior.

## 4. Projection and Behavior Tests

- [x] 4.1 Add unit tests for `project easy profile set` patching a field while preserving prompt overlay or mailbox blocks.
- [x] 4.2 Add unit tests for easy-profile replacement clearing omitted optional fields and refreshing `.houmao/agents/launch-profiles/<name>.yaml`.
- [x] 4.3 Add unit tests for explicit launch-profile `add --yes` replacement clearing omitted optional fields and refreshing the projection.
- [x] 4.4 Add unit tests that `create` or `add` without `--yes` rejects same-name replacement in non-interactive mode.
- [x] 4.5 Add unit tests that `--yes` does not permit cross-lane replacement.
- [x] 4.6 Add unit tests that `project easy profile set --name <profile>` without update or clear flags fails without mutating the profile.

## 5. Documentation and Skills

- [x] 5.1 Update `docs/reference/cli/houmao-mgr.md` for easy-profile `set` and same-lane replacement on both profile lanes.
- [x] 5.2 Update `docs/getting-started/easy-specialists.md` with easy-profile edit and replacement examples.
- [x] 5.3 Update `docs/getting-started/launch-profiles.md` to distinguish launch-time overrides, patch edits, and full same-lane replacement.
- [x] 5.4 Update `houmao-specialist-mgr` skill guidance for easy-profile `set` and `create --yes` replacement.
- [x] 5.5 Update `houmao-project-mgr` skill guidance for explicit launch-profile `set` and `add --yes` replacement.

## 6. Verification

- [x] 6.1 Run focused project-command unit tests for easy profiles and explicit launch profiles.
- [x] 6.2 Run `pixi run lint` or the narrowest applicable Ruff check for edited Python files.
- [x] 6.3 Run OpenSpec status or validation for `add-launch-profile-editing-controls` and confirm the change is apply-ready.
