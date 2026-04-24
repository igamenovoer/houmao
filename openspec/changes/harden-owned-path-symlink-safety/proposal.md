## Why

Houmao currently has multiple filesystem mutation paths that treat symlinked artifacts inconsistently. In several places, resolving a managed path before deleting or replacing it can redirect the mutation onto the symlink target, which risks altering caller-owned files outside Houmao-managed space or the wrong files inside managed space.

## What Changes

- Introduce a cross-cutting owned-path mutation safety contract for Houmao-managed filesystem operations.
- Require destructive writes, replacements, and cleanup to act on lexical Houmao-owned artifact paths rather than resolved symlink targets.
- Require external or caller-provided source paths to remain read-only inputs unless a command explicitly declares ownership transfer.
- Extend the owned-path safety model to project catalog content, project migration, credential storage, managed cleanup, registry cleanup, and managed-agent authority storage.
- Add regression coverage for symlink-backed artifacts and escaped-path cleanup cases across the affected subsystems.

## Capabilities

### New Capabilities
- `owned-path-mutation-safety`: Defines the repository-wide invariants for mutating Houmao-managed filesystem artifacts in the presence of symlinks, including lexical owned-path mutation, external-path read-only handling, and contained cleanup.

### Modified Capabilities
- `project-config-catalog`: Managed catalog content and derived projections must mutate only owned lexical paths and must not follow symlink targets during replace or delete flows.
- `houmao-mgr-project-migrate-cli`: Project migration must canonicalize overlay content without mutating repo-owned or otherwise external source trees through symlink resolution.
- `houmao-mgr-credentials-cli`: Credential update and removal flows must keep filesystem mutations contained to Houmao-managed credential roots, even when existing artifacts are symlink-backed.
- `houmao-mgr-cleanup-cli`: Cleanup flows must remove only owned session or runtime artifacts and must not delete escaped or symlink-targeted external paths.
- `agent-discovery-registry`: Shared-registry removal and stale-record cleanup must stay contained to registry-owned lexical directories even when entries are malformed or symlink-backed.
- `houmao-server`: Server-managed headless authority storage cleanup must delete only server-owned artifacts and must not follow symlinked agent roots.

## Impact

- Affected code: `src/houmao/project/catalog.py`, `src/houmao/project/migration.py`, `src/houmao/srv_ctrl/commands/credentials.py`, `src/houmao/srv_ctrl/commands/runtime_cleanup.py`, `src/houmao/agents/realm_controller/registry_storage.py`, `src/houmao/server/managed_agents.py`, and shared owned-path helpers.
- Affected systems: project overlay content/projection management, migration, credential storage, runtime cleanup, shared registry cleanup, and server-managed headless state.
- Validation: new unit coverage for symlink-backed mutation, contained cleanup, and external-path preservation across the affected subsystems.
