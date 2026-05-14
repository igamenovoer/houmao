## ADDED Requirements

### Requirement: Advanced-usage guidance recognizes lite as a lightweight loop path
The `houmao-adv-usage-pattern` skill SHALL recognize `houmao-agent-loop-lite` as the current lightweight generated-skill loop path when the user explicitly wants Markdown contracts, typed Markdown communication templates, direct SQLite state, and no generated harness.

The skill SHALL continue to route topology-rich generated execplans, rendered graphs, graph policy, complex multi-edge tree loops, multi-lane relay routes, schema/harness validation, and generated loop run-control actions to `houmao-agent-loop-pro`.

The skill SHALL keep elemental mailbox, gateway, notifier, relay, and local-close patterns distinct from both pro and lite generated loop packages.

#### Scenario: Advanced user asks for no-harness generated loop
- **WHEN** a user asks advanced-usage guidance for a generated loop package without schemas or harnesses
- **THEN** the skill points them to `houmao-agent-loop-lite`
- **AND THEN** it does not expand a pro-style execplan inline

#### Scenario: Advanced user asks for graph-heavy loop authoring
- **WHEN** a user asks for topology-rich graph planning or generated validation contracts
- **THEN** the skill points them to `houmao-agent-loop-pro`
- **AND THEN** it does not route that request to lite
