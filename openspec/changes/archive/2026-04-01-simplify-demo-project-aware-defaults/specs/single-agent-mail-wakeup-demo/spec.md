## MODIFIED Requirements

### Requirement: The demo SHALL keep project files and redirected overlay state under the demo output root

Each demo run SHALL keep all generated state under one canonical demo-owned output root. Normal operator usage SHALL default that root to `scripts/demo/single-agent-mail-wakeup/outputs/`.

That output root SHALL contain:
- a copied project worktree under `project/`,
- a redirected Houmao project overlay under `overlay/`,
- demo-owned registry, control, log, delivery, and evidence artifacts under sibling directories.

The redirected overlay SHALL remain the authority for project-local Houmao-owned state in the supported workflow, including:
- `overlay/agents/`
- `overlay/runtime/`
- `overlay/jobs/`
- `overlay/mailbox/`
- overlay-backed catalog and managed content

The demo SHALL run project-aware commands from the copied project root while exporting `HOUMAO_PROJECT_OVERLAY_DIR` as the absolute path to the sibling `overlay/` directory.

The maintained workflow MAY retain an explicit demo-local registry override so the run does not collide with the operator's shared registry, but it SHALL NOT require separate agent-definition, runtime, or jobs root overrides merely to keep the demo self-contained.

The demo SHALL ignore generated outputs from git through a demo-local ignore policy rather than requiring edits to the repository root ignore rules.

The demo SHALL preserve reusable overlay-backed specialist state across fresh runs, including the overlay-backed project-easy catalog, managed content, specialist metadata, and generated agent-definition projections.

The demo SHALL reset ephemeral run-local state on a fresh `start`, including the copied project, overlay-local mailbox contents, overlay-local runtime state, overlay-local jobs state, logs, deliveries, and evidence.

#### Scenario: Operator runs the demo with the canonical output root
- **WHEN** an operator starts the demo for either supported tool
- **THEN** the run uses `scripts/demo/single-agent-mail-wakeup/outputs/` as the canonical managed output root
- **AND THEN** it creates or refreshes the copied project under `outputs/project/`
- **AND THEN** it creates or reuses the redirected overlay under `outputs/overlay/`
- **AND THEN** all generated demo-owned state remains under that canonical output root

#### Scenario: Project-aware commands use the redirected overlay root
- **WHEN** the demo runs `houmao-mgr project ...`, `houmao-mgr project easy ...`, or `houmao-mgr project mailbox ...` commands for one run
- **THEN** those commands execute from the copied project root
- **AND THEN** they resolve the active overlay through `HOUMAO_PROJECT_OVERLAY_DIR=<output-root>/overlay`
- **AND THEN** they do not depend on separate agent-definition, runtime, or jobs root overrides for ordinary project-local state

#### Scenario: Fresh start preserves specialists but resets overlay-local ephemeral state
- **WHEN** an operator starts a new run after a prior run has already populated the demo overlay
- **THEN** the demo preserves reusable overlay-backed specialist and auth/setup state under `outputs/overlay/`
- **AND THEN** it resets `outputs/project/`, `outputs/registry/`, `outputs/logs/`, `outputs/deliveries/`, `outputs/evidence/`, and the overlay-local `runtime/`, `jobs/`, and `mailbox/` state under `outputs/overlay/`
- **AND THEN** the operator does not need to recreate the project-easy specialist only because a fresh run is starting

#### Scenario: Generated output root stays gitignored
- **WHEN** a maintainer inspects the demo after generated output exists
- **THEN** the demo-local ignore policy excludes the generated output tree from git tracking
- **AND THEN** the copied project, overlay-local mailbox state, overlay-local runtime state, and other demo-owned artifacts remain disposable under the canonical output root
