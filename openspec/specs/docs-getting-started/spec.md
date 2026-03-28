# docs-getting-started Specification

## Purpose
Define the documentation requirements for Houmao getting-started documentation.

## Requirements

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

### Requirement: Quickstart guide covers build and launch

The getting-started section SHALL include a quickstart page showing how to build a brain home and start, prompt, and stop a session using the current `houmao-mgr` managed-agent workflow, derived from the CLI command groups in `srv_ctrl/commands/`.

The quickstart SHALL:

- present the `houmao-mgr agents join` adoption workflow as the simplest entry point before the build-and-launch workflow,
- use `houmao-mgr brains build` when teaching build-phase concepts,
- use `houmao-mgr agents launch --agents <selector> --agent-name <name>` for the primary managed launch path,
- show follow-up control targeted by `--agent-name` or `--agent-id`,
- use `houmao-mgr agents stop` for shutdown,
- avoid presenting `--manifest`, `--session-id`, or `agents terminate` as the primary `houmao-mgr` workflow.

The quickstart section covering `agents join` SHALL include a Mermaid sequence diagram illustrating the join pipeline: operator starts a provider TUI in tmux, runs `agents join`, and Houmao wraps the session with manifest, gateway, and registry artifacts.

#### Scenario: Quickstart presents agents join as the simplest entry point

- **WHEN** a reader opens the quickstart section in `README.md`
- **THEN** the first workflow shown is `houmao-mgr agents join` adopting an existing tmux-backed provider session
- **AND THEN** the join workflow appears before the build-and-launch workflow
- **AND THEN** the join section includes a Mermaid sequence diagram showing the adoption flow

#### Scenario: Quickstart uses current managed-agent selectors

- **WHEN** a reader follows the quickstart command examples
- **THEN** the page shows `houmao-mgr` commands that target managed agents with `--agents`, `--agent-name`, or `--agent-id`
- **AND THEN** the page does not instruct the reader to use `--session-id` for the main managed-agent flow

#### Scenario: Quickstart uses current stop command

- **WHEN** a reader reaches the shutdown step
- **THEN** the page documents `houmao-mgr agents stop`
- **AND THEN** the page does not describe `houmao-mgr agents terminate` as the supported shutdown command

### Requirement: README documents agents join as a first-class adoption path

The project `README.md` SHALL describe `houmao-mgr agents join` as a working, first-class adoption path for bringing an already-running provider TUI into Houmao control. The README SHALL NOT describe bring-your-own-process adoption as a future design goal or claim that management commands assume the session was launched by `houmao-mgr`.

The README SHALL include at minimum:

- a "Quick Start: Adopt an Existing Session" section before the build-based workflow,
- concrete command examples for TUI join (minimal), TUI join with relaunch options, and headless join,
- a Mermaid sequence diagram showing the join pipeline (operator → tmux → provider → agents join → managed agent envelope),
- a brief explanation of what the operator gets after joining: registry discovery, gateway capability, prompt/interrupt commands, mailbox support.

#### Scenario: New user finds the join workflow in README before build-based workflow

- **WHEN** a new user reads the README from top to bottom
- **THEN** they encounter the `agents join` adoption workflow before the build-brain / start-session workflow
- **AND THEN** the join section shows concrete commands they can run immediately if they already have a provider TUI in tmux

#### Scenario: README no longer claims adoption is a future design goal

- **WHEN** a reader reads the "How Agents Join Your Workflow" paragraph
- **THEN** the paragraph describes both managed launch and `agents join` as working paths
- **AND THEN** the paragraph does not contain language like "today, the management commands assume the session was launched by `houmao-mgr`"

### Requirement: Getting-started docs point to the supported minimal demo

The getting-started documentation SHALL point readers to `scripts/demo/minimal-agent-launch/` as the supported runnable companion to the canonical agent-definition and managed-agent launch documentation.

#### Scenario: Agent-definition docs link to the runnable demo

- **WHEN** a reader finishes the getting-started explanation of the canonical `agents/` directory layout
- **THEN** the page points them to `scripts/demo/minimal-agent-launch/` for a small runnable example that uses the same `skills/`, `roles/`, and `tools/` structure

#### Scenario: Quickstart docs link to the runnable demo

- **WHEN** a reader follows the getting-started quickstart for preset-backed build and launch
- **THEN** the page points them to `scripts/demo/minimal-agent-launch/` as the maintained minimal end-to-end example for local launch
