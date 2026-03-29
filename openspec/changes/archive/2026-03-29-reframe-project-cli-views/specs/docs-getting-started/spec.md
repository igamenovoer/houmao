## MODIFIED Requirements

### Requirement: Agent definition directory layout documented

The getting-started section SHALL include a page documenting the repo-local Houmao project overlay rooted at `.houmao/`, including:

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

The page SHALL distinguish:

- `project agents ...` as the low-level filesystem-oriented project source surface,
- `project easy ...` as the higher-level specialist and instance UX,
- `project mailbox ...` as the project-scoped mailbox-root wrapper.

#### Scenario: Reader can initialize and interpret a new local Houmao project overlay
- **WHEN** a reader follows the agent definition directory page
- **THEN** they understand that `houmao-mgr project init` creates the local `.houmao/` overlay and local `agents/` source tree
- **AND THEN** they understand that `.houmao/mailbox/` is a project-local mailbox root created only when mailbox workflows are enabled explicitly
- **AND THEN** they understand which files are local-only, including the whole `.houmao/` overlay and `tools/<tool>/auth/`

### Requirement: Quickstart guide covers build and launch

The getting-started section SHALL include a quickstart page showing how to build a brain home and start, prompt, and stop a session using the current `houmao-mgr` managed-agent workflow, derived from the CLI command groups in `srv_ctrl/commands/`.

The quickstart SHALL:

- present the `houmao-mgr agents join` adoption workflow as the simplest entry point before the build-and-launch workflow,
- start the build-based workflow with `houmao-mgr project init`,
- use `houmao-mgr project easy specialist create ...` as the primary project-local authoring path before falling back to `project agents ...` for low-level maintenance,
- use project-local default agent-definition resolution rooted at `.houmao/houmao-config.toml` for the build-based workflow rather than instructing readers to manually copy `.agentsys/agents`,
- use `houmao-mgr brains build` when teaching build-phase concepts,
- use `houmao-mgr agents launch --agents <selector> --agent-name <name>` for the primary managed launch path,
- show follow-up control targeted by `--agent-name` or `--agent-id`,
- use `houmao-mgr agents stop` for shutdown,
- avoid presenting `--manifest`, `--session-id`, or `agents terminate` as the primary `houmao-mgr` workflow.

The quickstart section covering `agents join` SHALL include a Mermaid sequence diagram illustrating the join pipeline: operator starts a provider TUI in tmux, runs `agents join`, and Houmao wraps the session with manifest, gateway, and registry artifacts.

#### Scenario: Build-based quickstart uses the higher-level project authoring path
- **WHEN** a reader follows the build-based quickstart workflow
- **THEN** the first setup command is `houmao-mgr project init`
- **AND THEN** the workflow uses `houmao-mgr project easy specialist create ...` as the primary project-local authoring path
- **AND THEN** the workflow does not tell the reader to manually copy or assemble `.agentsys/agents` before build or launch

## ADDED Requirements

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
