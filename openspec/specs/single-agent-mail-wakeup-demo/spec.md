# single-agent-mail-wakeup-demo Specification

## Purpose
Define the supported `scripts/demo/single-agent-mail-wakeup/` demo surface for one `project easy` TUI agent that wakes on mailbox delivery through a live gateway mail notifier while keeping the copied project and redirected overlay under a demo-owned output root.

## Requirements
### Requirement: `scripts/demo/` SHALL publish a supported `single-agent-mail-wakeup` demo

The repository SHALL publish a supported runnable demo under `scripts/demo/single-agent-mail-wakeup/` and SHALL present it from `scripts/demo/README.md` as part of the maintained demo surface.

Historical material under `scripts/demo/legacy/` MAY remain as archival reference content, but the maintained operator workflow SHALL point to the supported non-legacy demo location.

#### Scenario: Maintainer inspects the supported demo index
- **WHEN** a maintainer reads `scripts/demo/README.md`
- **THEN** the README identifies `single-agent-mail-wakeup/` as a supported runnable demo
- **AND THEN** it continues to describe `legacy/` as archived reference content rather than the maintained operator surface

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

### Requirement: The stepwise demo SHALL expose interactive operator commands for attach, gateway observation, message injection, and notifier control

The supported stepwise/manual surface of `scripts/demo/single-agent-mail-wakeup/` SHALL expose operator-facing commands for:

- `attach`
- `send`
- `watch-gateway`
- `notifier status`
- `notifier on`
- `notifier off`
- `notifier set-interval`

The implementation MAY retain `manual-send` as a compatibility alias, but the maintained README and operator workflow SHALL teach `send` as the primary message-injection command.

`attach` SHALL resolve the persisted active demo state and re-attach the operator to the live agent tmux session for the selected tool lane.

`watch-gateway` SHALL resolve the persisted active demo state, query the authoritative live gateway tmux window metadata, and print the gateway console by polling that tmux pane rather than requiring the user to enter tmux and discover the gateway window manually.

The `notifier ...` subcommands SHALL reuse the existing gateway mail-notifier behavior for the running demo instance and SHALL allow the operator to inspect current notifier state, enable or disable notifier polling, and update the polling interval.

#### Scenario: Operator re-attaches to the live agent session after stepwise start
- **WHEN** an operator runs `scripts/demo/single-agent-mail-wakeup/run_demo.sh attach` for an active stepwise demo root
- **THEN** the command resolves the persisted active demo state for that root
- **AND THEN** it attaches to the live agent tmux session without requiring the operator to copy a raw tmux command from prior JSON output

#### Scenario: Operator watches the gateway console without manual tmux window discovery
- **WHEN** an operator runs `scripts/demo/single-agent-mail-wakeup/run_demo.sh watch-gateway` for an active stepwise demo root
- **THEN** the command resolves the authoritative gateway tmux window for that active demo
- **AND THEN** it prints the gateway console output by polling that tmux pane
- **AND THEN** it fails clearly when no active watchable gateway window exists

#### Scenario: Operator injects an additional message with `send`
- **WHEN** an operator runs `scripts/demo/single-agent-mail-wakeup/run_demo.sh send` for an active stepwise demo root
- **THEN** the command injects one operator-originated filesystem-backed mailbox message for the running demo instance
- **AND THEN** it persists the delivery artifact and delivery metadata under the selected output root

#### Scenario: Operator manages notifier state from the demo pack
- **WHEN** an operator runs `scripts/demo/single-agent-mail-wakeup/run_demo.sh notifier status`, `on`, `off`, or `set-interval`
- **THEN** the command targets the running demo instance resolved from persisted demo state
- **AND THEN** it reports or updates the gateway mail-notifier state for that live demo session

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

The stepwise workflow SHALL use a watchable auxiliary tmux gateway window so the operator can observe the live gateway console through the demo-owned `watch-gateway` command while separately attaching to the agent TUI.

#### Scenario: Automatic workflow runs the full single-agent flow
- **WHEN** an operator runs the demo automatic workflow for one supported tool
- **THEN** the workflow performs project initialization or reuse, specialist preparation or reuse, mailbox setup, TUI launch, gateway attach, notifier enablement, message delivery, verification, and cleanup from the canonical output root

#### Scenario: Stepwise workflow starts with a watchable gateway console
- **WHEN** an operator runs the stepwise `start` command for one supported tool
- **THEN** the workflow records the selected tool and active run details in canonical persisted demo state under `outputs/control/demo_state.json`
- **AND THEN** it attaches the gateway in a watchable auxiliary tmux window for that live demo session
- **AND THEN** the operator can subsequently use `attach`, `watch-gateway`, `send`, `notifier ...`, `inspect`, `verify`, and `stop` without passing `--demo-output-dir` during normal usage

#### Scenario: Matrix workflow no longer depends on concurrent tool-specific output roots
- **WHEN** an operator runs the demo matrix workflow
- **THEN** the workflow executes supported tool lanes against the canonical output root in sequence
- **AND THEN** it does not require concurrent `outputs/claude/` and `outputs/codex/` live roots to satisfy the maintained operator contract

### Requirement: The supported TUI wake-up demo uses runtime-home mailbox skills without project-local mirrors
The supported `single-agent-mail-wakeup` demo SHALL rely on the installed runtime-home Houmao mailbox skill surface for its wake-up flow and SHALL NOT copy runtime-owned mailbox skills into the copied project worktree as project content.

The demo's inspect and verify surfaces SHALL treat runtime-home mailbox skill availability as the maintained contract and SHALL NOT define success by the presence of a copied `project/skills` or `skills/mailbox` mirror inside the copied project.

#### Scenario: Demo start keeps the copied project free of Houmao mailbox skill mirrors
- **WHEN** the supported TUI demo starts a maintained Claude or Codex lane
- **THEN** the copied project worktree does not contain a runtime-owned Houmao mailbox-skill mirror
- **AND THEN** the demo relies on the mailbox skills already installed into the selected brain home

#### Scenario: Demo verification checks runtime-home skill availability instead of a project mirror
- **WHEN** the supported TUI demo inspects or verifies a completed run
- **THEN** it records whether the runtime-home mailbox skill surface for the selected tool is present
- **AND THEN** it does not require a project-local mailbox skill surface as part of a successful maintained run

### Requirement: The demo SHALL verify completion through gateway evidence, output creation, and actor-scoped unread completion

The supported demo SHALL treat success as all of the following:
- gateway notifier evidence shows unread work was detected and processed,
- the agent creates the requested artifact under the copied project's `tmp/` directory,
- `houmao-mgr agents mail list --read-state unread` reaches zero actionable unread messages for the selected agent.

`houmao-mgr project mailbox messages list|get` SHALL remain structural inspection only within this demo and SHALL be used to corroborate message identity, folder, projection path, canonical path, sender, recipients, subject, body, and attachments rather than authoritative read-state.

#### Scenario: Demo verifies actor-scoped unread completion
- **WHEN** the demo verifies one completed run after the delivered message is processed
- **THEN** it checks `houmao-mgr agents mail list --read-state unread` for zero actionable unread messages
- **AND THEN** it does not require project-mailbox inspection to report a global `read: true` state

#### Scenario: Demo verifies the requested project artifact
- **WHEN** the delivered message asks the agent to write one deterministic file
- **THEN** the demo verifies that file under `<output-root>/project/tmp/`
- **AND THEN** it verifies that the created artifact matches the expected deterministic content for that run

#### Scenario: Demo uses project mailbox inspection as structural corroboration
- **WHEN** the demo inspects the delivered message through `houmao-mgr project mailbox messages list|get`
- **THEN** it verifies structural projection details for the selected address
- **AND THEN** it treats those project-mailbox surfaces as structural inspection rather than as the completion authority for read-state
