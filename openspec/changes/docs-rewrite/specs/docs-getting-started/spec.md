## ADDED Requirements

### Requirement: Architecture overview explains two-phase lifecycle

The getting-started section SHALL include an architecture overview document that explains the two-phase lifecycle (build phase → run phase), the agent definition directory model, and the backend abstraction. The content SHALL be derived from `brain_builder.py` and `realm_controller/` module docstrings.

#### Scenario: Reader understands build-then-run flow

- **WHEN** a reader opens the architecture overview
- **THEN** they find a clear explanation of: (1) build phase producing a BrainManifest from a recipe/blueprint, (2) run phase composing manifest + role into a LaunchPlan dispatched to a backend

#### Scenario: Backend model presented with local_interactive as primary

- **WHEN** the architecture overview describes backends
- **THEN** `local_interactive` (tmux-backed) is presented as the primary backend, headless backends as direct-CLI alternatives, and CAO-backed backends mentioned only as legacy

### Requirement: Agent definition directory layout documented

The getting-started section SHALL include a page documenting the agent definition directory structure (`brains/tool-adapters/`, `brains/skills/`, `brains/cli-configs/`, `brains/api-creds/`, `brains/brain-recipes/`, `roles/`, `blueprints/`) with the purpose of each subdirectory.

#### Scenario: Reader can set up a new agent definition directory

- **WHEN** a reader follows the agent definition directory page
- **THEN** they understand what goes in each subdirectory and which files are committed vs local-only (api-creds)

### Requirement: Quickstart guide covers build and launch

The getting-started section SHALL include a quickstart page showing how to build a brain home and start a session using `houmao-mgr` commands, derived from the CLI command groups in `srv_ctrl/commands/`.

#### Scenario: Quickstart uses houmao-mgr commands

- **WHEN** the quickstart shows example commands
- **THEN** it uses `houmao-mgr` (not `houmao-cli` or raw `cao` commands) for all operations
