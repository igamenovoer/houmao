## ADDED Requirements

### Requirement: Project command group accepts explicit project directory selection
`houmao-mgr project` SHALL accept a group-level `--project-dir <dir>` option that applies to every nested project subcommand.

The supplied directory SHALL be interpreted as the human-facing project directory. The selected overlay root SHALL be `<project-dir>/.houmao`.

When `--project-dir` is supplied, project subcommands SHALL use that selected project directory instead of discovering a project from the process current working directory.

Stateful project subcommands SHALL fail clearly when the selected project directory does not contain an initialized Houmao overlay, except for `project init`, which SHALL create or validate the selected overlay.

#### Scenario: Explicit project directory selects credentials target
- **WHEN** `/repo-a/.houmao/houmao-config.toml` exists
- **AND WHEN** the operator runs `houmao-mgr project --project-dir /repo-a credentials codex list` from `/repo-b`
- **THEN** the command resolves `/repo-a/.houmao` as the active project overlay
- **AND THEN** it does not discover or use `/repo-b/.houmao`

#### Scenario: Omitted project directory still discovers by current working directory
- **WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** the operator runs `houmao-mgr project status` from `/repo/subdir`
- **THEN** the command discovers `/repo/.houmao` as the active project overlay

#### Scenario: Missing selected project fails for stateful command
- **WHEN** `/repo-a/.houmao/houmao-config.toml` does not exist
- **AND WHEN** the operator runs `houmao-mgr project --project-dir /repo-a specialist list`
- **THEN** the command fails clearly
- **AND THEN** the diagnostic tells the operator to run `houmao-mgr project --project-dir /repo-a init`

## MODIFIED Requirements

### Requirement: `houmao-mgr project init` bootstraps one repo-local `.houmao` overlay
`houmao-mgr project init` SHALL resolve the target overlay root in this order:

1. group-level `--project-dir <dir>` when supplied, resolving to `<dir>/.houmao`,
2. retained project-overlay environment selection when set for automation or internal workflows,
3. default `<cwd>/.houmao`.

When `--project-dir` is supplied, `project init` SHALL bootstrap the overlay under that project directory rather than under the caller's current working directory.
When retained environment selection is used, it SHALL be an absolute overlay path.
When retained environment selection is used, `project init` SHALL bootstrap the overlay directly under that selected directory rather than under the caller's current working directory.

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

#### Scenario: Operator initializes an explicitly selected project directory
- **WHEN** an operator runs `houmao-mgr project --project-dir /repo/app init` from `/tmp`
- **AND WHEN** `/repo/app/.houmao/houmao-config.toml` does not already exist
- **THEN** the command creates `/repo/app/.houmao/houmao-config.toml`
- **AND THEN** the written config sets `paths.agent_def_dir = "agents"`
- **AND THEN** it creates `/repo/app/.houmao/.gitignore` without editing `/repo/app/.gitignore`
- **AND THEN** it creates `/repo/app/.houmao/catalog.sqlite`
- **AND THEN** it creates the managed project-local content roots required by the catalog-backed overlay contract

#### Scenario: Operator initializes the default local Houmao overlay
- **WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **AND WHEN** no explicit project directory or retained env selection is supplied
- **AND WHEN** `/repo/app/.houmao/houmao-config.toml` does not already exist
- **THEN** the command creates `/repo/app/.houmao/houmao-config.toml`
- **AND THEN** the written config sets `paths.agent_def_dir = "agents"`
- **AND THEN** it creates `/repo/app/.houmao/.gitignore` without editing `/repo/app/.gitignore`
- **AND THEN** it creates `/repo/app/.houmao/catalog.sqlite`
- **AND THEN** it creates the managed project-local content roots required by the catalog-backed overlay contract

#### Scenario: Env override redirects init to the selected overlay directory
- **WHEN** retained project-overlay env selection points to `/tmp/ci-overlay`
- **AND WHEN** an operator runs `houmao-mgr project init` from `/repo/app`
- **THEN** the command creates `/tmp/ci-overlay/houmao-config.toml`
- **AND THEN** it creates `/tmp/ci-overlay/catalog.sqlite`
- **AND THEN** it does not instead bootstrap `/repo/app/.houmao/`

#### Scenario: Relative env override fails clearly
- **WHEN** retained project-overlay env selection is `relative/overlay`
- **AND WHEN** an operator runs `houmao-mgr project init`
- **THEN** the command fails explicitly
- **AND THEN** the error explains that the retained overlay env selector must be an absolute path

#### Scenario: Re-running init preserves compatible local auth state
- **WHEN** an operator already has a compatible local overlay and `/repo/app/.houmao/custom-agents/tools/claude/auth/personal/`
- **AND WHEN** `/repo/app/.houmao/houmao-config.toml` resolves `paths.agent_def_dir = "custom-agents"`
- **AND WHEN** they run `houmao-mgr project --project-dir /repo/app init`
- **THEN** the command validates the existing project overlay
- **AND THEN** it does not delete or overwrite that existing local auth bundle only because init was re-run
