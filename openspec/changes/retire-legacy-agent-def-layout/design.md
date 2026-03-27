## Context

Houmao has already standardized on a canonical agent-definition model built from:

- `skills/<skill>/SKILL.md`
- `roles/<role>/system-prompt.md`
- `roles/<role>/presets/<tool>/<setup>.yaml`
- `tools/<tool>/adapter.yaml`
- `tools/<tool>/setups/<setup>/`
- `tools/<tool>/auth/<auth>/`

That model is implemented in the parsed agent catalog and in preset-backed launch helpers such as `resolve_demo_preset_launch(...)`. However, the repository still carries three classes of migration residue:

1. Demo-owned `scripts/demo/**/agents` trees that ship both canonical `roles/` and `tools/` assets and legacy `brains/` / `blueprints/` duplicates.
2. Runtime helpers, demo runners, exploration harnesses, scripts, and tests that still hardcode old path families such as `brains/api-creds/`, `brains/brain-recipes/`, or `blueprints/`.
3. Specs and docs that still describe the legacy layout as if it were current, even when implementation has already moved to preset-backed resolution.

The result is an inconsistent repository contract:

```text
documented source of truth:   roles/ + tools/ + skills/
actual shipped demo assets:   roles/ + tools/ + skills/ + brains/ + blueprints/
consumer behavior:            mixed preset-backed and legacy-path-dependent
```

The requested change is to stop shipping old-style demo-owned directories and refactor remaining consumers to the canonical layout.

## Goals / Non-Goals

**Goals:**

- Remove legacy `brains/` and `blueprints/` subtrees from demo-owned `scripts/demo/**/agents` trees that already have canonical assets.
- Make affected runtime/demo/test/script consumers resolve canonical preset/setup/auth paths rather than requiring legacy layout paths.
- Align shipped docs and OpenSpec requirements with the canonical layout.
- Preserve current functional coverage while eliminating repository-maintained duplicate source trees.

**Non-Goals:**

- Renaming every compatibility-shaped field such as `recipe_path`, `brain_recipe_path`, or `blueprint_path` in one pass.
- Removing all internal blueprint parsing or hidden CLI compatibility flags when they are still needed for unrelated compatibility tests or gateway-default parsing.
- Reworking unrelated launch-policy, mailbox, or server-runtime behavior beyond what is needed to remove legacy layout dependencies.
- Removing local-only `tools/<tool>/auth/**` support or changing how secret material is projected into runtime homes.

## Decisions

### Decision: Canonical preset-backed resolution becomes the only supported source-tree dependency

All shipped repo-owned demos, helper scripts, tests, and docs touched by this change will resolve launch inputs through canonical preset/setup/auth layout or through helpers derived from that layout.

Why:

- The parsed catalog and launch helpers already treat canonical presets as the authority.
- Maintaining duplicate `brains/` and `blueprints/` trees inside demo packs invites drift.
- This directly matches the intent already captured in `component-agent-construction` and `demo-agent-launch-recovery`.

Alternatives considered:

- Keep both layouts indefinitely and rely on docs to steer users toward the new one. Rejected because it preserves duplicate tracked assets and unclear ownership.
- Remove legacy code paths and compatibility names in the same change. Rejected because it expands scope from source-tree migration into public/internal API cleanup.

### Decision: Demo-owned `agents/` trees may keep only canonical layout plus explicitly needed compatibility metadata

For pack-local `scripts/demo/**/agents` trees, the tracked source-of-truth surface will be limited to canonical directories such as `roles/`, `tools/`, `skills/`, and `compatibility-profiles/` when needed. Legacy `brains/` and `blueprints/` directories will not be shipped in those trees.

Why:

- These trees are repo-owned fixtures, not third-party compatibility bundles.
- The server demo packs already resolve launch inputs from `roles/.../presets/...`, so the legacy subtrees are duplicate cargo.
- Removing them clarifies what maintainers are expected to edit.

Alternatives considered:

- Leave legacy subtrees as read-only mirrors. Rejected because mirrors still drift and still attract new dependencies.
- Replace removed trees with symlinks. Rejected because the goal is to stop depending on that layout entirely, not to hide it.

### Decision: Compatibility field names may remain temporarily when the value semantics are canonical

Config or report fields named `blueprint`, `blueprint_path`, `recipe_path`, or `brain_recipe_path` may remain temporarily when they now carry a canonical preset path or preset-derived metadata. The implementation requirement is semantic, not purely lexical: those fields must no longer require legacy source trees.

Why:

- Several demo packs already use this pattern successfully.
- Field renaming is a separate cleanup concern and would inflate migration scope.
- This avoids breaking report snapshots and helper interfaces unnecessarily.

Alternatives considered:

- Rename all legacy-looking fields now. Rejected because it creates broad snapshot churn without advancing the core layout migration.

### Decision: Fix consumers in dependency order from highest-authority assets outward

Implementation will proceed in this order:

1. Pack-owned tracked `agents/` trees.
2. Runtime/demo/explore helpers and shell scripts with live legacy path dependencies.
3. Tests that seed or assert the old layout.
4. Docs and specs that still describe the old layout as current behavior.

Why:

- Removing duplicate tracked assets first makes the intended source of truth obvious.
- Refactoring code and tests second ensures the repo no longer needs those removed trees.
- Updating docs/specs last lets them describe the final behavior rather than an intermediate state.

Alternatives considered:

- Update docs first. Rejected because it can temporarily document behavior the code does not yet satisfy.

### Decision: Keep legacy blueprint parsing only where behavior still explicitly depends on it

This change will not automatically remove `load_blueprint(...)`, hidden `--blueprint` / `--recipe` CLI flags, or gateway-default parsing behavior. Instead, it will remove shipped asset and workflow dependencies on legacy layout while leaving isolated compatibility surfaces to a later retirement change.

Why:

- Some tests still exercise blueprint parsing as a compatibility contract.
- Gateway-default parsing is separable from file-tree layout cleanup.
- The requested change is about stopping layout dependence, not about deleting every compatibility symbol.

Alternatives considered:

- Remove blueprint compatibility surfaces immediately. Rejected because it risks bundling unrelated behavior changes into a source-tree migration.

## Risks / Trade-offs

- [Old-path assumptions are scattered across demos, tests, and docs] → Use a repo-wide search-driven migration list and keep tasks grouped by consumer class so path-dependent leftovers are less likely to survive.
- [Compatibility field names may confuse maintainers after layout migration] → Document explicitly that those names are compatibility-only and point at canonical preset-backed values.
- [Some demo/test helpers may rely on `load_brain_recipe(...)` against preset files] → Treat that as acceptable transitional behavior when the underlying file is a canonical preset path; only fail the change if the helper still requires legacy directory structure.
- [Specs currently conflict with each other on old vs new layout] → Update all directly affected capability specs in the same change so the archive state is internally consistent.
- [Removing pack-local duplicate trees could break ad hoc maintainer workflows] → Preserve the same pack-local `agents/` root and canonical selector paths so operators still work from the same pack directory, just without the legacy mirrors.

## Migration Plan

1. Update affected capability specs so the contract clearly prefers canonical preset/setup/auth layout and forbids demo-owned legacy tree dependencies.
2. Remove legacy `agents/brains` and `agents/blueprints` subtrees from the affected demo packs after confirming their code paths already resolve canonical presets.
3. Refactor remaining scripts, helpers, and tests that still hardcode `brains/` or `blueprints/` path families to resolve canonical preset/setup/auth inputs.
4. Refresh docs and fixture READMEs so repository guidance consistently describes the new layout.
5. Run targeted demo/unit/integration coverage for the touched launch helpers and demo packs, plus repository searches that verify old path families are no longer described as current behavior in the changed scope.

Rollback strategy:

- Because this is repository-owned fixture and helper migration, rollback is a normal git revert of the change if an overlooked consumer still requires the old layout.
- No persistent data migration or external system rollback is required.

## Open Questions

- Should a follow-up change remove hidden `--recipe` / `--blueprint` CLI compatibility flags once repo-owned workflows stop using them?
- Should compatibility-shaped report fields be renamed to `preset` / `preset_path` after this migration lands and snapshots are refreshed?
- Are there any intentionally retained legacy fixture trees outside the touched demo packs that should be formalized as compatibility-only rather than silently left in place?
