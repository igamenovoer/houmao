# docs-getting-started Specification

## Purpose
Define the documentation requirements for Houmao getting-started documentation.
## Requirements
### Requirement: Architecture overview explains two-phase lifecycle

The getting-started section SHALL include an architecture overview document that explains the two-phase lifecycle (build phase → run phase), the agent definition directory model, the backend abstraction, and the current operator-facing CLI surfaces. The content SHALL be derived from `brain_builder.py`, `realm_controller/`, and the current `houmao-mgr` and `houmao-server` command trees. The build-phase mermaid diagram SHALL reference the current manifest schema version (`schema_version=4`).

#### Scenario: Reader understands build-then-run flow

- **WHEN** a reader opens the architecture overview
- **THEN** they find a clear explanation of: (1) build phase producing a BrainManifest from a preset-backed build specification, (2) run phase composing manifest plus role into a LaunchPlan dispatched to a backend, and (3) `houmao-mgr` as the primary operator CLI for the supported workflow

#### Scenario: Manifest schema version is current

- **WHEN** the architecture overview mermaid diagram mentions a manifest schema version
- **THEN** the referenced version SHALL be `4`, matching `SESSION_MANIFEST_SCHEMA_VERSION` in `src/houmao/agents/realm_controller/manifest.py`

#### Scenario: Backend model presented with current operator posture

- **WHEN** the architecture overview describes backends and entrypoints
- **THEN** `local_interactive` is presented as the primary backend, native headless backends are presented as direct CLI alternatives, and CAO-backed backends are described only as legacy or compatibility paths
- **AND THEN** the overview does not present deprecated or compatibility entrypoints as the primary way to operate Houmao

### Requirement: Loop authoring guide cross-references runnable examples

The loop authoring guide SHALL cross-reference the `examples/writer-team/` template as a concrete end-to-end pairwise loop example. The cross-reference SHALL appear near the skill-selection guidance so readers can see a working plan alongside the conceptual explanation.

#### Scenario: Reader discovers writer-team example from loop authoring guide

- **WHEN** a reader is on the loop authoring guide page
- **THEN** they find a visible cross-reference to `examples/writer-team/` with a brief description of what the example demonstrates

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
- optional `.houmao/mailbox/`

That page SHALL explain the purpose of each subdirectory and SHALL make clear that the `.houmao/` overlay is local-only by default.
That page SHALL document `HOUMAO_PROJECT_OVERLAY_DIR` as an absolute-path env override for selecting the overlay directory directly in CI or controlled automation.
That page SHALL document `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` as an ambient discovery-mode env where `ancestor` remains the default and `cwd_only` restricts ambient lookup to `<cwd>/.houmao/houmao-config.toml`.

That page SHALL distinguish:

- `project agents ...` as the low-level filesystem-oriented project source surface,
- `project ...` as the higher-level specialist, project-profile, and instance UX,
- `project mailbox ...` as the project-scoped mailbox-root wrapper.

That page SHALL explain that the canonical low-level source object is the named recipe and that recipe files projected under `.houmao/agents/presets/` carry `role`, `tool`, and `setup` in their content rather than deriving those identities from the directory path. The page SHALL state that `internals native-agent recipes ...` is the canonical CLI surface for those resources and that `project agents presets ...` remains a compatibility alias that operates on the same files.

That page SHALL explain that reusable birth-time launch profiles project under `.houmao/agents/launch-profiles/<profile>.yaml`, that project profiles and native launch dossiers share the same underlying catalog model, and that the explicit lane is administered through `internals native-agent launch-dossiers ...`.

That page SHALL NOT document `.houmao/agents/compatibility-profiles/` as a user-facing project-layout directory or project-init option.

That page SHALL link to `docs/getting-started/launch-profiles.md` for the shared conceptual model when readers want to understand the easy-versus-explicit lane split rather than just the directory layout.

#### Scenario: Reader can initialize and interpret a new local Houmao project overlay
- **WHEN** a reader follows the agent definition directory page
- **THEN** they understand that `houmao-mgr project init` creates the local `.houmao/` overlay by default
- **AND THEN** they understand that `HOUMAO_PROJECT_OVERLAY_DIR` can redirect the overlay directory directly for CI
- **AND THEN** they understand that `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=cwd_only` can keep ambient overlay discovery scoped to the current working directory
- **AND THEN** they understand that recipe files projected under `.houmao/agents/presets/` carry `role`, `tool`, and `setup` in their content, that `internals native-agent recipes ...` is the canonical authoring surface, and that `project agents presets ...` remains a compatibility alias
- **AND THEN** they understand that launch-profile files projected under `.houmao/agents/launch-profiles/` are reusable birth-time configuration shared between easy and explicit authoring lanes
- **AND THEN** they understand that `.houmao/mailbox/` is a project-local mailbox root created only when mailbox workflows are enabled explicitly
- **AND THEN** they understand which files are local-only, including the whole `.houmao/` overlay and `tools/<tool>/auth/`
- **AND THEN** they do not see compatibility-profile bootstrap guidance as part of the maintained project-init workflow

#### Scenario: Reader is sent to the launch-profiles guide for the conceptual model
- **WHEN** a reader needs to understand the easy-versus-explicit launch-profile lane split rather than the projection layout
- **THEN** the agent-definition page links them to `docs/getting-started/launch-profiles.md`

### Requirement: Repo-owned onboarding docs use the catalog-backed `.houmao` overlay and `.houmao`-only ambient agent-definition defaults
Repo-owned onboarding docs that explain local build and launch workflows SHALL describe the catalog-backed `.houmao` overlay and ambient agent-definition resolution as:

1. explicit CLI `--agent-def-dir`,
2. `HOUMAO_NATIVE_AGENT_ROOT`,
3. the overlay directory selected by `HOUMAO_PROJECT_OVERLAY_DIR`,
4. ambient project-overlay discovery controlled by `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`,
5. default fallback `<cwd>/.houmao/agents`.

Those docs SHALL describe `HOUMAO_PROJECT_OVERLAY_DIR` as an absolute-path env override for selecting the overlay directory directly, and SHALL describe `houmao-config.toml` as the discovery anchor within the selected overlay directory.
Those docs SHALL describe `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` as the ambient project-overlay discovery selector, where `ancestor` remains the default and `cwd_only` limits lookup to `<cwd>/.houmao/houmao-config.toml`.
Those docs SHALL describe `agents/` as the compatibility projection used when file-tree consumers need a local agent-definition root.
They SHALL NOT describe `.agentsys` as a supported default or fallback path for current workflows.

At minimum, this requirement SHALL apply to:

- `README.md` sections that explain local project initialization and build-based workflows,
- getting-started pages that explain the `.houmao/` overlay and local launch flow,
- current CLI-facing onboarding pages linked from getting-started content.

#### Scenario: Reader sees the catalog-backed `.houmao` overlay and discovery-mode precedence in onboarding docs
- **WHEN** a reader follows the repo-owned onboarding docs for local build and launch
- **THEN** the docs describe the catalog-backed `.houmao` overlay with `houmao-config.toml` as the discovery anchor
- **AND THEN** the docs describe `HOUMAO_PROJECT_OVERLAY_DIR` as the explicit overlay-root selector
- **AND THEN** the docs describe `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` as the ambient discovery-mode selector with `ancestor` and `cwd_only`
- **AND THEN** the docs describe ambient agent-definition lookup using `houmao-config.toml` and the default `<cwd>/.houmao/agents`
- **AND THEN** the docs do not present `<cwd>/.agentsys/agents` as a supported fallback

#### Scenario: Reader is not told to preserve `.agentsys` during local setup
- **WHEN** a reader follows the build-based project setup guidance
- **THEN** the docs tell them to initialize or use `.houmao/`
- **AND THEN** the docs do not tell them to create, copy, or retain `.agentsys/agents` as part of the supported setup flow

### Requirement: Quickstart guide covers build and launch

The getting-started section SHALL include a quickstart page that teaches the current recommended first-run Houmao workflow as agent-driven use through installed Houmao system skills. The page SHALL help a reader start from their existing CLI-agent surface, install or project Houmao system skills, invoke `houmao-touring`, and ask that agent for a useful managed-agent outcome.

The quickstart SHALL:

- present the user's current CLI agent as the primary operator of Houmao workflows,
- explain that Houmao system skills guide that CLI agent toward maintained `houmao-mgr` command surfaces,
- show the preferred installed-user setup path with `uv tool install houmao`, `tmux` verification, and `npx skills add https://github.com/igamenovoer/houmao-skills` when `npx` and internet access are available,
- show the Houmao-owned `houmao-mgr system-skills install --tool <tool>[,<tool>...]` path for offline, installed-package-local, explicit-home, named-set, subset-skill, symlink/copy, or cleanup needs,
- include a from-source note that source checkout commands use `pixi run houmao-mgr ...` while installed users use `houmao-mgr ...`,
- instruct the reader to start Claude Code, Codex, Kimi, Gemini, or another supported CLI-agent surface from the target project directory and ask for `$houmao-touring start a guided tour`,
- include a first useful agent-mediated prompt that asks the user's CLI agent to create or select a specialist, prepare a reusable project profile when useful, launch a managed agent, send an initial prompt, inspect the result, and stop or leave the agent running according to the user's instruction,
- explain the resulting concepts in user-facing terms: project overlay, specialist, project profile, managed agent, gateway, messaging, inspection, memory, mailbox, and loop follow-up,
- state that manual command examples are the underlying machinery the agent may run, manual fallback for debugging, or source-developer reference rather than the primary first-run path,
- preserve direct command examples for project initialization, specialist/profile authoring, launch, prompt or gateway-backed communication, inspection, and stop in a compact fallback or reference section,
- preserve `agents self join` as the supported adoption workflow for an already-running provider TUI and position it after the primary agent-driven path,
- keep the `agents self join` Mermaid sequence diagram or an equivalent diagram illustrating adoption from provider TUI to managed-agent registry/gateway artifacts,
- use current supported command surfaces such as `houmao-mgr project init`, `houmao-mgr project specialist ...`, `houmao-mgr project profile ...`, `houmao-mgr project agents launch|stop`, `houmao-mgr agents single ...`, `houmao-mgr agents self ...`, and `houmao-mgr system-skills ...`,
- avoid presenting retired or removed surfaces such as `houmao-cli`, standalone `houmao-server`, standalone CAO launcher workflows, `agents terminate`, or manual `.agentsys` setup as current first-run guidance,
- link to `docs/getting-started/system-skills-overview.md`, `docs/getting-started/easy-specialists.md`, `docs/getting-started/launch-profiles.md`, `docs/getting-started/managed-memory-dirs.md`, gateway and mailbox references when those concepts appear, and `docs/reference/cli/houmao-mgr.md` or dedicated CLI reference pages for flag-level details.

The getting-started overview and quickstart SHALL present Kimi Code as a primary supported provider alongside Claude and Codex. Neutral provider lists SHALL order maintained launch-capable providers as Claude, Codex, Kimi, then Gemini; compact three-provider examples and diagrams SHALL use Claude, Codex, and Kimi.

Getting-started docs that introduce Kimi Code SHALL include a Kimi Code 0.11.0 warning that this version does not expose a native system-prompt flag. The warning SHALL tell readers to invoke `houmao-auto-system-prompt` manually before substantive Kimi chat begins when the Houmao system prompt has not been confirmed loaded.

#### Scenario: Quickstart starts with the agent-driven path

- **WHEN** a new reader opens `docs/getting-started/quickstart.md`
- **THEN** the first workflow teaches them to install Houmao and Houmao system skills, start their CLI agent in the target project, and invoke `houmao-touring`
- **AND THEN** the page presents manual `houmao-mgr` command sequences only after the agent-driven entrypoint is established

#### Scenario: Reader sees a first useful managed-agent outcome

- **WHEN** a reader follows the primary quickstart workflow
- **THEN** they see an outcome-oriented prompt they can give to their CLI agent
- **AND THEN** the prompt covers creating or selecting a specialist, preparing a project profile when useful, launching a managed agent, prompting it, inspecting the result, and handling stop or follow-up
- **AND THEN** the page explains those steps as Houmao outcomes rather than requiring the reader to type every command manually

#### Scenario: Source checkout readers understand launcher translation

- **WHEN** a source checkout reader follows the quickstart
- **THEN** the page explains that installed-user examples using `houmao-mgr ...` translate to `pixi run houmao-mgr ...` in the source checkout
- **AND THEN** the page does not require installed users to run `pixi install && pixi shell`

#### Scenario: Manual fallback uses maintained command surfaces

- **WHEN** a reader reaches the manual fallback or underlying-machinery section
- **THEN** the examples use maintained `houmao-mgr` command families for project setup, specialist/profile authoring, launch, prompt or gateway communication, inspection, stop, system-skill installation, and join
- **AND THEN** the examples do not use removed or retired command surfaces as recommended current guidance

#### Scenario: Join is documented as adoption

- **WHEN** a reader already has a provider TUI running in tmux
- **THEN** the quickstart provides an `agents self join` adoption workflow
- **AND THEN** that workflow appears after the primary agent-driven first-run path
- **AND THEN** it includes a Mermaid sequence diagram or equivalent visual showing Houmao wrapping the existing provider session with managed-agent artifacts

### Requirement: Quickstart covers both workflows end-to-end without truncation

The quickstart page at `docs/getting-started/quickstart.md` SHALL present the primary agent-driven workflow and the secondary provider-session adoption workflow completely:

- **Primary workflow (Agent-driven first run)**: from installing Houmao and system skills through invoking `houmao-touring`, requesting a first managed-agent outcome, understanding created project/runtime concepts, and choosing stop or follow-up.
- **Secondary workflow (Join)**: from an already-running provider TUI in tmux through `agents self join`, managed-agent control, inspection, and stop or cleanup.

Manual fallback command sections SHALL be complete enough for a reader to understand the underlying maintained commands without being cut off mid-flow.

#### Scenario: Primary workflow is complete

- **WHEN** a reader follows the primary agent-driven workflow in the quickstart
- **THEN** they can reach a first managed-agent outcome without encountering a truncated section
- **AND THEN** they can find next links for deeper specialist, profile, system-skill, gateway, mailbox, memory, and CLI reference material

#### Scenario: Join workflow is complete

- **WHEN** a reader follows the secondary join workflow in the quickstart
- **THEN** they can complete the provider TUI adoption, inspect or prompt the managed agent, and stop or clean up the managed agent without encountering a truncated section

#### Scenario: Manual fallback is complete enough for debugging

- **WHEN** a reader needs to debug or manually reproduce what the agent-driven path does
- **THEN** the quickstart includes compact maintained command examples or links for each major stage rather than ending mid-command sequence

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
Repo-owned getting-started guidance for the repo-local `.houmao/` project overlay SHALL describe project-local auth management through `houmao-mgr internals native-agent tools <tool> auth ...` rather than through `project credential ...`.

At minimum, the agent-definition layout guide SHALL explain that the CLI mirrors `.houmao/agents/tools/<tool>/auth/<name>/`, and quickstart-style examples SHALL use the supported `internals native-agent tools` command family when showing local auth-bundle creation or inspection.

#### Scenario: Reader sees matching CLI and directory-tree nouns
- **WHEN** a reader follows the project-overlay and agent-definition getting-started docs
- **THEN** the docs use `houmao-mgr internals native-agent tools <tool> auth ...` when describing local auth bundles
- **AND THEN** the surrounding explanation matches the documented directory tree under `.houmao/agents/tools/<tool>/auth/<name>/`

### Requirement: Getting-started docs explain the low-level and high-level project views
Repo-owned getting-started guidance for the repo-local `.houmao/` project overlay SHALL explain when to use `project`, `project agents`, and `project mailbox`.

At minimum:

- low-level auth management examples SHALL use `houmao-mgr internals native-agent tools <tool> auth ...`,
- higher-level reusable agent examples SHALL use `houmao-mgr project specialist ...`,
- project-local mailbox examples SHALL use `houmao-mgr project mailbox ...` when teaching repo-scoped mailbox-root workflows.

#### Scenario: Reader sees the revised project nouns in docs
- **WHEN** a reader follows the project-overlay and quickstart getting-started docs
- **THEN** the docs use `houmao-mgr internals native-agent tools <tool> auth ...` for low-level project auth bundles
- **AND THEN** the docs use `houmao-mgr project specialist ...` for the simpler project-local authoring path
- **AND THEN** the docs use `houmao-mgr project mailbox ...` when describing repo-scoped mailbox-root operations

### Requirement: Getting-started docs point to the supported minimal demo

The getting-started documentation SHALL point readers to `scripts/demo/minimal-agent-launch/` as the supported runnable companion to the canonical agent-definition and managed-agent launch documentation.

#### Scenario: Agent-definition docs link to the runnable demo

- **WHEN** a reader finishes the getting-started explanation of the canonical `agents/` directory layout
- **THEN** the page points them to `scripts/demo/minimal-agent-launch/` for a small runnable example that uses the same `skills/`, `roles/`, and `tools/` structure

#### Scenario: Quickstart docs link to the runnable demo

- **WHEN** a reader follows the getting-started quickstart for preset-backed build and launch
- **THEN** the page points them to `scripts/demo/minimal-agent-launch/` as the maintained minimal end-to-end example for local launch

### Requirement: Getting-started links to easy-specialist guide

The getting-started section SHALL link to the new easy-specialist conceptual guide from both the quickstart page and the agent-definitions page, so readers can deepen their understanding of the specialist model after encountering it in the quickstart workflow.

#### Scenario: Quickstart links to easy-specialist guide

- **WHEN** a reader encounters `project specialist create` in the quickstart
- **THEN** the page includes a link to `docs/getting-started/easy-specialists.md` for a deeper explanation of the model

### Requirement: Getting-started links to loop authoring guide

The getting-started section of the docs site SHALL include a link to `docs/getting-started/loop-authoring.md` in the `docs/index.md` Getting Started navigation list. The link entry SHALL describe the page as the guide for choosing a loop skill and understanding the pairwise-v2 routing-packet model.

#### Scenario: Reader discovers loop authoring guide from docs index

- **WHEN** a reader scans the Getting Started section of `docs/index.md`
- **THEN** they find a link to `getting-started/loop-authoring.md`
- **AND THEN** the link description makes clear the page covers loop skill selection and the routing-packet model

### Requirement: Getting-started docs explain managed memory memo and pages
Getting-started documentation SHALL explain the default managed-agent memory layout, the `houmao-memo.md` file, the contained `pages/` directory, and the current memory environment variables.

The docs SHALL describe `houmao-memo.md` as free-form Markdown edited by users or LLMs, and SHALL state that Houmao does not generate or refresh a page index inside that memo.

The docs SHALL direct durable work artifacts to the launched workdir or explicit operator-designated project paths rather than to managed scratch or persist lanes.

The docs SHALL explain that memory pages live under `HOUMAO_AGENT_PAGES_DIR`, and that interesting pages may be linked from `houmao-memo.md` with authored relative links such as `pages/notes/run.md`.

#### Scenario: New user sees memo-pages layout
- **WHEN** a new user reads the managed memory getting-started page
- **THEN** the page shows a default launch example
- **AND THEN** it explains the `houmao-memo.md` memo file
- **AND THEN** it explains the `pages/` directory
- **AND THEN** it does not show `--persist-dir`, `--no-persist-dir`, `--memory-dir`, or `--no-memory-dir` as current managed-memory options

### Requirement: Getting-started docs explain path discovery
Getting-started documentation SHALL explain that supported CLI, gateway, and pair-server memory surfaces can return full page paths and memo-relative links for contained page paths.

Path-discovery guidance SHALL not require the page to exist before the path is resolved.

#### Scenario: User discovers a page path for memo linking
- **WHEN** a reader wants to create or link `notes/run.md`
- **THEN** the docs show or describe a supported memory resolve operation
- **AND THEN** the docs explain that the operation returns both an absolute page path and a memo-relative link such as `pages/notes/run.md`

### Requirement: Getting-started memory docs explain memo cue and memory-management skill
The getting-started managed-memory documentation SHALL explain that managed launches render a default memo cue in the managed prompt header.

That documentation SHALL state that the memo cue includes the resolved absolute path to `houmao-memo.md` and instructs the agent to read that memo at the start of each prompt turn before planning or acting.

That documentation SHALL explain that `houmao-memory-mgr` is the packaged system skill for agent-facing requests to read, edit, add to, remove from, or organize the managed memo and contained pages.

That documentation SHALL preserve the existing memory model:

- `houmao-memo.md` is free-form Markdown,
- `pages/` contains authored supporting files,
- page links in the memo are authored references,
- Houmao does not generate or refresh memo indexes.

#### Scenario: Reader sees how managed agents are cued to use the memo
- **WHEN** a reader opens the managed-memory getting-started page
- **THEN** the page explains that the managed prompt header includes a default memo cue
- **AND THEN** the page states that the cue identifies the absolute memo path and tells agents to read it at the start of each prompt turn

#### Scenario: Reader sees the packaged skill for memo edits
- **WHEN** a reader wants an agent to add something to or remove something from its Houmao memo
- **THEN** the getting-started docs identify `houmao-memory-mgr` as the packaged system skill for that request
- **AND THEN** the docs keep the memo and pages model free-form rather than describing generated indexes

### Requirement: Getting-started docs explain canonical project skill storage versus derived projection
The getting-started documentation SHALL explain that canonical project-local custom skills live under `.houmao/content/skills/`.

That guidance SHALL explain that `.houmao/agents/skills/` is a derived compatibility projection rather than the source of truth for project-local skill authoring.

The docs SHALL introduce `houmao-mgr project skills ...` as the maintained surface for registering or updating project-local custom skills.

The docs SHALL introduce `houmao-mgr project migrate` as the supported command for existing users who need to convert one known older project structure into the current `houmao-mgr project` layout.

When the docs describe project skill storage modes, they SHALL explain that:

- `copy` mode creates a project-owned copy under `.houmao/content/skills/<name>/`,
- `symlink` mode creates `.houmao/content/skills/<name>` as a symlink to the chosen source directory.

#### Scenario: Reader sees one canonical project skill root
- **WHEN** a reader follows the getting-started project overlay documentation
- **THEN** the docs identify `.houmao/content/skills/` as the canonical project-local skill root
- **AND THEN** the docs describe `.houmao/agents/skills/` as derived projection state

#### Scenario: Reader is directed to explicit project migration for older overlays
- **WHEN** a reader already has one older project overlay that predates the current project layout
- **THEN** the getting-started docs direct them to `houmao-mgr project migrate`
- **AND THEN** the docs do not imply that ordinary project commands will silently upgrade that overlay in place

### Requirement: Getting-started guidance excludes Gemini
Maintained onboarding, quickstart, overview, specialist, profile, credential, mailbox, and demo guidance SHALL teach only current provider workflows and SHALL not present Gemini as supported.

#### Scenario: New reader sees the maintained provider set
- **WHEN** a reader follows getting-started documentation
- **THEN** provider examples and matrices use Claude, Codex, and Kimi as applicable
- **AND THEN** no Gemini setup prerequisite or workflow is offered

### Requirement: Getting-started guidance describes maintained current Kimi behavior
Getting-started pages SHALL describe Kimi 0.23.x as the maintained Kimi Code family. They SHALL remove Kimi 0.11-specific launch and system-prompt statements and SHALL not instruct users to issue a policy-changing confirmation or `/auto on` bootstrap step during unattended operation.

#### Scenario: New reader sees current Kimi baseline
- **WHEN** a reader opens the overview, quickstart, or system-skills overview
- **THEN** the guidance describes the maintained current Kimi contract
- **AND THEN** it contains no Kimi 0.11.0 compatibility claim
