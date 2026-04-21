## MODIFIED Requirements

### Requirement: The v2 skill preserves the enriched pairwise workflow surface
The packaged `houmao-agent-loop-pairwise-v2` skill SHALL preserve the enriched pairwise workflow currently carried by the renamed v2 asset tree.

That workflow SHALL include:

- authoring guidance,
- prestart preparation guidance,
- expanded operating guidance for enriched pairwise control, including restart recovery after participant stop or relaunch.

The canonical operator action vocabulary for `houmao-agent-loop-pairwise-v2` SHALL include at minimum:

- `plan`,
- `initialize`,
- `start`,
- `peek`,
- `ping`,
- `pause`,
- `resume`,
- `recover_and_continue`,
- `stop`,
- `hard-kill`.

The v2 guidance SHALL continue to define canonical observed states separately from those operator actions.

That observed-state vocabulary SHALL include at minimum:

- `authoring`,
- `initializing`,
- `awaiting_ack`,
- `ready`,
- `running`,
- `paused`,
- `recovering`,
- `recovered_ready`,
- `stopping`,
- `stopped`,
- `dead`.

#### Scenario: Reader sees the enriched operator action vocabulary in v2
- **WHEN** a reader opens the packaged `houmao-agent-loop-pairwise-v2` skill assets
- **THEN** the operating guidance includes the enriched operator action vocabulary including `recover_and_continue`
- **AND THEN** that vocabulary remains broader than the restored stable `houmao-agent-loop-pairwise` surface

#### Scenario: V2 keeps prestart guidance
- **WHEN** a reader opens the packaged `houmao-agent-loop-pairwise-v2` skill assets
- **THEN** the skill includes explicit prestart preparation guidance
- **AND THEN** that prestart lane remains packaged under the v2 skill rather than under the restored stable pairwise skill

#### Scenario: V2 exposes restart recovery as a distinct enriched control lane
- **WHEN** a reader opens the packaged `houmao-agent-loop-pairwise-v2` operating guidance
- **THEN** the guidance distinguishes `recover_and_continue` from both soft `resume` and terminal `hard-kill`
- **AND THEN** it exposes `recovering` and `recovered_ready` as canonical observed states before the run returns to `running`

## ADDED Requirements

### Requirement: Pairwise-v2 distinguishes soft resume from restart recovery
The packaged `houmao-agent-loop-pairwise-v2` guidance SHALL define `resume` as the action that restores one previously paused run whose participant set and wakeup posture remained logically live.

The guidance SHALL define `recover_and_continue` as the action that restores one accepted pairwise-v2 run after one or more participants were stopped, killed, or relaunched and later need to continue the same logical run under the same `run_id`.

During restart recovery, the guidance SHALL treat `recovering` as the observed state while participant rebinding, durable continuation-material refresh, or wakeup restoration is still in progress.

The guidance SHALL treat `recovered_ready` as the observed state after restart-recovery preparation is complete but before the designated master explicitly accepts continuation.

The guidance SHALL return the run to `running` only after the designated master explicitly replies `accepted` to the compact `recover_and_continue` trigger.

The guidance SHALL define `hard-kill` as terminal and SHALL NOT present it as an ordinary entrypoint to `recover_and_continue`.

#### Scenario: Previously paused run uses soft resume
- **WHEN** one pairwise-v2 run is currently `paused`
- **AND WHEN** the participant set and wakeup posture remained logically live
- **THEN** the guidance uses `resume` for that run
- **AND THEN** it does not require `recover_and_continue`

#### Scenario: Restarted participant uses recover_and_continue
- **WHEN** one accepted pairwise-v2 run has a participant that was stopped or relaunched
- **THEN** the guidance uses `recover_and_continue` rather than `resume`
- **AND THEN** the run does not return to `running` until restart recovery completes and the master explicitly accepts continuation

#### Scenario: Hard-killed run does not use ordinary restart recovery
- **WHEN** one pairwise-v2 run previously ended through `hard-kill`
- **THEN** the guidance does not present ordinary `recover_and_continue` as the next action for that run
- **AND THEN** it keeps `hard-kill` distinct from pause or restart recovery
