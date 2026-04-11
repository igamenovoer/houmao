## ADDED Requirements

### Requirement: docs site includes a loop authoring guide

The docs site SHALL include a getting-started guide at `docs/getting-started/loop-authoring.md` that helps readers choose a loop skill and understand the current loop authoring models.

The guide SHALL include a skill-selection table that lists the three packaged loop skills — `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, and `houmao-agent-loop-generic` — with at minimum: the lifecycle verbs each skill supports, the prestart model it uses, and the topology it targets.

The guide SHALL explain the pairwise-v2 routing-packet prestart model in a short conceptual section. That section SHALL cover:
- what a routing packet is (a precomputed instruction block embedded in the plan before the run starts),
- what `initialize` does with routing packets (validates packet coverage and root packet availability before the start charter is sent),
- how the default `precomputed_routing_packets` strategy differs from the explicit `operator_preparation_wave` opt-in,
- that `houmao-mgr internals graph high packet-expectations` and `validate-packets` are the supported CLI helpers for authoring and validating routing packets.

The guide SHALL include a short orientation to `houmao-agent-loop-generic`: what a "generic loop graph" means (a graph with typed pairwise and relay components), when to use it over the pairwise-only skills, and a pointer to the skill's SKILL.md for the full authoring vocabulary.

The guide SHALL link to:
- each loop skill's SKILL.md (or the skills directory) for full lifecycle vocabulary and operating pages,
- `docs/reference/cli/internals.md` for the `graph high` command reference,
- `docs/getting-started/system-skills-overview.md` for the full skill catalog.

The guide SHALL NOT reproduce the full pairwise-v2 routing-packet JSON schema, the complete loop-plan template, or the full operating-page vocabulary — those live in the skill SKILL.md and its supporting pages.

#### Scenario: Reader can choose a loop skill from the guide

- **WHEN** a reader opens `docs/getting-started/loop-authoring.md`
- **THEN** they find a reference table comparing the three loop skills by lifecycle verbs, prestart model, and topology
- **AND THEN** they can decide which skill fits their workflow without reading all three SKILL.md files

#### Scenario: Reader understands pairwise-v2 routing packets

- **WHEN** a reader reads the pairwise-v2 section of the loop authoring guide
- **THEN** they understand that routing packets are precomputed at authoring time and validated during `initialize`, not sent as separate operator mail
- **AND THEN** they know that `graph high packet-expectations` and `validate-packets` are the CLI helpers for this step

#### Scenario: Reader discovers internals graph from loop authoring context

- **WHEN** a reader is authoring a pairwise-v2 plan and reads the loop authoring guide
- **THEN** they find a direct reference to `houmao-mgr internals graph high` as the available CLI tooling for structural analysis and packet validation
- **AND THEN** they find a link to `docs/reference/cli/internals.md` for the full command reference

#### Scenario: Reader understands when to use generic vs pairwise

- **WHEN** a reader wants to run a loop that involves both pairwise edges and relay lanes
- **THEN** the loop authoring guide explains that `houmao-agent-loop-generic` is the appropriate skill and that it decomposes user intent into typed pairwise and relay components
