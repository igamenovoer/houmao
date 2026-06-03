## REMOVED Requirements

### Requirement: `houmao-mgr project agents launch-profiles` manages explicit recipe-backed launch profiles
**Reason**: Recipe-backed launch defaults are native-agent launch dossiers and belong to `internals native-agent`.
**Migration**: Use `houmao-mgr internals native-agent launch-dossiers ... --native-agent-root <path>`.

#### Scenario: Launch-profile tree moves to launch dossiers
- **WHEN** an operator needs direct recipe-backed native launch defaults
- **THEN** the supported internal path is `houmao-mgr internals native-agent launch-dossiers ...`
- **AND THEN** ordinary project help does not present `project agents launch-profiles`

### Requirement: `project agents launch-profiles` manages named explicit launch-profile resources
**Reason**: Named explicit launch-profile resources are renamed launch dossiers.
**Migration**: Use `internals native-agent launch-dossiers add|set|get|list|remove`.

#### Scenario: Launch dossier mutation uses native-agent command paths
- **WHEN** an operator edits recipe-backed native launch defaults
- **THEN** the command path is `houmao-mgr internals native-agent launch-dossiers set`
- **AND THEN** the edited resource is described as a launch dossier

### Requirement: `project agents launch-profiles` manages explicit launch-profile managed-header policy
**Reason**: Managed-header policy on native launch material belongs to launch dossiers; project profiles own project-layer reusable launch defaults.
**Migration**: Use launch-dossier commands for direct native material or project profile commands for ordinary project defaults.

#### Scenario: Managed-header policy is edited at the correct layer
- **WHEN** an operator edits a project profile
- **THEN** project profile commands own user-facing managed-header policy
- **AND WHEN** an operator edits native launch material
- **THEN** launch-dossier commands own internal managed-header policy

### Requirement: Launch-profile auth overrides track auth profile identity across auth rename
**Reason**: The same identity-preservation behavior remains required, but the direct native resource is now a launch dossier and the project resource is now a project profile.
**Migration**: Use project profile auth references for ordinary workflows or native launch-dossier auth references for direct internals.

#### Scenario: Auth identity behavior survives terminology change
- **WHEN** a project profile or launch dossier references a credential/auth profile
- **AND WHEN** that credential is renamed
- **THEN** the relationship remains valid through identity rather than display-name text
- **AND THEN** inspection renders the current display name

### Requirement: `project agents launch-profiles add --yes` replaces same-lane explicit profiles
**Reason**: Same-lane replacement behavior now belongs to launch-dossier create semantics or project profile create semantics, depending on layer.
**Migration**: Use `internals native-agent launch-dossiers add --yes` for native material or `project profile create --yes` for project profiles.

#### Scenario: Replacement happens in the selected layer
- **WHEN** an operator replaces a native launch dossier
- **THEN** launch-dossier create replacement semantics apply
- **AND WHEN** an operator replaces a project profile
- **THEN** project profile replacement semantics apply

### Requirement: Launch-profile authoring surfaces provide command-template entries
**Reason**: Direct native launch defaults are now launch dossiers and command-template ids must reflect the new command path.
**Migration**: Use native-agent launch-dossier command-template ids.

#### Scenario: Launch-dossier command templates use native ids
- **WHEN** an agent lists command templates
- **THEN** direct launch-dossier authoring templates use native-agent ids
- **AND THEN** they do not use `project.agents.launch-profiles.*` ids as the maintained public names
