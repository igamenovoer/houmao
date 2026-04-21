## Context

The current project-easy skill flow duplicates skill content across two live-looking trees:

- `project easy specialist create|set --with-skill` first copies the source directory into `.houmao/agents/skills/<name>`
- specialist persistence snapshots that projected directory into `.houmao/content/skills/<name>`
- catalog materialization later rewrites `.houmao/agents/skills/<name>` back from `.houmao/content/skills/<name>`

That model leaves operators with two mutable-looking skill trees, makes it unclear which tree is canonical, and prevents a clean repo-owned skill workflow where edits to one source directory are immediately visible. Upstream issue `#34` asks for the canonical-vs-derived explanation, while issue `#22` asks for symlink-friendly repo skill usage.

The repository is still pre-1.0 and already treats the catalog-backed overlay as the semantic source of truth. Breaking model cleanup is therefore preferable to layering more compatibility logic on top of the duplicated tree design. At the same time, existing users already have older project structures, including legacy `.houmao/easy/specialists/*.toml` specialist metadata and compatibility-tree-first `.houmao/agents/...` content, so the current change needs one explicit migration seam instead of scattering auto-upgrade code across ordinary project commands.

## Goals / Non-Goals

**Goals:**

- Establish one canonical per-project skill location under `.houmao/content/skills/<name>`.
- Let project skill registration choose `copy` or `symlink` at registration time.
- Make specialists bind registered project skill names instead of owning skill imports directly.
- Keep `.houmao/agents/skills/` and runtime-home skill trees as derived projection surfaces only.
- Centralize supported existing-project upgrades behind one explicit `project migrate` command instead of opportunistic load-time rewrites.
- Clarify the operator model in docs so issue `#34` is answered by the supported project layout.

**Non-Goals:**

- Building a fully generic operator-facing asset CLI for every future asset kind in this change.
- Preserving manual editing of `.houmao/agents/skills/` as a supported workflow.
- Updating already-running managed agents in place when project skill bindings change.
- Solving arbitrary external-content references outside the project overlay beyond the explicit skill `copy|symlink` modes.
- Supporting arbitrary damaged or unknown historical project layouts through best-effort auto-repair.

## Decisions

### 1. Canonical project skills live under `.houmao/content/skills/`

Project-local skills will use `.houmao/content/skills/<name>` as the single canonical project location.

- In `copy` mode, that path is a normal directory copied from the user-provided source.
- In `symlink` mode, that path is a symlink whose target is the user-provided source directory.

This keeps the operator-visible canonical location inside the existing `content/` namespace while avoiding two independent live trees. It also scales naturally to future asset kinds under `.houmao/content/<kind>/...` without treating `skills/` as the generic root.

Alternatives considered:

- Keep `.houmao/agents/skills/` as canonical and treat `content/skills/` as cache. Rejected because it preserves the current ambiguity and continues to mix semantic state with compatibility projection.
- Introduce a separate `.houmao/skills/` root. Rejected because the existing `content/` namespace already represents canonical project-owned payloads and provides a better long-term layout for future asset kinds.

### 2. Add a first-class `project skills` registry surface

Skill registration becomes its own project command family:

- `project skills add`
- `project skills set`
- `project skills list`
- `project skills get`
- `project skills remove`

The registry owns skill naming and the `copy|symlink` choice. Specialist commands then bind or unbind skill names from that registry.

This separates durable asset registration from specialist authoring and lets the same registered skill be reused by multiple specialists without each specialist re-importing it.

Alternatives considered:

- Keep `project easy specialist --with-skill` as the primary storage model. Rejected because it makes specialist authoring own project asset storage semantics and keeps issue `#22` trapped inside one command instead of solving the underlying layout.
- Add only launch-time `copy|symlink` flags. Rejected because launch needs a stable canonical project skill to project from.

### 3. Specialists store skill names, not imported source directories

Specialists will persist skill bindings as references to registered project skill names.

`project easy specialist create` and `set` should prefer name-based binding (`--skill` / `--add-skill`). A `--with-skill <dir>` convenience path may remain, but it should mean “register or update a project skill, then bind it” rather than “copy directly into the specialist-owned tree.”

This keeps specialist semantics stable even when the registered skill mode changes from `copy` to `symlink`.

Alternatives considered:

- Store full source paths directly on specialists. Rejected because it duplicates skill registration state across specialists and makes shared-skill reasoning harder.

### 4. Derived projections symlink from the canonical project skill entry

Per-agent and compatibility projections should be derived from `.houmao/content/skills/<name>`.

- `.houmao/agents/skills/<name>` becomes a derived compatibility projection when that tree is needed.
- Managed runtime homes should install selected skills by symlinking from the canonical project skill entry whenever the target backend supports normal filesystem symlink resolution.

This matches the accepted design principle: project-local skill storage is canonical in one place, while per-agent views are cheap derived links.

Alternatives considered:

- Continue copying from canonical content into every compatibility and runtime tree. Rejected because it recreates live drift points and weakens the value of symlink-backed project skills.
- Remove `.houmao/agents/skills/` immediately with no compatibility projection. Rejected because existing builder and file-tree consumers still expect that projection seam.

### 5. Catalog metadata records registry semantics, while the filesystem path remains the canonical payload location

The catalog should record project skill identity and registry metadata such as mode, but the payload itself remains canonical at `.houmao/content/skills/<name>`.

That means:

- operators and docs can treat the filesystem entry as the canonical project skill location,
- inspection commands can report mode and source intent explicitly,
- projection code can rebuild derived trees without inventing a second canonical store.

This avoids a more abstract “external content ref” design while still keeping the catalog as the semantic graph.

### 6. Add one explicit `project migrate` command for supported project-structure upgrades

Project-structure upgrades should run only through a new top-level command:

- `houmao-mgr project migrate`

The command should support a non-destructive planning mode by default and an explicit apply mode for mutation.

When apply mode succeeds, the command should refresh the selected project overlay to the latest supported structure in place. It should not preserve legacy project files as a second live tree, and it should not own a built-in backup workflow. Operators who want a backup should take one before running migration.

Normal `project` commands, project-aware catalog loaders, and easy-specialist flows should not silently rewrite old project structures. When they detect a known legacy project state that requires conversion, they should fail clearly and direct the operator to `houmao-mgr project migrate`.

This keeps migration ownership in one place and prevents “upgrade if old” branches from leaking into `project init`, `project easy ...`, catalog loading, or compatibility materialization.

Alternatives considered:

- Let `project init` or ordinary stateful project commands absorb legacy layout as they run. Rejected because it hides data mutation behind unrelated commands and makes migration behavior hard to audit or test.
- Continue telling users to recreate overlays manually. Rejected because we already have known legacy project states worth migrating, and the current change directly alters canonical project structure for existing users.

### 7. `project migrate` recognizes only named, supported legacy project states

The migration surface should work from a central registry of known migration steps. Examples include:

- importing legacy `.houmao/easy/specialists/*.toml` specialist metadata into the current catalog-backed specialist model,
- upgrading compatibility-tree-first project skill state into canonical `.houmao/content/skills/<name>` entries,
- removing legacy project-only paths that are no longer part of the maintained contract once their current equivalents have been written.

Unknown or structurally incompatible project states should remain explicit failures rather than best-effort migration attempts.

This preserves rigor and keeps the command from becoming a catch-all repair tool.

## Risks / Trade-offs

- [Existing overlays may contain manually edited `.houmao/agents/skills` trees] → Mitigation: treat the change as breaking, rematerialize derived skill projections from the new canonical registry, and document that `.houmao/agents/skills` is no longer an editing surface.
- [Symlink-backed project skills can break if the source path disappears] → Mitigation: `project skills get`, projection materialization, and launch should fail clearly when a registered symlink target no longer resolves.
- [Some consumers may assume copied runtime content rather than symlinked runtime content] → Mitigation: keep projection behavior centralized and limit the symlink contract to maintained local filesystems; fall back to explicit copy only where a backend cannot tolerate symlinked skill trees.
- [Adding a new project command family broadens the CLI surface] → Mitigation: keep `project skills` narrowly scoped to registry administration and move specialist docs toward binding by name so the mental model is simpler overall.
- [Migration support spreads into unrelated code paths] → Mitigation: require ordinary commands to fail with migration guidance and reserve structural conversion logic for `project migrate` only.
- [Operators may expect `project migrate` to repair any broken historical overlay] → Mitigation: define a narrow set of named supported migrations, expose a plan before apply, and reject unsupported layouts clearly.
- [Migration is intentionally destructive to legacy project files] → Mitigation: document clearly that `project migrate` refreshes the overlay to the latest structure in place and that operators must take any desired backup before running it.

## Migration Plan

1. Add the new project skill registry model and CLI surface.
2. Add `project migrate` with explicit plan/apply behavior for supported existing-project conversions.
3. Update specialist create and set flows to consume registered skill names and to use `--with-skill` only as a registration convenience path.
4. Change compatibility projection materialization so `.houmao/agents/skills/` is derived from `.houmao/content/skills/` rather than being treated as a peer live tree.
5. Update managed runtime skill projection to symlink from canonical project skill entries where supported.
6. Make ordinary project-aware commands fail with migration guidance when they detect a supported-but-stale project structure that now requires explicit migration.
7. Refresh docs to mark `.houmao/content/skills/` as canonical, `.houmao/agents/skills/` as derived, and `project migrate` as the supported upgrade path for existing overlays.
8. Because the project catalog is still pre-1.0, structurally incompatible or unknown persisted overlays may still require explicit reinitialization instead of migration when they fall outside the supported migration set.

## Open Questions

- Whether the initial CLI should expose `project easy specialist create --skill <name>` in addition to `set --add-skill <name>`, or whether the first pass should keep `--with-skill` as a shorthand plus `set --add-skill` for binding existing registered skills.
- Whether any maintained backend or test fixture needs a forced-copy runtime fallback even when the project skill registry entry is symlink-backed.
- Which exact legacy project states are in the first supported migration set beyond legacy easy-specialist TOML and compatibility-tree-first project skill storage.
