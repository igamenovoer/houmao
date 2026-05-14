## 1. README Alignment

- [x] 1.1 Update Quick Start step 1 so `npx skills add https://github.com/igamenovoer/houmao/tree/main/src/houmao/agents/assets/system_skills/` is the recommended path only when `npx` and internet access are available.
- [x] 1.2 Keep `houmao-mgr system-skills install` in step 1 as the offline/package-local/customizable path for named sets, subset skills, explicit homes, symlink/copy projection, and cleanup.
- [x] 1.3 Ensure README text points the Skills CLI at the `system_skills/` collection directory rather than an individual skill path.
- [x] 1.4 Ensure README mentions explicit read-only skill help with at least one `$<skill> help` example and distinguishes it from `houmao-mgr system-skills install`.

## 2. Docs Site Alignment

- [x] 2.1 Update `docs/index.md` installed-user starting guidance so it no longer presents `houmao-mgr system-skills install --tool claude` as the only recommended first step.
- [x] 2.2 Update `docs/index.md` to point installed users toward the current agent-driven path: install skills, then invoke `houmao-touring` or explicit skill help.
- [x] 2.3 Update `docs/getting-started/system-skills-overview.md` with a compact installation-choices section comparing `npx skills add` and `houmao-mgr system-skills install`.
- [x] 2.4 Ensure the overview keeps managed launch/join auto-install behavior separate from explicit user-driven installation choices.
- [x] 2.5 Ensure the overview explains prompt-level read-only skill help and the explicit-help versus ordinary workflow-request boundary.

## 3. CLI Reference Alignment

- [x] 3.1 Update `docs/reference/cli/system-skills.md` to state that the page documents `houmao-mgr system-skills` command behavior.
- [x] 3.2 Add adjacent guidance in `docs/reference/cli/system-skills.md` for the `npx skills add` GitHub collection install path.
- [x] 3.3 Explain in `docs/reference/cli/system-skills.md` that `$<skill> help` is prompt-level installed-skill behavior, not a `houmao-mgr system-skills help` subcommand.
- [x] 3.4 Preserve the existing CLI reference authority for effective-home resolution, named sets, subset skills, symlink/copy projection, status, uninstall, and retired-skill cleanup.

## 4. Tests And Verification

- [x] 4.1 Add or update docs guard tests for README installation choices and read-only skill help.
- [x] 4.2 Add or update docs guard tests for `docs/index.md`, system-skills overview, and system-skills CLI reference install/help wording.
- [x] 4.3 Run focused docs tests.
- [x] 4.4 Run `openspec validate refresh-system-skill-install-help-docs --strict`.
