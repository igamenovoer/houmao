## MODIFIED Requirements

### Requirement: Local-only auth bundles

Auth bundles SHALL be stored under `agents/tools/<tool>/auth/<auth>/` and MUST be local-only whenever they contain secrets. Brain construction SHALL project the selected auth bundle into the runtime tool home according to the selected tool adapter's projection contract.

One tool MAY provide multiple auth bundles, and auth identifiers SHALL be unique only within that tool's `auth/` namespace.

Tracked fixture auth files kept under repository-owned agent-definition examples or test fixtures SHALL remain secret-free. If the repo needs a tracked auth-shaped file for fixture structure, that tracked file SHALL use empty-object stubs, inert placeholders, or bootstrap templates with no live credential material.

#### Scenario: Auth bundle is selected without committing secrets

- **WHEN** a brain is constructed selecting auth bundle `<auth>`
- **THEN** the runtime tool home SHALL contain the tool's auth material projected from `agents/tools/<tool>/auth/<auth>/`
- **AND THEN** the project SHALL NOT require committing secret material to version control

#### Scenario: Setup and auth remain independent axes

- **WHEN** a tool offers multiple setup bundles and multiple auth bundles
- **THEN** the system MAY combine one selected setup with one selected auth for the same tool
- **AND THEN** selecting one setup does not imply exactly one auth bundle

#### Scenario: Tracked fixture auth file uses secret-free stub content

- **WHEN** the repository tracks one auth-shaped file inside a fixture auth bundle for structural test coverage
- **THEN** that tracked file SHALL contain only secret-free placeholder, stub, or bootstrap-template content
- **AND THEN** live tokens or API keys SHALL remain in ignored local-only files instead
