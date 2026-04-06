## 1. Flatten Packaged Skill Layout

- [x] 1.1 Move the packaged Houmao-owned system-skill directories to `src/houmao/agents/assets/system_skills/<skill-name>/` and update catalog `asset_subpath` values to the flat skill-name form.
- [x] 1.2 Remove family-derived projection/reference helpers from the shared installer so Claude, Codex, and Gemini all resolve Houmao-owned skill paths from the flat tool-native root.

## 2. Migrate Installed Homes Safely

- [x] 2.1 Update install-state handling so reinstall removes previously owned `skills/mailbox/...` and `skills/project/...` paths when those skills now project to flat top-level paths.
- [x] 2.2 Add or update automated tests for flat packaged layout, flat visible projection, owned-path migration, idempotent reinstall, and fail-closed collision behavior.

## 3. Update Runtime Contracts And Validation

- [x] 3.1 Update mailbox runtime helpers, packaged skill content, and related prompts so Codex mailbox and specialist flows no longer reference family-namespaced skill paths.
- [x] 3.2 Update CLI docs, runtime docs, and other repo-owned references that still describe `skills/mailbox/...`, `skills/project/...`, or packaged `mailbox/` and `project/` skill families.
- [x] 3.3 Run the focused validation suites covering system-skill installation, managed/joined-home projection, mailbox runtime prompts, and any regressions introduced by the flat layout migration.
