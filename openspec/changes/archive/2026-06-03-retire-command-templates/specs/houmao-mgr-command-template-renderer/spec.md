## REMOVED Requirements

### Requirement: `houmao-mgr internals command-templates` exposes supported command templates
**Reason**: The command-template CLI is retired as a historical mis-implementation; executable commands are spelled directly in skills and YAML authoring uses config drafts.
**Migration**: Use direct `houmao-mgr` command invocations for actions. Use `houmao-mgr internals config-drafts generate` only when a YAML config draft is needed.

#### Scenario: Command-template group is absent
- **WHEN** an operator inspects `houmao-mgr internals --help`
- **THEN** `command-templates` is not listed as a supported internal command group

### Requirement: Command templates use consolidated project targeting
**Reason**: Project command targeting is owned by the maintained `houmao-mgr project` command groups, not by a separate argv renderer.
**Migration**: Spell project-scoped commands directly, including group-level `--project-dir <dir>` when a workflow needs an explicit project selector.

#### Scenario: Project targeting is expressed directly
- **WHEN** a skill documents a project-scoped command
- **THEN** it shows the direct `houmao-mgr project [--project-dir <dir>] ...` invocation

### Requirement: Command templates expose internal native-agent credential and brain build paths
**Reason**: Internal native-agent commands remain ordinary internal CLI paths and do not need template registry entries.
**Migration**: Use direct `houmao-mgr internals native-agent ...` commands where direct native-agent plumbing is still maintained.

#### Scenario: Native internals are called directly
- **WHEN** a skill needs direct native-agent build plumbing
- **THEN** it documents `houmao-mgr internals native-agent brain build ...` directly

### Requirement: Command templates describe sparse field semantics
**Reason**: Sparse field semantics duplicated the real command contracts and made skills depend on a second schema.
**Migration**: Required inputs, optional flags, conflicts, and omitted-field behavior belong to the command implementation, command help, specs, and direct skill guardrails.

#### Scenario: Skill guardrails own missing-input recovery
- **WHEN** required action-command input is missing from a user request
- **THEN** the skill asks for that input before running the direct command

### Requirement: Renderer converts sparse intent into non-executing argv
**Reason**: Sparse intent-to-argv rendering is removed; skills now author the command they intend to run.
**Migration**: Use direct `bash` snippets for action commands and run the resulting `houmao-mgr` command only after required inputs are explicit.

#### Scenario: Action workflow does not render argv first
- **WHEN** a skill has enough explicit input to run an action command
- **THEN** it runs the maintained `houmao-mgr` command directly rather than rendering through an intermediate command-template command

### Requirement: Renderer preserves omission, clear, and patch semantics
**Reason**: Omission, clear, and patch semantics belong to the target command implementations and their direct guidance.
**Migration**: Skills omit optional flags unless the user explicitly requested them, and use explicit clear flags only when the maintained command exposes them and the user requested clearing.

#### Scenario: Optional flags remain explicit
- **WHEN** a user does not request prompt mode, launch posture, cleanup purge, or another optional action flag
- **THEN** the skill does not include that flag in the direct command snippet

### Requirement: Command templates are declared in code-first family modules
**Reason**: The code-first family registry is removed with the command-template abstraction.
**Migration**: Maintain direct CLI behavior in each command family's implementation and tests.

#### Scenario: Registry package is gone
- **WHEN** the source tree is inspected after implementation
- **THEN** there is no maintained command-template family registry package

### Requirement: Template datamodel remains frozen and typed
**Reason**: The command-template datamodel is removed with the renderer and registry.
**Migration**: Typed command behavior remains in the real command modules and domain models.

#### Scenario: Template models are gone
- **WHEN** the command-template package is removed
- **THEN** no frozen command-template datamodel remains as a maintained API

### Requirement: Command templates export deterministic YAML views
**Reason**: YAML export of executable command metadata is retired with the registry.
**Migration**: Use config-drafts for YAML documents. Do not export action-command metadata as YAML templates.

#### Scenario: Command metadata YAML export is unavailable
- **WHEN** a caller needs a YAML authoring aid
- **THEN** the maintained surface is `houmao-mgr internals config-drafts generate`

### Requirement: Internal CLI exposes YAML export for command templates
**Reason**: The `command-templates export` command is retired with the `command-templates` group.
**Migration**: Use `config-drafts generate` for config YAML and direct command snippets for executable workflows.

#### Scenario: Export command is absent
- **WHEN** an operator inspects `houmao-mgr internals --help`
- **THEN** there is no `command-templates export` path

### Requirement: Command templates remain argv-oriented and do not own config drafts
**Reason**: The entire command-template surface is removed; config drafts remain the only template-like CLI surface and are YAML-only.
**Migration**: Route YAML authoring to config drafts and executable workflows to direct `houmao-mgr` commands.

#### Scenario: Template responsibility is split without command templates
- **WHEN** an agent needs YAML
- **THEN** it uses config drafts
- **AND THEN** when it needs an action, it runs a direct `houmao-mgr` command

### Requirement: Command templates use explicit agent scope paths
**Reason**: Explicit agent scope paths are owned by the maintained `houmao-mgr agents single|self|global` command surface, not by a command-template registry.
**Migration**: Spell selected-agent and current-session commands directly with `agents single ...` or `agents self ...`.

#### Scenario: Agent scope is documented directly
- **WHEN** a skill documents a selected-agent operation
- **THEN** it shows the direct `houmao-mgr agents single --agent-id <id> ...` or `--agent-name <name>` command path
