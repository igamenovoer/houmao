## Why

The `remove-source-migration-paths` refactor (b18817e4) deleted session manifest v2/v3 schemas and bumped the canonical version to 4, but two documentation files still reference the old schema versions. These stale references mislead readers about the current manifest format and point to files that no longer exist on disk.

## What Changes

- Fix `docs/reference/system-files/agents-and-runtime.md` line 71: update `schema_version=2` → `schema_version=4` and correct the operational note on line 78 to reflect that the loader now rejects anything other than v4 (not just v1).
- Fix `openspec/specs/brain-launch-runtime/spec.md` line 806: update the example from `session_manifest.v3.schema.json` to `session_manifest.v4.schema.json` to reference a file that actually exists.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `brain-launch-runtime`: The spec example referencing a versioned schema filename needs updating from v3 to v4 to match the current on-disk schema files.

## Impact

- `docs/reference/system-files/agents-and-runtime.md` — user-facing reference doc, two lines
- `openspec/specs/brain-launch-runtime/spec.md` — spec artifact, one example line
- No code, API, or dependency changes
