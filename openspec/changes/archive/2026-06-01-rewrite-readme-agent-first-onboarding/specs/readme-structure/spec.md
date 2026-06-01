## MODIFIED Requirements

### Requirement: README section ordering follows specialist-first onboarding

The README SHALL present an agent-first onboarding order: title/intro, What It Is, Why This Design, Architecture at a Glance, Quick Start, agent-driven examples, Core Concepts, Agent Loops, Typical Use Cases, concise System Skills summary, Subsystems, Demos and Examples, CLI Entry Points, Full Documentation, Development.

The Quick Start SHALL NOT require a reader to walk through a numbered 0-through-6 manual `houmao-mgr` tutorial before seeing Houmao's agent-driven value. Manual command details and secondary paths SHALL be linked to docs rather than expanded as the primary README flow.

#### Scenario: Reader scans the README headings
- **WHEN** a reader opens README.md and scans section headings
- **THEN** they see a concise Quick Start before detailed usage references
- **AND THEN** they see agent-driven examples before low-level CLI command details
- **AND THEN** the README does not present project init, specialist creation, agent join, and full recipes as a long numbered manual tutorial

### Requirement: Drive with Your CLI Agent is step 1

The README Quick Start SHALL present the skill-driven path as the primary recommended entry point. It SHALL instruct the user to install Houmao, verify `tmux`, install Houmao system skills, start their CLI agent from the target directory, and invoke `houmao-touring`.

When `npx` is available and the target machine has internet access, the README SHALL recommend the release-synced tool-skills install path:

```bash
npx skills add igamenovoer/tool-skills/houmao
```

The README SHALL still mention `houmao-mgr system-skills install --tool <tool>[,<tool>...]` as the Houmao-owned installation path for environments without `npx`, installed-package/offline workflows, named sets, subset skills, explicit homes, symlink/copy projection, or retired-skill cleanup.

The README SHALL mention that installed Houmao system skills support explicit read-only help such as `$houmao-touring help` and that the user's next action is to ask their CLI agent to run `$houmao-touring start a guided tour`.

The README SHALL NOT recommend installing system skills from the full Houmao source-tree `system_skills/` path as the ordinary first path.

#### Scenario: User follows the preferred skill install path
- **WHEN** a user reads the Quick Start on a machine with `npx` and internet access
- **THEN** they see `npx skills add igamenovoer/tool-skills/houmao` as the preferred system-skill installation command
- **AND THEN** they understand that `houmao-touring` is the first guided workflow to ask their CLI agent to run

#### Scenario: User needs the Houmao-owned installer
- **WHEN** a user reads the Quick Start without `npx`, without internet access, or with explicit projection needs
- **THEN** they see `houmao-mgr system-skills install --tool <tool>[,<tool>...]` as the supported fallback or custom installation path
- **AND THEN** the README keeps detailed flag behavior in linked docs rather than expanding it inline

### Requirement: Install prerequisites are step 0

The README Quick Start install block SHALL focus on the minimum first-run path:

```bash
uv tool install houmao
command -v tmux
npx skills add igamenovoer/tool-skills/houmao
```

The install block SHALL state that `tmux` is required because managed agents run in tmux-backed sessions. It SHALL mention the Houmao-owned `system-skills install` command after the preferred `npx` path, not as the default first command.

#### Scenario: Reader sees a short install path first
- **WHEN** a reader scans the README Quick Start
- **THEN** they see `uv tool install houmao`, `command -v tmux`, and `npx skills add igamenovoer/tool-skills/houmao`
- **AND THEN** they do not have to read project initialization or specialist command syntax before starting the guided tour

### Requirement: project init is step 2

The README SHALL explain project initialization as work the user's CLI agent can perform through Houmao skills during the guided flow. It MAY show `houmao-mgr project init` as an example of underlying machinery, but SHALL NOT make manual project initialization a mandatory numbered step before the user sees specialist and loop examples.

The README SHALL still explain that Houmao creates a `.houmao/` project overlay and SHALL link to getting-started docs for the overlay layout and command details.

#### Scenario: User understands project setup is agent-driven
- **WHEN** a reader encounters project initialization in the README
- **THEN** they understand that their CLI agent can initialize or inspect the project through Houmao skills
- **AND THEN** they can follow docs links for the complete `.houmao/` overlay layout

### Requirement: Specialist creation and launch is the primary path (step 2)

The README SHALL introduce specialists, easy profiles, and managed agents through a simple agent-driven workflow rather than through a full `houmao-mgr project easy specialist create` flag tutorial.

The workflow SHALL show the user asking their CLI agent to create or select a specialist, create a reusable easy launch profile when useful, launch a managed agent, and send an initial prompt through the gateway or maintained messaging surface. The README MAY include a short illustrative command or outcome list, but detailed command syntax SHALL be delegated to linked docs.

#### Scenario: Reader sees the specialist workflow
- **WHEN** a reader follows the first agent workflow example
- **THEN** they understand that a specialist is the reusable role/tool/credential definition
- **AND THEN** they understand that an easy profile captures reusable launch defaults
- **AND THEN** they understand that the launched managed agent can be prompted or inspected through a gateway-backed Houmao surface

### Requirement: Agent loop section showcases pairwise coordination (step 3)

The README SHALL present agent loops as the place where Houmao's multi-agent system shines. The main loop story SHALL focus on `houmao-agent-loop-pro`: the user feeds a complex multi-agent plan to the pro loop skill, the CLI agent decomposes it into intention and execplan artifacts, prepares required specialists, profiles, workspaces, skills, credentials, mailbox/gateway posture, and then launches and operates the loop.

The README SHALL mention `houmao-agent-loop-lite` as the lighter Markdown/direct-SQL loop path, but SHALL keep `houmao-agent-loop-pro` as the marquee example for complex plans. The README SHALL avoid presenting retired pairwise loop skill packages as the current main loop lifecycle.

The README MAY keep or link to the writer-team example, but it SHALL frame it as an example/template rather than as a long command-first tutorial.

#### Scenario: Reader understands pro loop value
- **WHEN** a reader finishes the agent loop section
- **THEN** they understand that they can ask their CLI agent to use `houmao-agent-loop-pro` for a complex multi-agent plan
- **AND THEN** they understand that the loop skill decomposes, prepares, validates, launches, and operates the loop through generated artifacts and maintained Houmao skills

#### Scenario: Reader sees lite as a secondary loop path
- **WHEN** the README mentions `houmao-agent-loop-lite`
- **THEN** it describes lite as the lightweight Markdown/direct-SQL loop option
- **AND THEN** it does not make lite replace pro as the primary complex-plan story

### Requirement: agents join is a secondary path (step 4)

The README SHALL treat `agents join` as a secondary advanced or reference path for adopting an already-running provider TUI, not as part of the first-run onboarding flow.

The README MAY summarize joined-session capability at a high level and SHALL link to detailed docs for step-by-step commands, capabilities, and managed-header behavior.

#### Scenario: Join section positioning
- **WHEN** a reader encounters `agents join` in the README
- **THEN** it is clearly framed as "if you already have a running provider session" rather than the default starting path
- **AND THEN** detailed join commands are available through docs links rather than expanded as the main README flow

### Requirement: System Skills section lists every shipped skill with its purpose

The README System Skills section SHALL be a concise summary of skill families and the agent-driven model, not a full table of every shipped system skill. It SHALL explain that Houmao installs skills into CLI-agent homes so the agent can drive project setup, specialist/profile authoring, live-agent messaging, gateway/mailbox/memory work, inspection, and loop orchestration through supported `houmao-mgr` surfaces.

The README SHALL link to the System Skills Overview for the full packaged-skill catalog and per-skill boundaries.

#### Scenario: Reader sees skills as an agent capability layer
- **WHEN** a reader scans the System Skills section
- **THEN** they understand that skills let the CLI agent operate Houmao on the user's behalf
- **AND THEN** they see a link to the full System Skills Overview instead of a long inline catalog

### Requirement: README skill table uses unified agent-definition row

If the README mentions individual system skills, it SHALL mention only the most important entry points needed for orientation, such as `houmao-touring`, `houmao-agent-definition`, `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-loop-lite`, and `houmao-agent-loop-pro`.

If the README mentions `houmao-agent-definition`, it SHALL describe it as the agent-facing surface for specialist, easy profile, raw profile, recipe, launch, and `create-agent-fast-forward` workflows. If the README mentions `houmao-specialist-mgr`, that mention SHALL identify it as compatibility or migration guidance rather than as the primary current specialist-management surface.

#### Scenario: README keeps individual skill references compact
- **WHEN** the README mentions individual system skills
- **THEN** it limits the list to orientation-level entry points
- **AND THEN** detailed skill boundaries are delegated to the System Skills Overview

#### Scenario: README names the current definition surface
- **WHEN** the README describes specialist or profile authoring through system skills
- **THEN** it identifies `houmao-agent-definition` as the current primary skill surface
- **AND THEN** it does not present `houmao-specialist-mgr` as the primary current surface

## ADDED Requirements

### Requirement: README usage examples use AI/user chat style

The README SHALL include at least one concise "You:" / "AI:" usage example after installation. The example SHALL show the user asking their CLI agent to perform Houmao work and the AI reporting concrete Houmao outcomes, such as project initialization, specialist creation, easy profile preparation, managed-agent launch, gateway attachment, prompt delivery, or loop preparation.

#### Scenario: Reader sees agent-mediated usage
- **WHEN** a reader reaches the first usage example after Quick Start
- **THEN** they see the user asking a CLI agent for an outcome rather than manually invoking a long sequence of commands
- **AND THEN** they see the AI report completed Houmao steps in plain language

### Requirement: README leaves command detail to docs

The README SHALL keep command examples short and illustrative. Detailed command flags, full lifecycle command lists, complete system-skill catalogs, join diagrams, managed-header details, and recipe/raw-profile reference material SHALL be linked to existing docs or reference pages instead of expanded inline.

#### Scenario: Reader wants command details
- **WHEN** a reader wants exact CLI syntax beyond the concise README examples
- **THEN** the README points them to the relevant getting-started or reference docs
- **AND THEN** the README itself remains focused on concepts, agent-driven workflows, and examples

### Requirement: README introduces core concepts before command reference

After the first usage example, the README SHALL introduce the core model in compact form: user CLI agent, specialist, easy profile, managed agent, gateway, mailbox, and loop. The concepts SHALL be described from the user's mental model rather than from storage layout or CLI implementation detail.

#### Scenario: Reader learns the mental model
- **WHEN** a reader reaches the concept section
- **THEN** they can distinguish the user's CLI agent from Houmao-managed agents
- **AND THEN** they understand how specialists, easy profiles, gateways, mailboxes, and loops fit together
