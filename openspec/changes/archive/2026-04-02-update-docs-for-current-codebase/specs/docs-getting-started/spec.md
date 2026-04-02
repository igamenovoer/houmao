## ADDED Requirements

### Requirement: Quickstart covers both workflows end-to-end without truncation

The quickstart page at `docs/getting-started/quickstart.md` SHALL present both workflows completely:

- **Workflow 1 (Join)**: from `agents join` through to managed agent control, with no truncation.
- **Workflow 2 (Build from `.houmao/` overlay)**: from `project init` through `project easy specialist create`, `agents launch`, prompt/control, and `agents stop`, with no truncation.

Each workflow SHALL include all steps needed for a reader to complete the workflow without guessing or consulting other pages.

#### Scenario: Workflow 1 is complete

- **WHEN** a reader follows Workflow 1 (Join) in the quickstart
- **THEN** they can complete the entire join → control → stop cycle without encountering a truncated section

#### Scenario: Workflow 2 is complete

- **WHEN** a reader follows Workflow 2 (Build) in the quickstart
- **THEN** they can complete the entire init → specialist create → launch → prompt → stop cycle without encountering a truncated section

### Requirement: Getting-started links to easy-specialist guide

The getting-started section SHALL link to the new easy-specialist conceptual guide from both the quickstart page and the agent-definitions page, so readers can deepen their understanding of the specialist model after encountering it in the quickstart workflow.

#### Scenario: Quickstart links to easy-specialist guide

- **WHEN** a reader encounters `project easy specialist create` in the quickstart
- **THEN** the page includes a link to `docs/getting-started/easy-specialists.md` for a deeper explanation of the model

## MODIFIED Requirements

### Requirement: Quickstart guide covers build and launch

The getting-started section SHALL include a quickstart page showing how to build a brain home and start, prompt, and stop a session using the current `houmao-mgr` managed-agent workflow, derived from the CLI command groups in `srv_ctrl/commands/`.

The quickstart SHALL:

- present the `houmao-mgr agents join` adoption workflow as the simplest entry point before the build-and-launch workflow,
- start the build-based workflow with `houmao-mgr project init`,
- use `houmao-mgr project easy specialist create ...` as the primary project-local authoring path before falling back to `project agents ...` for low-level maintenance,
- describe `--credential` as optional for the higher-level specialist workflow and explain the derived default naming behavior when the example relies on it,
- avoid describing `--system-prompt` as required for the higher-level specialist workflow,
- use project-local default agent-definition resolution rooted at `.houmao/houmao-config.toml` for the build-based workflow rather than instructing readers to manually copy `.agentsys/agents`,
- use `houmao-mgr brains build` when teaching build-phase concepts,
- use `houmao-mgr agents launch --agents <selector> --agent-name <name>` for the primary managed launch path,
- show follow-up control targeted by `--agent-name` or `--agent-id`,
- use `houmao-mgr agents stop` for shutdown,
- avoid presenting `--manifest`, `--session-id`, or `agents terminate` as the primary `houmao-mgr` workflow,
- present both workflows completely without truncation (added requirement).

The quickstart section covering `agents join` SHALL include a Mermaid sequence diagram illustrating the join pipeline: operator starts a provider TUI in tmux, runs `agents join`, and Houmao wraps the session with manifest, gateway, and registry artifacts.

#### Scenario: Quickstart presents agents join as the simplest entry point

- **WHEN** a reader opens the quickstart section
- **THEN** the first workflow shown is `houmao-mgr agents join` adopting an existing tmux-backed provider session
- **AND THEN** the join workflow appears before the build-and-launch workflow
- **AND THEN** the join section includes a Mermaid sequence diagram showing the adoption flow

#### Scenario: Build-based quickstart uses the higher-level project authoring path
- **WHEN** a reader follows the build-based quickstart workflow
- **THEN** the first setup command is `houmao-mgr project init`
- **AND THEN** the workflow uses `houmao-mgr project easy specialist create ...` as the primary project-local authoring path
- **AND THEN** the quickstart explains the derived default credential naming when `--credential` is omitted
- **AND THEN** the workflow does not describe `--system-prompt` as required for specialist creation
- **AND THEN** the workflow does not tell the reader to manually copy or assemble `.agentsys/agents` before build or launch

#### Scenario: Quickstart uses current managed-agent selectors

- **WHEN** a reader follows the quickstart command examples
- **THEN** the page shows `houmao-mgr` commands that target managed agents with `--agents`, `--agent-name`, or `--agent-id`
- **AND THEN** the page does not instruct the reader to use `--session-id` for the main managed-agent flow

#### Scenario: Quickstart uses current stop command

- **WHEN** a reader reaches the shutdown step
- **THEN** the page documents `houmao-mgr agents stop`
- **AND THEN** the page does not describe `houmao-mgr agents terminate` as the supported shutdown command

#### Scenario: Both workflows are complete and untruncated

- **WHEN** a reader reaches the end of either workflow
- **THEN** the workflow completes with a shutdown step and optional next-steps links
- **AND THEN** no section is cut off mid-content
