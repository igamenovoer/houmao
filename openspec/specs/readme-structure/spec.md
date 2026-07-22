## Purpose
Define the README structure and onboarding order for the primary Houmao project documentation entry point.
## Requirements
### Requirement: README section ordering follows specialist-first onboarding

The README SHALL present an agent-first onboarding order: title/intro, What It Is, Why This Design, Architecture at a Glance, Quick Start, agent-driven examples, Core Concepts, Agent Loops, Typical Use Cases, concise System Skills summary, Subsystems, Demos and Examples, CLI Entry Points, Full Documentation, Development.

The Quick Start SHALL NOT require a reader to walk through a numbered 0-through-6 manual `houmao-mgr` tutorial before seeing Houmao's agent-driven value. Manual command details and secondary paths SHALL be linked to docs rather than expanded as the primary README flow.

#### Scenario: Reader scans the README headings
- **WHEN** a reader opens README.md and scans section headings
- **THEN** they see a concise Quick Start before detailed usage references
- **AND THEN** they see agent-driven examples before low-level CLI command details
- **AND THEN** the README does not present project init, specialist creation, agent join, and full recipes as a long numbered manual tutorial

### Requirement: Drive with Your CLI Agent is step 1
The README Quick Start SHALL present the skill-driven human-operator path as the primary recommended entry point. It SHALL instruct the user to install Houmao, verify `tmux`, install the admin system-skill pack into the target CLI-agent home with `houmao-mgr system-skills install --tool <tool> --pack admin`, start that CLI agent from the target directory, and invoke `$houmao-admin-welcome start-guided-tour`.

The README SHALL explain that the welcome is read-only and hands executable work to `$houmao-admin-entrypoint ...`. It SHALL keep detailed pack, home, mode, migration, and receipt behavior in linked documentation and SHALL NOT recommend direct installation from the source asset tree, old named sets, protected routine selectors, or `$houmao-touring`.

#### Scenario: User follows the preferred admin-pack path
- **WHEN** a user reads the Quick Start
- **THEN** they see the Houmao-owned admin-pack installation command
- **AND THEN** their first guided prompt uses `houmao-admin-welcome`
- **AND THEN** they understand that execution transfers to the admin entrypoint

#### Scenario: User needs installation detail
- **WHEN** a user needs an explicit home, symlink mode, upgrade, or conflict resolution
- **THEN** the README links to the system-skills reference
- **AND THEN** it does not expand the full lifecycle flag reference inline

#### Scenario: User follows the preferred skill install path
- **WHEN** a user reads the Quick Start on a machine with `npx` and internet access
- **THEN** they see `npx skills add https://github.com/igamenovoer/houmao-skills` as the preferred system-skill installation command
- **AND THEN** they understand that `houmao-touring` is the first guided workflow to ask their CLI agent to run

#### Scenario: User needs the Houmao-owned installer
- **WHEN** a user reads the Quick Start without `npx`, without internet access, or with explicit projection needs
- **THEN** they see `houmao-mgr system-skills install --tool <tool>[,<tool>...]` as the supported fallback or custom installation path
- **AND THEN** the README keeps detailed flag behavior in linked docs rather than expanding it inline

### Requirement: project init is step 2

The README SHALL explain project initialization as work the user's CLI agent can perform through Houmao skills during the guided flow. It MAY show `houmao-mgr project init` as an example of underlying machinery, but SHALL NOT make manual project initialization a mandatory numbered step before the user sees specialist and loop examples.

The README SHALL still explain that Houmao creates a `.houmao/` project overlay and SHALL link to getting-started docs for the overlay layout and command details.

#### Scenario: User understands project setup is agent-driven
- **WHEN** a reader encounters project initialization in the README
- **THEN** they understand that their CLI agent can initialize or inspect the project through Houmao skills
- **AND THEN** they can follow docs links for the complete `.houmao/` overlay layout

### Requirement: Specialist creation and launch is the primary path (step 2)

The README SHALL introduce specialists, project profiles, and managed agents through a simple agent-driven workflow rather than through a full `houmao-mgr project specialist create` flag tutorial.

The workflow SHALL show the user asking their CLI agent to create or select a specialist, create a reusable easy launch profile when useful, launch a managed agent, and send an initial prompt through the gateway or maintained messaging surface. The README MAY include a short illustrative command or outcome list, but detailed command syntax SHALL be delegated to linked docs.

#### Scenario: Reader sees the specialist workflow
- **WHEN** a reader follows the first agent workflow example
- **THEN** they understand that a specialist is the reusable role/tool/credential definition
- **AND THEN** they understand that an project profile captures reusable launch defaults
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
The README System Skills section SHALL be a concise summary of the three public roles and the actor-driven model, not a table of protected routines.

It SHALL explain that the admin welcome orients the human, the admin entrypoint performs human-directed work against explicit targets, and the agent entrypoint performs verified managed-agent work. It SHALL state that project, specialist/profile, messaging, gateway, mailbox, memory, inspection, workspace, interop, and loop behavior is nested protected implementation and SHALL link to the System Skills Overview for the complete route map.

#### Scenario: Reader sees skills as an actor-qualified capability layer
- **WHEN** a reader scans the System Skills section
- **THEN** they understand the three public roles and which actor each serves
- **AND THEN** they see a link to protected routine detail instead of a long flat catalog

#### Scenario: Reader sees skills as an agent capability layer
- **WHEN** a reader scans the System Skills section
- **THEN** they understand that skills let the CLI agent operate Houmao on the user's behalf
- **AND THEN** they see a link to the full System Skills Overview instead of a long inline catalog

### Requirement: agents join capabilities table mentions agents memory

The capabilities table in step 5 (Adopt an Existing Session) SHALL include at least one row describing `houmao-mgr agents memory` commands, covering memory path inspection, memo file operations, and page link/path resolution.

#### Scenario: Reader sees memory commands in join capabilities table
- **WHEN** a reader scans the capabilities table in step 5
- **THEN** they find a row for memory inspection, memo operations, or page resolution that references `houmao-mgr agents memory`

### Requirement: Intro condensed to two sections

The introductory content SHALL be condensed from four subsections (What It Is, Core Idea, What The Framework Provides, Why This Is Useful) into two: **What It Is** (one paragraph covering what Houmao does and the real-CLI-process model) and **Why This Approach** (bullet list of capabilities, specialist/project/loop first, join as one bullet). The name-origin blockquote SHALL be preserved.

#### Scenario: Intro brevity
- **WHEN** a reader finishes the intro sections
- **THEN** they have read no more than ~20 lines of prose before reaching Quick Start

### Requirement: README What It Is section acknowledges Copilot system-skills target

The README opening "What It Is" paragraph SHALL mention Copilot as a supported system-skills install target alongside the three primary launch-capable tools (`claude`, `codex`, `kimi`). The mention SHALL use a qualifier that makes clear Copilot is a skill-install surface, not a launch backend.

When the README opening paragraph or nearby first-screen prose mentions all maintained launch-capable providers, it SHALL order them as `claude`, `codex`, `kimi`, then `gemini`.

The README SHALL include a Kimi Code warning that names Kimi Code 0.11.0 and states that this version does not expose a native system-prompt flag. The warning SHALL tell readers that Kimi Code users may need to invoke `houmao-auto-system-prompt` manually before substantive chat begins when the Houmao system prompt is not confirmed loaded.

#### Scenario: Reader understands Copilot scope

- **WHEN** a reader reads the README "What It Is" section
- **THEN** they see that Houmao manages `claude`, `codex`, and `kimi` as the primary launch backend examples
- **AND THEN** they see Gemini only after Kimi when a complete launch-provider list appears
- **AND THEN** they see that Houmao additionally supports `copilot` for system-skill installation
- **AND THEN** they do not conclude that Copilot is a launch backend

#### Scenario: Reader sees Kimi system-prompt caveat

- **WHEN** a reader scans the README Kimi provider guidance
- **THEN** they see that Kimi Code 0.11.0 does not expose a native system-prompt flag
- **AND THEN** they see that `houmao-auto-system-prompt` may need manual invocation before substantive Kimi chat begins

### Requirement: README demos section includes writer-team example

The README SHALL include a reference to the `examples/writer-team/` template in or adjacent to the "Runnable Demos" section so that the multi-agent loop example is discoverable alongside the demo scripts.

#### Scenario: Reader finds writer-team in demos area

- **WHEN** a reader scans the "Runnable Demos" section of the README
- **THEN** they find a reference to `examples/writer-team/` with a description of what the example demonstrates

### Requirement: README links to the reusable writer-team example

When the repository contains `examples/writer-team/`, the README agent-loop story-writing section SHALL link to that example as the reusable template for the three-agent writing team.

The README SHALL distinguish the reusable example from the inline quick-start narrative by making clear that the example contains the prompt files, loop plan, start charter, and local setup instructions.

#### Scenario: Reader wants to reuse the story-writing team

- **WHEN** a reader finishes the README story-writing loop section
- **THEN** they find a link to `examples/writer-team/`
- **AND THEN** they understand that the linked example is the reusable template for creating the three-agent writing team locally

### Requirement: Install prerequisites are step 0

The README Quick Start install block SHALL focus on the minimum first-run path:

```bash
uv tool install houmao
command -v tmux
npx skills add https://github.com/igamenovoer/houmao-skills
```

The install block SHALL state that `tmux` is required because managed agents run in tmux-backed sessions. It SHALL mention the Houmao-owned `system-skills install` command after the preferred `npx` path, not as the default first command.

#### Scenario: Reader sees a short install path first
- **WHEN** a reader scans the README Quick Start
- **THEN** they see `uv tool install houmao`, `command -v tmux`, and `npx skills add https://github.com/igamenovoer/houmao-skills`
- **AND THEN** they do not have to read project initialization or specialist command syntax before starting the guided tour

### Requirement: README usage examples use AI/user chat style

The README SHALL include at least one concise "You:" / "AI:" usage example after installation. The example SHALL show the user asking their CLI agent to perform Houmao work and the AI reporting concrete Houmao outcomes, such as project initialization, specialist creation, project profile preparation, managed-agent launch, gateway attachment, prompt delivery, or loop preparation.

#### Scenario: Reader sees agent-mediated usage
- **WHEN** a reader reaches the first usage example after Quick Start
- **THEN** they see the user asking a CLI agent for an outcome rather than manually invoking a long sequence of commands
- **AND THEN** they see the AI report completed Houmao steps in plain language

### Requirement: README leaves command detail to docs

The README SHALL keep command examples short and illustrative. Detailed command flags, full lifecycle command lists, complete system-skill catalogs, join diagrams, managed-header details, and recipe/launch-dossier reference material SHALL be linked to existing docs or reference pages instead of expanded inline.

#### Scenario: Reader wants command details
- **WHEN** a reader wants exact CLI syntax beyond the concise README examples
- **THEN** the README points them to the relevant getting-started or reference docs
- **AND THEN** the README itself remains focused on concepts, agent-driven workflows, and examples

### Requirement: README introduces core concepts before command reference

After the first usage example, the README SHALL introduce the core model in compact form: user CLI agent, specialist, project profile, managed agent, gateway, mailbox, and loop. The concepts SHALL be described from the user's mental model rather than from storage layout or CLI implementation detail.

#### Scenario: Reader learns the mental model
- **WHEN** a reader reaches the concept section
- **THEN** they can distinguish the user's CLI agent from Houmao-managed agents
- **AND THEN** they understand how specialists, project profiles, gateways, mailboxes, and loops fit together

### Requirement: README excludes Gemini support claims
The repository README SHALL not present Gemini as a launch provider, credential provider, TUI tool, headless backend, system-skill target, or maintained demo lane.

#### Scenario: Reader scans README provider guidance
- **WHEN** a reader scans the README introduction, concepts, examples, and demos
- **THEN** no current support claim or workflow names Gemini
- **AND THEN** the remaining provider guidance stays accurate for Claude, Codex, and Kimi

### Requirement: README system-skill examples preserve the actor boundary
Every README system-skill example SHALL make clear whether the user's CLI assistant is acting for the human through the admin entrypoint or whether a managed Houmao agent is acting through the agent entrypoint.

Examples SHALL use public skill invocations and SHALL NOT rely on a protected logical id as a top-level trigger.

#### Scenario: README shows a managed-agent mailbox example
- **WHEN** the README demonstrates mailbox work performed by a managed agent
- **THEN** the example begins through `$houmao-agent-entrypoint`
- **AND THEN** it does not make the reader invoke the protected mailbox routine directly
