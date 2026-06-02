# houmao-mgr-project-cli Specification

## Purpose
Define the repo-local `houmao-mgr project` workflow for bootstrapping and inspecting one local `.houmao/` project overlay.
## Requirements
### Requirement: `houmao-mgr project` exposes repo-local project administration commands
`houmao-mgr` SHALL expose a top-level `project` command family for first-class Houmao project administration and ordinary project-based managed-agent workflows.

At minimum, that family SHALL include:

- `init`
- `status`
- `specialist`
- `profile`
- `agents`
- `migrate`
- `skills`
- `credentials`
- `mailbox`

The `project` family SHALL be presented as the ordinary local Houmao workflow. It SHALL NOT present `easy` as a public nesting level, and it SHALL NOT present provider-aligned native-agent material as ordinary project resources.

#### Scenario: Operator sees the first-class project command family
- **WHEN** an operator runs `houmao-mgr project --help`
- **THEN** the help output lists `init`, `status`, `specialist`, `profile`, `agents`, `migrate`, `skills`, `credentials`, and `mailbox`
- **AND THEN** the help output does not list `easy` as a public command group
- **AND THEN** the help output presents `project` as the ordinary local Houmao workflow

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

### Requirement: Project commands use specialist/profile/managed-agent language
Ordinary `houmao-mgr project` commands SHALL use project-layer terms:

- `specialist` for reusable project-local persona/tool/credential definitions,
- `profile` for reusable launch defaults for a specialist,
- `managed agent` or `agent instance` for live or stopped Houmao-managed runtime identities.

Project help text, structured output keys intended for ordinary users, config drafts, and packaged project-management skill guidance SHALL NOT call those project-layer resources native agents, raw agent definitions, raw profiles, or launch dossiers.

#### Scenario: Project specialist help avoids native-agent terms
- **WHEN** an operator runs `houmao-mgr project specialist --help`
- **THEN** the help output describes project-local specialists
- **AND THEN** it does not describe the command as native-agent role or recipe management

### Requirement: Project initialization is the explicit project creation entrypoint
`houmao-mgr project init` SHALL remain the explicit command for creating or validating a project overlay.

Ordinary stateful project-backed commands SHALL require an active project overlay and SHALL fail clearly when no active project exists. They SHALL NOT implicitly bootstrap `<cwd>/.houmao` merely because the command requires local Houmao-owned state.

#### Scenario: Specialist create requires an initialized project
- **WHEN** no active Houmao project exists from the invocation directory
- **AND WHEN** an operator runs `houmao-mgr project specialist create --name reviewer --tool codex --credential reviewer-creds`
- **THEN** the command fails clearly
- **AND THEN** the error tells the operator to run `houmao-mgr project init` or select an existing project overlay
- **AND THEN** the command does not create `<cwd>/.houmao` as a side effect

### Requirement: `houmao-mgr project credentials` provides explicit project-scoped credential management
`houmao-mgr project credentials <tool>` SHALL expose:

- `list`
- `get`
- `add`
- `set`
- `rename`
- `remove`
- `login`

`project credentials` SHALL use the selected project overlay supplied by the `project` command group and SHALL use the project-backed credential behavior defined for project-local catalog-backed auth profiles.

`project credentials` SHALL NOT expose `--project`, `--agent-def-dir`, or direct native-agent root selectors because its target is the selected project overlay by definition.

#### Scenario: Operator sees the project-scoped credential verbs for one tool
- **WHEN** an operator runs `houmao-mgr project credentials claude --help`
- **THEN** the help output presents `list`, `get`, `add`, `set`, `rename`, `remove`, and `login`
- **AND THEN** those commands are described as project-scoped credential management for the active overlay

#### Scenario: Project credential add uses the active overlay
- **WHEN** an operator runs `houmao-mgr project credentials codex add --name work --api-key sk-test`
- **THEN** the command resolves the active project overlay
- **AND THEN** it creates a project-local catalog-backed Codex credential in that overlay

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

#### Scenario: Operator initializes the default local Houmao overlay
- **WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **AND WHEN** no explicit project directory or retained env selection is supplied
- **AND WHEN** `/repo/app/.houmao/houmao-config.toml` does not already exist
- **THEN** the command creates `/repo/app/.houmao/houmao-config.toml`
- **AND THEN** the written config sets `paths.agent_def_dir = "agents"`
- **AND THEN** it creates `/repo/app/.houmao/.gitignore` without editing `/repo/app/.gitignore`
- **AND THEN** it creates `/repo/app/.houmao/catalog.sqlite`
- **AND THEN** it creates the managed project-local content roots required by the catalog-backed overlay contract

#### Scenario: Operator initializes an explicitly selected project directory
- **WHEN** an operator runs `houmao-mgr project --project-dir /repo/app init` from `/tmp`
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

### Requirement: `houmao-mgr project status` reports discovered local project state
`houmao-mgr project status` SHALL resolve the active overlay root in this order:

1. `HOUMAO_PROJECT_OVERLAY_DIR` when set,
2. ambient discovery from the caller's current working directory under `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`.

When `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` is unset, the effective mode SHALL be `ancestor`.
When the effective mode is `ancestor`, status SHALL use nearest-ancestor project discovery from the caller's current working directory.
When the effective mode is `cwd_only`, status SHALL inspect only `<cwd>/.houmao/houmao-config.toml` and SHALL NOT search parent directories.
When `HOUMAO_PROJECT_OVERLAY_DIR` is set, it SHALL be an absolute path.
The command SHALL report whether a repo-local Houmao overlay was discovered under the selected overlay root rather than only under the caller's current working directory.

At minimum, the reported payload SHALL include:

- whether a project overlay was found,
- the resolved overlay root when selected or discovered,
- the source of the resolved overlay root,
- the effective overlay discovery mode,
- the resolved config path when found,
- the resolved project-local catalog path when found,
- the effective agent-definition root,
- the effective agent-definition-root source.

When no project overlay is discovered under the selected overlay root, the command SHALL report that local project state is not initialized instead of silently pretending a project config exists.

#### Scenario: Status reports the env-selected catalog-backed overlay even when cwd-only mode is active
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=cwd_only`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` exists for a catalog-backed overlay
- **AND WHEN** an operator runs `houmao-mgr project status` from `/repo/subdir`
- **THEN** the command reports `/tmp/ci-overlay` as the resolved overlay root
- **AND THEN** it reports `env` as the overlay-root source
- **AND THEN** it reports `cwd_only` as the effective overlay discovery mode
- **AND THEN** it reports `/tmp/ci-overlay/houmao-config.toml` as the discovered config path

#### Scenario: Status reports the nearest discovered catalog-backed overlay by default
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` is unset
- **AND WHEN** `/repo/.houmao/houmao-config.toml` exists for a catalog-backed overlay
- **AND WHEN** an operator runs `houmao-mgr project status` from `/repo/subdir`
- **THEN** the command reports `/repo/.houmao` as the resolved overlay root
- **AND THEN** it reports `ancestor` as the effective overlay discovery mode
- **AND THEN** it reports `/repo/.houmao/houmao-config.toml` as the discovered config path

#### Scenario: Status reports the cwd-local overlay candidate in cwd-only mode
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=cwd_only`
- **AND WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** `/repo/subdir/.houmao/houmao-config.toml` does not exist
- **AND WHEN** an operator runs `houmao-mgr project status` from `/repo/subdir`
- **THEN** the command reports `/repo/subdir/.houmao` as the selected overlay root
- **AND THEN** it reports that no local Houmao project overlay was discovered
- **AND THEN** it reports `cwd_only` as the effective overlay discovery mode

### Requirement: Maintained project-local inspection and existing-state flows remain non-creating
Maintained `houmao-mgr project agents ...` commands that inspect existing project-local source content or remove existing project-local state SHALL resolve overlay selection through the shared non-creating project-aware resolver.

When no active project overlay exists for the caller and no stronger overlay selection override applies, these commands SHALL fail clearly without bootstrapping the selected or would-bootstrap overlay root.

At minimum, this requirement SHALL apply to:

- `houmao-mgr internals native-agent tools <tool> get`
- `houmao-mgr internals native-agent tools <tool> setups list`
- `houmao-mgr internals native-agent tools <tool> setups get`
- `houmao-mgr internals native-agent tools <tool> setups remove`
- `houmao-mgr project credentials <tool> list`
- `houmao-mgr project credentials <tool> get`
- `houmao-mgr project credentials <tool> remove`
- `houmao-mgr internals native-agent roles list`
- `houmao-mgr internals native-agent roles get`
- `houmao-mgr internals native-agent roles remove`
- `houmao-mgr project agents presets list`
- `houmao-mgr project agents presets get`
- `houmao-mgr project agents presets remove`

#### Scenario: Tool get fails clearly without bootstrapping a missing overlay
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr internals native-agent tools codex get`
- **THEN** the command fails clearly because no project overlay was discovered for the current invocation
- **AND THEN** it does not create `<cwd>/.houmao` as a side effect of that inspection command

#### Scenario: Preset remove does not create an empty overlay
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project agents presets remove --name reviewer-codex-default`
- **THEN** the command fails clearly before attempting removal
- **AND THEN** it does not bootstrap a new project overlay only to report missing existing state

### Requirement: `houmao-mgr project status` remains a read-only reporting surface
`houmao-mgr project status` SHALL report the selected project overlay root and derived project-aware local roots without bootstrapping a missing overlay.

When no overlay exists yet, the command SHALL report the would-bootstrap overlay root for the current invocation context rather than creating it.

#### Scenario: Project status reports the would-bootstrap overlay without creating it
- **WHEN** no explicit CLI overlay root is supplied
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** no ancestor `.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs `houmao-mgr project status` from `/repo/app`
- **THEN** the command reports `/repo/app/.houmao` as the selected or would-bootstrap overlay root
- **AND THEN** it does not create `/repo/app/.houmao` during that status command

### Requirement: Project command wording distinguishes selected overlays, non-creating resolution, and implicit bootstrap
Maintained `houmao-mgr project ...` help text, failures, and structured payload wording SHALL distinguish among:

- the selected overlay root for the current invocation,
- non-creating resolution that intentionally does not create the selected or would-bootstrap overlay,
- implicit bootstrap that created the selected overlay during the current invocation.

Operator-facing wording for maintained project commands SHALL use `selected overlay root` or `selected project overlay` terminology rather than stale `discovered project overlay` wording when the command resolved an env-selected or explicitly bootstrapped overlay.

#### Scenario: Non-creating project inspection reports the selected or would-bootstrap overlay
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs a maintained non-creating `houmao-mgr project ...` inspection or removal command
- **THEN** the failure explains which overlay root was selected or would be bootstrapped for that invocation
- **AND THEN** the failure states that the command remained non-creating instead of implying a discovery failure under a different root

#### Scenario: Project-aware bootstrap result surfaces the created overlay explicitly
- **WHEN** a maintained stateful `houmao-mgr project ...` command bootstraps the selected overlay during the current invocation
- **THEN** the resulting operator-facing text or payload identifies the selected overlay root that was created
- **AND THEN** the result does not require the operator to infer that bootstrap solely from later filesystem state

### Requirement: Ordinary project-aware commands do not silently migrate legacy project structure
Maintained `houmao-mgr project ...` commands and project-aware catalog-backed flows SHALL NOT silently rewrite known legacy project structure as a side effect of ordinary inspection, bootstrap, authoring, or launch preparation commands.

When one of those flows detects a known legacy project structure that requires conversion into the current supported project model, the command SHALL fail clearly and direct the operator to `houmao-mgr project migrate`.

This requirement applies to ordinary project administration and authoring flows such as `project init`, `project ...`, project-backed credential commands, and project-aware compatibility materialization.

#### Scenario: Project command fails with migration guidance instead of upgrading implicitly
- **WHEN** the selected project overlay contains one known legacy project structure that requires explicit migration
- **AND WHEN** an operator runs one ordinary stateful `houmao-mgr project ...` command other than `project migrate`
- **THEN** the command fails clearly
- **AND THEN** the diagnostic directs the operator to `houmao-mgr project migrate`
