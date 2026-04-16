## 1. Catalog And Model

- [x] 1.1 Remove memo-seed policy from `LaunchProfileMemoSeed`, `ResolvedLaunchProfileMemoSeed`, profile defaults payloads, compatibility projection rendering, and launch-profile provenance payloads.
- [x] 1.2 Update `ProjectCatalog.store_launch_profile()` and shared launch-profile storage helpers so memo seed storage accepts only source kind plus text/file/tree content.
- [x] 1.3 Add a project catalog schema migration that preserves existing memo seed source/content references and discards stored `memo_seed_policy`.
- [x] 1.4 Update catalog view/select/build-row logic so loaded launch-profile memo seeds no longer require or expose policy metadata.

## 2. Runtime Behavior

- [x] 2.1 Simplify `apply_launch_profile_memo_seed()` to always materialize the loaded payload with source-scoped replacement semantics.
- [x] 2.2 Remove skipped/fail-if-nonempty policy paths, represented-target content checks, and policy-specific error messages from memo-seed application.
- [x] 2.3 Update launch completion memo-seed payloads to omit policy and report only applied source-scoped write metadata.

## 3. CLI Surfaces

- [x] 3.1 Remove `--memo-seed-policy` from `project agents launch-profiles add|set` and `project easy profile create|set`.
- [x] 3.2 Remove policy-only patch support and update validation so `--clear-memo-seed` is incompatible only with a new memo seed source.
- [x] 3.3 Update explicit launch-profile and easy-profile get/list payload expectations so memo seeds report presence, source kind, and content refs without policy.

## 4. Docs And Skills

- [x] 4.1 Update launch-profile, easy-specialist, quickstart, and CLI reference docs to describe replace-only source-scoped memo seeding and remove `--memo-seed-policy`.
- [x] 4.2 Update packaged `houmao-memory-mgr`, `houmao-project-mgr`, and `houmao-specialist-mgr` guidance to stop suggesting memo-seed policies.
- [x] 4.3 Update docs/system-skill guard tests so stale `--memo-seed-policy`, `initialize`, and `fail-if-nonempty` guidance is caught where appropriate.

## 5. Tests And Validation

- [x] 5.1 Update memo-seed runtime tests to cover memo-only replacement preserving pages, pages-only replacement preserving memo, empty memo seeding, empty pages seeding, and multi-component directory replacement.
- [x] 5.2 Update project command tests for removed policy options, source replacement, clear behavior, profile inspection payloads, and projection YAML.
- [x] 5.3 Update catalog migration tests for existing policy-bearing memo seeds migrating to source-only replace semantics.
- [x] 5.4 Update managed launch tests so memo seeds are applied before build and completion payloads omit policy.
- [x] 5.5 Run `pixi run test`, plus targeted docs/catalog/runtime command tests if the full suite is not practical.
