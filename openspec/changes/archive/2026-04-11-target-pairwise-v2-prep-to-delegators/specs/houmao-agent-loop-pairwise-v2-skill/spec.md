## ADDED Requirements

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
