## Context

Launch-profile memo seeds currently carry two independent pieces of behavior: a source (`memo` or `tree`) and an apply policy (`initialize`, `replace`, or `fail-if-nonempty`). The source already defines the managed-memory components that are represented by the seed, while the policy adds a second user-facing decision about whether to skip, replace, or abort when existing state is present.

That extra axis is rarely useful in practice. Profile-backed launches are reusable birth-time configuration, so a stored memo seed is most naturally read as "materialize this known memo/page content for launches from this profile." The current `initialize` default makes that less predictable because a profile can store a seed and then silently skip it when prior memo state exists. `fail-if-nonempty` is even narrower, and it forces docs, skills, tests, payloads, and schema to explain a behavior that most users do not need.

## Goals / Non-Goals

**Goals:**

- Make launch-profile memo seeding a source-only feature with one apply behavior: replace represented components.
- Remove `--memo-seed-policy` from public CLI surfaces and packaged skill guidance.
- Remove memo-seed policy from the authoritative launch-profile model and operator-facing payloads.
- Preserve the useful scoped replacement contract: omitted memo/page components remain unchanged.
- Keep `--clear-memo-seed` as the explicit operation for removing stored seed configuration.
- Keep memo-seed application before prompt composition and provider startup.

**Non-Goals:**

- No new memo-seed source forms.
- No merge or append semantics for seeded memo/page content.
- No attempt to infer page links from memo Markdown or synchronize memo links with pages.
- No backward-compatible CLI alias for `--memo-seed-policy`.
- No compatibility promise for preserving `initialize` or `fail-if-nonempty` behavior in existing project catalogs.

## Decisions

### Replace Policy With Source-Scoped Application

The runtime will load the memo-seed payload exactly as it does today, then apply it without consulting a policy:

```text
source kind / tree contents        affected target
────────────────────────────       ─────────────────────────────
--memo-seed-text                   houmao-memo.md only
--memo-seed-file                   houmao-memo.md only
dir/houmao-memo.md                 houmao-memo.md only
dir/pages/                         pages/ only
dir/houmao-memo.md + dir/pages/    houmao-memo.md and pages/
```

Replacement is scoped to represented targets. A memo-only seed writes `houmao-memo.md` and does not inspect, clear, or rewrite pages. A pages seed clears and rewrites only the contained `pages/` tree and does not inspect, clear, or rewrite `houmao-memo.md`. A directory seed with an empty `pages/` directory is an explicit request to clear pages.

Alternatives considered:

- Keep the policy field but make `replace` the default: rejected because it leaves misleading options in the CLI and payload model.
- Keep hidden policy storage while hiding the CLI flag: rejected because stale policy state would still affect future behavior or require surprising normalization.
- Add separate source-specific flags such as `--replace-memo`: rejected because the existing source forms already express the component being seeded.

### Drop Policy From Public Payloads

Profile inspection, compatibility projection YAML, launch-profile provenance, and launch completion payloads should stop emitting `policy`. For memo seeds, payloads should report whether a seed is present, the source kind, and the managed content reference metadata. Launch completion can report `status: applied`, `source_kind`, `memo_written`, `page_file_count`, and `page_directory_count`; invalid or missing seed content remains a launch error rather than a successful skipped result.

This is intentionally breaking. It avoids preserving an obsolete field that would otherwise look configurable.

### Migrate Catalogs By Discarding Policy

The project catalog schema should advance and remove `memo_seed_policy` from the authoritative `launch_profiles` table. Existing rows with `memo_seed_content_ref_id` and `memo_seed_source_kind` remain valid memo seeds; their stored policy is discarded during migration. After migration, all stored memo seeds use replace-only source-scoped application.

SQLite migration can rebuild `launch_profiles` into a new table without `memo_seed_policy`, copy all non-policy columns, drop the old table, and recreate the view. If implementation cost is high, a short-lived physical column may remain as ignored storage, but the dataclass, validation, payloads, projection, and runtime must treat policy as nonexistent.

### Remove CLI Policy-Only Mutation

Both authoring lanes should accept only memo seed sources and `--clear-memo-seed`:

- `houmao-mgr project agents launch-profiles add|set`
- `houmao-mgr project easy profile create|set`

Click should reject `--memo-seed-policy` as an unknown option. Patch commands should preserve an existing memo seed when no memo seed source or clear flag is provided. Supplying a new seed source replaces the stored seed content. `--clear-memo-seed` removes stored seed configuration and cannot be combined with a new seed source.

### Update Skills And Docs In The Same Change

Packaged system skills are part of the user-facing control surface for this project. `houmao-memory-mgr`, `houmao-project-mgr`, and `houmao-specialist-mgr` should no longer instruct agents to choose a memo-seed policy or to use `--memo-seed-policy replace` for empty memo seeds. The correct empty memo seed guidance becomes `--memo-seed-text ''`; the correct seed removal guidance remains `--clear-memo-seed`.

Docs should describe the single behavior directly: memo seeds replace represented managed-memory components before provider startup.

## Risks / Trade-offs

- Existing profiles with policy `initialize` will start replacing represented targets on future launches -> The project is unstable and this is the intended simplification; document the breaking behavior in the change and tests.
- Removing `fail-if-nonempty` eliminates a defensive guard for rare workflows -> Users who need that guard can inspect or manage memo state explicitly before launching, rather than embedding the guard in reusable profile config.
- Catalog table rebuilds can be more fragile than additive migrations -> Keep the migration narrow, copy existing non-policy columns only, and cover migration with catalog tests.
- Dropping `policy` from structured payloads can break consumers -> This is a deliberate breaking API cleanup; update tests and docs to make the new payload shape explicit.
- Skill/docs drift is easy because several files mention the old flag -> Include docs and system-skill guard tests in the implementation tasks.

## Migration Plan

1. Add the new catalog schema version and migrate existing launch-profile rows by preserving memo seed source/content references while dropping memo seed policy.
2. Remove policy from launch-profile dataclasses, resolution payloads, compatibility projections, provenance payloads, and launch completion payloads.
3. Remove `--memo-seed-policy` options and policy-only mutation branches from both CLI lanes.
4. Simplify runtime memo-seed application to always materialize represented targets with replacement semantics.
5. Update docs, skills, and tests in the same change.

Rollback is not schema-compatible after catalogs migrate. In development, restore from a project overlay backup or reinitialize the overlay if rollback is needed.

## Open Questions

None. The intended behavior is a breaking simplification to replace-only scoped memo seeding.
