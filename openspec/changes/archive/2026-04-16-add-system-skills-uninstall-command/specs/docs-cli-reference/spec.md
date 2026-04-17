## ADDED Requirements

### Requirement: CLI reference documents system-skills uninstall
The CLI reference pages `docs/reference/cli/system-skills.md`, `docs/reference/cli/houmao-mgr.md`, and `docs/reference/cli.md` SHALL document `houmao-mgr system-skills uninstall` as the supported command for removing current Houmao-owned system skills from resolved Claude, Codex, Copilot, and Gemini homes.

That coverage SHALL state that `system-skills uninstall` requires `--tool` with either one supported tool identifier or a comma-separated list of supported tool identifiers.

That coverage SHALL describe `--home` as optional for single-tool `uninstall` invocations and invalid when `--tool` names more than one comma-separated tool.

That coverage SHALL document effective-home resolution for omitted-home uninstall with this precedence:

1. tool-native home env var
2. project-scoped default home

That coverage SHALL explain that uninstall removes all current catalog-known Houmao system-skill projection paths for the resolved tool home and does not accept install-selection flags such as `--skill`, `--skill-set`, `--set`, `--default`, or `--symlink`.

That coverage SHALL distinguish install and uninstall semantics: install can select sets or explicit skills, while uninstall always targets all current known Houmao system skills for the resolved home.

That coverage SHALL explain that uninstall removes exact current Houmao skill paths whether they are copied directories, symlinks, or files.

That coverage SHALL explain that uninstall is idempotent, reports missing current skill paths as absent or skipped, and does not create missing homes or parent skill roots.

That coverage SHALL explain that uninstall preserves parent skill roots, unrelated user skills, unrecognized `houmao-*` paths, legacy family-namespaced paths, and obsolete install-state files.

That coverage SHALL show at least one single-tool explicit-home uninstall example and at least one comma-separated multi-tool uninstall example.

#### Scenario: Reader finds system-skills uninstall in the command shape
- **WHEN** a reader opens `docs/reference/cli/system-skills.md` or `docs/reference/cli/houmao-mgr.md`
- **THEN** the command shape includes `system-skills uninstall`
- **AND THEN** the page explains that uninstall removes all current known Houmao system skills for the resolved home

#### Scenario: Reader sees uninstall home-resolution rules
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page documents `--home` as optional for single-tool uninstall
- **AND THEN** it explains that comma-separated multi-tool uninstall cannot use `--home`
- **AND THEN** it explains omitted-home uninstall resolution through tool-native env vars and project-scoped defaults

#### Scenario: Reader understands uninstall is not selective
- **WHEN** a reader checks uninstall options in the CLI reference
- **THEN** the page explains that uninstall does not accept `--skill`, `--skill-set`, or `--symlink`
- **AND THEN** the page contrasts that all-known-skill uninstall behavior with selective install behavior

#### Scenario: Reader understands uninstall preserves unrelated content
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page explains that uninstall removes exact current Houmao skill paths only
- **AND THEN** it explains that unrelated user skills, parent roots, legacy paths, and stale install-state files are not removed
