## 1. Graphing Extension Asset Rename

- [x] 1.1 Rename `src/houmao/agents/assets/system_skills/houmao-utils-graphing/` to `src/houmao/agents/assets/system_skills/houmao-ext-graphing/`.
- [x] 1.2 Update the graphing skill frontmatter, title, help prompts, related-skill text, and examples from `houmao-utils-graphing` to `houmao-ext-graphing`.
- [x] 1.3 Update graphing agent metadata under `agents/openai.yaml` so display names, descriptions, and default prompts describe a graphing extension.
- [x] 1.4 Verify no current asset or docs text presents `houmao-utils-graphing` as a current skill name.

## 2. Catalog, Sets, and Retired Names

- [x] 2.1 Rename the graphing skill constant and catalog entry from `houmao-utils-graphing` to `houmao-ext-graphing`.
- [x] 2.2 Add an installable `extensions` named set containing `houmao-ext-graphing`.
- [x] 2.3 Remove graphing from `core` and keep it available through `extensions` and `all`.
- [x] 2.4 Update managed launch and managed join auto-install set lists to resolve `core` followed by `extensions`.
- [x] 2.5 Add `houmao-utils-graphing` to retired system-skill names so install and uninstall cleanup remove stale old-name projections.
- [x] 2.6 Verify explicit `--skill-set core` excludes `houmao-ext-graphing`, while default managed install and `--skill-set all` include it.

## 3. Non-Extension Routing Boundary

- [x] 3.1 Remove all `houmao-utils-graphing` references from `houmao-interop-ag-ui`.
- [x] 3.2 Keep `houmao-interop-ag-ui` focused on AG-UI protocol validation, implementation rendering for already-chosen payloads, gateway publishing, endpoint selection, and delivery-result interpretation.
- [x] 3.3 Ensure `houmao-interop-ag-ui` does not route, delegate, or hand off to `houmao-ext-graphing`.
- [x] 3.4 Add or update tests that scan non-extension skill assets for forbidden routing references to `houmao-ext-graphing`.

## 4. Documentation

- [x] 4.1 Update `docs/getting-started/system-skills-overview.md` to list `houmao-ext-graphing` as an extension skill and remove current-skill references to `houmao-utils-graphing`.
- [x] 4.2 Update overview guidance so managed launch and join resolve `core` plus `extensions`, while omitted-selection CLI install resolves `all`.
- [x] 4.3 Update `docs/reference/cli/system-skills.md` to document `core`, `extensions`, and `all`, including default set lists and explicit `core` exclusion of extensions.
- [x] 4.4 Document `houmao-utils-graphing` only as a retired projection name that current install or uninstall cleanup may remove.
- [x] 4.5 Document that extension skills are default-installed but non-extension skills do not depend on or route to extension skills.

## 5. Tests and Verification

- [x] 5.1 Update unit tests for packaged system-skill constants, catalog parsing, set membership, default install resolution, and retired-name cleanup.
- [x] 5.2 Update system-skills CLI tests for `list`, `install`, `status`, and `uninstall` output using `houmao-ext-graphing` and the `extensions` set.
- [x] 5.3 Update docs tests for the overview and CLI reference to expect extension terminology, default set lists, and retired old-name wording.
- [x] 5.4 Run `openspec validate rename-graphing-extension-skill --strict` and fix any artifact issues.
- [x] 5.5 Run the focused system-skill and docs test suites that cover the changed behavior.
