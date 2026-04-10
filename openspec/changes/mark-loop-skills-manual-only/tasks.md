## 1. Spec And Skill Guidance

- [ ] 1.1 Update the packaged `houmao-agent-loop-pairwise` capability and top-level `SKILL.md` guidance so the skill is manual-invocation-only and only enters when the user explicitly asks for `houmao-agent-loop-pairwise`.
- [ ] 1.2 Update the packaged `houmao-loop-planner` capability and top-level `SKILL.md` guidance so the skill is manual-invocation-only and only enters when the user explicitly asks for `houmao-loop-planner`.
- [ ] 1.3 Add explicit non-auto-routing guidance for generic pairwise loop, loop-bundle authoring, distribution, and runtime-handoff requests that do not name either skill.

## 2. Validation

- [ ] 2.1 Update packaged skill content tests under `tests/unit/agents/` to assert the new manual-only wording in both `SKILL.md` files.
- [ ] 2.2 Run the relevant packaged system-skill unit-test slice and record the passing command output in the implementation results.
