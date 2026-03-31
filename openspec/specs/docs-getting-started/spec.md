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

The getting-started section SHALL include a page documenting the default Houmao project overlay rooted at `.houmao/` beneath the working directory, including:

- `.houmao/houmao-config.toml`
- `.houmao/.gitignore`
- `.houmao/agents/skills/<skill>/`
- `.houmao/agents/roles/<role>/system-prompt.md`
- `.houmao/agents/roles/<role>/presets/<tool>/<setup>.yaml`
- `.houmao/agents/tools/<tool>/adapter.yaml`
- `.houmao/agents/tools/<tool>/setups/<setup>/`
- `.houmao/agents/tools/<tool>/auth/<auth>/`
- optional `.houmao/agents/compatibility-profiles/`
- optional `.houmao/mailbox/`

That page SHALL explain the purpose of each subdirectory and SHALL make clear that the `.houmao/` overlay is local-only by default.
That page SHALL document `HOUMAO_PROJECT_OVERLAY_DIR` as an absolute-path env override for selecting the overlay directory directly in CI or controlled automation.

That page SHALL distinguish:

- `project agents ...` as the low-level filesystem-oriented project source surface,
- `project easy ...` as the higher-level specialist and instance UX,
- `project mailbox ...` as the project-scoped mailbox-root wrapper.

That page SHALL make clear that `.houmao/agents/compatibility-profiles/` is optional specialized metadata and is not created by default during `project init`.

#### Scenario: Reader can initialize and interpret a new local Houmao project overlay
- **WHEN** a reader follows the agent definition directory page
- **THEN** they understand that `houmao-mgr project init` creates the local `.houmao/` overlay by default
- **AND THEN** they understand that `HOUMAO_PROJECT_OVERLAY_DIR` can redirect the overlay directory directly for CI
- **AND THEN** they understand that `.houmao/agents/compatibility-profiles/` is created only when explicitly enabled
- **AND THEN** they understand that `.houmao/mailbox/` is a project-local mailbox root created only when mailbox workflows are enabled explicitly
- **AND THEN** they understand which files are local-only, including the whole `.houmao/` overlay and `tools/<tool>/auth/`

### Requirement: Repo-owned onboarding docs use the catalog-backed `.houmao` overlay and `.houmao`-only ambient agent-definition defaults
Repo-owned onboarding docs that explain local build and launch workflows SHALL describe the catalog-backed `.houmao` overlay and ambient agent-definition resolution as:

1. explicit CLI `--agent-def-dir`,
2. `AGENTSYS_AGENT_DEF_DIR`,
3. the overlay directory selected by `HOUMAO_PROJECT_OVERLAY_DIR`,
4. nearest ancestor `.houmao/houmao-config.toml`,
5. default fallback `<cwd>/.houmao/agents`.

Those docs SHALL describe `HOUMAO_PROJECT_OVERLAY_DIR` as an absolute-path env override for selecting the overlay directory directly, and SHALL describe `houmao-config.toml` as the discovery anchor within the selected overlay directory.
Those docs SHALL describe `agents/` as the compatibility projection used when file-tree consumers need a local agent-definition root.
They SHALL NOT describe `.agentsys` as a supported default or fallback path for current workflows.

At minimum, this requirement SHALL apply to:

- `README.md` sections that explain local project initialization and build-based workflows,
- getting-started pages that explain the `.houmao/` overlay and local launch flow,
- current CLI-facing onboarding pages linked from getting-started content.

#### Scenario: Reader sees the catalog-backed `.houmao` overlay and `HOUMAO_PROJECT_OVERLAY_DIR` precedence in onboarding docs
- **WHEN** a reader follows the repo-owned onboarding docs for local build and launch
- **THEN** the docs describe the catalog-backed `.houmao` overlay with `houmao-config.toml` as the discovery anchor
- **AND THEN** the docs describe `HOUMAO_PROJECT_OVERLAY_DIR` between `AGENTSYS_AGENT_DEF_DIR` and nearest-ancestor discovery
- **AND THEN** the docs describe ambient agent-definition lookup using `houmao-config.toml` and the default `<cwd>/.houmao/agents`
- **AND THEN** the docs do not present `<cwd>/.agentsys/agents` as a supported fallback

#### Scenario: Reader is not told to preserve `.agentsys` during local setup
- **WHEN** a reader follows the build-based project setup guidance
- **THEN** the docs tell them to initialize or use `.houmao/`
- **AND THEN** the docs do not tell them to create, copy, or retain `.agentsys/agents` as part of the supported setup flow

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
- avoid presenting `--manifest`, `--session-id`, or `agents terminate` as the primary `houmao-mgr` workflow.

The quickstart section covering `agents join` SHALL include a Mermaid sequence diagram illustrating the join pipeline: operator starts a provider TUI in tmux, runs `agents join`, and Houmao wraps the session with manifest, gateway, and registry artifacts.

#### Scenario: Quickstart presents agents join as the simplest entry point

- **WHEN** a reader opens the quickstart section in `README.md`
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

### Requirement: Getting-started docs use tool-oriented project auth commands
Repo-owned getting-started guidance for the repo-local `.houmao/` project overlay SHALL describe project-local auth management through `houmao-mgr project agents tools <tool> auth ...` rather than through `project credential ...`.

At minimum, the agent-definition layout guide SHALL explain that the CLI mirrors `.houmao/agents/tools/<tool>/auth/<name>/`, and quickstart-style examples SHALL use the supported `project agents tools` command family when showing local auth-bundle creation or inspection.

#### Scenario: Reader sees matching CLI and directory-tree nouns
- **WHEN** a reader follows the project-overlay and agent-definition getting-started docs
- **THEN** the docs use `houmao-mgr project agents tools <tool> auth ...` when describing local auth bundles
- **AND THEN** the surrounding explanation matches the documented directory tree under `.houmao/agents/tools/<tool>/auth/<name>/`

### Requirement: Getting-started docs explain the low-level and high-level project views
Repo-owned getting-started guidance for the repo-local `.houmao/` project overlay SHALL explain when to use `project easy`, `project agents`, and `project mailbox`.

At minimum:

- low-level auth management examples SHALL use `houmao-mgr project agents tools <tool> auth ...`,
- higher-level reusable agent examples SHALL use `houmao-mgr project easy specialist ...`,
- project-local mailbox examples SHALL use `houmao-mgr project mailbox ...` when teaching repo-scoped mailbox-root workflows.

#### Scenario: Reader sees the revised project nouns in docs
- **WHEN** a reader follows the project-overlay and quickstart getting-started docs
- **THEN** the docs use `houmao-mgr project agents tools <tool> auth ...` for low-level project auth bundles
- **AND THEN** the docs use `houmao-mgr project easy specialist ...` for the simpler project-local authoring path
- **AND THEN** the docs use `houmao-mgr project mailbox ...` when describing repo-scoped mailbox-root operations

### Requirement: Getting-started docs point to the supported minimal demo

The getting-started documentation SHALL point readers to `scripts/demo/minimal-agent-launch/` as the supported runnable companion to the canonical agent-definition and managed-agent launch documentation.

#### Scenario: Agent-definition docs link to the runnable demo

- **WHEN** a reader finishes the getting-started explanation of the canonical `agents/` directory layout
- **THEN** the page points them to `scripts/demo/minimal-agent-launch/` for a small runnable example that uses the same `skills/`, `roles/`, and `tools/` structure

#### Scenario: Quickstart docs link to the runnable demo

- **WHEN** a reader follows the getting-started quickstart for preset-backed build and launch
- **THEN** the page points them to `scripts/demo/minimal-agent-launch/` as the maintained minimal end-to-end example for local launch

