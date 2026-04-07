## MODIFIED Requirements

### Requirement: Agent definition directory layout documented

The getting-started section SHALL include a page documenting the default Houmao project overlay rooted at `.houmao/` beneath the working directory, including:

- `.houmao/houmao-config.toml`
- `.houmao/.gitignore`
- `.houmao/agents/skills/<skill>/`
- `.houmao/agents/roles/<role>/system-prompt.md`
- `.houmao/agents/presets/<recipe>.yaml`
- `.houmao/agents/launch-profiles/<profile>.yaml`
- `.houmao/agents/tools/<tool>/adapter.yaml`
- `.houmao/agents/tools/<tool>/setups/<setup>/`
- `.houmao/agents/tools/<tool>/auth/<auth>/`
- optional `.houmao/agents/compatibility-profiles/`
- optional `.houmao/mailbox/`

That page SHALL explain the purpose of each subdirectory and SHALL make clear that the `.houmao/` overlay is local-only by default.
That page SHALL document `HOUMAO_PROJECT_OVERLAY_DIR` as an absolute-path env override for selecting the overlay directory directly in CI or controlled automation.
That page SHALL document `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` as an ambient discovery-mode env where `ancestor` remains the default and `cwd_only` restricts ambient lookup to `<cwd>/.houmao/houmao-config.toml`.

That page SHALL distinguish:

- `project agents ...` as the low-level filesystem-oriented project source surface,
- `project easy ...` as the higher-level specialist, easy-profile, and instance UX,
- `project mailbox ...` as the project-scoped mailbox-root wrapper.

That page SHALL explain that the canonical low-level source object is the named recipe and that recipe files projected under `.houmao/agents/presets/` carry `role`, `tool`, and `setup` in their content rather than deriving those identities from the directory path. The page SHALL state that `project agents recipes ...` is the canonical CLI surface for those resources and that `project agents presets ...` remains a compatibility alias that operates on the same files.

That page SHALL explain that reusable birth-time launch profiles project under `.houmao/agents/launch-profiles/<profile>.yaml`, that easy profiles and explicit launch profiles share the same underlying catalog model, and that the explicit lane is administered through `project agents launch-profiles ...`.

That page SHALL make clear that `.houmao/agents/compatibility-profiles/` is optional specialized metadata and is not created by default during `project init`.

That page SHALL link to `docs/getting-started/launch-profiles.md` for the shared conceptual model when readers want to understand the easy-versus-explicit lane split rather than just the directory layout.

#### Scenario: Reader can initialize and interpret a new local Houmao project overlay
- **WHEN** a reader follows the agent definition directory page
- **THEN** they understand that `houmao-mgr project init` creates the local `.houmao/` overlay by default
- **AND THEN** they understand that `HOUMAO_PROJECT_OVERLAY_DIR` can redirect the overlay directory directly for CI
- **AND THEN** they understand that `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=cwd_only` can keep ambient overlay discovery scoped to the current working directory
- **AND THEN** they understand that recipe files projected under `.houmao/agents/presets/` carry `role`, `tool`, and `setup` in their content, that `project agents recipes ...` is the canonical authoring surface, and that `project agents presets ...` remains a compatibility alias
- **AND THEN** they understand that launch-profile files projected under `.houmao/agents/launch-profiles/` are reusable birth-time configuration shared between easy and explicit authoring lanes
- **AND THEN** they understand that `.houmao/agents/compatibility-profiles/` is created only when explicitly enabled
- **AND THEN** they understand that `.houmao/mailbox/` is a project-local mailbox root created only when mailbox workflows are enabled explicitly
- **AND THEN** they understand which files are local-only, including the whole `.houmao/` overlay and `tools/<tool>/auth/`

#### Scenario: Reader is sent to the launch-profiles guide for the conceptual model
- **WHEN** a reader needs to understand the easy-versus-explicit launch-profile lane split rather than the projection layout
- **THEN** the agent-definition page links them to `docs/getting-started/launch-profiles.md`

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
- mention `houmao-mgr agents launch --launch-profile <name>` as the saved-launch-profile alternative and link readers to `docs/getting-started/launch-profiles.md` for the shared conceptual model and to `docs/reference/cli/houmao-mgr.md` for the canonical CLI options,
- show follow-up control targeted by `--agent-name` or `--agent-id`,
- use `houmao-mgr agents stop` for shutdown,
- avoid presenting `--manifest`, `--session-id`, or `agents terminate` as the primary `houmao-mgr` workflow,
- present both workflows completely without truncation (added requirement),
- describe the canonical low-level source object as a recipe and use `project agents recipes ...` when teaching named source authoring inspection, while preserving `project agents presets ...` as the compatibility alias when the example relies on the legacy verb explicitly.

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

#### Scenario: Quickstart mentions `agents launch --launch-profile` and links to the launch-profiles guide

- **WHEN** a reader reaches the managed-launch step in the build-based workflow
- **THEN** the quickstart shows `houmao-mgr agents launch --launch-profile <name>` as the saved-profile alternative to `--agents <selector>`
- **AND THEN** the page links to `docs/getting-started/launch-profiles.md` for the shared conceptual model

#### Scenario: Quickstart uses recipes vocabulary for low-level source authoring

- **WHEN** a reader reaches the inspection step in the build-based workflow
- **THEN** the example commands use `project agents recipes get` for canonical recipe inspection
- **AND THEN** any reference to `project agents presets ...` is described as a compatibility alias rather than as the canonical authoring surface
