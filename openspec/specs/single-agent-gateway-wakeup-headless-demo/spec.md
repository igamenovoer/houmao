# single-agent-gateway-wakeup-headless-demo Specification

## Purpose
TBD - created by archiving change add-single-agent-gateway-wakeup-headless-demo. Update Purpose after archive.
## Requirements
### Requirement: `scripts/demo/` SHALL publish a supported `single-agent-gateway-wakeup-headless` demo

The repository SHALL publish a supported runnable demo under `scripts/demo/single-agent-gateway-wakeup-headless/` and SHALL present it from `scripts/demo/README.md` as part of the maintained demo surface.

The maintained operator surface SHALL treat this pack as separate from the existing `single-agent-mail-wakeup/` TUI demo rather than broadening the TUI demo contract to cover headless behavior.

#### Scenario: Maintainer inspects the supported demo index
- **WHEN** a maintainer reads `scripts/demo/README.md`
- **THEN** the README identifies `single-agent-gateway-wakeup-headless/` as a supported runnable demo
- **AND THEN** it continues to present `single-agent-mail-wakeup/` as the separate supported TUI specialist demo

### Requirement: The demo SHALL keep project files and redirected overlay state under the demo output root

Each run of `scripts/demo/single-agent-gateway-wakeup-headless/` SHALL keep all generated state under one canonical demo-owned output root. Normal operator usage SHALL default that root to `scripts/demo/single-agent-gateway-wakeup-headless/outputs/`.

That output root SHALL contain:

- a copied project worktree under `project/`,
- a redirected Houmao project overlay under `overlay/`,
- demo-owned registry, control, log, delivery, and evidence artifacts under sibling directories.

The demo SHALL run project-aware commands from the copied project root while exporting `HOUMAO_PROJECT_OVERLAY_DIR` as the absolute path to the sibling `overlay/` directory.

The demo SHALL preserve reusable overlay-backed specialist state across fresh runs, including overlay-backed auth, setup, specialist metadata, managed content, and generated agent-definition projections.

The demo SHALL reset ephemeral run-local state on a fresh `start`, including the copied project, overlay-local mailbox contents, overlay-local runtime state, overlay-local jobs state, logs, deliveries, and evidence.

#### Scenario: Operator runs the demo with the canonical output root
- **WHEN** an operator starts the headless demo for one supported tool
- **THEN** the run uses `scripts/demo/single-agent-gateway-wakeup-headless/outputs/` as the canonical managed output root
- **AND THEN** it creates or refreshes the copied project under `outputs/project/`
- **AND THEN** it creates or reuses the redirected overlay under `outputs/overlay/`
- **AND THEN** all generated demo-owned state remains under that canonical output root

#### Scenario: Fresh start preserves specialists but resets overlay-local ephemeral state
- **WHEN** an operator starts a new run after a prior run has already populated the demo overlay
- **THEN** the demo preserves reusable overlay-backed specialist and auth/setup state under `outputs/overlay/`
- **AND THEN** it resets `outputs/project/`, `outputs/registry/`, `outputs/logs/`, `outputs/deliveries/`, `outputs/evidence/`, and the overlay-local `runtime/`, `jobs/`, and `mailbox/` state under `outputs/overlay/`
- **AND THEN** the operator does not need to recreate the project-easy specialist only because a fresh run is starting

### Requirement: The demo SHALL support Claude Code and Codex headless lanes through `project easy`

The supported demo SHALL expose three maintained lanes:

- Claude Code headless
- Codex headless
- Gemini headless

For each maintained lane, the demo SHALL:

- import or materialize the expected project-local auth bundle,
- create or reuse one specialist through `houmao-mgr project easy specialist create`,
- launch one headless instance through `houmao-mgr project easy instance launch --headless`.

The Gemini lane SHALL use the maintained Gemini headless contract already supported by project-local Gemini auth and easy-specialist flows, including API-key auth with optional `GOOGLE_GEMINI_BASE_URL` and OAuth auth via `oauth_creds.json`.

The demo SHALL persist the selected tool in canonical demo state rather than encoding it in a tool-specific output-root path.

The maintained demo contract SHALL follow supported unattended headless launch posture and SHALL NOT claim unsupported maintained lanes merely because a backend exists.

#### Scenario: Claude headless lane starts through project easy
- **WHEN** an operator runs the demo for tool `claude`
- **THEN** the demo creates or reuses a project-local Claude auth bundle under the redirected overlay
- **AND THEN** it creates or reuses a Claude specialist through `houmao-mgr project easy specialist create`
- **AND THEN** it launches one Claude headless instance through `houmao-mgr project easy instance launch --headless`
- **AND THEN** the selected tool is persisted in canonical demo state under the shared output root

#### Scenario: Codex headless lane starts through project easy
- **WHEN** an operator runs the demo for tool `codex`
- **THEN** the demo creates or reuses a project-local Codex auth bundle under the redirected overlay
- **AND THEN** it creates or reuses a Codex specialist through `houmao-mgr project easy specialist create`
- **AND THEN** it launches one Codex headless instance through `houmao-mgr project easy instance launch --headless`
- **AND THEN** the selected tool is persisted in canonical demo state under the shared output root

#### Scenario: Gemini headless lane starts through project easy
- **WHEN** an operator runs the demo for tool `gemini`
- **THEN** the demo creates or reuses a project-local Gemini auth bundle under the redirected overlay using one maintained Gemini auth family
- **AND THEN** it creates or reuses a Gemini specialist through `houmao-mgr project easy specialist create`
- **AND THEN** it launches one Gemini headless instance through `houmao-mgr project easy instance launch --headless`
- **AND THEN** the selected tool is persisted in canonical demo state under the shared output root

### Requirement: The stepwise demo SHALL keep a tmux-backed headless session with separate agent and gateway windows

The stepwise headless workflow SHALL keep the managed agent inside one demo-owned tmux session even though the runtime surface is headless.

The primary agent surface and the live gateway surface SHALL remain separately inspectable within that tmux session. The headless agent SHALL run in the primary agent window, and the gateway SHALL attach in a separate watchable auxiliary window.

`attach` SHALL resolve the persisted active demo state and re-attach the operator to the live demo tmux session for the selected tool lane.

`watch-gateway` SHALL resolve the persisted active demo state, query the authoritative live gateway tmux window metadata, and print the gateway console by polling that tmux pane rather than requiring the operator to enter tmux and discover the gateway window manually.

#### Scenario: Stepwise start creates a headless tmux session with a separate gateway window
- **WHEN** an operator runs the stepwise `start` command for one supported tool
- **THEN** the workflow launches a headless managed-agent instance inside one demo-owned tmux session
- **AND THEN** it attaches the gateway in a separate watchable auxiliary tmux window for that same live demo session
- **AND THEN** the resulting active demo state is sufficient for later `attach` and `watch-gateway` follow-up commands

#### Scenario: Operator re-attaches to the live headless session after stepwise start
- **WHEN** an operator runs `scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh attach` for an active stepwise demo root
- **THEN** the command resolves the persisted active demo state for that root
- **AND THEN** it attaches to the live demo tmux session without requiring the operator to copy a raw tmux command from prior JSON output

#### Scenario: Operator watches the gateway console without manual tmux window discovery
- **WHEN** an operator runs `scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh watch-gateway` for an active stepwise demo root
- **THEN** the command resolves the authoritative gateway tmux window for that active demo
- **AND THEN** it prints the gateway console output by polling that tmux pane
- **AND THEN** it fails clearly when no active watchable gateway window exists

### Requirement: The stepwise demo SHALL expose message injection and notifier control commands

The supported stepwise/manual surface of `scripts/demo/single-agent-gateway-wakeup-headless/` SHALL expose operator-facing commands for:

- `send`
- `watch-gateway`
- `notifier status`
- `notifier on`
- `notifier off`
- `notifier set-interval`

The implementation MAY retain `manual-send` as a compatibility alias, but the maintained README and operator workflow SHALL teach `send` as the primary message-injection command.

The `notifier ...` subcommands SHALL reuse the existing gateway mail-notifier behavior for the running demo instance and SHALL allow the operator to inspect current notifier state, enable or disable notifier polling, and update the polling interval.

#### Scenario: Operator injects an additional message with `send`
- **WHEN** an operator runs `scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh send` for an active stepwise demo root
- **THEN** the command injects one operator-originated filesystem-backed mailbox message for the running demo instance
- **AND THEN** it persists the delivery artifact and delivery metadata under the selected output root

#### Scenario: Operator manages notifier state from the demo pack
- **WHEN** an operator runs `scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh notifier status`, `on`, `off`, or `set-interval`
- **THEN** the command targets the running demo instance resolved from persisted demo state
- **AND THEN** it reports or updates the gateway mail-notifier state for that live demo session

### Requirement: The demo SHALL teach the single-agent headless gateway wake-up workflow from project creation through notifier wake-up

The supported demo SHALL present one narrow single-agent workflow:

1. initialize or reuse the redirected project overlay,
2. initialize the project mailbox under that overlay,
3. register the agent and operator mailbox identities,
4. launch one project-easy headless instance,
5. attach one live gateway,
6. enable gateway mail-notifier polling,
7. inject one operator-originated filesystem-backed mailbox message,
8. observe the headless agent wake and process that message.

The demo SHALL include:

- one automatic one-shot workflow,
- one stepwise workflow that preserves canonical demo state and supports direct operator interaction with the running headless session, gateway, and notifier,
- a demo README that explains prerequisites, outputs, verification, and failure modes.

The automatic workflow SHALL remain the canonical unattended path and SHALL keep its existing non-interactive gateway execution model.

The stepwise workflow SHALL use canonical persisted demo state under `outputs/` so that follow-up commands such as `attach`, `watch-gateway`, `send`, `notifier ...`, `inspect`, `verify`, and `stop` do not require operators to specify a tool-specific demo output root during normal usage.

#### Scenario: Automatic workflow runs the full single-agent headless flow
- **WHEN** an operator runs the demo automatic workflow for one supported tool
- **THEN** the workflow performs project initialization or reuse, specialist preparation or reuse, mailbox setup, headless launch, gateway attach, notifier enablement, message delivery, verification, and cleanup from the canonical output root

#### Scenario: Stepwise workflow starts with persisted demo state and a watchable gateway console
- **WHEN** an operator runs the stepwise `start` command for one supported tool
- **THEN** the workflow records the selected tool and active run details in canonical persisted demo state under `outputs/control/demo_state.json`
- **AND THEN** it attaches the gateway in a watchable auxiliary tmux window for that live demo session
- **AND THEN** the operator can subsequently use `attach`, `watch-gateway`, `send`, `notifier ...`, `inspect`, `verify`, and `stop` without passing `--demo-output-dir` during normal usage

### Requirement: The demo SHALL verify completion through gateway evidence, headless managed-agent evidence, output creation, and actor-scoped unread completion

The supported demo SHALL treat success as all of the following:

- gateway notifier evidence shows unread work was detected and processed,
- the headless managed-agent inspection surface records execution evidence for the delivered work,
- the agent creates the requested artifact under the copied project's `tmp/` directory,
- `houmao-mgr agents mail check --unread-only` reaches zero actionable unread messages for the selected agent.

`houmao-mgr project mailbox messages list|get` SHALL remain structural inspection only within this demo and SHALL be used to corroborate message identity, folder, projection path, canonical path, sender, recipients, subject, body, and attachments rather than authoritative read-state.

#### Scenario: Demo verifies actor-scoped unread completion
- **WHEN** the demo verifies one completed run after the delivered message is processed
- **THEN** it checks `houmao-mgr agents mail check --unread-only` for zero actionable unread messages
- **AND THEN** it does not require project-mailbox inspection to report a global `read: true` state

#### Scenario: Demo verifies headless managed-agent evidence without relying on TUI posture
- **WHEN** the demo verifies one completed headless run after the delivered message is processed
- **THEN** it collects managed-agent headless evidence from existing managed-agent inspection surfaces or durable turn artifacts
- **AND THEN** it uses that evidence as the canonical runtime-observation complement to gateway notifier evidence
- **AND THEN** it does not require parser-owned TUI ready-posture evidence in order to declare the headless run complete

#### Scenario: Demo verifies the requested project artifact
- **WHEN** the delivered message asks the agent to write one deterministic file
- **THEN** the demo verifies that file under `<output-root>/project/tmp/`
- **AND THEN** it verifies that the created artifact matches the expected deterministic content for that run
