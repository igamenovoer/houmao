## ADDED Requirements

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

## MODIFIED Requirements

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
- one stepwise workflow that preserves demo-owned state and supports direct operator interaction with the running agent, gateway, and notifier,
- a demo README that explains prerequisites, outputs, verification, and failure modes.

The automatic workflow SHALL remain the canonical unattended path and SHALL keep its existing non-interactive gateway execution model.

The stepwise workflow SHALL use a watchable auxiliary tmux gateway window so the operator can observe the live gateway console through the demo-owned `watch-gateway` command while separately attaching to the agent TUI.

#### Scenario: Automatic workflow runs the full single-agent flow
- **WHEN** an operator runs the demo automatic workflow for one supported tool
- **THEN** the workflow performs project initialization, specialist creation, mailbox setup, TUI launch, gateway attach, notifier enablement, message delivery, verification, and cleanup from the selected output root

#### Scenario: Stepwise workflow starts with a watchable gateway console
- **WHEN** an operator runs the stepwise `start` command for one supported tool
- **THEN** the workflow preserves demo-owned state under the selected output root
- **AND THEN** it attaches the gateway in a watchable auxiliary tmux window for that live demo session
- **AND THEN** the operator can subsequently use `attach`, `watch-gateway`, `send`, `notifier ...`, `verify`, and `stop` against that same persisted demo root
