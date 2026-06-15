## 1. System Skill Assets

- [x] 1.1 Create `src/houmao/agents/assets/system_skills/houmao-utils-graphing/SKILL.md` with help, launcher selection, graphing layer selection, schema discovery, Plotly.js templated graphics guidance, Vega-Lite freeform graphics guidance, validation/render workflow, handoff-to-interop guidance, and graphing safety limits.
- [x] 1.2 Add optional `src/houmao/agents/assets/system_skills/houmao-utils-graphing/agents/openai.yaml` metadata that describes built-in Plotly.js and Vega-Lite graphing authoring.
- [x] 1.3 Narrow `src/houmao/agents/assets/system_skills/houmao-interop-ag-ui/SKILL.md` so it focuses on AG-UI protocol validation/framing, generic implementation rendering, new-component rendering, gateway publishing, endpoint/routing boundaries, publish-result interpretation, and a short `houmao-utils-graphing` handoff.
- [x] 1.4 Update `src/houmao/agents/assets/system_skills/houmao-interop-ag-ui/agents/openai.yaml` so its display metadata no longer claims Plotly.js or Vega-Lite graphing authoring ownership.

## 2. Catalog and Installation Wiring

- [x] 2.1 Register `houmao-utils-graphing` in `src/houmao/agents/assets/system_skills/catalog.toml` with a utility-focused description.
- [x] 2.2 Add `houmao-utils-graphing` to the `core` and `all` named sets so managed homes that receive `houmao-interop-ag-ui` also receive its graphing delegation target.
- [x] 2.3 Preserve flat visible projection semantics for the new skill across Claude, Codex, Kimi, Gemini, and Copilot install destinations.

## 3. Documentation Updates

- [x] 3.1 Update `docs/getting-started/system-skills-overview.md` to add `houmao-utils-graphing`, narrow the `houmao-interop-ag-ui` row, and explain the graphing-versus-interop boundary.
- [x] 3.2 Update `docs/reference/cli/system-skills.md` current inventory, named set descriptions, examples, and conceptual `utils` grouping to include `houmao-utils-graphing`.
- [x] 3.3 Update any README or generated docs references that enumerate packaged Houmao system skills or describe AG-UI interop as owning Plotly.js/Vega-Lite authoring.

## 4. Tests

- [x] 4.1 Update catalog and packaged-asset tests in `tests/unit/agents/test_system_skills.py` for the new skill name, ordering, descriptions, installed asset shape, and narrowed interop skill text.
- [x] 4.2 Update system-skills CLI tests in `tests/unit/srv_ctrl/test_system_skills_commands.py` for list/install/status/uninstall output and projected `skills/houmao-utils-graphing/SKILL.md`.
- [x] 4.3 Update brain builder, docs, and project command tests that assert default resolved system-skill lists or installed skill paths.
- [x] 4.4 Add or update docs tests proving the overview and CLI reference mention `houmao-utils-graphing` and route built-in graphing authoring away from `houmao-interop-ag-ui`.

## 5. Verification

- [x] 5.1 Run `openspec validate split-ag-ui-graphing-system-skill --strict` and fix any proposal/spec/task issues.
- [x] 5.2 Run focused tests for system skills and docs, including `pixi run pytest tests/unit/agents/test_system_skills.py tests/unit/srv_ctrl/test_system_skills_commands.py tests/unit/docs/test_system_skills_docs.py -q`.
- [x] 5.3 Run the repository standard checks required by the touched surface: `pixi run format`, `pixi run lint`, `pixi run typecheck`, and `pixi run test`.
