## 1. Coverage Inventory

- [x] 1.1 Inventory managed system-skill assertions added across system skill helper, definition parser, catalog, brain builder, launch forwarding, and project command tests.
- [x] 1.2 Classify each assertion by owned layer: pure policy, recipe parser, catalog projection, build/runtime integration, launch forwarding, or CLI smoke.
- [x] 1.3 Identify duplicate higher-level assertions and record which retained lower-level or representative test covers the same behavior.

## 2. Pure Policy And Storage Coverage

- [x] 2.1 Keep or consolidate pure `system_skills.py` tests so they remain the authoritative matrix for policy parsing, serialization, validation, resolution, sync cleanup, retired cleanup, and user-skill preservation.
- [x] 2.2 Keep definition parser tests focused on accepting `launch.system_skills` and rejecting source-invalid policy modes.
- [x] 2.3 Keep catalog tests focused on launch-profile persistence and compatibility projection of `defaults.system_skills`.

## 3. Build And Launch Integration Coverage

- [x] 3.1 Trim brain-builder tests so filesystem cleanup details covered by sync helper tests are not repeated there.
- [x] 3.2 Preserve representative brain-builder coverage for source additive policy, profile override or disabled policy, reused-home integration outcome, collision rejection, Gemini projection roots, and manifest provenance.
- [x] 3.3 Preserve launch forwarding coverage that proves source and launch-profile policies reach `BuildRequest`.

## 4. CLI Coverage Deduplication

- [x] 4.1 Reduce `project easy specialist` system-skill tests to compact create/get/set-or-clear smoke coverage plus any lane-specific payload shape checks.
- [x] 4.2 Reduce `project easy profile` system-skill tests to compact create/patch/disable-or-clear smoke coverage plus any lane-specific payload shape checks.
- [x] 4.3 Reduce `project agents launch-profiles` system-skill tests to compact add/set/clear smoke coverage plus projection evidence.
- [x] 4.4 Cover shared CLI conflict/error behavior once, or move it to direct helper-level tests if the shared option resolver is separable.

## 5. Verification

- [x] 5.1 Run focused tests for touched modules: system skills, definition parser, catalog, brain builder, launch forwarding, and project commands.
- [x] 5.2 Run `pixi run test`.
- [x] 5.3 Run `pixi run lint` and `pixi run typecheck` if test helper refactors touch typed source or lint-sensitive test code.
- [x] 5.4 Run `pixi run openspec validate deduplicate-system-skill-unit-tests --strict`.
