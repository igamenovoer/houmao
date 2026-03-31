## MODIFIED Requirements

### Requirement: The demo SHALL keep project files and redirected overlay state under the demo output root

Each demo run SHALL keep all generated state under one canonical demo-owned output root at `scripts/demo/single-agent-mail-wakeup/outputs/`.

That output root SHALL contain:
- a copied project worktree under `project/`,
- a redirected Houmao project overlay under `overlay/`,
- demo-owned control, log, delivery, and evidence artifacts under sibling directories.

The demo SHALL run project-aware commands from the copied project root while exporting `HOUMAO_PROJECT_OVERLAY_DIR` as the absolute path to the sibling `overlay/` directory.

The demo SHALL ignore generated outputs from git through a demo-local ignore policy rather than requiring edits to the repository root ignore rules.

The demo SHALL preserve reusable overlay-backed specialist state across fresh runs, including the overlay-backed project-easy catalog, managed content, specialist metadata, and generated agent-definition projections.

The demo SHALL reset ephemeral run-local state on a fresh `start`, including the copied project, mailbox contents, runtime state, logs, deliveries, and evidence.

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
- **AND THEN** they do not depend on `<copied-project>/.houmao` as the overlay location

#### Scenario: Fresh start preserves specialists but resets mailbox and runtime state
- **WHEN** an operator starts a new run after a prior run has already populated the demo overlay
- **THEN** the demo preserves reusable overlay-backed specialist and auth/setup state under `outputs/overlay/`
- **AND THEN** it resets `outputs/project/`, `outputs/runtime/`, `outputs/registry/`, `outputs/jobs/`, `outputs/logs/`, `outputs/deliveries/`, `outputs/evidence/`, and `outputs/overlay/mailbox/`
- **AND THEN** the operator does not need to recreate the project-easy specialist only because a fresh run is starting

#### Scenario: Generated output root stays gitignored
- **WHEN** a maintainer inspects the demo after generated output exists
- **THEN** the demo-local ignore policy excludes the generated output tree from git tracking
- **AND THEN** the copied project, mailbox state, runtime state, and other demo-owned artifacts remain disposable under the canonical output root

### Requirement: The demo SHALL support Claude Code and Codex TUI lanes through `project easy`

The supported demo SHALL expose two maintained lanes:
- Claude Code TUI
- Codex TUI

For each lane, the demo SHALL:
- import or materialize the expected project-local auth bundle,
- create or reuse one specialist through `houmao-mgr project easy specialist create`,
- launch one TUI instance through `houmao-mgr project easy instance launch`.

The demo SHALL persist the selected tool in canonical demo state rather than encoding it in a tool-specific output-root path.

The demo SHALL NOT claim headless or mixed-mode support as part of this operator contract.

#### Scenario: Claude TUI lane starts through project easy
- **WHEN** an operator runs the demo for tool `claude`
- **THEN** the demo creates or reuses a project-local Claude auth bundle under the redirected overlay
- **AND THEN** it creates or reuses a Claude specialist through `houmao-mgr project easy specialist create`
- **AND THEN** it launches one Claude TUI instance through `houmao-mgr project easy instance launch`
- **AND THEN** the selected tool is persisted in canonical demo state under the shared output root

#### Scenario: Codex TUI lane starts through project easy
- **WHEN** an operator runs the demo for tool `codex`
- **THEN** the demo creates or reuses a project-local Codex auth bundle under the redirected overlay
- **AND THEN** it creates or reuses a Codex specialist through `houmao-mgr project easy specialist create`
- **AND THEN** it launches one Codex TUI instance through `houmao-mgr project easy instance launch`
- **AND THEN** the selected tool is persisted in canonical demo state under the shared output root

### Requirement: The demo SHALL teach the single-agent gateway wake-up workflow from project creation through notifier wake-up

The supported demo SHALL present one narrow single-agent workflow:
1. initialize or reuse the redirected project overlay,
2. initialize the project mailbox under that overlay,
3. register the agent and operator mailbox identities,
4. launch one project-easy TUI instance,
5. attach one live gateway,
6. enable gateway mail-notifier polling,
7. inject one operator-originated filesystem-backed mailbox message,
8. observe the agent wake and process that message.

The demo SHALL include:
- one automatic one-shot workflow,
- one stepwise workflow that preserves canonical demo state and supports direct operator interaction with the running agent, gateway, and notifier,
- a demo README that explains prerequisites, outputs, verification, and failure modes.

The automatic workflow SHALL remain the canonical unattended path and SHALL keep its existing non-interactive gateway execution model.

The stepwise workflow SHALL use the canonical persisted demo state under `outputs/` so that follow-up commands such as `attach`, `watch-gateway`, `send`, `notifier ...`, `inspect`, `verify`, and `stop` do not require operators to specify a tool-specific demo output root during normal usage.

#### Scenario: Automatic workflow runs the full single-agent flow
- **WHEN** an operator runs the demo automatic workflow for one supported tool
- **THEN** the workflow performs project initialization or reuse, specialist preparation or reuse, mailbox setup, TUI launch, gateway attach, notifier enablement, message delivery, verification, and cleanup from the canonical output root

#### Scenario: Stepwise workflow resolves follow-up commands from canonical state
- **WHEN** an operator runs the stepwise `start` command for one supported tool
- **THEN** the workflow records the selected tool and active run details in canonical persisted demo state under `outputs/control/demo_state.json`
- **AND THEN** the operator can subsequently use `attach`, `watch-gateway`, `send`, `notifier ...`, `inspect`, `verify`, and `stop` without passing `--demo-output-dir` during normal usage
- **AND THEN** those follow-up commands resolve the active run from the canonical persisted demo state

#### Scenario: Matrix workflow no longer depends on concurrent tool-specific output roots
- **WHEN** an operator runs the demo matrix workflow
- **THEN** the workflow executes supported tool lanes against the canonical output root in sequence
- **AND THEN** it does not require concurrent `outputs/claude/` and `outputs/codex/` live roots to satisfy the maintained operator contract
