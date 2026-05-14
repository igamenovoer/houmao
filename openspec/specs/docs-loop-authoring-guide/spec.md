# docs-loop-authoring-guide Specification

## Purpose
Define the documentation requirements for the Houmao loop authoring getting-started guide — a page that helps readers choose a loop skill, understand the pairwise-v2 routing-packet and recovery model, understand pairwise-v3 workspace posture, and discover graph tooling that supports plan authoring.
## Requirements
### Requirement: docs site includes a loop authoring guide

The docs site SHALL include a getting-started guide at `docs/getting-started/loop-authoring.md` that helps readers choose a loop skill and understand the current loop authoring models.

The guide SHALL include a skill-selection table that lists the current packaged loop skills — `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-pairwise-v3`, `houmao-agent-loop-pairwise-v4`, and `houmao-agent-loop-generic` — with at minimum: the lifecycle verbs each skill supports, the prestart model it uses, and the topology it targets.

The guide SHALL explain that `houmao-agent-loop-pairwise-v3` is the workspace-aware extension of pairwise-v2.

That v3 guidance SHALL cover:
- that pairwise-v3 adds a workspace contract to the authored run plan,
- that the workspace contract supports `standard` and `custom` modes,
- that `standard` mode may rely on Houmao's standard workspace posture,
- that `custom` mode records operator-owned paths directly in the loop plan,
- that standard in-repo posture is task-scoped under `houmao-ws/<task-name>/...`,
- that `houmao-utils-workspace-mgr` remains the standard workspace-preparation skill rather than a custom-workspace lane.

The guide SHALL explain that `houmao-agent-loop-pairwise-v4` is the template-driven successor to pairwise-v3 for rich task-note plans where source constraints, policy-bearing verbs, role-local hard gates, and coverage audits need to be preserved explicitly.

That v4 guidance SHALL cover:
- that pairwise-v4 keeps the v3 workspace-aware lifecycle model,
- that v4 adds strict generated document templates,
- that v4 planners fill required slots instead of freeform-organizing rich task contracts,
- that v4 preserves policy-bearing schema verbs such as `ALWAYS`, `NEVER`, `CHECK`, `RUN`, `READ`, `ANALYZE`, `DECIDE`, `OUTPUT`, `UPDATE`, `COMMIT`, `MERGE`, and `DISPATCH`,
- that v4 includes a source-constraint coverage audit for rich bundle plans.

The guide SHALL continue to explain the pairwise-v2 routing-packet and recovery model as the conceptual baseline that pairwise-v3 and pairwise-v4 extend rather than replace.

The guide SHALL include a short orientation to `houmao-agent-loop-generic`: what a "generic loop graph" means (a graph with typed pairwise and relay components), when to use it over the pairwise-only skills, and a pointer to the skill's SKILL.md for the full authoring vocabulary.

The guide SHALL link to:
- each loop skill's SKILL.md (or the skills directory) for full lifecycle vocabulary and operating pages,
- `docs/reference/cli/internals.md` for the `graph high` command reference,
- `docs/getting-started/system-skills-overview.md` for the full skill catalog.

The guide SHALL NOT reproduce the full pairwise-v2 routing-packet JSON schema, the complete loop-plan template, or the full operating-page vocabulary — those live in the skill SKILL.md and its supporting pages.

#### Scenario: Reader can choose between v2, v3, and v4
- **WHEN** a reader opens `docs/getting-started/loop-authoring.md`
- **THEN** they find a reference table comparing the current loop skills including pairwise-v2, pairwise-v3, and pairwise-v4
- **AND THEN** they can see that pairwise-v3 is the workspace-aware extension while pairwise-v4 is the stricter template-driven successor for rich source contracts

#### Scenario: Reader understands v3 standard versus custom workspace
- **WHEN** a reader studies the pairwise-v3 section of the loop authoring guide
- **THEN** the guide explains `standard` versus `custom` workspace mode
- **AND THEN** it explains that custom workspace is recorded in the loop plan rather than routed through `houmao-utils-workspace-mgr`

#### Scenario: Reader understands task-scoped standard in-repo posture
- **WHEN** a reader studies the standard in-repo workspace posture for pairwise-v3
- **THEN** the guide explains that the standard team root is `houmao-ws/<task-name>/...`
- **AND THEN** it does not present the flat `houmao-ws/<agent-name>/...` layout as the current standard in-repo model

#### Scenario: Reader understands when to use v4
- **WHEN** a reader has a rich loop-task note with policy-bearing verbs and role-local hard gates
- **THEN** the guide points them at `houmao-agent-loop-pairwise-v4`
- **AND THEN** it explains that v4 preserves those constraints through strict document templates and a coverage audit

### Requirement: Loop authoring guide is pro-oriented
The loop authoring guide SHALL present `houmao-agent-loop-pro` as the current loop authoring skill.

The guide SHALL explain that tree-loop and generic-loop are topology decisions inside pro-generated execplans.

The guide SHALL NOT maintain a current skill-selection table among retired pairwise and generic loop packages.

#### Scenario: Reader chooses topology inside pro
- **WHEN** a reader wants to author a new loop
- **THEN** the guide directs them to `houmao-agent-loop-pro`
- **AND THEN** the guide explains when to choose tree-loop versus generic-loop mode

### Requirement: Loop authoring guide preserves graph helper context
The loop authoring guide SHALL continue to mention `houmao-mgr internals graph high` as deterministic graph tooling available to pro authoring when graph artifacts are useful.

#### Scenario: Reader needs deterministic graph validation
- **WHEN** a pro-generated loop has a topology graph that benefits from deterministic analysis
- **THEN** the guide points to `houmao-mgr internals graph high`
- **AND THEN** it does not require retired loop package names to use that tool

### Requirement: Loop authoring guide presents pro and lite as current choices
The loop authoring guide SHALL present both `houmao-agent-loop-pro` and `houmao-agent-loop-lite` as current maintained Houmao loop skills.

The guide SHALL describe pro as the schema-rich generated-execplan path with generated contracts, harnesses, generated skills, agent bindings, workspace readiness, validation, launch, and run control.

The guide SHALL describe lite as the Markdown/direct-SQL path with required communication templates, required generated skills, direct SQLite state, no JSON schemas, no Jinja2, no generated harness, and no generated docs layer.

The guide SHALL NOT present retired pairwise or generic loop packages as current choices.

#### Scenario: Reader chooses lite for a simple Markdown loop
- **WHEN** a reader wants a lightweight loop with Markdown contracts and direct SQLite bookkeeping
- **THEN** the guide directs them to `houmao-agent-loop-lite`
- **AND THEN** it explains that lite does not generate harness or docs directories

#### Scenario: Reader chooses pro for stronger generated validation
- **WHEN** a reader wants topology contracts, schema-typed mail, harness commands, or stronger generated validation
- **THEN** the guide directs them to `houmao-agent-loop-pro`
- **AND THEN** it does not route that work to lite
