## MODIFIED Requirements

### Requirement: Architecture overview explains two-phase lifecycle
The getting-started section SHALL include an architecture overview document that explains the two-phase lifecycle (build phase → run phase), the agent definition directory model, the backend abstraction, and the current operator-facing CLI surfaces. The content SHALL be derived from `brain_builder.py`, `realm_controller/`, and the current `houmao-mgr` and `houmao-server` command trees.

#### Scenario: Reader understands build-then-run flow
- **WHEN** a reader opens the architecture overview
- **THEN** they find a clear explanation of: (1) build phase producing a BrainManifest from a preset-backed build specification, (2) run phase composing manifest plus role into a LaunchPlan dispatched to a backend, and (3) `houmao-mgr` as the primary operator CLI for the supported workflow

#### Scenario: Backend model presented with current operator posture
- **WHEN** the architecture overview describes backends and entrypoints
- **THEN** `local_interactive` is presented as the primary backend, native headless backends are presented as direct CLI alternatives, and CAO-backed backends are described only as legacy or compatibility paths
- **AND THEN** the overview does not present deprecated or compatibility entrypoints as the primary way to operate Houmao

### Requirement: Agent definition directory layout documented
The getting-started section SHALL include a page documenting the agent definition directory structure (`skills/<skill>/`, `roles/<role>/system-prompt.md`, `roles/<role>/presets/<tool>/<setup>.yaml`, `tools/<tool>/adapter.yaml`, `tools/<tool>/setups/<setup>/`, `tools/<tool>/auth/<auth>/`, and optional `compatibility-profiles/`) with the purpose of each subdirectory.

#### Scenario: Reader can set up a new agent definition directory
- **WHEN** a reader follows the agent definition directory page
- **THEN** they understand what goes in each canonical subdirectory and which files are committed vs local-only (`tools/<tool>/auth/`)
