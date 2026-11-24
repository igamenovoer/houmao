# README System Skills Delta

## MODIFIED Requirements

### Requirement: README introduces the three-skill public surface
The README System Skills subsection SHALL introduce `houmao-admin-welcome`, `houmao-admin-entrypoint`, and `houmao-agent-entrypoint` by their orientation and actor roles. It SHALL also identify the standalone shared and loop siblings, describe shared routines as parent-owned children, and link to the System Skills Overview for the full route map.

#### Scenario: Reader scans the README system-skills section
- **WHEN** a reader wants the shortest public-surface explanation
- **THEN** the README identifies the welcome, admin execution, and managed-agent execution roles
- **AND THEN** it distinguishes standalone shared and loop siblings from parent-owned child routines

### Requirement: README examples use public entrypoint invocations
System-skill examples SHALL start with a standalone public skill name. The README SHALL label shared children as parent-scoped routes and use read-only, role-appropriate help examples.

#### Scenario: README mentions agent-definition behavior
- **WHEN** the README explains specialist or profile authoring
- **THEN** it starts the executable example from `$houmao-admin-entrypoint`
- **AND THEN** it may identify `houmao-agent-definition` as the parent-scoped owner

### Requirement: README system-skill inventory matches the static public root
The README SHALL list `houmao-admin-welcome`, `houmao-admin-entrypoint`, `houmao-agent-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite` exactly once as current standalone skills. It SHALL explain that actor entrypoints and advanced direct shared invocation can select the manifest-declared children of shared routines.

#### Scenario: README inventory is checked against packaged assets
- **WHEN** a maintainer reviews the README inventory against `system_skills/public/*/SKILL.md`
- **THEN** both inventories contain the same six names
- **AND THEN** the README describes new shared children as routes under `houmao-shared-routines`

### Requirement: README provides complete static installation examples
The README SHALL show the recommended Houmao admin-pack install, managed agent-pack default, copy-paste directory lists, Skills CLI all-skills discovery, and explicit actor-specific Skills CLI selections. Actor pack examples SHALL include shared routines and both loops. The README SHALL distinguish Houmao's pack ownership config from independent Skills CLI installation.

#### Scenario: User copies the admin skills manually
- **WHEN** a reader follows the README copy-paste admin example
- **THEN** the example copies all five admin-pack roots
- **AND THEN** the admin entrypoint has its shared and loop siblings
