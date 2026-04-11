## ADDED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-loop-pairwise-v2` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-loop-pairwise-v2` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-agent-loop-pairwise-v2` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The top-level `SKILL.md` for that packaged skill SHALL describe the skill as the versioned enriched pairwise authoring, prestart, and run-control surface rather than as the stable pairwise contract.

The packaged `houmao-agent-loop-pairwise-v2` skill SHALL be manual-invocation-only. It SHALL instruct agents to use the skill only when the user explicitly asks for `houmao-agent-loop-pairwise-v2` by name.

That packaged skill SHALL remain distinct from both the restored stable `houmao-agent-loop-pairwise` skill and the lower-level messaging, mailbox, gateway, and advanced-usage skills that it composes.

#### Scenario: User explicitly asks to invoke the v2 pairwise skill
- **WHEN** a user explicitly asks for `houmao-agent-loop-pairwise-v2`
- **THEN** `houmao-agent-loop-pairwise-v2` is the correct packaged Houmao-owned skill
- **AND THEN** it presents itself as the versioned enriched pairwise skill rather than as the restored stable pairwise skill

#### Scenario: Generic pairwise loop request does not auto-route to v2
- **WHEN** a user asks generically to plan or operate a pairwise loop without explicitly asking for `houmao-agent-loop-pairwise-v2`
- **THEN** `houmao-agent-loop-pairwise-v2` does not present itself as the default skill for that request
- **AND THEN** the request remains outside this packaged skill entrypoint unless the user later invokes the skill explicitly

### Requirement: The v2 skill preserves the enriched pairwise workflow surface
The packaged `houmao-agent-loop-pairwise-v2` skill SHALL preserve the enriched pairwise workflow currently carried by the renamed v2 asset tree.

That workflow SHALL include:

- authoring guidance,
- prestart preparation guidance,
- expanded operating guidance for enriched pairwise control.

The canonical operator action vocabulary for `houmao-agent-loop-pairwise-v2` SHALL include at minimum:

- `plan`,
- `initialize`,
- `start`,
- `peek`,
- `ping`,
- `pause`,
- `resume`,
- `stop`,
- `hard-kill`.

The v2 guidance SHALL continue to define canonical observed states separately from those operator actions.

#### Scenario: Reader sees the enriched operator action vocabulary in v2
- **WHEN** a reader opens the packaged `houmao-agent-loop-pairwise-v2` skill assets
- **THEN** the operating guidance includes the enriched operator action vocabulary
- **AND THEN** that vocabulary remains broader than the restored stable `houmao-agent-loop-pairwise` surface

#### Scenario: V2 keeps prestart guidance
- **WHEN** a reader opens the packaged `houmao-agent-loop-pairwise-v2` skill assets
- **THEN** the skill includes explicit prestart preparation guidance
- **AND THEN** that prestart lane remains packaged under the v2 skill rather than under the restored stable pairwise skill
