## 1. Installer Core

- [x] 1.1 Remove tool-home install-state data models, state path helpers, state loading, state validation, state writing, record merging, and content-digest code from `src/houmao/agents/system_skills.py`.
- [x] 1.2 Refactor `install_system_skills_for_home()` so it resolves selected skills, removes each selected current skill destination if it exists or is a symlink, and projects the packaged skill in `copy` or `symlink` mode.
- [x] 1.3 Keep explicit symlink projection failure behavior when packaged skill assets are not filesystem-backed.
- [x] 1.4 Ensure install does not remove unselected skill directories, parent skill roots, legacy family-namespaced paths, unrelated tool-home content, or obsolete `.houmao/system-skills/install-state.json` files.

## 2. CLI Behavior

- [x] 2.1 Update `houmao-mgr system-skills install` behavior as needed so selected existing skill destinations are overwritten without install-state ownership checks.
- [x] 2.2 Keep single-tool and multi-tool install payload shapes unchanged, including resolved skill lists, projected relative dirs, and projection mode.
- [x] 2.3 Ensure `houmao-mgr system-skills status` remains filesystem-discovery based and ignores obsolete install-state files.
- [x] 2.4 Remove any CLI text or error paths that tell operators to use a clean target home because install-state ownership is missing or obsolete.

## 3. Tests

- [x] 3.1 Replace installer tests that expect non-owned selected-path collision failure with coverage that selected current skill paths are overwritten.
- [x] 3.2 Replace old install-state compatibility tests with coverage that obsolete install-state files are ignored by install and status.
- [x] 3.3 Keep or update copy-to-symlink and symlink-to-copy reinstall tests to verify remove-then-project behavior without install state.
- [x] 3.4 Add coverage that unselected skill directories, legacy family-namespaced paths, unrelated content, and obsolete install-state files are preserved.
- [x] 3.5 Update CLI command tests for status and install output after removing install-state assumptions.

## 4. Documentation And Specs

- [x] 4.1 Update `docs/reference/cli/system-skills.md` to remove install-state ownership guidance and document stateless selected-skill overwrite semantics.
- [x] 4.2 Update `docs/reference/cli/houmao-mgr.md` so the system-skills summary describes filesystem-discovered status and selected-path overwrite reinstall.
- [x] 4.3 Search docs and packaged system skills for stale `.houmao/system-skills/install-state.json`, old install-state, collision-failure, or clean-target-home guidance and revise current references.

## 5. Validation

- [x] 5.1 Run `openspec validate simplify-system-skill-install-overwrite --strict`.
- [x] 5.2 Run focused system-skill tests with `pixi run pytest tests/unit/agents/test_system_skills.py tests/unit/srv_ctrl/test_system_skills_commands.py`.
- [x] 5.3 Run `pixi run lint` or targeted Ruff checks for edited Python files.
