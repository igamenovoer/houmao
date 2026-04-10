## Context

Project-local auth bundles currently mix three different concerns into one string:

- the operator-facing auth name,
- the on-disk projection directory name,
- the semantic relationship key used by specialists, launch profiles, and auth CRUD.

That coupling shows up in both the CLI and the catalog. `project agents tools <tool> auth ...` mutates `.houmao/agents/tools/<tool>/auth/<name>/` directly, while the catalog snapshots auth content under name-derived managed-content paths and several stored relationships still persist auth display names as the reference key. This makes auth rename expensive, makes filesystem layout semantically significant, and weakens the project-config-catalog rule that SQLite is the authoritative semantic graph.

This change is intentionally a hard cut. The repository is under active development, and the user explicitly asked to skip compatibility or migration considerations. All maintained code, scripts, fixtures, and docs should adopt the new scheme together.

## Goals / Non-Goals

**Goals:**

- Make auth profiles first-class catalog-owned semantic objects with stable opaque identity.
- Make operator-facing auth names mutable labels rather than storage keys.
- Add an explicit rename surface for project-local auth profiles.
- Remove name-shaped auth identity from specialists and launch profiles.
- Keep managed auth content file-backed while moving semantic ownership fully into the catalog.
- Keep project-easy and skill-driven workflows readable by continuing to accept and render user-facing auth names.

**Non-Goals:**

- Preserve old on-disk auth directory names or add compatibility shims for them.
- Support external scripts that scan `.houmao/agents/tools/<tool>/auth/` and infer semantics from directory basenames.
- Design a data migration or rollback path for existing repositories.
- Change per-tool auth payload contracts such as supported env variables or supported auth files.

## Decisions

### 1. Auth identity splits into display name, opaque bundle ref, and numeric row id

Auth profiles will use three distinct identities:

| Field | Purpose | Mutability |
|---|---|---|
| `id` | SQLite relationship key | immutable |
| `bundle_ref` | opaque storage and projection key | immutable |
| `display_name` | operator-facing name used by CLI | mutable |

`bundle_ref` will be generated once when the auth profile is created. It will be opaque and non-semantic, for example a UUID-like value. The system will never derive meaning from it.

Why this shape:

- `id` is the natural relational key for joins.
- `bundle_ref` provides a stable filesystem-safe key for managed content and projection materialization.
- `display_name` stays readable and renamable without forcing storage-path churn.

Alternatives considered:

- Keep display name as the storage key and implement rename as a directory move plus cascading text rewrites.
  Rejected because it keeps storage layout semantically authoritative and leaves rename fragile.
- Keep display name as the primary key and add aliases.
  Rejected because aliases increase lookup complexity but still leave the storage key human-shaped.

### 2. The catalog becomes the sole authority for auth profiles

Auth CRUD will stop scanning or mutating `.houmao/agents/tools/<tool>/auth/<name>/` as the source of truth. Instead:

- auth commands will resolve an auth profile row from the catalog,
- auth content will be read and written through catalog-backed managed content references,
- projection materialization will publish the derived auth tree after catalog updates.

This aligns auth with the existing catalog direction for roles, skills, and launch-profile semantics.

Alternatives considered:

- Keep direct filesystem CRUD and merely change auth directory names to opaque refs.
  Rejected because the source-of-truth split would remain and rename would still depend on projection scanning behavior.

### 3. Managed auth content uses opaque `bundle_ref` paths

Managed content for auth will be stored under a path family such as:

```text
.houmao/content/auth/<tool>/<bundle_ref>/
```

The compatibility projection will materialize auth trees under:

```text
.houmao/agents/tools/<tool>/auth/<bundle_ref>/
```

Projection basenames are implementation detail. Maintained code must not assume the basename is meaningful or stable from an operator perspective.

Why keep a derived projection at all:

- tool adapters and existing project-aware build/runtime seams already consume file-backed auth content,
- the projection still provides a concrete filesystem layout for those consumers,
- the semantic ownership moves to the catalog without forcing inline SQLite storage for auth payloads.

### 4. Relationship-bearing records store auth profile references, not auth display names

Launch profiles and other reusable semantic records must stop storing auth display-name text as their reference key.

The core rule is:

- semantic relationships store `auth_profile_id`,
- user-facing output renders `display_name`,
- filesystem materialization resolves through `bundle_ref`.

This particularly applies to launch-profile auth overrides, because rename should not require editing every profile that points at the same auth profile.

For specialists, the stored specialist row should no longer carry an authoritative `credential_name` copy. The specialist already has a preset relationship, and the preset already points at an auth profile. The displayed auth name should come from that auth profile join.

Alternatives considered:

- Keep launch profiles storing `auth_name` and patch them during rename.
  Rejected because it preserves duplicate semantic identity and makes rename a graph rewrite instead of one row update.

### 5. CLI keeps display-name ergonomics and adds explicit rename

The maintained operator contract stays name-oriented:

- `auth add --name <display-name>` creates a new auth profile,
- `auth get|set|remove --name <display-name>` resolve the named profile for that tool,
- `auth rename --name <old> --to <new>` renames the display name only.

Operator-facing output should continue to show the display name prominently. It may also expose `bundle_ref` as advanced diagnostic metadata, but `bundle_ref` should not replace the normal name-oriented workflow.

This preserves ergonomic CLI usage while making rename a metadata-only change.

### 6. Project-easy and packaged skills adopt the same split identity model

`project easy specialist create --credential <name>` remains a display-name selection surface. When omitted, the current `<specialist-name>-creds` default remains as a display-name default only.

Packaged skills should describe auth names as user-facing names and should stop implying that:

- auth names determine directory names,
- direct auth-path editing is a supported management surface,
- storage path changes are part of rename.

### 7. Hard cut with repo-wide adoption

This change will not include compatibility code, one-way import, or fallback readers for old auth layouts. Implementation will update:

- schema,
- project-aware command paths,
- materialization logic,
- system-skill guidance,
- tests and fixtures,
- user-facing docs that describe auth storage or auth rename behavior.

The repository should converge on one scheme in one change rather than carrying both.

## Risks / Trade-offs

- [Opaque projection paths are less readable in the filesystem] → Keep display names in CLI output, docs, and inspection payloads so operators rarely need to inspect raw auth directories.
- [Catalog-first auth CRUD touches several codepaths at once] → Centralize auth-profile creation, lookup, update, rename, remove, and projection writeback behind shared catalog-aware helpers.
- [Derived projections can leave stale directories behind if materialization is incomplete] → Make projection materialization for auth authoritative and pruning-aware for bundle-ref keyed auth trees.
- [Removing duplicate name fields changes inspection payloads and joins] → Update inspection views and command output deliberately so advanced inspection remains stable and explicit.
- [Hard cut breaks any unmaintained script that scans auth directories by name] → Accept this break and update maintained scripts, tests, and docs in the same change.

## Migration Plan

No compatibility or migration plan will be provided for prior auth layouts or prior auth-name-keyed catalog records.

The implementation plan is a repo-wide hard cut:

1. Change the catalog schema and relationships to the new auth identity model.
2. Change auth CRUD and projection materialization to use catalog-backed auth profiles and opaque bundle refs.
3. Update project-easy, launch-profile, skill, fixture, and documentation surfaces to the new model.
4. Remove remaining maintained assumptions that auth directory names are meaningful.

Rollback is out of scope for this change.

## Open Questions

- None for proposal scope. The intended direction is a hard cut to catalog-owned auth identity with opaque bundle refs and a display-name-only rename surface.
