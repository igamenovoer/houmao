# project-aware-local-roots Specification

## Purpose
Give local Houmao commands a consistent way to select a project overlay and resolve its agent-definition, runtime, job, and mailbox roots alongside the shared registry. Carry the selected root context through managed launches and relaunches.
## Requirements
### Requirement: Project-aware local commands resolve one active overlay before using local Houmao-owned state
Maintained local Houmao command flows that need Houmao-owned local state SHALL resolve one active project overlay using this precedence:

1. explicit CLI overlay selection when a command supports it,
2. `HOUMAO_PROJECT_OVERLAY_DIR`,
3. nearest ancestor discovered project overlay within the current Git worktree boundary.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The current Git worktree boundary SHALL be inferred by walking ancestors from the invocation directory until the nearest ancestor containing a `.git` file or directory. When no ancestor contains `.git`, discovery MAY continue to the filesystem root.
When `HOUMAO_PROJECT_OVERLAY_DIR` is set, it SHALL be an absolute path.
When explicit CLI selection is supplied, it SHALL win over env and discovery.
Commands that only need to report selection state MAY report the selected overlay root without forcing bootstrap.
Commands that need local Houmao-owned state SHALL fail clearly when no active project overlay exists, except for explicit project initialization flows.

#### Scenario: Explicit CLI overlay selection wins
- **WHEN** an operator supplies an explicit CLI overlay root
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is also set
- **THEN** the command uses the explicitly selected overlay root
- **AND THEN** it does not replace that selection with the env-selected overlay

#### Scenario: Nearest ancestor overlay is reused when no override exists
- **WHEN** no explicit CLI overlay root is supplied
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs a maintained local Houmao command from `/repo/subdir/nested`
- **THEN** the command uses `/repo/.houmao` as the active overlay
- **AND THEN** it does not bootstrap `/repo/subdir/nested/.houmao`

#### Scenario: Discovery does not cross the current Git worktree boundary
- **WHEN** no explicit CLI overlay root is supplied
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `/parent/.houmao/houmao-config.toml` exists
- **AND WHEN** `/parent/nested-repo/.git` exists
- **AND WHEN** no `.houmao/houmao-config.toml` exists between `/parent/nested-repo` and its Git worktree root
- **AND WHEN** an operator runs a maintained local Houmao command from `/parent/nested-repo/app`
- **THEN** the command does not reuse `/parent/.houmao`
- **AND THEN** it reports that no active project exists for the invocation

#### Scenario: Missing overlay fails instead of bootstrapping
- **WHEN** no explicit CLI overlay root is supplied
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** no ancestor project overlay exists
- **AND WHEN** an operator runs a maintained local Houmao command that requires local Houmao-owned state from `/repo/app`
- **THEN** the command fails clearly because no active project exists
- **AND THEN** it does not bootstrap `/repo/app/.houmao`
- **AND THEN** the diagnostic points to `houmao-mgr project init`

### Requirement: Project-aware local roots default under the active overlay except registry
When a maintained local Houmao command runs in project context without a stronger explicit or env-var override, the effective local roots SHALL derive from the active project overlay as:

- agent-definition root: `<overlay>/agents`
- runtime root: `<overlay>/runtime`
- jobs root: `<overlay>/jobs`
- mailbox root: `<overlay>/mailbox`
- project catalog and managed content roots under the overlay.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The shared registry SHALL remain outside the project overlay by default under the platformdirs user config root, expected as `~/.config/houmao/registry` on Linux, unless the existing registry env override redirects it.
For this change, `runtime/`, `jobs/`, and `mailbox/` SHALL remain convention-derived overlay subpaths rather than new configurable `houmao-config.toml` path keys.

#### Scenario: Project-aware runtime and jobs roots derive from the overlay
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** no explicit runtime-root or jobs-root override is supplied
- **THEN** the effective runtime root is `/repo/.houmao/runtime`
- **AND THEN** the effective jobs root is `/repo/.houmao/jobs`

#### Scenario: Shared registry remains global under platformdirs by default
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** no registry override is supplied
- **THEN** the effective shared registry root remains outside the project overlay under the platformdirs user config root
- **AND THEN** the command does not relocate the registry under `/repo/.houmao/registry`

#### Scenario: Project config can still customize native projection without changing fixed overlay subpaths
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** `/repo/.houmao/houmao-config.toml` sets its native-agent projection path to `custom-agents`
- **AND WHEN** no stronger runtime-root, jobs-root, or mailbox-root override exists
- **THEN** the effective native-agent projection root resolves under `/repo/.houmao/custom-agents`
- **AND THEN** the effective runtime, jobs, and mailbox roots remain `/repo/.houmao/runtime`, `/repo/.houmao/jobs`, and `/repo/.houmao/mailbox`

### Requirement: Project launches honor configured runtime and mailbox roots

Project-aware managed launch SHALL resolve runtime and mailbox placement from authorized explicit launch selections, then owner-side shared-root overrides, then selected overlay defaults. The launch SHALL record the effective placements in their existing runtime and mailbox bindings.

#### Scenario: Shared runtime and mailbox roots override an overlay default

- **WHEN** a project launch selects an overlay and supplies `HOUMAO_GLOBAL_RUNTIME_DIR` and `HOUMAO_GLOBAL_MAILBOX_DIR` without explicit placement overrides
- **THEN** runtime state and the configured filesystem mailbox use the selected shared roots

#### Scenario: An explicit shared mailbox root takes precedence

- **WHEN** a project launch specifies `--mail-root` and a different `HOUMAO_GLOBAL_MAILBOX_DIR`
- **THEN** filesystem mailbox binding uses the explicit shared mailbox root

#### Scenario: Project launch uses the overlay defaults

- **WHEN** an operator launches a project agent without shared-root overrides or explicit runtime and mailbox placement
- **THEN** the runtime and configured filesystem mailbox use their respective overlay defaults

### Requirement: Managed launch preserves its selected Houmao root context

Managed launch SHALL publish absolute paths for the execution binding's registry, any selected shared runtime and mailbox roots, and the selected overlay. It SHALL use `HOUMAO_GLOBAL_REGISTRY_DIR`, `HOUMAO_GLOBAL_RUNTIME_DIR`, `HOUMAO_GLOBAL_MAILBOX_DIR`, and `HOUMAO_PROJECT_OVERLAY_DIR` respectively. Relaunch SHALL retain this context from recorded launch authority.

#### Scenario: Web peers share a registry across different projects

- **WHEN** a DSH Web agent and a Kimi Web agent launch from different overlays with the same shared registry, runtime, and mailbox roots
- **THEN** their tmux environments and local tool shells carry the same shared selectors and their respective overlay selectors
- **AND THEN** `houmao-mgr agents global list` from either agent lists both peers from the selected registry

#### Scenario: Local placement keeps project-relative defaults

- **WHEN** an agent launches with overlay-local runtime and mailbox defaults
- **THEN** the selected overlay is published and the two shared-root selectors remain absent
- **AND THEN** self queries can read the effective agent bindings from the runtime manifest

#### Scenario: Relaunch uses the selected project context

- **WHEN** an operator relaunches an agent from a directory and environment that select different roots and another overlay
- **THEN** the agent receives the selectors recorded for its original execution and project context
