## MODIFIED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-loop-pairwise` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-loop-pairwise` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-agent-loop-pairwise` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The top-level `SKILL.md` for that packaged skill SHALL describe the skill as a user-controlled pairwise loop planner and run controller rather than as a new runtime workflow engine.

The packaged `houmao-agent-loop-pairwise` skill SHALL be manual-invocation-only. It SHALL instruct agents to use the skill only when the user explicitly asks for `houmao-agent-loop-pairwise` by name.

That packaged skill SHALL organize its guidance through local authoring and operating pages beneath the same packaged skill directory.

That packaged skill SHALL remain distinct from the direct-operation skills and the existing `houmao-adv-usage-pattern` pattern pages that it composes.

That packaged skill SHALL NOT present itself as the default entrypoint for generic pairwise loop planning or pairwise run-control requests when the user did not explicitly invoke the skill by name.

#### Scenario: User explicitly asks to invoke the pairwise loop skill
- **WHEN** a user explicitly asks for `houmao-agent-loop-pairwise`
- **THEN** `houmao-agent-loop-pairwise` is the correct packaged Houmao-owned skill
- **AND THEN** it presents itself as a planner and run controller rather than as a replacement for the lower-level messaging, mailbox, or gateway skills

#### Scenario: User explicitly asks to use the pairwise skill for run control
- **WHEN** a user explicitly asks for `houmao-agent-loop-pairwise` to start, inspect, or stop a pairwise loop run owned by a designated master
- **THEN** `houmao-agent-loop-pairwise` is the correct packaged Houmao-owned skill
- **AND THEN** it routes the request through its operating guidance rather than claiming a new runtime control API

#### Scenario: Generic pairwise loop request does not auto-route to the skill
- **WHEN** a user asks generically to plan, start, inspect, or stop a pairwise loop without explicitly asking for `houmao-agent-loop-pairwise`
- **THEN** `houmao-agent-loop-pairwise` does not present itself as the default skill for that request
- **AND THEN** the request remains outside this packaged skill entrypoint unless the user later invokes the skill explicitly
