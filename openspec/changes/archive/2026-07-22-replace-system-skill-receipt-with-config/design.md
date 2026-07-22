## Context

The static system-skill lifecycle currently writes `receipt.json` below a tool-scoped Houmao state directory. The payload duplicates facts available from its location or packaged manifest and still uses receipt terminology even though install, sync, status, doctor, upgrade, uninstall, and managed-home provenance treat it as authoritative ownership configuration.

Houmao is under active development and permits breaking changes. This change therefore resets the persisted contract instead of preserving or migrating either historical receipt schema. Users must start with a clean target and reinstall system skills.

## Goals / Non-Goals

**Goals:**

- Give system-skill lifecycle state an explicit Houmao-owned filename and configuration model.
- Store only release identity, collection projection mode, and the per-root facts required for safe ownership and integrity decisions.
- Preserve overlapping admin/agent pack ownership without a duplicate selected-pack field.
- Rename public Python and CLI surfaces consistently from receipt to config terminology.
- Keep lifecycle writes atomic and keep doctor useful for configless static installations.

**Non-Goals:**

- Read, migrate, delete, diagnose, or otherwise recognize any `receipt.json` file.
- Preserve compatibility with receipt model names, JSON fields, status values, or structured CLI output.
- Add audit timestamps, operation history, source provenance, or duplicated manifest metadata.
- Infer ownership for paths installed without the new configuration.

## Decisions

### 1. Use One Explicit Tool-Scoped Configuration

The canonical path is `<home>/.houmao/system-skills/<tool>/houmao-skill-config.json`, with schema id `houmao-skill-config.v1`. The home and tool remain absent from the payload because the file location supplies both. `manifest_schema_version`, roles, activation posture, and source paths remain absent because the packaged manifest supplies them.

The lifecycle code uses `SystemSkillConfig`, `SystemSkillConfigSkillRecord`, `SystemSkillConfigInspection`, `system_skill_config_path()`, `inspect_system_skill_config()`, and config-named result fields. Compatibility aliases are not retained.

### 2. Store Exactly Four Top-Level Fields

The strict payload is:

```json
{
  "schema_version": "houmao-skill-config.v1",
  "houmao_version": "1.2.1",
  "projection_mode": "symlink",
  "skills": [
    {
      "name": "houmao-admin-entrypoint",
      "relative_path": "skills/houmao-admin-entrypoint",
      "content_digest": "<64 lowercase hexadecimal characters>",
      "owning_pack_ids": ["admin"]
    }
  ]
}
```

Every skill record has exactly the four shown fields. The parser rejects unknown or missing keys, duplicate names, unsafe relative paths, invalid digests, empty or duplicate owner sets, unsupported owners, an invalid projection mode, and a skill list that does not represent a valid installed static pack union.

The one `houmao_version` records the Houmao release that wrote all members. Per-root live versions remain in `SKILL.md` and doctor continues to read those values directly.

### 3. Derive Selected Packs From Owner Sets

The installed pack set is the manifest-ordered union of every skill record's `owning_pack_ids`. A read-only `selected_pack_ids` property may expose the derived value to callers, but it is never serialized. The parser validates that the records, owner sets, and derived packs form the exact static union expected for that recorded installation.

This keeps the minimum evidence required for partial uninstall. Removing one pack subtracts that id from each record and retains a shared root while another owner remains.

### 4. Make Receipt Removal a Clean Break

New code only probes `houmao-skill-config.json`. It has no legacy filename constant, legacy receipt model, legacy inspection status, or receipt parser. It neither reads nor removes an existing `receipt.json`.

When no new config exists, all same-name destinations remain unowned. Normal collision checks reject an install over those roots. Users must uninstall with the previous Houmao version or remove the old system-skill state and projections before reinstalling.

Legacy flat-path inspection that is independent of receipt parsing may remain if current commands still need it, but the new config does not record historical removals.

### 5. Keep Configuration Transactional

Install, sync, and upgrade stage and validate the complete requested union, commit projections, and atomically write the config last. Rollback restores the previous new-format config bytes and affected projections. Partial uninstall rewrites the reduced config after safe path changes; final uninstall removes it. Empty configs are invalid and are never persisted.

### 6. Rename CLI and Managed Provenance Surfaces

Structured install, upgrade, uninstall, status, doctor, and managed brain-construction provenance use `config_path` or `config`. Plain output says `Skill config:`. No current output contains `receipt`, `receipt_path`, or `Receipt:`.

Doctor keeps direct installed-root integrity and frontmatter checks independent from config ownership. Missing config evidence does not prevent a complete copy-paste or Skills CLI installation from being version-healthy.

## Risks / Trade-offs

- [Existing managed roots become unowned conflicts] → Treat this as the intended breaking boundary and document clean removal followed by reinstall.
- [Removing timestamps reduces auditability] → Keep the file focused on active ownership; use filesystem and command logs for operational history.
- [Deriving packs adds parser work] → Centralize derivation in the config model and validate it once when loading.
- [A stale `receipt.json` remains beside the new config] → Ignore it completely so the new lifecycle never claims ownership of an obsolete or foreign generic file.
- [Structured-output consumers break] → Document the field rename and require consumers to adopt `config` and `config_path`.

## Migration Plan

There is no data migration. Before adopting the new release, users uninstall system skills with the previous release or manually remove the old Houmao-owned projections and state. They then reinstall with the new release, which creates `houmao-skill-config.json`.

Implementation removes receipt types and parsers, introduces the strict config model, updates lifecycle transactions and consumers, updates tests and docs, and validates a fresh install/status/doctor/uninstall cycle. Rollback requires reverting the code and reinstalling system skills with the matching release; neither direction converts persisted state.

## Open Questions

None.
