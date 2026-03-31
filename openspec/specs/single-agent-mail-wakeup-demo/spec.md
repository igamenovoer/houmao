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

Each demo run SHALL keep all generated state under one demo-owned output root.

That output root SHALL contain:
- a copied project worktree under `project/`,
- a redirected Houmao project overlay under `overlay/`,
- demo-owned control, log, delivery, and evidence artifacts under sibling directories.

The demo SHALL run project-aware commands from the copied project root while exporting `HOUMAO_PROJECT_OVERLAY_DIR` as the absolute path to the sibling `overlay/` directory.

The demo SHALL ignore generated outputs from git through a demo-local ignore policy rather than requiring edits to the repository root ignore rules.

#### Scenario: Operator runs the demo with the default output root
- **WHEN** an operator starts one tool lane of the demo
- **THEN** the run creates a copied project under the selected output root
- **AND THEN** it creates a redirected overlay root under the same output root
- **AND THEN** all generated demo-owned state remains under that selected output root

#### Scenario: Project-aware commands use the redirected overlay root
- **WHEN** the demo runs `houmao-mgr project ...`, `houmao-mgr project easy ...`, or `houmao-mgr project mailbox ...` commands for one run
- **THEN** those commands execute from the copied project root
- **AND THEN** they resolve the active overlay through `HOUMAO_PROJECT_OVERLAY_DIR=<output-root>/overlay`
- **AND THEN** they do not depend on `<copied-project>/.houmao` as the overlay location

#### Scenario: Generated output roots stay gitignored
- **WHEN** a maintainer inspects the demo after generated output exists
- **THEN** the demo-local ignore policy excludes the generated output tree from git tracking
- **AND THEN** the copied project and redirected overlay remain demo-owned disposable artifacts

### Requirement: The demo SHALL support Claude Code and Codex TUI lanes through `project easy`

The supported demo SHALL expose two maintained lanes:
- Claude Code TUI
- Codex TUI

For each lane, the demo SHALL:
- import or materialize the expected project-local auth bundle,
- create one specialist through `houmao-mgr project easy specialist create`,
- launch one TUI instance through `houmao-mgr project easy instance launch`.

The demo SHALL NOT claim headless or mixed-mode support as part of this operator contract.

#### Scenario: Claude TUI lane starts through project easy
- **WHEN** an operator runs the demo for tool `claude`
- **THEN** the demo creates or uses a project-local Claude auth bundle under the redirected overlay
- **AND THEN** it creates a Claude specialist through `houmao-mgr project easy specialist create`
- **AND THEN** it launches one Claude TUI instance through `houmao-mgr project easy instance launch`

#### Scenario: Codex TUI lane starts through project easy
- **WHEN** an operator runs the demo for tool `codex`
- **THEN** the demo creates or uses a project-local Codex auth bundle under the redirected overlay
- **AND THEN** it creates a Codex specialist through `houmao-mgr project easy specialist create`
- **AND THEN** it launches one Codex TUI instance through `houmao-mgr project easy instance launch`

### Requirement: The demo SHALL teach the single-agent gateway wake-up workflow from project creation through notifier wake-up

The supported demo SHALL present one narrow single-agent workflow:
1. initialize the redirected project overlay,
2. initialize the project mailbox under that overlay,
3. register the agent and operator mailbox identities,
4. launch one project-easy TUI instance,
5. attach one live gateway,
6. enable gateway mail-notifier polling,
7. inject one operator-originated filesystem-backed mailbox message,
8. observe the agent wake and process that message.

The demo SHALL include:
- one automatic one-shot workflow,
- one stepwise workflow that allows live inspection before or after delivery,
- a demo README that explains prerequisites, outputs, verification, and failure modes.

#### Scenario: Automatic workflow runs the full single-agent flow
- **WHEN** an operator runs the demo automatic workflow for one supported tool
- **THEN** the workflow performs project initialization, specialist creation, mailbox setup, TUI launch, gateway attach, notifier enablement, message delivery, verification, and cleanup from the selected output root

#### Scenario: Stepwise workflow allows live inspection before or after delivery
- **WHEN** an operator runs the stepwise demo commands for one supported tool
- **THEN** the workflow preserves demo-owned state under the selected output root
- **AND THEN** it allows the operator to inspect the live session, gateway status, notifier status, and delivery artifacts before final verification or stop

### Requirement: The demo SHALL verify completion through gateway evidence, output creation, and actor-scoped unread completion

The supported demo SHALL treat success as all of the following:
- gateway notifier evidence shows unread work was detected and processed,
- the agent creates the requested artifact under the copied project's `tmp/` directory,
- `houmao-mgr agents mail check --unread-only` reaches zero actionable unread messages for the selected agent.

`houmao-mgr project mailbox messages list|get` SHALL remain structural inspection only within this demo and SHALL be used to corroborate message identity, folder, projection path, canonical path, sender, recipients, subject, body, and attachments rather than authoritative read-state.

#### Scenario: Demo verifies actor-scoped unread completion
- **WHEN** the demo verifies one completed run after the delivered message is processed
- **THEN** it checks `houmao-mgr agents mail check --unread-only` for zero actionable unread messages
- **AND THEN** it does not require project-mailbox inspection to report a global `read: true` state

#### Scenario: Demo verifies the requested project artifact
- **WHEN** the delivered message asks the agent to write one deterministic file
- **THEN** the demo verifies that file under `<output-root>/project/tmp/`
- **AND THEN** it verifies that the created artifact matches the expected deterministic content for that run

#### Scenario: Demo uses project mailbox inspection as structural corroboration
- **WHEN** the demo inspects the delivered message through `houmao-mgr project mailbox messages list|get`
- **THEN** it verifies structural projection details for the selected address
- **AND THEN** it treats those project-mailbox surfaces as structural inspection rather than as the completion authority for read-state
