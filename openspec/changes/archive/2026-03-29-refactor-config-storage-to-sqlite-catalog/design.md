## Context

Houmao currently has a meaningful separation between:

- user intent, mainly through `houmao-mgr project easy`,
- storage under project-local filesystem roots such as `.houmao/agents/` and `.houmao/easy/`,
- implementation-layer dataclasses and boundary models used by builders and runtime code.

That separation is not clean enough in practice because the storage layer still encodes too much meaning in directory layout and path-bearing config fields. Project-local specialist metadata persists generated paths, project-aware builders and loaders recover semantics by traversing `.houmao/agents/`, and relationship changes such as sharing or re-binding auth, skills, setups, or future policy objects are constrained by filesystem nesting rather than by explicit object relationships.

The refactor proposed here moves project-local semantic relationships into a SQLite-backed catalog while intentionally keeping large text blobs and tree-shaped payloads file-backed. The design therefore has to solve both persistence and assembly:

- define the canonical project-local semantic model,
- define how files remain payload storage without remaining the primary relationship model,
- define how project-aware build and runtime paths consume catalog/domain objects instead of reconstructing meaning from directory topology,
- define how existing project-local overlays are migrated or imported.

## Goals / Non-Goals

**Goals:**

- Introduce one project-local SQLite catalog as the canonical semantic store for project overlay configuration.
- Keep large text blobs and tree-shaped payloads such as prompts, auth files, setup bundles, and skill bundles file-backed under managed project-local content roots.
- Move relationship ownership for specialists, roles, presets, setup profiles, skill packages, auth profiles, mailbox policies, and related identities out of directory nesting and into explicit catalog rows and references.
- Refactor project-aware build, selector resolution, and `project easy` flows to consume a catalog-backed domain layer rather than treating `.houmao/agents/` as the source of truth.
- Preserve a clear advanced-operator inspection path through stable SQL-readable catalog tables or views.
- Define a one-way migration path from existing project-local path-first overlays into the new catalog-backed format.

**Non-Goals:**

- Replacing all repository-owned or external filesystem-backed `agents/` trees in one change.
- Moving all large content payloads into SQLite blobs.
- Replacing runtime session manifests, runtime home files, or live tmux/runtime state with the same project catalog database.
- Designing a networked multi-user catalog service; this remains a local project overlay feature.
- Defining full bidirectional sync between the new catalog and a still-authoritative `.houmao/agents/` tree. The catalog becomes authoritative.

## Decisions

### Decision: Use a hybrid project-local storage model: SQLite catalog plus managed file-backed content store

Project-local overlays will store canonical semantic state in `.houmao/catalog.sqlite` and will store large content payloads under managed file-backed roots such as `.houmao/content/`.

Recommended managed content classes:

- prompt blobs,
- auth file blobs,
- setup trees,
- skill trees,
- any other large text or structured payload that is better edited or projected as files.

Rationale:

- relationships and identity belong in the catalog,
- large payloads and trees remain easier to edit, inspect, and project as files,
- many current consumers still need real files even if the filesystem is no longer the semantic graph.

Alternative considered:

- Move everything into SQLite, including prompt text and auth file blobs.
  Rejected because it makes large payload editing less ergonomic, complicates tree-shaped asset handling, and increases the operational and security cost of raw auth material.

### Decision: The catalog unifies by domain concept, not by current runtime dataclass shape

The catalog schema will model stable project-local concepts such as:

- specialist,
- role,
- preset,
- setup profile,
- skill package,
- auth profile,
- mailbox policy,
- content blob reference,
- content tree reference.

Runtime-oriented artifacts such as `LaunchPlan`, resolved env bindings, runtime home paths, session manifests, and tmux/gateway state remain derived outputs, not canonical project config rows.

Rationale:

- runtime models intentionally reflect execution concerns,
- persisting those models as canonical config would over-couple storage to current implementation details,
- domain concepts are more stable than execution payload shapes.

Alternative considered:

- Reuse the current Python runtime models as the DB schema.
  Rejected because it would freeze storage around transient runtime concerns and make future runtime refactors unnecessarily expensive.

### Decision: Project-local files remain payload storage and are referenced from the catalog

The catalog will reference file-backed payloads through stable content references rather than encoding semantic meaning in their paths.

Recommended approach:

- single-file assets use content/blob ids plus managed storage metadata,
- tree-shaped assets use managed tree references,
- project-local content lives under managed overlay-owned paths rather than arbitrary external references by default.

The design permits advanced operators to inspect the content files directly, but file location will no longer define role/preset/auth/skill relationships.

Rationale:

- it keeps payload editing practical,
- it allows the DB to own object relationships,
- it avoids treating generated or nested paths as public semantic identifiers.

Alternative considered:

- Store only managed relative paths in the DB and use those paths as lasting object identity.
  Rejected because it preserves too much path sensitivity and weakens the decoupling benefit of the refactor.

### Decision: `.houmao/houmao-config.toml` remains the project overlay discovery anchor, but not the semantic catalog itself

The lightweight overlay config file remains the stable discovery and bootstrap anchor for project-aware commands, but it will point at or imply the project-local catalog and managed content roots instead of defining rich project semantics inline.

Rationale:

- the current overlay discovery contract is simple and effective,
- replacing it entirely would make project detection harder than necessary,
- keeping a tiny discovery file avoids forcing callers to guess whether a random SQLite file is the active overlay.

Alternative considered:

- Eliminate the TOML overlay file and discover the project only from the database.
  Rejected because the TOML file is useful as a simple anchor and migration boundary even after the semantic model moves into SQLite.

### Decision: Project-aware builders and selectors resolve through a catalog repository/service layer

Project-aware code paths will stop traversing `.houmao/agents/` as authoritative project state. Instead they will resolve:

- the active project overlay,
- the project catalog repository,
- domain objects and content references,
- derived build and launch inputs.

This means introducing a repository/service seam between persistence and current builders/loaders.

Rationale:

- it isolates persistence format from runtime assembly,
- it allows the existing canonical parsed/runtime contracts to survive with cleaner inputs,
- it makes future storage changes or projections less invasive.

Alternative considered:

- Keep current builders/loaders unchanged and regenerate a full project-local `.houmao/agents/` tree before every project-aware build or launch.
  Rejected because it preserves the wrong dependency direction and would keep the filesystem tree as a hidden second source of truth.

### Decision: Project-local `.houmao/agents/` becomes non-authoritative compatibility projection or import surface

After this change, project-local semantic truth lives in the catalog and managed content store. If `.houmao/agents/` still exists under project overlays, it is no longer authoritative.

The intended role for that tree is one of:

- import source for migration from the legacy project-local layout,
- derived compatibility projection for consumers that still need file-tree access during the transition.

Rationale:

- keeping the old tree authoritative would reintroduce split brain,
- some migration or compatibility surface is still useful while project-aware builders and related tooling move off direct tree traversal.

Alternative considered:

- Continue treating `.houmao/agents/` as co-equal source of truth alongside the catalog.
  Rejected because it creates permanent reconciliation ambiguity.

### Decision: Expose a stable advanced-operator SQL inspection surface deliberately

If advanced users are expected to inspect or manipulate catalog state through SQL tools, the catalog must define stable inspection surfaces such as:

- strongly typed tables with foreign keys and checks,
- stable read-oriented SQL views,
- explicit schema versioning and migrations,
- documented integrity expectations.

The design should not treat arbitrary raw tables as accidental public API without constraints.

Rationale:

- "advanced users may use SQL" implies the DB contract matters,
- stable views and constraints reduce accidental corruption,
- this keeps advanced inspection practical without making internal migration impossible.

Alternative considered:

- Expose only undocumented internal tables and rely on users to be careful.
  Rejected because that invites silent corruption and turns implementation details into de facto unsupported API.

### Decision: Migrate existing project-local overlays through one-way import into the catalog

Existing project-local overlays that currently store their semantic relationships in `.houmao/agents/` and `.houmao/easy/` need a one-way import path into the new catalog-backed format.

The migration will:

- read legacy project-local specialist metadata and canonical tree content,
- create catalog rows and managed content refs,
- mark the catalog as authoritative,
- stop treating the imported legacy tree as the canonical graph.

Rationale:

- active users need a path forward,
- a clean one-way migration is simpler than long-term bidirectional sync,
- breaking changes are allowed, but unnecessary local data loss is not a good default.

Alternative considered:

- Require manual recreation of all project-local overlays.
  Rejected because the amount of local-only auth and prompt/config state makes that operationally noisy and avoidably destructive.

## Risks / Trade-offs

- [Two persistence systems instead of one] -> Keep the division explicit: SQLite owns relationships, managed files own payload. Add integrity checks and orphan detection rather than allowing fuzzy overlap.
- [Split brain between catalog and legacy `.houmao/agents/` tree] -> Make the catalog authoritative and treat any remaining tree only as derived projection or migration input.
- [DB schema becomes too coupled to current Python internals] -> Base the schema on stable domain concepts and keep runtime models derived.
- [Advanced SQL access can corrupt catalog integrity] -> Use foreign keys, checks, stable read views, schema versioning, and documented invariants.
- [Auth material handling becomes risky if secrets are moved into the main catalog DB] -> Keep auth payload files file-backed and store references plus metadata in the catalog.
- [Project-aware build and launch refactor touches many modules] -> Introduce one catalog repository/materialization seam and migrate callers incrementally behind it.
- [Migration from current overlays may be lossy or ambiguous] -> Define a one-way importer that reads the existing tree and specialist metadata together and validates before writing catalog state.

## Migration Plan

1. Add the new project-local catalog and managed content root bootstrap contract to project overlay initialization.
2. Introduce catalog schema management, migrations, and repository/service APIs.
3. Implement one-way import from current project-local `.houmao/agents/` plus `.houmao/easy/` specialist metadata into the catalog.
4. Refactor `project easy` read/write paths to persist and resolve through the catalog.
5. Refactor project-aware build and launch resolution to consume catalog/domain objects rather than direct tree traversal.
6. Keep any necessary `.houmao/agents/` compatibility projection non-authoritative during the transition.
7. Update docs and operator guidance to describe the new project-local storage model and advanced SQL inspection expectations.

Rollback strategy:

- before migration/import, preserve the legacy local tree intact,
- allow reverting to the pre-migration overlay layout while the old tree still exists,
- once the catalog-backed contract is accepted as authoritative, treat rollback as a local operator restore from preserved files or backup rather than ongoing dual-write support.

## Open Questions

- Should project-local content refs use managed relative paths first, content ids first, or a mixed approach by asset type?
- Should `.houmao/content/` use content-addressed names, friendly managed names, or both?
- What is the exact advanced-user SQL contract: documented tables, documented views only, or documented read views plus CLI-mediated writes?
- Should `.houmao/agents/` compatibility projection be materialized lazily, eagerly, or not at all after migration?
- How much automatic migration should happen during `project init` or project-aware command execution versus through an explicit migration command?
