## ADDED Requirements

### Requirement: Managed-agent birth is source-scoped rather than global management
The maintained global managed-agent management surface SHALL NOT expose a first-birth launch command.

Project-backed managed-agent birth SHALL be represented by:

```text
houmao-mgr project [--project-dir <dir>] agents launch
```

Direct native/provider construction plumbing, when retained, SHALL live under internal native-agent command surfaces rather than `houmao-mgr agents global`.

Existing local managed-agent identities MAY be adopted into the registry through `houmao-mgr agents self join` when the target is the caller's current tmux session.

#### Scenario: Global management omits launch
- **WHEN** an operator runs `houmao-mgr agents global --help`
- **THEN** the help output does not list `launch`
- **AND THEN** the operator must choose a source-scoped birth command or a join/import command instead

#### Scenario: Project launch remains public birth path
- **WHEN** an operator wants to create a managed agent from project profile `reviewer`
- **THEN** the maintained command path is `houmao-mgr project agents launch --profile reviewer`
- **AND THEN** the launch resolves source definitions from the selected project overlay rather than from global registry state

## REMOVED Requirements

### Requirement: `houmao-mgr agents launch` performs local brain building and agent launch
**Reason**: First-birth launch is no longer a maintained root/global managed-agent management action.
**Migration**: Use `houmao-mgr project [--project-dir <dir>] agents launch ...` for project-backed agent birth, `houmao-mgr agents self join ...` to adopt the current tmux session, or retained internal native-agent plumbing for direct native/provider construction.

### Requirement: `houmao-mgr agents launch` accepts the established launch options
**Reason**: The public root/global launch surface is retired.
**Migration**: Use `houmao-mgr project [--project-dir <dir>] agents launch ...` for project-backed launch options.

### Requirement: `houmao-mgr agents launch` supports unified model configuration
**Reason**: The public root/global launch surface is retired.
**Migration**: Use project-backed launch and profile/specialist model controls under `houmao-mgr project`.

### Requirement: `houmao-mgr agents launch` resolves preset selectors with explicit default-setup behavior
**Reason**: Direct preset-selector launch is no longer a public root/global managed-agent management action.
**Migration**: Resolve launch sources through project specialists/profiles or retained internal native-agent surfaces.

### Requirement: `houmao-mgr agents launch` supports headless and interactive modes
**Reason**: The public root/global launch surface is retired.
**Migration**: Use project-backed launch posture controls under `houmao-mgr project agents launch`.

### Requirement: `houmao-mgr agents launch` resolves backend from provider and launch mode
**Reason**: The public root/global launch surface is retired.
**Migration**: Use source-scoped project launch or internal native-agent plumbing.

### Requirement: `houmao-mgr agents launch` reports unattended strategy compatibility failures distinctly
**Reason**: The public root/global launch surface is retired.
**Migration**: Preserve compatibility diagnostics on the retained project-backed or internal launch surface that performs birth.

### Requirement: `houmao-mgr agents launch` preserves preset launch settings during local build
**Reason**: The public root/global launch surface is retired.
**Migration**: Preserve source launch settings through project-backed launch or internal native-agent construction.

### Requirement: `houmao-mgr agents launch` keeps managed-agent identity launch-time only
**Reason**: The public root/global launch surface is retired.
**Migration**: Keep identity creation on source-scoped project launch and current-session adoption through `agents self join`.

### Requirement: `houmao-mgr agents launch` supports explicit launch-profile-backed launch
**Reason**: Project launch profiles are project resources and no longer belong on a root/global launch surface.
**Migration**: Use `houmao-mgr project [--project-dir <dir>] agents launch --profile <name>`.

### Requirement: Launch-profile-backed launch applies profile defaults before direct CLI overrides
**Reason**: Project launch-profile-backed launch now belongs to the project command family.
**Migration**: Use `houmao-mgr project [--project-dir <dir>] agents launch --profile <name>` and preserve the same default/override semantics there.

### Requirement: `houmao-mgr agents launch` consumes the canonical parsed contract
**Reason**: The public root/global launch surface is retired.
**Migration**: Keep canonical parsed contract consumption on retained source-scoped birth surfaces.

### Requirement: `houmao-mgr agents launch` accepts user-specified agent identity fields
**Reason**: The public root/global launch surface is retired.
**Migration**: Use identity fields on project-backed launch when creating a project-owned instance, or `agents self join` when adopting the current tmux session.

### Requirement: `houmao-mgr agents launch` reports managed-agent and tmux identities separately
**Reason**: The public root/global launch surface is retired.
**Migration**: Preserve identity reporting on retained source-scoped birth surfaces and self-join output.

### Requirement: `houmao-mgr agents launch` supports one-shot managed-header override
**Reason**: The public root/global launch surface is retired.
**Migration**: Use managed-header controls on retained project-backed launch/profile surfaces.

### Requirement: `houmao-mgr agents launch` supports launch-owned managed force takeover
**Reason**: The public root/global launch surface is retired.
**Migration**: Use force/takeover controls on retained project-backed birth surfaces when applicable.

### Requirement: `houmao-mgr agents launch` supports one-shot launch-owned system-prompt appendix
**Reason**: The public root/global launch surface is retired.
**Migration**: Use retained project-backed launch/profile prompt overlay controls.

### Requirement: `houmao-mgr agents launch` supports one-shot managed-header section overrides
**Reason**: The public root/global launch surface is retired.
**Migration**: Use managed-header section controls on retained project-backed launch/profile surfaces.

### Requirement: `houmao-mgr agents launch` reports simplified managed memory paths
**Reason**: The public root/global launch surface is retired.
**Migration**: Preserve simplified managed memory reporting on retained source-scoped birth surfaces.

### Requirement: Explicit launch-profile-backed launch applies stored memo seeds
**Reason**: Launch-profile-backed birth is now project-scoped.
**Migration**: Use `houmao-mgr project [--project-dir <dir>] agents launch --profile <name>`.

### Requirement: Explicit launch-profile memo seed application is component-scoped
**Reason**: Launch-profile-backed birth is now project-scoped.
**Migration**: Preserve component-scoped memo seed semantics under `project agents launch --profile`.

### Requirement: `houmao-mgr agents launch` supports explicit preserved-home reuse
**Reason**: The public root/global launch surface is retired.
**Migration**: Use preserved-home reuse on retained project-backed launch surfaces when applicable.

### Requirement: Launch-profile-backed launch applies skill overlays
**Reason**: Launch-profile-backed birth is now project-scoped.
**Migration**: Use `houmao-mgr project [--project-dir <dir>] agents launch --profile <name>`.

### Requirement: Launch provenance records profile skill overlays
**Reason**: Launch-profile-backed birth is now project-scoped.
**Migration**: Preserve profile skill overlay provenance under `project agents launch --profile`.

### Requirement: Agent launch CLI surfaces provide command-template entries
**Reason**: Command templates for public root/global launch paths are retired with the public root/global launch surface.
**Migration**: Provide templates for retained project-backed birth paths and internal native-agent construction paths.
