## Context

The current system-skill installer treats each target tool home as a stateful Houmao-owned installation. It writes `.houmao/system-skills/install-state.json` into the home, validates that state on reinstall, and refuses to overwrite a selected skill path unless the state file records that path as current Houmao-owned content.

The requested behavior is simpler: a selected current Houmao system skill is always replaceable at its exact tool-native projected path. This matches the development posture of the project before 1.0 and avoids keeping Houmao metadata in external tool config homes. `--symlink` remains supported; it should use the same overwrite boundary as copied projection.

## Goals / Non-Goals

**Goals:**

- Remove install-state JSON creation, loading, validation, and ownership checks from system-skill installation.
- Make reinstall deterministic by removing each selected current skill destination, if present, before projecting the packaged skill.
- Preserve `copy` and `symlink` projection modes.
- Keep destructive behavior limited to the selected current `houmao-*` skill destination paths.
- Keep `system-skills status` as live filesystem discovery of current packaged skill paths and projection mode.
- Update tests and docs so install-state is no longer part of the current public or internal contract.

**Non-Goals:**

- Do not add migration handling for old `.houmao/system-skills/install-state.json` files.
- Do not remove old state files or old family-namespaced skill paths as part of install.
- Do not add prompts or confirmation flags for replacing selected current Houmao skill paths.
- Do not change catalog selection, named set expansion, supported tools, effective-home resolution, or multi-tool install parsing.

## Decisions

### Remove install state entirely from the install path

The installer should no longer call `load_system_skill_install_state()` or write `system_skill_state_path_for_home()` after projection. The install result already carries selected and projected paths for the current invocation, while status already discovers installed skills from the filesystem.

Alternative considered: keep a state file outside the tool config home. That would avoid polluting tool homes but preserves most of the complexity: schema versioning, stale-state handling, and ownership-proof decisions. The change intentionally removes that layer instead.

### Treat selected current skill paths as replaceable

For each resolved selected skill, installation should compute the existing tool-native destination path, remove it if it exists or is a symlink, then project the packaged skill in the requested mode.

This makes idempotence independent of recorded ownership:

```text
selected skill
  -> target = <home>/<tool skill root>/<skill name>
  -> rm -rf target if present
  -> copy tree or create symlink
```

Alternative considered: only overwrite directories that contain a matching `SKILL.md` header or Houmao marker. That would reintroduce heuristic ownership checks and leave edge cases where stale skill content still blocks reinstall.

### Keep the overwrite boundary exact and narrow

The installer should replace only the selected current skill destination paths. It should not delete the parent `skills/` directory, unselected skill directories, legacy family-namespaced paths, or `.houmao/system-skills/install-state.json` if such a stale file already exists.

This means the change accepts destruction of an existing selected Houmao skill path in a tool config home, but avoids broad cleanup.

### Preserve `--symlink`

`--symlink` remains a projection-mode choice on install. Reinstalling copy over symlink or symlink over copy should work through the same remove-then-project flow. If packaged assets are not filesystem-backed, explicit symlink installation should still fail rather than falling back to copy.

### Make status filesystem-only

`system-skills status` should continue to inspect the known current skill paths and infer `copy` from a directory and `symlink` from a symlink. It should not report whether install-state exists, should not parse install-state files, and should not treat old state as an error.

## Risks / Trade-offs

- Existing user-authored content at a selected `houmao-*` skill path can be replaced without warning. Mitigation: replacement is limited to explicitly selected current Houmao skill paths, and this behavior is documented.
- Stale `.houmao/system-skills/install-state.json` files may remain after upgrading. Mitigation: the new installer ignores them, so they no longer affect behavior; docs can describe them as obsolete.
- Removing content-digest state means status cannot distinguish copied package content from manually edited copied content. Mitigation: the current requested behavior does not require drift detection; reinstall always refreshes selected skills.
- Multi-tool install remains partially applied if a later tool fails during projection. Mitigation: this is not introduced by the state removal; preflight selection validation remains before filesystem mutation.

## Migration Plan

Implement the change as a breaking pre-1.0 contract simplification. Existing target homes do not need migration. Future installs ignore old state files and replace selected current skill destinations directly.

Rollback is straightforward at code level: restore the install-state model and collision checks. Existing installs made under the simplified model will still have ordinary projected skill directories or symlinks.

## Open Questions

None. The user confirmed `--symlink` remains supported and selected existing Houmao system-skill projections in tool config homes may be overwritten.
