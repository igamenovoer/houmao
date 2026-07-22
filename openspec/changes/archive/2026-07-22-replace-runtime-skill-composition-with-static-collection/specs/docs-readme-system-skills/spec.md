## ADDED Requirements

### Requirement: README system-skill inventory matches the static public root
The README system-skills section SHALL list `houmao-admin-welcome`, `houmao-admin-entrypoint`, `houmao-agent-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite` exactly once as current standalone skills.

It SHALL explain that the sixteen ordinary routines are selected below shared routines through actor entrypoints or direct advanced invocation. It SHALL NOT list those children as top-level installed peers.

#### Scenario: README inventory is checked against packaged assets
- **WHEN** documentation validation compares README names with `system_skills/public/*/SKILL.md`
- **THEN** both inventories contain the same six names
- **AND THEN** no old protected-mount or flat low-level skill is advertised as a current root

### Requirement: README provides complete static installation examples
The README SHALL show the recommended Houmao admin-pack install, the managed agent-pack default, copy-paste directory lists, Skills CLI all-skills discovery, and explicit actor-specific Skills CLI selections.

Every example SHALL include shared routines and both loops when an actor entrypoint depends on them. The README SHALL state that Houmao's manager owns pack receipts while Skills CLI performs ordinary independent skill installation.

#### Scenario: User copies the admin skills manually
- **WHEN** a reader follows the README copy-paste admin example
- **THEN** the example copies all five admin-pack roots
- **AND THEN** the admin entrypoint has its shared and loop siblings

### Requirement: README preserves welcome and direct advanced routes
The README SHALL recommend `$houmao-admin-welcome` for first-use orientation, `$houmao-admin-entrypoint` for normal human operations, `$houmao-agent-entrypoint` for managed self, `$houmao-shared-routines` for advanced direct ordinary routines, and the two loop skills for explicit manual loop work.

#### Scenario: Advanced reader wants direct inspection
- **WHEN** a reader wants to bypass actor-entrypoint route selection
- **THEN** the README shows direct shared-routines invocation
- **AND THEN** it explains that target, identity, and runtime validation remain active
