## Context

`houmao-mgr system-skills install` projects packaged Houmao-owned skills into resolved tool homes for Claude, Codex, Copilot, and Gemini. Installation is intentionally stateless: it resolves selected catalog skills, computes exact tool-native projection paths, removes selected existing paths, and projects copied or symlinked skill trees. `status` discovers current packaged skill paths from the filesystem.

There is no matching supported removal command. Users who want to remove Houmao system skills must know each tool's projection root and delete paths by hand. The requested behavior is intentionally simpler than install: uninstall means all known Houmao system skills, not a selected subset.

## Goals / Non-Goals

**Goals:**

- Add `houmao-mgr system-skills uninstall` for Claude, Codex, Copilot, and Gemini homes.
- Define "known Houmao skills" as the current packaged catalog inventory.
- Remove every current catalog-known Houmao system-skill projection path for the resolved tool home.
- Reuse existing tool parsing and effective-home resolution, including comma-separated multi-tool support and the single-tool-only `--home` override.
- Preserve unrelated tool-home content, parent skill roots, legacy family-namespaced paths, obsolete install-state files, and user-authored non-Houmao skills.
- Make uninstall idempotent and filesystem-friendly: missing homes or missing skill paths are reported as absent rather than errors.
- Return structured output that makes removed versus absent paths clear.

**Non-Goals:**

- Do not support uninstall selection flags such as `--skill`, `--skill-set`, or `--all`.
- Do not remove historical aliases or old family-namespaced Houmao skill paths that are no longer in the current catalog.
- Do not remove parent roots such as `skills/` or `.gemini/skills/`.
- Do not add confirmation prompts or interactive deletion flows.
- Do not change managed launch or managed join auto-install behavior.

## Decisions

### Uninstall all current catalog-known skills

Uninstall should load the packaged catalog and iterate `catalog.skill_names`. For each current skill, it should compute the existing tool-native projection path using the same `projected_system_skill_relative_dir()` helper used by install and status.

Alternative considered: mirror install selection with `--skill` and `--skill-set`. The user explicitly rejected that model. Keeping uninstall all-known avoids selection ambiguity and provides a simple inverse for "remove Houmao's current skill surface from this home."

### Add a shared core removal helper

Add a helper beside `install_system_skills_for_home()` in `src/houmao/agents/system_skills.py`, likely named `uninstall_system_skills_for_home()`. It should return a dataclass result with:

- tool,
- resolved home path,
- removed skill names and relative dirs,
- absent skill names and relative dirs.

The helper should not call `mkdir()`. If the resolved home does not exist, it should report every current skill as absent and leave the filesystem untouched.

Alternative considered: implement deletion entirely in the Click command. That would duplicate projection-path knowledge outside the shared system-skill module and make future tool projection changes easier to miss.

### Use exact-path removal only

For each current skill path, uninstall should remove the exact path when it exists as a directory, file, or symlink. It should reuse the same low-level removal semantics as reinstall for the target path only.

```text
catalog skill
  -> relative path for selected tool
  -> target = resolved_home / relative_path
  -> absent if target does not exist and is not a symlink
  -> remove target if directory, file, or symlink
```

It should not scan the parent skill root looking for arbitrary `houmao-*` names. The catalog is the authority for "known" skills.

Alternative considered: glob `houmao-*` under the tool skill root. That would remove unknown user-created or future/legacy directories and would make uninstall broader than the current packaged contract.

### Reuse install multi-tool parsing, not install selection

The command should reuse `_parse_system_skills_tools()`, `_validate_home_scope_for_system_skills_tools()`, and `_resolve_effective_system_skills_home()` so `install` and `uninstall` agree on supported tools and home resolution. It should not accept install-only options.

For multi-tool JSON output, use an aggregate payload parallel to install:

- `tools`: parsed tool list,
- `uninstallations`: one single-tool-shaped uninstall result per tool.

Plain output should identify the target homes and summarize removed and absent counts.

### Keep status as the verification path

After uninstall, `system-skills status` should show no installed current Houmao-owned skills for the same home. Uninstall itself does not need to perform a second status scan; tests can verify the interaction.

## Risks / Trade-offs

- Existing user-authored content under a current Houmao catalog skill name can be deleted. Mitigation: this is the same reserved-name boundary install already owns, and docs will state that uninstall removes all current known Houmao skill names.
- Legacy Houmao aliases may remain after uninstall. Mitigation: this is intentional; current catalog-known uninstall avoids accidental broad deletion. Legacy cleanup can be a separate explicit command if needed.
- A missing home producing a successful no-op could hide a mistyped `--home`. Mitigation: structured output will show the resolved home and every known skill as absent, making the target visible without creating directories.
- Multi-tool uninstall may be partially applied if a later tool hits a filesystem error. Mitigation: preflight tool parsing and `--home` validation happen before mutation; this mirrors the existing multi-tool install posture.

## Migration Plan

This is an additive pre-1.0 CLI feature. Existing installations need no migration. After upgrade, operators can run `houmao-mgr system-skills uninstall --tool <tool>` against a resolved home to remove current catalog-known Houmao system-skill projections.

Rollback is straightforward at code level: remove the Click command and shared helper. Existing tool homes remain ordinary directories or symlinks that can still be inspected by `status` or refreshed by `install`.

## Open Questions

None. The user clarified that uninstall should mean all known Houmao skills rather than mirroring install selection.
