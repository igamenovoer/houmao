## 1. Catalog And Data Model

- [ ] 1.1 Add catalog support for memo seed content references, source kind metadata, and `initialize|replace|fail-if-nonempty` policy storage.
- [ ] 1.2 Add schema migration for existing project catalogs so missing memo seed fields resolve as absent seed state.
- [ ] 1.3 Extend `LaunchProfileCatalogEntry` and launch-profile resolution payloads with memo seed metadata.
- [ ] 1.4 Add managed-content snapshot helpers for inline memo text, memo seed files, and memo-shaped seed directories.
- [ ] 1.5 Validate memo seed directory shape: only `houmao-memo.md` and `pages/` at the top level, UTF-8 text content, no NUL bytes, and no symlinks.
- [ ] 1.6 Update compatibility projection rendering and profile inspection payloads to report memo seed presence, source kind, policy, and managed content reference metadata without dumping full content by default.

## 2. Profile Authoring CLI

- [ ] 2.1 Add shared CLI parsing for `--memo-seed-text`, `--memo-seed-file`, `--memo-seed-dir`, `--memo-seed-policy`, and `--clear-memo-seed`.
- [ ] 2.2 Wire memo seed options into `houmao-mgr project agents launch-profiles add|set|get`.
- [ ] 2.3 Wire memo seed options into `houmao-mgr project easy profile create|set|get`.
- [ ] 2.4 Enforce source mutual exclusion, policy defaults, policy-only update rules, and clear/source conflict errors.
- [ ] 2.5 Preserve memo seeds on patch operations and clear omitted memo seeds on same-lane replacement operations.

## 3. Launch-Time Application

- [ ] 3.1 Implement a memo seed application helper that writes `houmao-memo.md` and contained `pages/` through existing memo/page helpers.
- [ ] 3.2 Implement `initialize`, `replace`, and `fail-if-nonempty` policy behavior as unit-testable logic.
- [ ] 3.3 Apply explicit launch-profile memo seeds in `houmao-mgr agents launch --launch-profile` after identity/memo path resolution and before provider startup.
- [ ] 3.4 Apply easy-profile memo seeds in `houmao-mgr project easy instance launch --profile` through the shared managed launch path.
- [ ] 3.5 Report memo seed status in launch completion payloads without exposing full memo/page content.
- [ ] 3.6 Ensure direct non-profile launches never apply stored memo seeds.

## 4. Documentation And Guidance

- [ ] 4.1 Update `docs/getting-started/launch-profiles.md` to describe memo seeds, source forms, policies, and how they differ from prompt overlays.
- [ ] 4.2 Update easy-specialist and quickstart documentation where profile-backed launch defaults are listed.
- [ ] 4.3 Update CLI reference documentation for explicit launch-profile and easy-profile memo seed options.
- [ ] 4.4 Update packaged system-skill guidance if needed so project/profile management skills mention memo seed options using memo terminology.

## 5. Tests And Verification

- [ ] 5.1 Add catalog tests for memo seed persistence, projection, patch preservation, replacement clearing, and integrity validation.
- [ ] 5.2 Add CLI tests for explicit launch-profile memo seed add/set/get/clear validation.
- [ ] 5.3 Add CLI tests for easy-profile memo seed create/set/get/clear validation.
- [ ] 5.4 Add runtime tests for seed application timing and policies, including skipped initialize, destructive replace, and fail-before-start.
- [ ] 5.5 Add containment tests for directory seeds that reject unsupported files, traversal, symlinks, non-UTF-8 content, and NUL bytes.
- [ ] 5.6 Add docs wording tests to guard against public “memory seed” terminology for this feature.
- [ ] 5.7 Run `pixi run test` and targeted runtime or CLI suites affected by the launch-profile changes.
