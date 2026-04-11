# houmao-agent-loop-pairwise-v2-skill Specification

## Purpose
Define the packaged versioned enriched pairwise loop skill, including its manual invocation boundary, prestart preparation lane, expanded operator actions, and targeted preparation behavior.

## Requirements
### Requirement: Houmao provides a packaged `houmao-agent-loop-pairwise-v2` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-loop-pairwise-v2` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-agent-loop-pairwise-v2` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The top-level `SKILL.md` for that packaged skill SHALL describe the skill as the versioned enriched pairwise authoring, prestart, and run-control surface rather than as the stable pairwise contract.

The packaged `houmao-agent-loop-pairwise-v2` skill SHALL be manual-invocation-only. It SHALL instruct agents to use the skill only when the user explicitly asks for `houmao-agent-loop-pairwise-v2` by name.

That packaged skill SHALL remain distinct from both the restored stable `houmao-agent-loop-pairwise` skill and the lower-level messaging, mailbox, gateway, and advanced-usage skills that it composes.

That packaged skill SHALL own composed pairwise loop planning concerns, including multi-edge topology, recursive child-control edges, rendered control graphs, master-owned run planning, lifecycle preparation, run charters, and enriched run-control actions.

When that packaged skill references `houmao-adv-usage-pattern`, it SHALL treat the advanced-usage pairwise page as the elemental immediate driver-worker edge protocol to use per edge rather than as the owner of composed pairwise topology.

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

### Requirement: V2 initialize targets delegating participants by default
The packaged `houmao-agent-loop-pairwise-v2` prestart guidance SHALL distinguish participant preparation material from the preparation mail recipient set.

The v2 authoring guidance SHALL allow authored plans to retain participant preparation material for all participants.

The v2 `initialize` guidance SHALL define the default preparation mail recipient set as participants that have descendants in the authored topology, meaning participants expected to delegate jobs to other agents.

The v2 `initialize` guidance SHALL exclude leaf participants from the default preparation mail recipient set.

The v2 `initialize` guidance SHALL include leaf participants only when the user explicitly asks to prepare leaf agents, prepare all participants, or names leaf participants in the preparation target set.

The v2 `initialize` guidance SHALL define `require_ack` as applying to the actual preparation mail recipient set rather than to every participant by default.

The v2 `initialize` and `start` guidance SHALL define `ready` as requiring completion of the targeted preparation wave and any required acknowledgements from targeted preparation recipients.

The v2 guidance SHALL require the authoring lane to clarify descendant relationships before initialization when the plan topology is not clear enough to identify delegating participants.

#### Scenario: Default initialize prepares only delegating participants
- **WHEN** a user invokes `houmao-agent-loop-pairwise-v2` and asks to initialize an authored plan whose topology identifies both delegating and leaf participants
- **THEN** the v2 preparation guidance targets preparation mail to the participants that have descendants
- **AND THEN** the leaf participants are not sent preparation mail by default

#### Scenario: Explicit leaf preparation override includes leaf participants
- **WHEN** a user explicitly asks to prepare leaf agents, prepare all participants, or names leaf participants in the preparation target set
- **THEN** the v2 preparation guidance includes those leaf participants in the preparation mail recipient set
- **AND THEN** acknowledgement requirements apply to those leaf participants when `require_ack` is active

#### Scenario: Ready state tracks targeted preparation recipients
- **WHEN** a v2 pairwise run uses targeted preparation recipients and `require_ack`
- **THEN** the run enters `ready` only after the targeted preparation mail has been sent and required replies have arrived from targeted recipients
- **AND THEN** missing acknowledgements from leaf participants do not block `ready` unless leaf participants were explicitly included in the preparation target set

#### Scenario: Unclear topology returns to authoring
- **WHEN** a v2 pairwise plan does not make descendant relationships clear enough to identify delegating participants
- **THEN** the v2 initialization guidance returns to authoring or revision before sending preparation mail
- **AND THEN** it does not guess the preparation mail recipient set
