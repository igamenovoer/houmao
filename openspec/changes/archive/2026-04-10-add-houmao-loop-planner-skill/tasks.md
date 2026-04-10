## 1. Packaged Skill Assets

- [x] 1.1 Add a new packaged system skill directory at `src/houmao/agents/assets/system_skills/houmao-loop-planner/`, register it in the system-skill catalog, and add a top-level `SKILL.md` that presents the skill as an operator-owned loop-bundle planner with separate authoring, distribution, and handoff lanes.
- [x] 1.2 Add authoring-lane guidance pages that cover creating and revising the canonical operator-owned bundle in a user-designated directory, writing Markdown-first artifacts with fixed section structure, and keeping the bundle separate from agent-local runtime state.
- [x] 1.3 Add distribution and handoff guidance pages that cover preparing `participants.md`, `execution.md`, and `distribution.md`, generating `runs/charter.template.toml`, and routing later runtime activation to `houmao-agent-loop-pairwise` or `houmao-agent-loop-relay` by loop kind.

## 2. References And Templates

- [x] 2.1 Add local reference pages for the canonical bundle directory structure, required section conventions for `participants.md`, `execution.md`, and `distribution.md`, the minimal `profile.toml` schema, the minimal `runs/charter.template.toml` schema, and operator-managed storage rules.
- [x] 2.2 Add Markdown and TOML templates for `plan.md`, `participants.md`, `execution.md`, `distribution.md`, `profile.toml`, and `runs/charter.template.toml`.
- [x] 2.3 Add graph guidance that requires a top-level Mermaid diagram in `plan.md` and shows how to render the operator, designated master, execution topology, supervision loop, completion condition, and stop condition for pairwise or relay bundles.

## 3. Validation

- [x] 3.1 Update system-skill packaging and projection tests under `tests/unit/agents/` to assert that `houmao-loop-planner` is packaged, cataloged, and routed correctly.
- [x] 3.2 Add or update content tests to assert the required guidance strings for Markdown-first bundle authoring, minimal TOML usage, operator-managed distribution, runtime handoff to existing loop skills, and the prohibition on agent-local runtime-directory planning.
- [x] 3.3 Run the relevant unit-test slice for packaged system skills and record the passing command output in the implementation results.

## Verification

- `pixi run pytest tests/unit/agents/test_system_skills.py tests/unit/agents/test_brain_builder.py::test_build_brain_home_projects_selected_components_and_manifest tests/unit/srv_ctrl/test_system_skills_commands.py`
- Result: `35 passed in 3.29s`
