## Context

`houmao-mgr system-skills install` currently has one projection behavior: copy the packaged Houmao-owned skill tree into the target tool home. The shared installer in [`src/houmao/agents/system_skills.py`](/data1/huangzhe/code/houmao/src/houmao/agents/system_skills.py) records ownership by skill name, packaged asset subpath, projected relative directory, and content digest, but it does not distinguish whether the owned entry is a copied directory or some other filesystem projection.

That becomes a problem once explicit operator installs need a link-backed mode. A symlink-owned entry still occupies the tool-native skill path, but its resolved target can live outside the tool home, so path validation and previous-owned-path cleanup can no longer assume that resolving the installed path stays inside the home. The CLI inspection surface also needs to tell operators whether an installed skill is portable copied content or an environment-local symlink projection.

## Goals / Non-Goals

**Goals:**

- Add an explicit symlink projection mode for `houmao-mgr system-skills install`.
- Make symlink installs use absolute filesystem targets for packaged skill directories.
- Preserve the installer's existing idempotent ownership tracking, collision safety, and renamed-skill migration behavior when reinstall switches between copy and symlink modes.
- Expose projection mode in recorded install state and `houmao-mgr system-skills status`.
- Keep default and Houmao-managed auto-installs on copy mode.

**Non-Goals:**

- Changing the packaged catalog format or adding catalog-level default projection modes.
- Making managed launch/join homes use symlink-installed system skills.
- Supporting relative symlink targets.
- Supporting file-by-file symlink projection instead of one directory entry per skill.
- Preserving compatibility with older install-state schema readers without migration handling.

## Decisions

### Decision: Projection mode is an explicit install-time input, defaulting to copy

`houmao-mgr system-skills install` will gain a `--symlink` flag that selects `projection_mode = "symlink"` for that install request. Without the flag, the command continues to use `projection_mode = "copy"`. The shared installer will accept an explicit projection mode parameter so the CLI and any internal reuse call the same projection path, but Houmao-managed auto-install callers will continue to pass copy mode only.

This keeps the new behavior narrow and operator-driven. It avoids changing the semantics of existing managed homes and avoids introducing catalog-wide or tool-wide defaults that would be harder to inspect and reason about.

Alternatives considered:

- Inferring symlink mode from the target home or tool type. Rejected because it hides behavior behind environment conventions instead of an explicit operator choice.
- Making `--symlink` affect managed auto-installs too. Rejected because managed homes currently benefit from self-contained copied skill content.

### Decision: Install state schema is bumped and records per-skill `projection_mode`

The install-state schema version will be incremented and each installed skill record will store `projection_mode` with the enum values `copy` or `symlink`. The installer will treat the recorded projected relative directory as the owned in-home path and the projection mode as metadata about how that path was produced.

Ownership checks will continue to protect the visible in-home path from non-Houmao collisions, but path removal logic will stop resolving the installed path before validating it against the tool home. For symlink-owned entries, the owned path is the symlink entry inside the home, not the resolved external target. Reinstalling the same skill in a different projection mode will replace the existing owned entry at the same in-home path and update the recorded mode in state.

Alternatives considered:

- Inferring projection mode from the filesystem on every status/read. Rejected because recorded state needs to remain authoritative for safe reinstall and mode-migration behavior.
- Recording a mode only at the top-level state object. Rejected because per-skill records are more robust if the installer later needs mixed-mode migration or partial updates.

### Decision: Symlink installs use absolute packaged-asset paths and require a stable filesystem-backed source

For `projection_mode = "symlink"`, Houmao will create one directory symlink per selected skill whose target is the absolute filesystem path of the packaged skill asset directory. The installer will require that the packaged asset root is backed by a stable real filesystem directory path before creating the symlink. If Houmao cannot obtain such a path, symlink installation fails explicitly.

The implementation should not rely on temporary extraction paths such as `importlib.resources.as_file(...)` for non-filesystem-backed resources, because a symlink target must remain valid after the install command exits. Absolute targets are chosen deliberately so the created link does not depend on the relative position of the tool home to the Python environment.

Alternatives considered:

- Relative symlink targets. Rejected for this change because the operator explicitly wants environment-anchored absolute links and because relative paths add extra reasoning around target computation without improving the local-machine contract.
- Falling back silently to copy mode when a stable source path is unavailable. Rejected because it hides the operator's requested projection mode.

### Decision: CLI inspection surfaces projection mode without removing current summary fields

`houmao-mgr system-skills status` will continue to report whether state exists and which skills are recorded as installed, and it will additionally report each installed skill's projection mode. The JSON payload can do this through per-record objects while preserving the existing summary fields for names and projected directories. Plain-text rendering should show projection mode alongside each installed skill.

This keeps the new detail observable without forcing callers to reconstruct mode from filesystem inspection.

Alternatives considered:

- Reporting projection mode only from `install` output. Rejected because operators need a durable inspection surface after installation completes.
- Replacing the existing `installed_skills` summary with records only. Rejected because additive reporting is less disruptive.

## Risks / Trade-offs

- `[Environment relocation breaks absolute symlinks]` → Document `--symlink` as a local-machine convenience mode and require reinstall after venv rebuild, package reinstall, or interpreter relocation.
- `[State schema bump makes old state unreadable by new code unless migrated]` → Implement explicit backward-compatible state loading or a one-step migration path during the new reader rollout.
- `[Symlink-owned paths can confuse home-relative safety checks if code still resolves them too early]` → Validate ownership against the literal in-home path and only resolve the packaged source path when creating the symlink target.
- `[Status payload expansion could surprise strict JSON consumers]` → Preserve existing summary fields and add new projection-mode detail additively.

## Migration Plan

1. Bump the install-state schema version and teach the loader to either migrate or explicitly accept older copy-only records by normalizing them to `projection_mode = "copy"`.
2. Add projection helpers that can either copy a packaged skill tree or create an absolute symlink entry from a filesystem-backed packaged asset root.
3. Thread projection mode through `houmao-mgr system-skills install`, install result payloads, state writing, and status rendering.
4. Update CLI docs and unit tests to cover copy installs, symlink installs, reinstall mode switches, and status inspection.

## Open Questions

None at proposal time.
