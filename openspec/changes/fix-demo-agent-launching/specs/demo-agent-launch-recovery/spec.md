## ADDED Requirements

### Requirement: Affected demos launch against the current agent-definition model
The system SHALL restore agent startup for the affected demo and tutorial packs by resolving launch inputs against the current preset/setup/auth agent-definition model rather than requiring legacy recipe or blueprint launch wiring.

Affected packs for this change include the demo and tutorial launch flows currently blocked by legacy launch-path dependencies, such as shared TUI tracking, mail ping-pong gateway, TUI mail gateway, mailbox roundtrip tutorial, skill invocation, gateway stalwart/cypht interactive, passive-server parallel validation, Houmao server agent API, and Houmao server dual shadow watch.

#### Scenario: Demo launch helper starts an agent without legacy recipe lookup
- **WHEN** an affected demo helper needs to build or start one agent
- **THEN** it SHALL resolve a preset-backed launch target or equivalent current launch input
- **AND THEN** it SHALL NOT require a `brains/brain-recipes/` file lookup to make startup succeed

#### Scenario: Demo launch helper starts an agent without blueprint-owned binding
- **WHEN** an affected demo helper needs role and launch metadata for one agent startup
- **THEN** it SHALL use current preset-backed launch/build surfaces or a compatibility adapter that resolves through them
- **AND THEN** it SHALL NOT require a legacy `blueprints/` file as the authoritative launch input for startup success

### Requirement: Launch recovery scope is limited to startup success
This change SHALL define demo recovery in terms of successful startup only. A repaired demo for this change MUST be able to complete its agent-launching process and publish the expected startup artifact or startup metadata for the demo flow.

Examples of acceptable startup completion evidence include a built brain manifest, a started runtime session, a returned session manifest path, or published startup identity metadata, depending on the demo's launch pattern.

#### Scenario: Launch-focused repair does not require post-launch behavior
- **WHEN** an affected demo successfully builds and starts its agent session
- **THEN** the demo SHALL be considered repaired for this change's scope
- **AND THEN** mailbox exchange, reporting, scripted interaction, or other post-launch functionality SHALL NOT be required by this change

### Requirement: Compatibility-only demo field names may remain temporarily
Demo-owned config, state, or report fields MAY temporarily keep names such as `recipe_path`, `brain_recipe_path`, or `blueprint` during this change, but only if those fields no longer force startup to depend on legacy recipe or blueprint source trees.

#### Scenario: Compatibility field name points at current launch behavior
- **WHEN** a demo-owned config or state payload still uses a legacy-looking field name
- **THEN** the underlying startup logic SHALL still resolve through preset-backed or otherwise current launch/build behavior
- **AND THEN** that compatibility field SHALL NOT require restoring legacy recipe/blueprint launch semantics
