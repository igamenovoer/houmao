## ADDED Requirements

### Requirement: `project easy template create/list/get/remove` manages specialist-backed launch templates
`houmao-mgr project easy template create --name <template> --specialist <specialist>` SHALL persist one reusable easy-layer launch template that targets exactly one existing specialist.

When no active project overlay exists for the caller and no stronger overlay selection override is supplied, `project easy template create` SHALL ensure `<cwd>/.houmao` exists before persisting template state.

`project easy template list`, `get`, and `remove` SHALL resolve the active overlay through the shared non-creating project-aware resolver and SHALL fail clearly when no active overlay exists.

`project easy template get --name <template>` SHALL report the source specialist plus the stored template-owned launch defaults.

`project easy template remove --name <template>` SHALL remove only the template definition and SHALL NOT remove the referenced specialist only because that specialist was the template source.

#### Scenario: Easy template create bootstraps the missing overlay on demand
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project easy template create --name alice --specialist cuda-coder`
- **THEN** the command ensures `<cwd>/.houmao` exists before storing the template
- **AND THEN** the persisted template lands in the resulting project-local catalog and compatibility projection

#### Scenario: Easy template remove preserves the referenced specialist
- **WHEN** launch template `alice` targets specialist `cuda-coder`
- **AND WHEN** an operator runs `houmao-mgr project easy template remove --name alice`
- **THEN** the command removes the persisted `alice` launch template
- **AND THEN** it does not remove specialist `cuda-coder` only because `alice` referenced it

### Requirement: `project easy instance launch` supports template-backed launch
`houmao-mgr project easy instance launch` SHALL support selecting a reusable easy launch template through `--template <template>`.

`--template` and `--specialist` SHALL be mutually exclusive on this surface.

When `--template` is used, the command SHALL derive the source specialist from the stored template, SHALL apply template defaults before direct CLI overrides, and SHALL still use the selected project overlay as the authoritative source context.

When a selected template stores a default managed-agent name, the command MAY omit `--name` and SHALL use the template-owned default identity.

When a selected template stores workdir, auth override, mailbox config, or launch posture, those values SHALL apply unless the operator supplies a direct launch-time override.

If the selected template resolves to a Gemini specialist, the existing headless-only Gemini rule SHALL still apply.

#### Scenario: Template-backed easy launch uses stored instance name and workdir
- **WHEN** launch template `alice` targets specialist `cuda-coder`
- **AND WHEN** `alice` stores default managed-agent name `alice` and default workdir `/repos/alice-cuda`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --template alice`
- **THEN** the launch uses specialist `cuda-coder`
- **AND THEN** the launch uses managed-agent name `alice` and runtime workdir `/repos/alice-cuda`

#### Scenario: Direct CLI overrides still win for template-backed easy launch
- **WHEN** launch template `alice` stores auth override `alice-creds` and workdir `/repos/alice-cuda`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --template alice --auth breakglass --workdir /tmp/debug`
- **THEN** the resulting launch uses auth bundle `breakglass`
- **AND THEN** the resulting launch records `/tmp/debug` as the runtime workdir instead of the template default

### Requirement: Easy instance inspection reports launch-template origin when available
When a managed-agent instance was launched from a project-easy launch template, `project easy instance list` and `project easy instance get` SHALL report that originating launch-template identity when it is resolvable from runtime-backed state.

The instance inspection surface SHALL continue to report the originating specialist when available.

#### Scenario: Easy instance get reports both template origin and specialist origin
- **WHEN** instance `alice` was launched from launch template `alice`
- **AND WHEN** that template targets specialist `cuda-coder`
- **AND WHEN** an operator runs `houmao-mgr project easy instance get --name alice`
- **THEN** the command reports launch template `alice` as the originating reusable launch profile
- **AND THEN** it also reports specialist `cuda-coder` as the underlying reusable source
