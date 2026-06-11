## 1. Packaged Skill Identity

- [x] 1.1 Move `src/houmao/agents/assets/system_skills/houmao-agent-ag-ui/` to `src/houmao/agents/assets/system_skills/houmao-interop-ag-ui/`.
- [x] 1.2 Update the moved `SKILL.md` frontmatter `name`, title, help trigger text, and common starting prompts from `houmao-agent-ag-ui` to `houmao-interop-ag-ui`.
- [x] 1.3 Preserve the existing AG-UI authoring, validation, rendering, publishing, delivery-count, active-thread, and safety guidance behavior under the new skill name.

## 2. Catalog and Runtime Selection

- [x] 2.1 Replace the catalog entry `[skills.houmao-agent-ag-ui]` with `[skills.houmao-interop-ag-ui]`, set `asset_subpath = "houmao-interop-ag-ui"`, and update the description if needed.
- [x] 2.2 Replace `houmao-agent-ag-ui` with `houmao-interop-ag-ui` in the `core` and `all` catalog set membership.
- [x] 2.3 Add `houmao-agent-ag-ui` to `retired_skill_names` so install and sync remove stale old-name projections.
- [x] 2.4 Rename the Python system-skill constant to a `houmao-interop-ag-ui` name and update imports/usages without adding an old-name alias.

## 3. Current Docs and OpenSpec References

- [x] 3.1 Rename the current main OpenSpec skill capability from `openspec/specs/houmao-agent-ag-ui-skill/` to `openspec/specs/houmao-interop-ag-ui-skill/` when syncing or directly updating current specs for this rename.
- [x] 3.2 Update current system-skill docs, including `docs/getting-started/system-skills-overview.md`, so `houmao-interop-ag-ui` is listed as the current AG-UI interop skill and `houmao-agent-ag-ui` is not listed as current.
- [x] 3.3 Update active unarchived change artifacts under `openspec/changes/add-ag-ui-template-graphics-vega/` that still refer to `houmao-agent-ag-ui`.
- [x] 3.4 Leave archived OpenSpec changes unchanged unless a separate archive-maintenance task explicitly asks to rewrite history.

## 4. Tests

- [x] 4.1 Update unit tests that assert catalog membership, constants, skill frontmatter, and packaged asset paths.
- [x] 4.2 Update managed home and brain-builder tests to expect `skills/houmao-interop-ag-ui/SKILL.md`.
- [x] 4.3 Update `houmao-mgr system-skills` CLI tests to expect `houmao-interop-ag-ui` in list, install, and status output.
- [x] 4.4 Add or update install/sync coverage proving a stale `skills/houmao-agent-ag-ui` projection is removed as a retired skill.
- [x] 4.5 Update docs tests if they assert the packaged system-skill inventory or overview-guide contents.

## 5. Guardrails and Verification

- [x] 5.1 Review remaining current references with `rg "houmao-agent-ag-ui" src tests docs openspec/specs openspec/changes/add-ag-ui-template-graphics-vega context/plans/ag-ui-advanced-cap/roadmap.md` and keep only intentional retired-name or historical references.
- [x] 5.2 Confirm protocol and product names remain unchanged: `/v1/ag-ui`, `houmao-mgr internals ag-ui`, `houmao-mgr agents ... gateway ag-ui publish`, `apps/ag-ui-workbench`, `houmao.graphic.template`, and `houmao_render_graphic`.
- [x] 5.3 Run focused tests: `pixi run pytest tests/unit/agents/test_system_skills.py tests/unit/agents/test_brain_builder.py tests/unit/srv_ctrl/test_system_skills_commands.py tests/unit/docs/test_system_skills_docs.py -q`.
- [x] 5.4 Run `openspec validate rename-houmao-agent-ag-ui-skill --strict`.
