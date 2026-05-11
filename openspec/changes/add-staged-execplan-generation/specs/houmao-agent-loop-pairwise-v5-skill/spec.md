## ADDED Requirements

### Requirement: V5 exposes staged execplan generation subcommands
The packaged v5 skill SHALL expose these staged execplan generation subcommands:

- `execplan-specs-process`;
- `execplan-specs-contract`;
- `execplan-harness`;
- `execplan-skills`;
- `execplan-agent-bindings`;
- `execplan-finalize`.

The staged subcommands SHALL be authoring operations under the selected `<loop-dir>` and SHALL NOT perform Houmao platform launch, mailbox delivery, gateway, memory, lifecycle, or workspace creation side effects.

Each staged subcommand SHALL state its inputs, outputs, prerequisites, downstream invalidation effects, and boundaries.

#### Scenario: User asks for one staged generation step
- **WHEN** a user explicitly asks v5 to run `execplan-harness` for a selected loop directory
- **THEN** the skill routes to the staged harness-generation guidance
- **AND THEN** the staged operation works only on generated execplan material and does not start or mutate live agents

#### Scenario: Staged commands are discoverable
- **WHEN** a user asks which execplan generation stages are available
- **THEN** the skill lists the six staged subcommands in dependency order
- **AND THEN** it explains that `generate-execplan` runs them as the common orchestration path

### Requirement: V5 generates execplan stages in process-first order
The staged execplan generation order SHALL be:

1. `execplan-specs-process`;
2. `execplan-specs-contract`;
3. `execplan-harness`;
4. `execplan-skills`;
5. `execplan-agent-bindings`;
6. `execplan-finalize`.

The `execplan-specs-process` stage SHALL generate or update the canonical loop process model before other execplan stages.

The process model SHALL describe the loop in generic process terms, including phases, events, handoffs, tick responsibilities, ownership, terminal posture, recovery posture, and provisional participant, message, or record families when those concepts apply.

Downstream stages SHALL derive their generated artifacts from the process model and intention source rather than inventing independent process semantics.

#### Scenario: Process model precedes derived contracts
- **WHEN** `generate-execplan` creates a fresh generated execplan
- **THEN** it treats `execplan-specs-process` as the first generation stage
- **AND THEN** objective, participant, topology, communication, state, workspace, harness, skill, agent-binding, docs, and final manifest artifacts are derived after the process model exists

#### Scenario: Process-first order applies without a fixed topology
- **WHEN** the intention source describes a custom loop topology
- **THEN** the process stage captures that topology in generic process terms
- **AND THEN** later stages derive contracts and generated role behavior from that process model without forcing a built-in participant shape

### Requirement: Generate and update orchestration use staged execplan order
The `generate-execplan` operation SHALL orchestrate the staged execplan subcommands in dependency order unless the user explicitly asks for one staged subcommand.

The `update-execplan` operation SHALL determine the earliest affected stage from the changed intention source or explicit user request, then rerun that stage and downstream stages as needed.

The `execplan-finalize` stage SHALL produce final support docs, package README updates, final manifest entries, generated metadata, explicit omission notes, and consistency notes after authoritative generated artifacts exist.

The manifest MAY be seeded before finalization, but final manifest content SHALL be produced or checked during `execplan-finalize`.

#### Scenario: Generate-execplan runs all stages
- **WHEN** a user asks v5 to `generate-execplan`
- **THEN** the operation runs `execplan-specs-process`, `execplan-specs-contract`, `execplan-harness`, `execplan-skills`, `execplan-agent-bindings`, and `execplan-finalize` in order
- **AND THEN** it runs or requests `validate-execplan` before reporting the execplan ready

#### Scenario: Update-execplan reruns affected downstream stages
- **WHEN** intention changes affect participant process flow or handoff semantics
- **THEN** `update-execplan` starts from `execplan-specs-process`
- **AND THEN** it reruns downstream stages whose generated artifacts depend on the changed process model

#### Scenario: Finalization is last
- **WHEN** a staged generation run reaches `execplan-finalize`
- **THEN** generated docs, package README, final manifest content, generated metadata, and explicit omission notes reflect the artifacts actually emitted by earlier stages
- **AND THEN** finalization does not introduce new authoritative process, contract, harness, skill, or agent-binding semantics that bypass earlier stages
