# docs-loop-authoring-guide Specification

## Purpose
Define the documentation requirements for the Houmao loop authoring getting-started guide — a page that helps readers choose a loop skill, understand the pairwise-v2 routing-packet and recovery model, understand pairwise-v3 workspace posture, and discover graph tooling that supports plan authoring.

## Requirements

### Requirement: docs site includes a loop authoring guide

The docs site SHALL include a getting-started guide at `docs/getting-started/loop-authoring.md` that helps readers choose a loop skill and understand the current loop authoring models.

The guide SHALL include a skill-selection table that lists the current packaged loop skills — `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-pairwise-v3`, and `houmao-agent-loop-generic` — with at minimum: the lifecycle verbs each skill supports, the prestart model it uses, and the topology it targets.

The guide SHALL explain that `houmao-agent-loop-pairwise-v3` is the workspace-aware extension of pairwise-v2.

That v3 guidance SHALL cover:
- that pairwise-v3 adds a workspace contract to the authored run plan,
- that the workspace contract supports `standard` and `custom` modes,
- that `standard` mode may rely on Houmao's standard workspace posture,
- that `custom` mode records operator-owned paths directly in the loop plan,
- that standard in-repo posture is task-scoped under `houmao-ws/<task-name>/...`,
- that `houmao-utils-workspace-mgr` remains the standard workspace-preparation skill rather than a custom-workspace lane.

The guide SHALL continue to explain the pairwise-v2 routing-packet and recovery model as the conceptual baseline that pairwise-v3 extends rather than replaces.

The guide SHALL include a short orientation to `houmao-agent-loop-generic`: what a "generic loop graph" means (a graph with typed pairwise and relay components), when to use it over the pairwise-only skills, and a pointer to the skill's SKILL.md for the full authoring vocabulary.

The guide SHALL link to:
- each loop skill's SKILL.md (or the skills directory) for full lifecycle vocabulary and operating pages,
- `docs/reference/cli/internals.md` for the `graph high` command reference,
- `docs/getting-started/system-skills-overview.md` for the full skill catalog.

The guide SHALL NOT reproduce the full pairwise-v2 routing-packet JSON schema, the complete loop-plan template, or the full operating-page vocabulary — those live in the skill SKILL.md and its supporting pages.

#### Scenario: Reader can choose between v2 and v3
- **WHEN** a reader opens `docs/getting-started/loop-authoring.md`
- **THEN** they find a reference table comparing the current loop skills including pairwise-v2 and pairwise-v3
- **AND THEN** they can see that pairwise-v3 is the workspace-aware extension while pairwise-v2 remains available as its predecessor

#### Scenario: Reader understands v3 standard versus custom workspace
- **WHEN** a reader studies the pairwise-v3 section of the loop authoring guide
- **THEN** the guide explains `standard` versus `custom` workspace mode
- **AND THEN** it explains that custom workspace is recorded in the loop plan rather than routed through `houmao-utils-workspace-mgr`

#### Scenario: Reader understands task-scoped standard in-repo posture
- **WHEN** a reader studies the standard in-repo workspace posture for pairwise-v3
- **THEN** the guide explains that the standard team root is `houmao-ws/<task-name>/...`
- **AND THEN** it does not present the flat `houmao-ws/<agent-name>/...` layout as the current standard in-repo model
