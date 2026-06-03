## REMOVED Requirements

### Requirement: `houmao-mgr project agents roles` mirrors the project-local role tree
**Reason**: Low-level roles are native-agent material and are no longer ordinary project resources.
**Migration**: Use `houmao-mgr internals native-agent roles ... --native-agent-root <path>`.

#### Scenario: Role tree management moves to native-agent internals
- **WHEN** an operator needs direct low-level role management
- **THEN** the supported internal path is `houmao-mgr internals native-agent roles ...`
- **AND THEN** ordinary project help does not present `project agents roles`

### Requirement: `project agents roles init/get/remove` manages role roots under the project overlay
**Reason**: Direct role roots belong to a selected native-agent root, not to first-class project state.
**Migration**: Use `internals native-agent roles init|get|remove` with `--native-agent-root`.

#### Scenario: Role roots use native-agent root selection
- **WHEN** an operator initializes a native role
- **THEN** the command writes under the selected native-agent root
- **AND THEN** it does not mutate the project catalog

### Requirement: `project agents roles get` can include prompt content on explicit request
**Reason**: Direct role inspection belongs to native-agent internals.
**Migration**: Use `internals native-agent roles get --include-prompt`.

#### Scenario: Full native role inspection stays internal
- **WHEN** an operator inspects native role prompt content
- **THEN** the maintained path is `internals native-agent roles get --include-prompt`
- **AND THEN** the command is not part of ordinary project specialist inspection

### Requirement: `project agents roles` fail clearly when referenced preset files are malformed
**Reason**: Malformed native recipe references are diagnosed by native-agent internals or by project projection validation, not by a public project roles subtree.
**Migration**: Use native-agent recipe validation or project specialist/profile validation depending on the resource being managed.

#### Scenario: Malformed native references are diagnosed in the native layer
- **WHEN** a native role command encounters malformed recipe material
- **THEN** the native-agent internals command reports the malformed native resource
- **AND THEN** ordinary project commands keep specialist/profile diagnostics at the project layer

### Requirement: Role authoring surfaces provide command-template entries
**Reason**: Role authoring command templates must follow the new `internals native-agent roles` command path and native-agent terminology.
**Migration**: Use native-agent command-template ids for direct role authoring.

#### Scenario: Role command templates use native ids
- **WHEN** an agent lists command templates
- **THEN** direct role authoring templates use native-agent ids
- **AND THEN** they do not use `project.agents.roles.*` ids as the maintained public names
