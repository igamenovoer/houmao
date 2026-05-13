## ADDED Requirements

### Requirement: V5 generated execplans provide a loop-local operator control skill
The packaged v5 skill SHALL guide generated execplans with lifecycle control needs to emit a generated skill named `<loop-slug>-operator-control`.

The generated operator control skill SHALL live directly under `<loop-dir>/execplan/skills/<loop-slug>-operator-control/`.

The generated operator control skill SHALL identify the concrete loop slug, loop directory, manifest path, harness path, agent binding path, and supported run lifecycle operations for that generated loop.

The generated operator control skill SHALL provide loop-local guidance for lifecycle operations such as status, start, pause, resume, stop, recover, mode switching, and manual stepping when those operations apply.

The generated operator control skill MAY use local subskill or reference pages for lifecycle procedures, but those files SHALL remain inside the `<loop-slug>-operator-control` skill directory rather than under category directories such as `execplan/skills/operator/`.

The generated operator control skill SHALL route platform mechanics through maintained Houmao skills or CLI surfaces instead of duplicating launch, messaging, mailbox, gateway, workspace, memory, or inspection contracts.

#### Scenario: Execplan emits operator control
- **WHEN** the packaged skill generates `execplan/skills/` for a loop that supports operator lifecycle control
- **THEN** the generated execplan includes `<loop-dir>/execplan/skills/<loop-slug>-operator-control/SKILL.md`
- **AND THEN** that skill identifies the concrete generated loop and its lifecycle control surfaces

#### Scenario: Operator control uses flat skill namespace
- **WHEN** the generated operator control skill needs supporting lifecycle pages
- **THEN** those pages live inside `<loop-dir>/execplan/skills/<loop-slug>-operator-control/`
- **AND THEN** the generated execplan does not create `execplan/skills/operator/` or other category directories

#### Scenario: Operator control routes maintained platform operations
- **WHEN** the generated operator control procedure needs to inspect agents, send prompts, read or send mail, change notifier posture, or stop managed agents
- **THEN** it directs the operator to the maintained Houmao support skill or supported CLI surface that owns that platform operation
- **AND THEN** it keeps loop-local decisions, state queries, and record application in generated execplan or harness surfaces

### Requirement: V5 generated control contracts separate run state from execution mode
The packaged v5 skill SHALL guide generated execplans with lifecycle control needs to define loop-local control state that distinguishes run lifecycle state from execution mode.

Generated control state SHALL model run lifecycle state with values such as `not_started`, `running`, `paused`, `recovering`, `stopped`, and `completed`, or an explicitly documented equivalent state set.

Generated control state SHALL model execution mode with at least `auto` and `manual`, unless the generated execplan explicitly records that one of those modes is not applicable.

Generated control state SHALL default the initial execution mode to `auto` unless intention source, an accepted clarification decision, or an explicit operator-control action selects a different initial mode.

Generated control state SHALL define `auto` mode as notifier-driven execution where mail notification prompts are the normal wakeup path for mail-driven participants.

Generated control state SHALL define `manual` mode as operator-directed execution where mail notifier wakeups for the generated loop are suspended or disabled and the operator prompts bounded participant work directly.

Generated control state SHALL NOT treat `manual` mode as equivalent to `paused`; pausing blocks normal participant progress, while manual mode changes the wakeup authority.

Generated state or record contracts SHALL record operator intent events for mode switches, pauses, resumes, stops, overrides, and recovery actions when those controls exist.

#### Scenario: Running loop switches to manual mode
- **WHEN** an operator switches a running mail-driven loop from `auto` mode to `manual` mode
- **THEN** generated control state records the run lifecycle state separately from execution mode
- **AND THEN** the run can remain `running` while its execution mode becomes `manual`

#### Scenario: Unspecified initial mode defaults to auto
- **WHEN** a generated controllable loop has no explicit initial execution mode in intention source, accepted clarification decisions, or operator-control state
- **THEN** generated control state treats the initial execution mode as `auto`
- **AND THEN** generated status or mode lookup reports that default rather than leaving the mode ambiguous

#### Scenario: Pause remains distinct from manual mode
- **WHEN** an operator pauses a loop that is currently in manual mode
- **THEN** generated control state records a paused lifecycle posture
- **AND THEN** it does not rely on `manual` mode alone to mean participant progress is blocked

#### Scenario: Operator intent is auditable
- **WHEN** the operator changes mode, pauses, resumes, stops, overrides, or starts recovery
- **THEN** the generated execplan records an operator intent event or equivalent structured record
- **AND THEN** status and recovery can report the operator action, source, timestamp, affected run, and related evidence refs

### Requirement: V5 generated harnesses expose control and mode lookup commands
The packaged v5 skill SHALL guide generated harnesses for controllable loops to expose loop-local control commands or equivalent command groups.

Generated harness control commands SHALL support read-only status and execution-mode lookup for generated skills and operators.

Generated harness control commands SHALL support controlled mode changes when the generated loop supports `auto` and `manual` mode.

Generated harness control commands SHALL expose participant-specific manual context when manual operation is supported.

Generated participant context output SHALL include enough structured information for generated skills to decide one bounded pass, including run identity, run state, execution mode, participant identity, relevant pending mail refs or active handoff refs, allowed actions, and whether the participant must stop after one pass.

Generated harness control commands SHALL record requested control changes in loop-local state or records but SHALL NOT directly own gateway notifier implementation, mailbox delivery, managed-agent prompting, or managed-agent lifecycle mechanics.

#### Scenario: Agent queries execution mode
- **WHEN** a generated participant skill begins tick work
- **THEN** it can query the generated harness for current run state, execution mode, and participant control context
- **AND THEN** it does not infer execution mode from static skill prose or intention Markdown

#### Scenario: Operator changes mode through generated control surface
- **WHEN** the generated operator control skill changes a loop from `auto` to `manual`
- **THEN** it uses the generated harness to record the requested mode change and resulting loop-local control state
- **AND THEN** it routes notifier posture changes through the maintained Houmao gateway surface

#### Scenario: Manual context is actionable
- **WHEN** an operator prompts a participant for one manual-mode step
- **THEN** the generated participant skill can obtain manual context from the harness
- **AND THEN** that context identifies the bounded actions the participant may take before ending the turn

### Requirement: V5 generated on-tick skills are execution-mode aware
The packaged v5 skill SHALL guide generated on-tick skills for controllable loops to query generated harness control context before deciding tick behavior.

Generated on-tick skills SHALL branch between `auto` mode and `manual` mode behavior when both modes are supported.

In `auto` mode, generated on-tick skills SHALL perform the bounded post-mail, scheduling, reconciliation, timeout, completion, or "what now" work defined by notifier-prompt-driven loop semantics.

In `manual` mode, generated on-tick skills SHALL perform one operator-prompted bounded pass that may include checking relevant mail, processing one relevant mail or bounded mail batch, querying current state, acting from current context when no mail is pending, applying generated records through the harness, sending downstream mail, replying upstream mail, or reporting no actionable work.

Generated on-tick skills SHALL finish the chat turn after their bounded pass in both modes.

Generated on-tick skills SHALL NOT sleep, poll, tail logs, wait in-chat for mail, or rely on a periodic external tick driver.

#### Scenario: Auto-mode tick remains notifier-driven
- **WHEN** a mail notifier prompt asks an agent to process mail and run a follow-up tick in `auto` mode
- **THEN** the generated on-tick skill queries control context and performs the bounded auto-mode tick behavior
- **AND THEN** the agent finishes the chat turn after the tick

#### Scenario: Manual-mode tick can work without notifier prompt context
- **WHEN** an operator prompts an agent to perform one manual-mode step
- **THEN** the generated on-tick skill queries manual context and checks the current mail or state posture needed for one bounded action
- **AND THEN** the agent sends any required downstream mail, upstream reply, state record, or no-action report before ending the turn

#### Scenario: Tick does not block future prompts
- **WHEN** a generated on-tick skill finds no actionable work in either execution mode
- **THEN** it reports the no-action posture
- **AND THEN** it does not keep the chat turn open waiting for future mail or status changes

### Requirement: V5 generated agent bindings and validation cover operator control mode semantics
The packaged v5 skill SHALL guide generated agent bindings for mail-driven controllable loops to document auto-mode notifier behavior and manual-mode operator-prompted behavior.

Generated notifier prompt material SHALL describe auto-mode behavior: the notifier wakes the agent for mail processing, the agent uses generated on-event skills for matching message families, and the agent runs any required follow-up tick before ending the turn.

Generated operator control material SHALL describe manual-mode behavior: notifier wakeups are suspended or disabled for the generated loop, and the operator prompts one bounded participant step at a time.

Generated validation guidance SHALL check that controllable generated execplans include the operator control skill, harness control/mode lookup surfaces, mode-aware on-tick guidance, mode-switch operator intent records, notifier posture boundaries, and no in-chat waiting posture.

Generated validation guidance SHALL report missing or inconsistent mode control as a generated execplan issue when the loop claims to support auto/manual operation.

#### Scenario: Agent binding documents both wakeup modes
- **WHEN** a generated mail-driven loop supports manual operation
- **THEN** generated agent binding or notifier prompt material documents auto-mode notifier-driven behavior
- **AND THEN** generated operator control material documents manual-mode operator-prompted behavior

#### Scenario: Validation catches missing mode lookup
- **WHEN** a generated execplan claims to support manual mode but the generated harness lacks a mode lookup or manual context surface
- **THEN** `validate-execplan` guidance reports the execplan as incomplete
- **AND THEN** it points to the harness and generated skill stages that must be regenerated or repaired

#### Scenario: Validation catches notifier/manual mismatch
- **WHEN** generated operator control says manual mode disables notifier wakeups but generated agent bindings still require notifier prompts for manual work
- **THEN** validation guidance reports the mismatch
- **AND THEN** the generated execplan must align manual operation around operator-prompted bounded turns
