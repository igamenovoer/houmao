## ADDED Requirements

### Requirement: `project easy profile create/list/get/remove` manages specialist-backed easy profiles
`houmao-mgr project easy profile create --name <profile> --specialist <specialist>` SHALL persist one reusable easy profile that targets exactly one existing specialist.

Easy profiles SHALL be specialist-backed birth-time launch configuration owned by the easy lane.

When no active project overlay exists for the caller and no stronger overlay selection override is supplied, `project easy profile create` SHALL ensure `<cwd>/.houmao` exists before persisting profile state.

`project easy profile list`, `get`, and `remove` SHALL resolve the active overlay through the shared non-creating project-aware resolver and SHALL fail clearly when no active overlay exists.

`project easy profile get --name <profile>` SHALL report the source specialist plus the stored easy-profile launch defaults.

`project easy profile remove --name <profile>` SHALL remove only the profile definition and SHALL NOT remove the referenced specialist only because that specialist was the profile source.

#### Scenario: Easy profile create bootstraps the missing overlay on demand
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist cuda-coder`
- **THEN** the command ensures `<cwd>/.houmao` exists before storing the profile
- **AND THEN** the persisted profile lands in the resulting project-local catalog and compatibility projection

#### Scenario: Easy profile remove preserves the referenced specialist
- **WHEN** easy profile `alice` targets specialist `cuda-coder`
- **AND WHEN** an operator runs `houmao-mgr project easy profile remove --name alice`
- **THEN** the command removes the persisted `alice` profile
- **AND THEN** it does not remove specialist `cuda-coder` only because `alice` referenced it

### Requirement: `project easy instance launch` supports easy-profile-backed launch
`houmao-mgr project easy instance launch` SHALL support selecting a reusable easy profile through `--profile <profile>`.

`--profile` and `--specialist` SHALL be mutually exclusive on this surface.

When `--profile` is used, the command SHALL derive the source specialist from the stored profile, SHALL apply easy-profile defaults before direct CLI overrides, and SHALL still use the selected project overlay as the authoritative source context.

When a selected profile stores a default managed-agent name, the command MAY omit `--name` and SHALL use the profile-owned default identity.

When a selected profile stores workdir, auth override, mailbox config, or launch posture, those values SHALL apply unless the operator supplies a direct launch-time override.

If the selected profile resolves to a Gemini specialist, the existing headless-only Gemini rule SHALL still apply.

#### Scenario: Easy-profile-backed launch uses stored instance name and workdir
- **WHEN** easy profile `alice` targets specialist `cuda-coder`
- **AND WHEN** `alice` stores default managed-agent name `alice` and default workdir `/repos/alice-cuda`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile alice`
- **THEN** the launch uses specialist `cuda-coder`
- **AND THEN** the launch uses managed-agent name `alice` and runtime workdir `/repos/alice-cuda`

#### Scenario: Direct CLI overrides still win for easy-profile-backed launch
- **WHEN** easy profile `alice` stores auth override `alice-creds` and workdir `/repos/alice-cuda`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile alice --auth breakglass --workdir /tmp/debug`
- **THEN** the resulting launch uses auth bundle `breakglass`
- **AND THEN** the resulting launch records `/tmp/debug` as the runtime workdir instead of the profile default

### Requirement: Easy instance inspection reports easy-profile origin when available
When a managed-agent instance was launched from a project-easy profile, `project easy instance list` and `project easy instance get` SHALL report that originating easy-profile identity when it is resolvable from runtime-backed state.

The instance inspection surface SHALL continue to report the originating specialist when available.

#### Scenario: Easy instance get reports both easy-profile origin and specialist origin
- **WHEN** instance `alice` was launched from easy profile `alice`
- **AND WHEN** that profile targets specialist `cuda-coder`
- **AND WHEN** an operator runs `houmao-mgr project easy instance get --name alice`
- **THEN** the command reports easy profile `alice` as the originating reusable birth-time configuration
- **AND THEN** it also reports specialist `cuda-coder` as the underlying reusable source
