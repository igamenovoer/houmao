# agent-fixture-contracts Specification

## Purpose
TBD - created by archiving change split-agent-fixtures-by-contract. Update Purpose after archive.
## Requirements
### Requirement: Repository SHALL publish separate maintained fixture families by contract
The repository SHALL treat tracked plain agent-definition fixtures, local-only auth bundles, and project-overlay or demo-local generated agent trees as separate maintained fixture families rather than as one canonical shared tree.

The maintained fixture families SHALL include at minimum:

- `tests/fixtures/plain-agent-def/` for explicit plain `--agent-def-dir` workflows,
- `tests/fixtures/auth-bundles/` for local-only host credential bundles,
- fresh `.houmao/` overlays or demo-owned tracked `inputs/agents/` trees for maintained project-aware and demo-local workflows.

The repository SHALL NOT describe one broad `tests/fixtures/agents/` tree as the maintained canonical source for all three families.

#### Scenario: Maintainer can discover the split fixture families
- **WHEN** a maintainer inspects the repository fixture guidance
- **THEN** the guidance identifies `tests/fixtures/plain-agent-def/` as the maintained plain direct-dir fixture root
- **AND THEN** it identifies `tests/fixtures/auth-bundles/` as the maintained local-only auth fixture root
- **AND THEN** it describes project overlays and demo-owned `inputs/agents/` trees as separate maintained sources for project-aware and demo-local workflows

#### Scenario: Old broad fixture root is not described as canonical
- **WHEN** a maintainer reads the maintained fixture guidance after this change
- **THEN** that guidance does not present one broad `tests/fixtures/agents/` tree as the maintained canonical agent-definition root for every workflow

### Requirement: Plain direct-dir fixture root SHALL match the current filesystem-backed contract
The tracked plain direct-dir fixture root at `tests/fixtures/plain-agent-def/` SHALL match the current maintained plain filesystem-backed agent-definition contract.

That root SHALL include at minimum:

- `skills/`
- `roles/`
- `presets/`
- `launch-profiles/`
- `tools/<tool>/adapter.yaml`
- `tools/<tool>/setups/<setup>/...`
- `tools/<tool>/auth/` roots for supported tools

When a plain direct-dir workflow populates auth bundles beneath that root, those auth bundle directories SHALL continue to use human-readable names under `tools/<tool>/auth/<name>/`.

The tracked plain direct-dir fixture root SHALL remain secret-free and SHALL NOT require committed plaintext auth contents.

#### Scenario: Maintainer can inspect the plain direct-dir fixture root
- **WHEN** a maintainer inspects `tests/fixtures/plain-agent-def/`
- **THEN** they find `presets/`, `launch-profiles/`, `roles/`, `skills/`, and tool-scoped `adapter.yaml`, `setups/`, and `auth/` roots
- **AND THEN** the tracked fixture root remains secret-free

#### Scenario: Plain direct-dir auth naming remains human-readable
- **WHEN** a plain filesystem-backed workflow creates or mutates auth bundles under the maintained direct-dir fixture contract
- **THEN** those bundles live under `tools/<tool>/auth/<name>/`
- **AND THEN** the contract does not require opaque project-overlay bundle refs for that plain direct-dir lane

### Requirement: Local auth-bundle fixtures SHALL be maintained separately from agent-definition fixtures
The repository SHALL maintain local-only credential fixtures under `tests/fixtures/auth-bundles/<tool>/<bundle>/...` instead of treating them as part of one canonical tracked agent-definition tree.

This fixture family SHALL own:

- local-only env and credential files for maintained tool lanes,
- maintained bundle names such as Claude `official-login`,
- repository guidance for encrypting, restoring, and handling local-only credential material.

Maintained demos, smoke flows, and manual helpers that need host-local credentials SHALL source them from `tests/fixtures/auth-bundles/` and SHALL materialize any required run-local aliasing separately.

#### Scenario: Maintainer can inspect the dedicated auth-bundle fixture lane
- **WHEN** a maintainer inspects the local credential fixture guidance
- **THEN** the guidance points them to `tests/fixtures/auth-bundles/<tool>/<bundle>/...`
- **AND THEN** it does not claim that the parent directory is itself a full canonical agent-definition source tree

#### Scenario: Maintained helper consumes auth from the dedicated auth-bundle lane
- **WHEN** a maintained demo or smoke helper needs one host-local credential bundle
- **THEN** it sources that bundle from `tests/fixtures/auth-bundles/<tool>/<bundle>/...`
- **AND THEN** it materializes any run-local auth alias or copied direct-dir auth path separately from that source lane

### Requirement: Maintained project-aware and demo-local flows SHALL not treat the plain direct-dir fixture root as a project-overlay substitute
Maintained project-aware tests, demos, and helpers SHALL use either fresh `.houmao/` overlays or demo-owned tracked `inputs/agents/` trees for their agent-definition source, and SHALL NOT treat `tests/fixtures/plain-agent-def/` as a substitute for the project-overlay compatibility projection.

Maintained project-aware flows MAY still source host-local credentials from `tests/fixtures/auth-bundles/`, but they SHALL materialize those credentials into run-local or overlay-local locations using the workflow's own contract.

#### Scenario: Maintained project-aware workflow uses a fresh overlay or demo-owned tree
- **WHEN** a maintainer runs one supported project-aware demo or test helper
- **THEN** that workflow builds from a fresh `.houmao/` overlay or a demo-owned tracked `inputs/agents/` tree
- **AND THEN** it does not point its maintained agent-definition source directly at `tests/fixtures/plain-agent-def/`

#### Scenario: Maintained project-aware workflow sources auth separately
- **WHEN** a maintained project-aware demo or helper needs local credentials
- **THEN** it may source those credentials from `tests/fixtures/auth-bundles/`
- **AND THEN** it materializes them into the workflow's run-local or overlay-local structure rather than treating the direct-dir fixture root as the credential source of truth

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

