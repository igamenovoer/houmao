## MODIFIED Requirements

### Requirement: Houmao provides a packaged `houmao-loop-planner` system skill
The system SHALL package a Houmao-owned system skill named `houmao-loop-planner` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-loop-planner` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The top-level `SKILL.md` for that packaged skill SHALL describe the skill as an operator-owned loop-bundle planner and handoff skill rather than as a new runtime workflow engine.

The packaged `houmao-loop-planner` skill SHALL be manual-invocation-only. It SHALL instruct agents to use the skill only when the user explicitly asks for `houmao-loop-planner` by name.

That packaged skill SHALL organize its guidance through local authoring, distribution, and handoff pages beneath the same packaged skill directory.

That packaged skill SHALL remain distinct from the loop runtime skills and the existing execution-pattern pages that it composes.

That packaged skill SHALL NOT present itself as the default entrypoint for generic loop-bundle authoring, distribution-preparation, or runtime-handoff requests when the user did not explicitly invoke the skill by name.

#### Scenario: User explicitly asks to invoke the loop planner skill
- **WHEN** a user explicitly asks for `houmao-loop-planner`
- **THEN** `houmao-loop-planner` is the correct packaged Houmao-owned skill
- **AND THEN** it presents itself as an operator-owned planner and handoff skill rather than as a replacement for the lower-level runtime skills

#### Scenario: User explicitly asks to use the loop planner skill for bundle preparation
- **WHEN** a user explicitly asks for `houmao-loop-planner` to create or revise a loop bundle in a user-designated directory for named Houmao agents
- **THEN** `houmao-loop-planner` is the correct packaged Houmao-owned skill
- **AND THEN** it routes the request through its authoring, distribution, or handoff guidance rather than claiming direct live-run ownership

#### Scenario: Generic loop-planning request does not auto-route to the skill
- **WHEN** a user asks generically to author a loop bundle, prepare distribution guidance, or prepare runtime handoff without explicitly asking for `houmao-loop-planner`
- **THEN** `houmao-loop-planner` does not present itself as the default skill for that request
- **AND THEN** the request remains outside this packaged skill entrypoint unless the user later invokes the skill explicitly
