## ADDED Requirements

### Requirement: User-facing repository metadata and guidance use the canonical Houmao identity
The repository SHALL present its user-facing metadata, contributor guidance, assistant instruction files, docstrings, CLI help, and shipped documentation using the canonical `Houmao` identity, the `houmao` Python package namespace, the `houmao-cli` runtime-management CLI name, the `houmao-cao-server` launcher CLI name, the `houmao.agents.realm_controller` runtime module surface, the `houmao.cao.tools.cao_server_launcher` launcher module surface, and the current GitHub repository URL.

User-facing guidance includes package metadata links, contributor instructions, AI-assistant guidance files, exported docstrings, CLI help/output, and repo-owned instructional docs that describe the current public surface.

#### Scenario: Package metadata and active guidance use the current GitHub repository identity
- **WHEN** a maintainer inspects active repository metadata or active guidance
- **THEN** GitHub repository references use the current canonical `houmao` repository URL
- **AND THEN** active guidance does not teach the old `gig-agents` repository slug as the current source of truth

#### Scenario: Assistant guidance files teach the current public names
- **WHEN** a contributor or AI assistant reads repo-owned instruction files for project overview, CLI entrypoints, or runtime paths
- **THEN** those files describe the project as `Houmao`
- **AND THEN** they teach `houmao-cli`, `houmao-cao-server`, `houmao.agents.realm_controller`, and `houmao.cao.tools.cao_server_launcher` as the canonical active surfaces

#### Scenario: User-facing source and CLI help avoid historical identifiers
- **WHEN** a user inspects shipped source docstrings or runs repo-owned CLI help
- **THEN** the visible names and examples use only the current Houmao identity
- **AND THEN** they do not expose `gig_agents`, `gig-agents`, or `gig-cao-server`

### Requirement: Canonical source-package and module-entrypoint surfaces use `houmao`
The repository SHALL keep its active Python source package under `src/houmao/`, and repo-owned code, tests, scripts, packaged-resource lookups, runnable documentation, and user-facing docstrings/help text SHALL use `houmao...` import and module-entrypoint paths as the current contract.

The repository SHALL NOT present `src/gig_agents/`, `gig_agents...`, or `gig-*` CLI names as the canonical current package surface outside clearly non-user-facing historical or provenance-preserving contexts.

#### Scenario: Build metadata and source layout point at the canonical package root
- **WHEN** a maintainer inspects the repository build configuration or source layout
- **THEN** package discovery, wheel/sdist inclusion, and entrypoint targets point at `src/houmao/` and `houmao...`
- **AND THEN** active build metadata does not describe `src/gig_agents/` as the current package root

#### Scenario: Repo-owned runnable examples use `houmao` module paths
- **WHEN** a developer follows repo-owned module invocation examples, scripts, or tests that launch Python modules directly
- **THEN** those examples use `python -m houmao...` or `from houmao... import ...`
- **AND THEN** active examples do not treat `python -m gig_agents...` or `from gig_agents...` as the supported current contract

#### Scenario: User-facing CLI binaries use Houmao names
- **WHEN** a developer inspects the published CLI entrypoints or command examples
- **THEN** the repo presents `houmao-cli` and `houmao-cao-server` as the supported user-facing binaries
- **AND THEN** command examples do not teach `gig-cao-server` as a current launcher command

### Requirement: Active instructional guidance uses portable execution paths by default
Repo-owned active instructional guidance SHALL use repo-relative paths or explicit placeholders such as `<repo-root>` when describing commands, files, or execution flows that the reader is expected to follow directly.

Active instructional guidance SHALL NOT present one maintainer's host-specific absolute checkout path as the default execution contract when a repo-relative or placeholder form is sufficient.

#### Scenario: Runnable guidance avoids host-specific absolute checkout paths
- **WHEN** a developer follows active repo-owned instructions for commands, file inspection, or local workflows
- **THEN** the documented paths are expressed as repo-relative locations or explicit placeholders
- **AND THEN** the guidance does not require the reader to mirror a host-specific `/data/.../gig-agents/...` checkout path unless that path is explicitly part of observed diagnostic output

### Requirement: Non-user-facing historical and provenance references may preserve former names and observed paths
The repository SHALL allow non-user-facing historical, provenance, archive, review, and observed-diagnostic materials to retain former repo names, former module names, or checkout-local absolute paths when those references are preserving what happened rather than defining the current active contract.

Those preserved references SHALL NOT be treated as the canonical source of truth for current metadata, contributor guidance, shipped source/docstrings, CLI help, or user-facing instructional docs.

#### Scenario: Historical references remain explicit without redefining the active contract
- **WHEN** a maintainer reads an archive, internal review document, or observed diagnostic note that is not part of the shipped user-facing surface
- **THEN** that artifact may retain earlier names such as `gig-agents` or `brain_launch_runtime` and original observed filesystem paths
- **AND THEN** active-facing metadata and current instructional guidance elsewhere in the repo still define the canonical Houmao identity
