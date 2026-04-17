## Why

Operators can install Houmao-owned system skills into Claude, Codex, Copilot, and Gemini homes, but there is no matching supported command to remove that installed Houmao skill surface. This leaves users to manually delete tool-specific skill directories, which is error-prone because projection roots differ by tool and should not remove unrelated user skills.

## What Changes

- Add `houmao-mgr system-skills uninstall` as the supported way to remove Houmao-owned system skills from resolved tool homes.
- Define uninstall as removing all current catalog-known Houmao system-skill projection paths for the selected tool home, with no `--skill` or `--skill-set` selection surface.
- Reuse the existing system-skills tool parsing and home-resolution rules, including comma-separated multi-tool support and the single-tool-only `--home` override rule.
- Keep the destructive boundary narrow: remove only exact current Houmao system-skill projection paths, whether copied directories, symlinks, or files; preserve parent skill roots, unrelated tool-home content, legacy family-namespaced paths, and obsolete install-state files.
- Make uninstall idempotent: missing current Houmao skill paths are reported as absent/skipped rather than treated as failures.
- Document the uninstall command and its all-known-Houmao-skills semantics in the CLI and system-skills overview docs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-system-skills-cli`: add the `uninstall` command and define its tool/home parsing, all-current-skill removal behavior, output shape, and idempotent missing-path handling.
- `houmao-system-skill-installation`: add the shared removal contract for all current catalog-known Houmao system-skill projections in a target tool home.
- `docs-cli-reference`: update CLI reference requirements so docs cover `system-skills uninstall` and distinguish selective install from all-known-skill uninstall.
- `docs-system-skills-overview-guide`: update the getting-started system-skills guide requirements so the overview includes uninstall usage and removal boundaries.

## Impact

- Affected implementation: `src/houmao/agents/system_skills.py` and `src/houmao/srv_ctrl/commands/system_skills.py`.
- Affected tests: system-skill core tests and CLI command tests under `tests/unit/agents/test_system_skills.py` and `tests/unit/srv_ctrl/test_system_skills_commands.py`.
- Affected docs: `docs/reference/cli/system-skills.md`, `docs/reference/cli.md`, `docs/reference/cli/houmao-mgr.md`, and `docs/getting-started/system-skills-overview.md`.
- No new runtime dependency is required.
