## 1. Preset Model And Catalog

- [ ] 1.1 Redefine the canonical preset parser and data model to load named presets from `agents/presets/<name>.yaml` with inline `role`, `tool`, and `setup` fields.
- [ ] 1.2 Update catalog schema, projection helpers, and specialist-facing preset references so presets carry a first-class name while preserving uniqueness on `(role, tool, setup)`.
- [ ] 1.3 Remove repository-supported path-derived preset assumptions from parser errors, projection paths, and low-level preset helper utilities.

## 2. Project CLI Refactor

- [ ] 2.1 Add the new `houmao-mgr project agents presets list|get|add|set|remove` command family and wire it to the updated named-preset storage model.
- [ ] 2.2 Narrow `houmao-mgr project agents roles` to prompt-only `list|get|init|set|remove` behavior.
- [ ] 2.3 Remove `houmao-mgr project agents roles scaffold` and the nested `roles presets ...` command surface, including help text and project-aware overlay resolution coverage.

## 3. Build And Launch Resolution

- [ ] 3.1 Update `brains build --preset` and internal preset resolution helpers to accept named preset paths and bare preset names where the command already names the preset resource explicitly.
- [ ] 3.2 Update `houmao-mgr agents launch` bare-role resolution to find the unique named preset for `(role, tool, setup=default)` and keep explicit preset-path launch working under `agents/presets/`.
- [ ] 3.3 Update manifest/reporting surfaces that expose preset paths so they report the new named preset locations consistently.

## 4. Repo-Owned Fixtures And Docs

- [ ] 4.1 Rewrite tracked agent fixtures and demo inputs from role-scoped preset paths to named preset files under `agents/presets/`.
- [ ] 4.2 Update fixture/demo helpers and tests that currently hard-code `roles/<role>/presets/<tool>/<setup>.yaml`.
- [ ] 4.3 Update getting-started and CLI reference docs to describe prompt-only roles, top-level named presets, and the removal of `roles scaffold`.

## 5. Verification

- [ ] 5.1 Add or update unit coverage for named preset parsing, project preset CLI operations, role deletion guards, catalog projection, and launch selector resolution.
- [ ] 5.2 Run targeted test suites and OpenSpec validation for `refactor-agent-presets-to-named-resources`, and record any remaining follow-up risks before implementation merge.
