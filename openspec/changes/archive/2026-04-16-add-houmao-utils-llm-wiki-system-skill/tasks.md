## 1. Package the Skill Asset

- [x] 1.1 Copy the full all-in-one LLM Wiki payload into `src/houmao/agents/assets/system_skills/houmao-utils-llm-wiki/`.
- [x] 1.2 Update `houmao-utils-llm-wiki/SKILL.md` frontmatter and body so the packaged skill name and Houmao-facing text use `houmao-utils-llm-wiki`.
- [x] 1.3 Remove upstream attribution text from the packaged Houmao skill while preserving the core LLM Wiki workflow instructions.
- [x] 1.4 Confirm scripts, references, subskills, and `viewer/` are included, while generated dependency/build artifacts such as `node_modules/` remain absent.
- [x] 1.5 Confirm helper examples in the packaged skill use `python3`.

## 2. Catalog and Selection

- [x] 2.1 Add `houmao-utils-llm-wiki` to `src/houmao/agents/assets/system_skills/catalog.toml` with `asset_subpath = "houmao-utils-llm-wiki"`.
- [x] 2.2 Add a `utils` named set containing only `houmao-utils-llm-wiki`.
- [x] 2.3 Keep `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` unchanged so the utility skill is explicit-only.
- [x] 2.4 Add or update system-skill constants only if needed by tests or documentation helpers.

## 3. Tests

- [x] 3.1 Update catalog unit tests to expect the new skill inventory entry and `utils` set.
- [x] 3.2 Add coverage that explicit `utils` selection resolves to `houmao-utils-llm-wiki`.
- [x] 3.3 Add coverage that CLI-default selection does not include `houmao-utils-llm-wiki`.
- [x] 3.4 Add install/status/uninstall CLI coverage for `--skill-set utils` or explicit `--skill houmao-utils-llm-wiki`.
- [x] 3.5 Add asset-shape coverage for the packaged skill payload, including `viewer/` presence and generated dependency artifacts absence.

## 4. Documentation

- [x] 4.1 Update the README system-skills table and examples to document `houmao-utils-llm-wiki` as an explicit utility install.
- [x] 4.2 Update `docs/getting-started/system-skills-overview.md` to include the utility skill and `utils` named set without adding it to default selections.
- [x] 4.3 Update `docs/reference/cli/system-skills.md` with the new inventory entry, named set, and explicit install examples.
- [x] 4.4 Update `docs/reference/cli/houmao-mgr.md` and `docs/reference/cli.md` if their system-skills summaries enumerate sets or inventory in a way that must include `utils`.

## 5. Verification

- [x] 5.1 Run focused system-skill unit tests.
- [x] 5.2 Run strict OpenSpec validation for `add-houmao-utils-llm-wiki-system-skill`.
- [x] 5.3 Run a catalog/list smoke command to confirm `houmao-utils-llm-wiki` and `utils` appear while defaults exclude `utils`.
- [x] 5.4 Check parent and submodule Git status so the packaged asset, catalog/docs changes, OpenSpec artifacts, and existing submodule pointer state are visible before commit.
