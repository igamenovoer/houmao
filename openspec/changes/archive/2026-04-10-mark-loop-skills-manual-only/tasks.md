## 1. Spec And Skill Guidance

- [x] 1.1 Update the packaged `houmao-agent-loop-pairwise` capability and top-level `SKILL.md` guidance so the skill is manual-invocation-only and only enters when the user explicitly asks for `houmao-agent-loop-pairwise`.
- [x] 1.2 Update the packaged `houmao-loop-planner` capability and top-level `SKILL.md` guidance so the skill is manual-invocation-only and only enters when the user explicitly asks for `houmao-loop-planner`.
- [x] 1.3 Add explicit non-auto-routing guidance for generic pairwise loop, loop-bundle authoring, distribution, and runtime-handoff requests that do not name either skill.

## 2. Validation

- [x] 2.1 Update packaged skill content tests under `tests/unit/agents/` to assert the new manual-only wording in both `SKILL.md` files.
- [x] 2.2 Run the relevant packaged system-skill unit-test slice and record the passing command output in the implementation results.

## Verification

- `pixi run pytest tests/unit/agents/test_system_skills.py tests/unit/agents/test_brain_builder.py::test_build_brain_home_projects_selected_components_and_manifest tests/unit/srv_ctrl/test_system_skills_commands.py`
- Result: `35 passed in 3.50s`
