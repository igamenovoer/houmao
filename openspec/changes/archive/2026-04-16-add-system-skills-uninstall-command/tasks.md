## 1. Shared Removal Core

- [x] 1.1 Add a `SystemSkillUninstallResult` dataclass in `src/houmao/agents/system_skills.py` with tool, home path, removed skill names/relative dirs, and absent skill names/relative dirs.
- [x] 1.2 Implement `uninstall_system_skills_for_home()` to load the current packaged catalog, compute every current skill's tool-native relative path, and remove exact existing paths.
- [x] 1.3 Ensure the shared removal helper handles directories, files, and symlinks while treating missing paths as absent instead of errors.
- [x] 1.4 Ensure the shared removal helper does not create missing homes or parent skill roots and preserves unrelated user skills, parent roots, legacy paths, unrecognized `houmao-*` paths, and obsolete install-state files.

## 2. CLI Command

- [x] 2.1 Add `houmao-mgr system-skills uninstall --tool <tool>[,<tool>...] [--home <path>]` in `src/houmao/srv_ctrl/commands/system_skills.py`.
- [x] 2.2 Reuse existing tool parsing, supported-tool validation, multi-tool duplicate/malformed rejection, home-resolution, and multi-tool `--home` rejection helpers.
- [x] 2.3 Keep uninstall free of install-selection options such as `--skill`, `--skill-set`, `--set`, `--default`, and `--symlink`.
- [x] 2.4 Add structured JSON payload builders for single-tool uninstall and multi-tool aggregate uninstall output.
- [x] 2.5 Add plain-text rendering that reports target homes and summarizes removed versus absent known Houmao skill paths.

## 3. Tests

- [x] 3.1 Add shared-core tests in `tests/unit/agents/test_system_skills.py` for removing copied directories, symlinks, files, and missing paths.
- [x] 3.2 Add shared-core tests that missing target homes are not created and unrelated user skills, parent roots, legacy paths, unrecognized `houmao-*` paths, and obsolete install-state files are preserved.
- [x] 3.3 Add CLI tests in `tests/unit/srv_ctrl/test_system_skills_commands.py` that help output lists `uninstall` and single-tool uninstall returns the expected JSON shape.
- [x] 3.4 Add CLI tests for effective-home resolution through explicit `--home`, tool-native env vars, and project-scoped defaults, including Gemini's `.gemini/skills/` removal path.
- [x] 3.5 Add CLI tests for comma-separated multi-tool uninstall output and rejection of multi-tool `--home`, malformed tool lists, duplicate tools, and install-only selection flags.
- [x] 3.6 Add a status-after-uninstall test showing `system-skills status` reports no current installed Houmao-owned skills for the target home after uninstall.

## 4. Documentation

- [x] 4.1 Update `docs/reference/cli/system-skills.md` command shape, examples, home-resolution notes, output notes, and removal-boundary guidance for `uninstall`.
- [x] 4.2 Update `docs/reference/cli/houmao-mgr.md` and `docs/reference/cli.md` so the summary command lists and system-skills overview mention `uninstall`.
- [x] 4.3 Update `docs/getting-started/system-skills-overview.md` to explain single-tool uninstall, all-current-known-Houmao-skills semantics, and the preserved-content boundary.

## 5. Validation

- [x] 5.1 Run `openspec validate add-system-skills-uninstall-command --strict`.
- [x] 5.2 Run focused tests with `pixi run pytest tests/unit/agents/test_system_skills.py tests/unit/srv_ctrl/test_system_skills_commands.py`.
- [x] 5.3 Run `pixi run lint` or targeted Ruff checks for edited Python files.
