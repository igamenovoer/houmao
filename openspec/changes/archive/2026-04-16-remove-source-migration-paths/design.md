## Context

Houmao currently carries source-level compatibility paths for persisted data created by older development snapshots. The most visible examples are:

- project catalog schema migration branches in `ProjectCatalog.initialize()`, including table rebuilds and old catalog version upgrades,
- automatic import of legacy `.houmao/agents/` and `.houmao/easy/` project metadata into the SQLite catalog,
- filesystem mailbox bootstrap logic that can materialize mailbox-local SQLite state from legacy shared mutable mailbox state.
- runtime session manifest parsing that upgrades schema v2/v3 manifests into the current manifest model,
- brain construction parsing that accepts legacy recipe files, hidden legacy CLI flags, and old tool-adapter field aliases,
- system-skill installation code that treats old install-state/path layouts as owned state to migrate or remove,
- gateway queue/notifier schema setup that alters older SQLite tables in place.

Those paths were useful during rapid iteration, but they now create the wrong maintenance contract. Houmao has not reached 1.0.0, and incompatible persisted project or mailbox formats should be treated as stale local state that operators recreate from scratch.

This change does not remove schema version fields. Version fields remain useful for rejecting incompatible state clearly.

## Goals / Non-Goals

**Goals:**

- Remove maintained source branches that transform old persisted formats into current formats.
- Remove maintained source branches that accept old source-shape aliases as equivalent to current source files.
- Keep fresh project, mailbox, runtime session, gateway, generated home, and system-skill creation working on the current schema.
- Fail clearly when existing persisted state or source files are incompatible with the current source.
- Remove legacy project tree import as an automatic catalog adoption path.
- Remove tests and docs that imply old persisted formats are supported through migrations.
- Preserve recovery flows that rebuild current-format indexes from canonical artifacts, where the source artifacts are still part of the current contract.

**Non-Goals:**

- No attempt to migrate existing project catalogs, mailbox roots, launch profiles, gateway roots, session manifests, system-skill install-state files, or legacy specialist trees.
- No long-term compatibility shim for old CLI data shapes, source field aliases, old manifest schemas, or old SQLite table constraints.
- No removal of unrelated deprecated launchers, demo packages, or compatibility namespaces unless they perform persisted-format migration for maintained project or mailbox state.
- No removal of provider-required current configuration seeding such as Codex `notice.model_migrations.*`; that is not Houmao persisted-state migration.
- No removal of schema version validation itself.

## Decisions

### Treat Format Changes As Hard Reset Boundaries

Project catalog, mailbox, manifest, gateway, system-skill, and source-shape incompatibilities will fail fast. The implementation should prefer checks shaped like:

```text
state/source exists?
  no  -> create current schema
  yes -> validate current schema/version/invariants
          ok       -> continue
          mismatch -> fail with recreate/rebootstrap/rebuild guidance
```

Alternatives considered:

- Keep migrations but mark them best effort: rejected because it still leaves unmaintained code paths that can silently corrupt or normalize user state.
- Keep only the latest migration: rejected because it preserves the same ambiguous compatibility promise.
- Drop version checks entirely: rejected because operators need explicit diagnostics instead of confusing SQLite errors.

### Remove Project Catalog Migration And Import Paths

`ProjectCatalog.initialize()` should create missing current tables and metadata, then validate existing catalog metadata against the current catalog schema version. If an existing catalog reports an older or unsupported version, initialization should fail with a clear message telling the operator to recreate the project overlay.

Automatic `ensure_legacy_import()` behavior should be removed from maintained catalog operations. Legacy tree-backed `.houmao/agents/` and `.houmao/easy/` metadata should not become an implicit migration source for the catalog. Fresh catalog-backed project commands continue to write current catalog rows and compatibility projection files as needed.

Implementation should remove helper functions whose only purpose is old-catalog transformation, such as table rebuild helpers for previous constraints and column-drop helpers for removed columns.

### Remove Mailbox Legacy State Migration, Keep Current-Format Recovery

Filesystem mailbox roots may still recover supported current-format structural indexes from canonical Markdown message files, because those files remain part of the current durability contract.

However, mailbox bootstrap and repair should not migrate old shared mutable mailbox state into mailbox-local SQLite. If mailbox-local SQLite is missing for a current registration, the system may initialize it using deterministic defaults derived from current structural records and canonical message projections. It should not consult legacy shared mutable state as an authoritative migration source.

This keeps the useful recovery boundary clear:

```text
supported recovery:
  canonical message corpus -> current structural index/current local state defaults

unsupported migration:
  old shared mutable mailbox_state -> current mailbox-local mutable state
```

### Remove Runtime Manifest Upgrades

Session manifest loading should accept only the current manifest schema. The current `parse_session_manifest_payload()` v2/v3 upgrade path should become explicit rejection with restart guidance. Legacy helper functions used only to synthesize current fields from old manifest payloads should be removed.

Runtime-owned fresh session start continues to write the current manifest schema. Current-schema validation and JSON Schema assets remain.

### Remove Legacy Construction Source Adoption

Brain construction and tool-adapter parsing should require current source shapes:

- presets instead of legacy recipe files,
- current CLI flags instead of hidden aliases such as `--recipe`, `--config-profile`, and `--cred-profile`,
- `setup_projection` and `auth_projection` instead of old adapter keys such as `config_projection` and `credential_projection`.

This removes support for treating old source documents as equivalent construction inputs. Operators should rewrite source files to the current format or recreate generated homes from current presets.

### Remove System-Skill Install-State Migration

System-skill installation should manage only current install-state records. Existing current records can still be used for idempotence and non-owned collision protection, but old copy-only state versions, old family-namespaced paths, and renamed-skill records should not be treated as migration sources.

When old Houmao-owned skill layouts are present, the operator should reinstall current system skills or clear the old target home. The installer should not silently adopt or rewrite old records as current ownership.

### Remove Gateway SQLite Schema Upgrade

Gateway durable queue/notifier storage should create the current schema for fresh gateway roots and validate existing roots before use. Older gateway SQLite tables should fail with guidance to recreate the gateway/session root instead of applying `ALTER TABLE` upgrades.

### Keep Errors Operator-Oriented

Fail-fast diagnostics should tell the operator what to recreate:

- incompatible project catalog: recreate the `.houmao/` project overlay or initialize a fresh project,
- incompatible mailbox root: delete and bootstrap a fresh mailbox root.
- incompatible session manifest or generated home: start a fresh runtime session or rebuild the generated home,
- incompatible system-skill install state: reinstall current system skills into a clean target home,
- incompatible gateway root: restart with a fresh session/gateway root.

The errors should avoid promising automatic repair or migration for old formats.

### Audit By Behavior, Not By Keyword

The source contains many uses of words such as "legacy" and "migration" for deprecated launchers, archived demos, or user-facing migration guidance. This change targets maintained persisted-format migration paths. The implementation should audit matches, remove behavior that transforms old stored formats, and leave unrelated fail-fast guidance or archived references alone unless they contradict the new specs.

## Risks / Trade-offs

- Operators with existing pre-change project catalogs cannot keep using them directly -> This is intentional before 1.0.0; errors should say to recreate the overlay rather than imply a broken install.
- Removing legacy project import can strand local prototype definitions in older trees -> The supported path is to recreate project agents on the current catalog-backed model.
- Removing mailbox legacy-state migration can reset per-message read/star/archive flags when only old shared mutable state exists -> The current-format mailbox-local database is authoritative; old shared mutable state is no longer maintained.
- Removing manifest upgrades makes old live/runtime sessions non-resumable -> Start fresh sessions from current launch profiles or presets.
- Removing system-skill install-state migration can leave stale directories in existing tool homes -> Reinstall into a clean tool home or remove stale Houmao-owned content manually.
- Removing legacy source aliases may break old local presets/adapters -> Rewrite those files to current field names.
- Broad keyword cleanup could accidentally remove unrelated compatibility surfaces -> Scope implementation to persisted-format migration behavior and validate with focused project/mailbox tests.

## Migration Plan

There is intentionally no data migration plan.

Deployment consists of removing the migration source paths and updating tests/docs. Existing incompatible local state should fail with restart-from-scratch guidance. Rollback during development means reverting the code change or recreating local Houmao-owned state with the checked-out version.

## Open Questions

None. The policy decision is explicit: before 1.0.0, Houmao does not maintain in-place migrations for incompatible persisted project or mailbox formats.
