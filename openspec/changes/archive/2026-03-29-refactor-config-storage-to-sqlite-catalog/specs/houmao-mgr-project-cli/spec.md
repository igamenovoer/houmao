## MODIFIED Requirements

### Requirement: `houmao-mgr project init` bootstraps one repo-local `.houmao` overlay
`houmao-mgr project init` SHALL treat the caller's current working directory as the target project root in v1.

A successful init SHALL create:

- `<project-root>/.houmao/`
- `<project-root>/.houmao/houmao-config.toml`
- `<project-root>/.houmao/.gitignore`
- `<project-root>/.houmao/catalog.sqlite`
- managed project-local content roots required by the catalog-backed overlay contract

The generated `.houmao/.gitignore` SHALL ignore all content under `.houmao/` and the command SHALL NOT modify the repository root `.gitignore`.

The generated `.houmao/houmao-config.toml` SHALL remain the lightweight discovery anchor for project-aware Houmao defaults, but the generated project-local catalog SHALL become the canonical semantic project-local configuration store.

The generated project-local content roots SHALL provide the managed file-backed storage needed for large text and tree-shaped payloads such as prompts, auth files, setup bundles, and skill packages.

When the target project overlay already exists and remains compatible, `project init` SHALL validate the existing overlay and preserve compatible local payload content rather than overwriting it.

#### Scenario: Operator initializes a catalog-backed local Houmao overlay
- **WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **THEN** the command creates `/repo/app/.houmao/houmao-config.toml`
- **AND THEN** it creates `/repo/app/.houmao/.gitignore` without editing `/repo/app/.gitignore`
- **AND THEN** it creates `/repo/app/.houmao/catalog.sqlite`
- **AND THEN** it creates the managed project-local content roots required by the catalog-backed overlay contract

#### Scenario: Re-running init preserves compatible local content
- **WHEN** an operator already has a compatible project-local catalog-backed overlay with local prompt or auth payload files
- **AND WHEN** they run `houmao-mgr project init` again inside `/repo/app`
- **THEN** the command validates the existing project overlay
- **AND THEN** it does not delete or overwrite that compatible local content only because init was re-run

### Requirement: `houmao-mgr project init` bootstraps project source roots but does not create optional project workflow state by default
`houmao-mgr project init` SHALL bootstrap the base project overlay, the project-local catalog, and the managed content roots required by the catalog-backed project contract without creating optional compatibility metadata or mailbox state by default.

At minimum, `project init` SHALL NOT create:

- `.houmao/agents/compatibility-profiles/`
- `.houmao/mailbox/`
- optional compatibility projection trees only because init was run

The catalog-backed overlay MAY create the managed content roots required by the base project-local storage contract even though those roots are not optional workflow state.

#### Scenario: Project init leaves optional roots opt-in
- **WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **THEN** the command creates the base `.houmao/` overlay, the project-local catalog, and the managed content roots required by that overlay contract
- **AND THEN** it does not create `/repo/app/.houmao/agents/compatibility-profiles/` only because init was run
- **AND THEN** it does not create `/repo/app/.houmao/mailbox/` only because init was run
- **AND THEN** it does not create an optional compatibility projection tree only because init was run

### Requirement: Project-aware agent-definition defaults discover the nearest project config
Project-aware command paths that need project-local semantic configuration and are invoked without explicit override SHALL resolve the active project overlay from the nearest ancestor `.houmao/houmao-config.toml`.

When a project config is discovered for a catalog-backed overlay, project-aware build and launch paths SHALL resolve project-local semantic configuration from that overlay's catalog and managed content store rather than assuming `.houmao/agents/` is the authoritative source tree.

Legacy fallback behavior outside a discovered project overlay MAY still use the existing filesystem-backed `agents/` tree contract.

At minimum, this project-aware defaulting SHALL apply to:

- `houmao-mgr project status`
- `houmao-mgr brains build`
- preset-backed `houmao-mgr agents launch`

#### Scenario: Build from a repo subdirectory uses the discovered project catalog
- **WHEN** `/repo/.houmao/houmao-config.toml` exists for a catalog-backed overlay
- **AND WHEN** an operator runs `houmao-mgr brains build ...` from `/repo/subdir/nested` without explicit project-local override
- **THEN** the command resolves the effective project-local semantic configuration from `/repo/.houmao/`
- **AND THEN** project-aware build resolution uses the discovered project catalog rather than assuming `/repo/.houmao/agents/` is the authoritative project-local source tree

#### Scenario: Missing project config still falls back outside project overlays
- **WHEN** no ancestor `.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs a project-aware build or launch path from `/repo`
- **THEN** the system falls back to the non-project filesystem-backed resolution path
- **AND THEN** the absence of a project overlay does not require a project-local catalog

### Requirement: `houmao-mgr project status` reports discovered local project state
`houmao-mgr project status` SHALL report whether a repo-local Houmao overlay was discovered from the caller's current working directory.

At minimum, the reported payload SHALL include:

- whether a project overlay was found,
- the resolved project root when found,
- the resolved config path when found,
- the resolved project-local catalog path when found.

When no project overlay is discovered, the command SHALL report that local project state is not initialized instead of silently pretending a project config exists.

#### Scenario: Status reports the nearest discovered catalog-backed overlay
- **WHEN** `/repo/.houmao/houmao-config.toml` exists for a catalog-backed overlay
- **AND WHEN** an operator runs `houmao-mgr project status` from `/repo/subdir`
- **THEN** the command reports `/repo` as the resolved project root
- **AND THEN** it reports `/repo/.houmao/houmao-config.toml` as the discovered config path
- **AND THEN** it reports the resolved project-local catalog path under that overlay

#### Scenario: Status reports missing project overlay clearly
- **WHEN** no ancestor `.houmao/houmao-config.toml` exists for the caller
- **AND WHEN** an operator runs `houmao-mgr project status`
- **THEN** the command reports that no local Houmao project overlay was discovered
- **AND THEN** it does not claim that a project-local catalog already exists
