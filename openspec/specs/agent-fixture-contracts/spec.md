# agent-fixture-contracts Specification

## Purpose
TBD - created by archiving change split-agent-fixtures-by-contract. Update Purpose after archive.
## Requirements

### Requirement: Repository SHALL publish separate maintained fixture families by contract

The repository SHALL distinguish tracked plain seed assets, tracked generic launch descriptors, external local credentials, and generated project/demo state. Maintained guidance SHALL identify `tests/fixtures/plain-agent-def/`, `tests/fixtures/agent-launch/`, and the external local store as separate owners. Neither `tests/fixtures/agents/` nor `tests/fixtures/auth-bundles/` SHALL be a maintained shared live source.

#### Scenario: Maintainer can discover the split fixture families
- **WHEN** a maintainer inspects repository fixture guidance
- **THEN** the guidance identifies the plain seed and generic launch descriptor roots
- **AND THEN** it identifies the external local credential store and private generated run roots separately
- **AND THEN** it describes project overlays and demo-owned tracked inputs as distinct seed/launch contracts

#### Scenario: Old broad fixture root is not described as canonical
- **WHEN** a maintainer reads maintained fixture guidance
- **THEN** it does not present `tests/fixtures/agents/` as a canonical source or `tests/fixtures/auth-bundles/` as a supported live credential source

### Requirement: Plain direct-dir fixture root SHALL match the current filesystem-backed contract

The tracked `tests/fixtures/plain-agent-def/` root SHALL retain `skills/`, `roles/`, `presets/`, `launch-profiles/`, and tool-scoped `adapter.yaml`, `setups/`, and empty auth mount roots. It SHALL remain secret-free. Populated plain test roots SHALL be external run-local copies, with human-readable auth names under `tools/<tool>/auth/<name>/`; the tracked seed root SHALL NOT receive live credentials.

#### Scenario: Maintainer can inspect the plain direct-dir fixture root
- **WHEN** a maintainer inspects `tests/fixtures/plain-agent-def/`
- **THEN** they find the supported preset, launch-profile, role, skill, adapter, setup, and auth mount layout
- **AND THEN** the tracked root contains no live credential material

#### Scenario: Plain direct-dir auth naming remains human-readable
- **WHEN** a plain test workflow populates a copied native-agent root outside the checkout
- **THEN** its auth selections use `tools/<tool>/auth/<name>/`
- **AND THEN** no opaque project-overlay bundle ref is required for that plain lane

### Requirement: Local auth-bundle fixtures SHALL be maintained separately from agent-definition fixtures

Reusable live test credentials SHALL live in the external local credential store, separately from tracked seed assets and launch descriptors. Maintained workflows SHALL resolve explicitly selected credentials there and materialize private run-local copies. Guidance SHALL explain discovery, import, backup, and restoration without account-specific defaults or committed auth files.

#### Scenario: Maintainer can inspect the dedicated auth-bundle fixture lane
- **WHEN** a maintainer reads credential fixture guidance
- **THEN** it explains the external local store, supported tool-specific files, and discovery/import commands
- **AND THEN** it does not treat that store as a full agent-definition source tree

#### Scenario: Maintained helper consumes auth from the dedicated auth-bundle lane
- **WHEN** a maintained demo or smoke selects a native login bundle
- **THEN** it reads the selected bundle from the external store and imports a run-local copy
- **AND THEN** it does not modify the reusable source bundle through a live runtime alias

#### Scenario: API-key test needs no native login bundle
- **WHEN** a self-hosted or cloud API case has its required key and endpoint configuration
- **THEN** the helper can prepare that case without a named native login bundle

### Requirement: Maintained project-aware and demo-local flows SHALL not treat the plain direct-dir fixture root as a project-overlay substitute

Maintained project-aware tests, demos, and helpers SHALL use fresh project overlays or demo-owned tracked inputs as seed sources. Credential-bearing project/demo state SHALL be external to the checkout. Local credentials SHALL be selected separately and imported into that private run state; the plain direct-dir seed root SHALL NOT substitute for a project overlay or credential store.

#### Scenario: Maintained project-aware workflow uses a fresh overlay or demo-owned tree
- **WHEN** a supported project-aware demo or test helper prepares a run
- **THEN** it creates a fresh overlay from selected tracked seed inputs outside the checkout
- **AND THEN** it does not use `tests/fixtures/plain-agent-def/` as a mutable project overlay

#### Scenario: Maintained project-aware workflow sources auth separately
- **WHEN** a maintained project-aware workflow selects local native credentials
- **THEN** it imports those credentials from the external store into the run-local overlay
- **AND THEN** live auth files remain outside both tracked fixture roots and repository-local output directories

### Requirement: Plain direct-dir fixture guidance SHALL stay aligned with scoped CLI and native-root terminology
Repository guidance inside `tests/fixtures/plain-agent-def/` SHALL describe that fixture as tracked, secret-free plain native-agent seed material for direct internals, copied temp roots, and project-overlay seeding.

That guidance SHALL use the current fixture-relative paths:

- `roles/<role>/system-prompt.md`
- `skills/<skill>/SKILL.md`
- `presets/<preset>.yaml`
- `launch-profiles/<profile>.yaml`
- `tools/<tool>/adapter.yaml`
- `tools/<tool>/setups/<setup>/...`
- `tools/<tool>/auth/<auth>/...`

That guidance SHALL NOT describe stale `agents/roles`, `agents/skills`, retired `brains/`, or retired `blueprints/` paths as current locations in this fixture root.

That guidance SHALL NOT present root-level `houmao-mgr agents launch`, `houmao-mgr agents stop`, or `houmao-mgr agents cleanup` as maintained public command paths.

When fixture guidance needs to discuss managed-agent lifecycle, it SHALL distinguish:

- project-backed birth through `houmao-mgr project agents launch`,
- selected-agent follow-up through `houmao-mgr agents single --agent-id <id> ...` or `houmao-mgr agents single --agent-name <name> ...`,
- current-session operations through `houmao-mgr agents self ...`,
- direct native-agent build plumbing through `houmao-mgr internals native-agent brain build`.

#### Scenario: Maintainer reads the plain fixture workflow guidance
- **WHEN** a maintainer reads `tests/fixtures/plain-agent-def/README.md` and `tests/fixtures/plain-agent-def/MIGRATION.md`
- **THEN** the guidance describes direct native-agent build usage through `houmao-mgr internals native-agent brain build`
- **AND THEN** it does not instruct the maintainer to launch with root-level `houmao-mgr agents launch`
- **AND THEN** it points public managed-agent birth to `houmao-mgr project agents launch` when a launch is needed

#### Scenario: Maintainer reads fixture role and skill guidance
- **WHEN** a maintainer reads `tests/fixtures/plain-agent-def/roles/README.md` and `tests/fixtures/plain-agent-def/skills/README.md`
- **THEN** the guidance uses fixture-relative `roles/` and `skills/` terminology
- **AND THEN** it does not present `agents/roles/` or `agents/skills/` as the current paths inside the plain fixture root

#### Scenario: Server API smoke role avoids retired server wording
- **WHEN** a maintainer inspects the `server-api-smoke` fixture role documentation and system prompt
- **THEN** the role is described in terms of maintained managed-agent API or passive-server smoke validation
- **AND THEN** it does not describe the maintained smoke target as retired standalone `houmao-server`

### Requirement: Maintained managed-agent fixtures SHALL preserve the managed-launch agent system-skill default

When a maintained fixture prepares a manager-surface managed agent without an explicit system-skill opt-out, it SHALL leave the managed-launch system-skill policy at its default so the complete `agent` pack is installed in the runtime home.

The fixture SHALL NOT pass a system-skill disabling option for that default path. The prepared run metadata SHALL record whether the default pack or an explicit opt-out applies.

#### Scenario: Default managed preparation keeps the agent pack
- **WHEN** a maintainer prepares a manager-surface fixture run without selecting a system-skill opt-out
- **THEN** the generated specialist leaves `launch.system_skills` at the managed default
- **AND THEN** the launched runtime home receives the complete `agent` system-skill pack
- **AND THEN** the prepared run metadata records the default-pack choice

#### Scenario: Default preparation does not record a disabled policy
- **WHEN** a maintainer inspects a default manager-surface fixture run
- **THEN** its generated specialist does not contain `system_skills: {mode: none}`
- **AND THEN** its run metadata does not describe the run as having no Houmao system skills

### Requirement: Maintained managed-agent fixtures SHALL provide an explicit system-skill opt-out

The fixture SHALL provide an explicit opt-out for managed preparation cases that intentionally require a minimal runtime home. When the opt-out is selected, the fixture SHALL create the specialist with the disabling policy and SHALL record that choice in the prepared run metadata.

#### Scenario: Explicit opt-out prepares a minimal home
- **WHEN** a maintainer prepares a manager-surface fixture run with the system-skill opt-out
- **THEN** the generated specialist records `launch.system_skills.mode` as `none`
- **AND THEN** the prepared run metadata records the opt-out choice

#### Scenario: Opt-out documentation is discoverable
- **WHEN** a maintainer reads the maintained fixture guidance
- **THEN** it identifies the managed-launch `agent` pack as the default
- **AND THEN** it explains the explicit opt-out and when to use it
