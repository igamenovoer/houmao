## ADDED Requirements

### Requirement: GitHub releases publish Houmao distributions to PyPI through a repository-owned workflow
The repository SHALL provide a GitHub Actions workflow that publishes Houmao release distributions to PyPI when a GitHub release is published.

That workflow SHALL:

- trigger from GitHub release publication rather than local maintainer machines,
- build both a wheel and a source distribution for the released version,
- publish the exact built distributions produced by the workflow run,
- use PyPI trusted publishing through GitHub OIDC rather than requiring a local `.env` token or repository-stored long-lived PyPI credential as the default path.

#### Scenario: Stable GitHub release publishes the package
- **WHEN** a maintainer publishes a stable GitHub release for Houmao from the repository
- **THEN** the release workflow builds a wheel and source distribution for that release
- **AND THEN** the workflow publishes those built distributions to PyPI through the repository-owned publish job

#### Scenario: Publish job uses trusted publishing
- **WHEN** the release workflow runs its PyPI publish job
- **THEN** the job obtains authentication through GitHub-to-PyPI trusted publishing
- **AND THEN** the default publication path does not require the temporary local `.env` PyPI token to exist on the runner

### Requirement: Public release artifacts contain only intended package release contents
The package build configuration SHALL constrain Houmao public release artifacts to the intended package release surface.

The wheel and source distribution SHALL include the runtime package, required package metadata, and other explicitly intended release files, and SHALL exclude unrelated repository content such as local reference checkouts, repo-internal context trees, or secret-bearing local files.

#### Scenario: Source distribution excludes repository-only content
- **WHEN** a maintainer builds release distributions for Houmao
- **THEN** the resulting source distribution does not include unrelated repository directories such as local reference checkouts or internal context trees
- **AND THEN** the source distribution still includes the files required to build and describe the public package

#### Scenario: Release artifacts exclude local secrets
- **WHEN** release distributions are built from the repository
- **THEN** files such as `.env`, credential payloads, and auth files are excluded from the published artifacts

### Requirement: Maintainers can configure and execute the first public release flow
The repository SHALL document the maintainer setup and execution steps required to publish Houmao to PyPI for the first public release.

That documentation SHALL cover:

- the GitHub workflow used for publication,
- the GitHub environment and PyPI trusted publisher configuration expected by that workflow,
- the release preparation checks required before publication,
- the release creation flow for the first public version `0.1.0`.

#### Scenario: Maintainer configures trusted publishing for the repository
- **WHEN** a maintainer prepares the repository for PyPI publication
- **THEN** the repository documentation tells the maintainer how to configure the expected GitHub workflow and environment name in PyPI trusted publishing
- **AND THEN** the maintainer can complete repository-side setup without relying on undocumented local-only steps

#### Scenario: Maintainer cuts the first public release
- **WHEN** the repository is configured for trusted publishing and version `0.1.0` is ready to ship
- **THEN** the maintainer can follow the documented release procedure to create the first public GitHub release
- **AND THEN** that release procedure is compatible with the repository-owned PyPI publishing workflow
