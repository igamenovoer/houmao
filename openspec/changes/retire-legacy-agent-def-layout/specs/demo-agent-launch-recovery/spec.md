## ADDED Requirements

### Requirement: Affected demo launch assets retire legacy source-tree dependencies
Affected demo and tutorial packs SHALL keep their tracked launch defaults, helper inputs, and pack-owned agent-definition assets on the canonical preset/setup/auth layout.

For the affected scope of this change, maintained launch helpers and tracked pack-owned `agents/` trees SHALL NOT require `brains/brain-recipes/`, `brains/cli-configs/`, `brains/api-creds/`, or `blueprints/` as the authoritative source-tree dependency for startup.

#### Scenario: Affected helper defaults point at canonical preset-backed inputs
- **WHEN** a maintainer inspects the tracked default launch inputs for an affected demo or tutorial pack
- **THEN** the maintained helper input resolves a canonical preset path or canonical tool setup/auth path
- **AND THEN** the helper default does not depend on a legacy recipe or blueprint directory as its authoritative source-tree input

#### Scenario: Affected pack-owned agent trees do not ship legacy launch subtrees
- **WHEN** an affected demo pack ships its own tracked `agents/` tree under `scripts/demo/`
- **THEN** that tree publishes the launchable tracked assets needed by the pack through the canonical layout
- **AND THEN** the pack does not need tracked `agents/brains/` or `agents/blueprints/` subtrees to make startup succeed
