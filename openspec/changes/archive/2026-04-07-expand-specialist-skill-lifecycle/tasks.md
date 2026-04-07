## 1. Update packaged skill assets

- [x] 1.1 Expand `src/houmao/agents/assets/system_skills/houmao-manage-specialist/SKILL.md` so its scope, workflow, routing guidance, and guardrails cover specialist-scoped `launch` and `stop` with explicit post-action handoff to `houmao-manage-agent-instance`.
- [x] 1.2 Add specialist action pages for `launch` and `stop` under `src/houmao/agents/assets/system_skills/houmao-manage-specialist/actions/` using `project easy instance launch` and `project easy instance stop`.
- [x] 1.3 Update `src/houmao/agents/assets/system_skills/houmao-manage-agent-instance/SKILL.md` and any affected action guidance so the skill remains the canonical follow-up lifecycle surface without claiming CRUD ownership or conflicting with the new specialist-skill entry points.

## 2. Update system-skill documentation

- [x] 2.1 Revise `docs/reference/cli/system-skills.md` to describe `houmao-manage-specialist` as covering specialist authoring plus specialist-scoped `launch` and `stop`, and to explain the handoff to `houmao-manage-agent-instance` for further lifecycle work.
- [x] 2.2 Revise `README.md` system-skill summaries so `houmao-manage-specialist` is no longer described as CRUD-only.

## 3. Validate the change

- [x] 3.1 Review the updated skill docs and system-skill docs together to confirm the two-skill boundary is consistent across scope, workflow, and guardrails.
- [x] 3.2 Run the relevant documentation or repository checks needed to verify the updated artifacts are well-formed, then mark any follow-up issues discovered during validation.
