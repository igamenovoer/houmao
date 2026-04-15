## MODIFIED Requirements

### Requirement: `houmao-mgr project init` bootstraps one repo-local `.houmao` overlay
`houmao-mgr project init` SHALL resolve the target overlay root in this order:

1. `HOUMAO_PROJECT_OVERLAY_DIR` when set,
2. default `<cwd>/.houmao`.

When `HOUMAO_PROJECT_OVERLAY_DIR` is set, it SHALL be an absolute path.
When `HOUMAO_PROJECT_OVERLAY_DIR` is set, `project init` SHALL bootstrap the overlay directly under that selected directory rather than under the caller's current working directory.

A successful init SHALL create:

- `<overlay-root>/`
- `<overlay-root>/houmao-config.toml`
- `<overlay-root>/.gitignore`
- `<overlay-root>/catalog.sqlite`
- managed project-local content roots required by the catalog-backed overlay contract

The generated `.gitignore` SHALL ignore all content under the selected overlay root and the command SHALL NOT modify a repository root `.gitignore` merely because the overlay root lives inside that repository.

The generated `houmao-config.toml` SHALL remain the lightweight discovery anchor for project-aware Houmao defaults, but the generated project-local catalog SHALL become the canonical semantic project-local configuration store.
The generated `houmao-config.toml` SHALL carry `paths.agent_def_dir` as compatibility-projection configuration for file-tree consumers, and when the config is first created `project init` SHALL set `paths.agent_def_dir = "agents"`.

The generated project-local content roots SHALL provide the managed file-backed storage needed for large text and tree-shaped payloads such as prompts, auth files, setup bundles, and skill packages.

When the target project overlay already exists and remains compatible, `project init` SHALL validate the existing overlay and preserve compatible local payload content rather than overwriting it.
When `houmao-config.toml` already exists and remains compatible, `project init` SHALL resolve `paths.agent_def_dir` relative to the selected overlay root for validation instead of assuming only `<overlay-root>/agents/`.

#### Scenario: Operator initializes the default local Houmao overlay
- **WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `/repo/app/.houmao/houmao-config.toml` does not already exist
- **THEN** the command creates `/repo/app/.houmao/houmao-config.toml`
- **AND THEN** the written config sets `paths.agent_def_dir = "agents"`
- **AND THEN** it creates `/repo/app/.houmao/.gitignore` without editing `/repo/app/.gitignore`
- **AND THEN** it creates `/repo/app/.houmao/catalog.sqlite`
- **AND THEN** it creates the managed project-local content roots required by the catalog-backed overlay contract

#### Scenario: Env override redirects init to the selected overlay directory
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** an operator runs `houmao-mgr project init` from `/repo/app`
- **THEN** the command creates `/tmp/ci-overlay/houmao-config.toml`
- **AND THEN** it creates `/tmp/ci-overlay/catalog.sqlite`
- **AND THEN** it does not instead bootstrap `/repo/app/.houmao/`

#### Scenario: Relative env override fails clearly
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=relative/overlay`
- **AND WHEN** an operator runs `houmao-mgr project init`
- **THEN** the command fails explicitly
- **AND THEN** the error explains that `HOUMAO_PROJECT_OVERLAY_DIR` must be an absolute path

#### Scenario: Re-running init preserves compatible local auth state
- **WHEN** an operator already has a compatible local overlay and `/repo/app/.houmao/custom-agents/tools/claude/auth/personal/`
- **AND WHEN** `/repo/app/.houmao/houmao-config.toml` resolves `paths.agent_def_dir = "custom-agents"`
- **AND WHEN** they run `houmao-mgr project init` again inside `/repo/app`
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **THEN** the command validates the existing project overlay
- **AND THEN** it does not delete or overwrite that existing local auth bundle only because init was re-run

### Requirement: `houmao-mgr project init` bootstraps project source roots but does not create optional project workflow state by default
`houmao-mgr project init` SHALL bootstrap the base project overlay, the project-local catalog, and the managed content roots required by the catalog-backed project contract without creating optional compatibility metadata or mailbox state.

At minimum, `project init` SHALL NOT create:

- `.houmao/agents/compatibility-profiles/`
- `.houmao/mailbox/`
- optional compatibility projection trees only because init was run

The catalog-backed overlay MAY create the managed content roots required by the base project-local storage contract even though those roots are not optional workflow state.

`houmao-mgr project init` SHALL NOT expose a public flag, option, or documented workflow for pre-creating `.houmao/agents/compatibility-profiles/`.

#### Scenario: Project init leaves optional roots uncreated
- **WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **THEN** the command creates the base `.houmao/` overlay, the project-local catalog, and the managed content roots required by that overlay contract
- **AND THEN** it does not create `/repo/app/.houmao/agents/compatibility-profiles/` only because init was run
- **AND THEN** it does not create `/repo/app/.houmao/mailbox/` only because init was run
- **AND THEN** it does not create an optional compatibility projection tree only because init was run

#### Scenario: Existing config with a custom relative compatibility root is respected
- **WHEN** `/repo/app/.houmao/houmao-config.toml` already exists
- **AND WHEN** that config resolves `paths.agent_def_dir = "custom-agents"`
- **AND WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **THEN** the command uses `/repo/app/.houmao/custom-agents/` as the resolved compatibility-projection root for validation
- **AND THEN** it does not silently replace that configured root with `/repo/app/.houmao/agents/`

#### Scenario: Compatibility-profile bootstrap flag is not a public project init option
- **WHEN** an operator runs `houmao-mgr project init --help`
- **THEN** the help output does not list `--with-compatibility-profiles`
- **AND WHEN** an operator runs `houmao-mgr project init --with-compatibility-profiles`
- **THEN** the command fails as an unsupported option
