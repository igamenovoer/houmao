# Spec Delta

## MODIFIED Requirements

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
