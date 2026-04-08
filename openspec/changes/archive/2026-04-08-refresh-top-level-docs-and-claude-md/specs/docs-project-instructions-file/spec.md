## ADDED Requirements

### Requirement: Repo-root CLAUDE.md reflects current build/run phase vocabulary

The repo-root `CLAUDE.md` file SHALL describe the Houmao build phase using the current recipe plus launch-profile vocabulary and SHALL NOT present the retired `AgentPreset` model as the current build-phase input shape.

The file SHALL describe the Houmao run phase using the current `BrainManifest` plus role plus `LaunchPlan` composition and SHALL NOT reintroduce retired run-phase vocabulary as current.

#### Scenario: Reader encounters the build-phase description in CLAUDE.md

- **WHEN** a reader opens `CLAUDE.md` and reads the Two-Phase Lifecycle section
- **THEN** the build-phase description refers to recipes and launch profiles as the current input shape
- **AND THEN** the text does not present `AgentPreset` as the current preset model

#### Scenario: Reader encounters the run-phase description in CLAUDE.md

- **WHEN** a reader opens `CLAUDE.md` and reads the run-phase description
- **THEN** the text describes the manifest-plus-role-plus-`LaunchPlan` composition that matches the current `src/houmao/agents/realm_controller/` layout

### Requirement: Repo-root CLAUDE.md Source Layout mirrors current src/houmao subsystems

The repo-root `CLAUDE.md` file Source Layout section SHALL include bullets for each current top-level subsystem under `src/houmao/` that is load-bearing for build, run, project, server, or subsystem behavior.

At minimum, the Source Layout section SHALL reference:

- `src/houmao/agents/brain_builder.py` for the build phase,
- `src/houmao/agents/realm_controller/` for the run phase,
- `src/houmao/project/` for project overlay, catalog, easy, and launch-profile resolution,
- `src/houmao/passive_server/` for the registry-driven passive server,
- `src/houmao/mailbox/` for the mailbox subsystem,
- `src/houmao/lifecycle/` for the shared lifecycle primitives,
- `src/houmao/terminal_record/` for the terminal recording subsystem,
- `src/houmao/shared_tui_tracking/` for the shared TUI tracking module,
- `src/houmao/server/` for the Houmao-owned REST server,
- `src/houmao/srv_ctrl/cli.py` for the `houmao-mgr` entrypoint.

The Source Layout section SHALL NOT describe `config/` as "CAO server launcher config" or otherwise imply that CAO is a current configuration concern.

#### Scenario: Reader scans the CLAUDE.md Source Layout section

- **WHEN** a reader opens `CLAUDE.md` and scans the Source Layout section
- **THEN** each of the required subsystem bullets is present
- **AND THEN** the section does not list `config/` as CAO server launcher configuration

#### Scenario: Reader uses CLAUDE.md to locate the project overlay code path

- **WHEN** a reader needs to know where project overlay, catalog, and launch-profile resolution lives
- **THEN** the Source Layout section points at `src/houmao/project/`
- **AND THEN** the reader does not need to grep `src/` to discover the subsystem exists

### Requirement: Repo-root CLAUDE.md does not describe retired CAO entrypoints as current

The repo-root `CLAUDE.md` file SHALL NOT describe `houmao-cao-server` or `python -m houmao.cao.tools.cao_server_launcher` as current operator entrypoints.

Any reference to CAO SHALL be framed as historical context or retired, not as a current workflow.

#### Scenario: Reader searches CLAUDE.md for entrypoints

- **WHEN** a reader scans `CLAUDE.md` for how to launch Houmao services
- **THEN** the file only surfaces `houmao-mgr` and `houmao-server` as current entrypoints
- **AND THEN** any mention of CAO-era launchers appears only as retired or historical context
