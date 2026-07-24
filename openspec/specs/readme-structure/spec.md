## Purpose
Define the README structure and onboarding order for the primary Houmao project documentation entry point.
## Requirements
### Requirement: README section ordering follows specialist-first onboarding

The README SHALL present an agent-first onboarding order: title/intro, Motivation, audience list, What It Is (with name origin), Why This Design, Architecture at a Glance, Quick Start, agent-driven examples, Core Concepts, Agent Loops, concise System Skills summary, Subsystems, Demos and Examples, CLI Entry Points, Full Documentation, Development, License. The former Typical Use Cases section is removed; audience signposting in the "who this is for" list and the Agent Loops and Demos sections carry that content.

The Quick Start SHALL NOT require a reader to walk through a numbered 0-through-6 manual `houmao-mgr` tutorial before seeing Houmao's agent-driven value. Manual command details and secondary paths SHALL be linked to docs rather than expanded as the primary README flow.

#### Scenario: Reader scans the README headings
- **WHEN** a reader opens README.md and scans section headings
- **THEN** they see a concise Quick Start before detailed usage references
- **AND THEN** they see agent-driven examples before low-level CLI command details
- **AND THEN** the README does not present project init, specialist creation, agent join, and full recipes as a long numbered manual tutorial

### Requirement: Drive with Your CLI Agent is step 1
The README Quick Start SHALL present the skill-driven human-operator path as the primary recommended entry point. It SHALL instruct the user to install Houmao, verify `tmux`, install the admin system-skill pack into the target CLI-agent home, start that CLI agent from the target directory, and invoke `$houmao-admin-welcome start-guided-tour`.

The README SHALL explain that the welcome is read-only and hands executable work to `$houmao-admin-entrypoint ...`. It SHALL keep detailed pack, home, mode, migration, and receipt behavior in linked documentation and SHALL NOT recommend direct installation from the source asset tree, old named sets, protected routine selectors, or `$houmao-touring`.

#### Scenario: User follows the preferred admin-pack path
- **WHEN** a user reads the Quick Start
- **THEN** they see the Houmao-owned admin-pack installation command or the preferred `npx skills add` command
- **AND THEN** their first guided prompt uses `houmao-admin-welcome`
- **AND THEN** they understand that execution transfers to the admin entrypoint

#### Scenario: User needs installation detail
- **WHEN** a user needs an explicit home, symlink mode, upgrade, or conflict resolution
- **THEN** the README links to the system-skills reference
- **AND THEN** it does not expand the full lifecycle flag reference inline

#### Scenario: User follows the preferred skill install path
- **WHEN** a user reads the Quick Start on a machine with `npx` and internet access
- **THEN** they see `npx skills add https://github.com/igamenovoer/houmao-skills` as the preferred system-skill installation command
- **AND THEN** they understand that `$houmao-admin-welcome start-guided-tour` is the first guided workflow to ask their CLI agent to run

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
The README System Skills section SHALL be a concise summary of the public roles and the actor-driven model, not a table of protected routines and not an inline reference for pack lifecycle behavior.

It SHALL keep the table of the six shipped skills with pack membership and role, presenting the welcome skill first as the starting skill, and SHALL explain the actor model in no more than a short paragraph: natural Houmao requests route to the admin entrypoint for a human-operator session and to the agent entrypoint for a verified managed session, while welcome and both loop skills are invoked explicitly. Pack membership resolution, shared-owner tracking, route-selection rules, bypass syntax, ownership config, and compatibility aliases SHALL live in the System Skills Overview and System Skills CLI reference; the README SHALL link to both instead of expanding them inline. The System Skills section body after the table SHALL NOT exceed roughly 15 lines of prose.

#### Scenario: Reader sees skills as an actor-qualified capability layer
- **WHEN** a reader scans the System Skills section
- **THEN** they understand the six shipped skills, the two actor entrypoints, and which actor each serves
- **AND THEN** they see a link to the System Skills Overview for route and pack detail instead of a long inline catalog

#### Scenario: Reader sees skills as an agent capability layer
- **WHEN** a reader scans the System Skills section
- **THEN** they understand that skills let the CLI agent operate Houmao on the user's behalf
- **AND THEN** they see a link to the full System Skills Overview instead of a long inline catalog

#### Scenario: Reader needs pack or routing detail
- **WHEN** a reader wants pack membership, route-selection, or install-lifecycle detail
- **THEN** they follow the README link to the System Skills Overview or CLI reference
- **AND THEN** the moved detail is present in that linked doc, merged with its existing content rather than duplicated

### Requirement: agents join capabilities table mentions agents memory

The capabilities table in step 5 (Adopt an Existing Session) SHALL include at least one row describing `houmao-mgr agents memory` commands, covering memory path inspection, memo file operations, and page link/path resolution.

#### Scenario: Reader sees memory commands in join capabilities table
- **WHEN** a reader scans the capabilities table in step 5
- **THEN** they find a row for memory inspection, memo operations, or page resolution that references `houmao-mgr agents memory`

### Requirement: README What It Is section acknowledges Copilot system-skills target

The README opening "What It Is" paragraph SHALL mention Copilot as a supported system-skills install target alongside the three primary launch-capable tools (`claude`, `codex`, `kimi`). The mention SHALL use a qualifier that makes clear Copilot is a skill-install surface, not a launch backend.

When the README opening paragraph or nearby first-screen prose mentions all maintained launch-capable providers, it SHALL order them as `claude`, `codex`, `kimi`, then `gemini`.

The README SHALL include a Kimi Code note that reflects the maintained release line (currently 0.23.x): Houmao delivers role context to managed Kimi sessions through managed bootstrap or auto-skill workflows and projects `houmao-auto-system-prompt` into managed Kimi homes. The note SHALL tell readers to invoke `houmao-auto-system-prompt` before substantive chat when the Houmao role prompt is not confirmed loaded. The note SHALL NOT pin guidance to the retired 0.11.0 system-prompt-flag wording.

#### Scenario: Reader understands Copilot scope

- **WHEN** a reader reads the README "What It Is" section
- **THEN** they see that Houmao manages `claude`, `codex`, and `kimi` as the primary launch backend examples
- **AND THEN** they see Gemini only after Kimi when a complete launch-provider list appears
- **AND THEN** they see that Houmao additionally supports `copilot` for system-skill installation
- **AND THEN** they do not conclude that Copilot is a launch backend

#### Scenario: Reader sees current Kimi role-prompt guidance

- **WHEN** a reader scans the README Kimi provider guidance
- **THEN** they see guidance matching the maintained Kimi Code release line and the `houmao-auto-system-prompt` projection behavior
- **AND THEN** they are told to invoke `houmao-auto-system-prompt` manually when the role prompt is not confirmed loaded

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

The README SHALL include at least one concise "You:" / "AI:" usage example inside the Quick Start, immediately after the install and tour steps. The example SHALL show the user asking their CLI agent to perform Houmao work and the AI reporting concrete Houmao outcomes, such as project initialization, specialist creation, project profile preparation, managed-agent launch, gateway attachment, prompt delivery, or loop preparation. Additional examples (such as gateway interaction) MAY appear in a later examples section and SHALL NOT duplicate the Quick Start exchange.

The first example prompt in the README SHALL invoke the entrypoint skill explicitly (for example, `$houmao-admin-entrypoint ...`), teaching the recommended first-prompt pattern; explicit-only skills (welcome, both loops) always show their handle. Later example prompts MAY drop the handle and SHALL include the keyword `houmao` so implicit skill routing triggers reliably.

#### Scenario: Reader sees agent-mediated usage

- **WHEN** a reader reaches the end of the Quick Start
- **THEN** they see the user asking a CLI agent for an outcome rather than manually invoking a long sequence of commands
- **AND THEN** they see the AI report completed Houmao steps in plain language

#### Scenario: Reader learns the invocation pattern

- **WHEN** a reader compares the first and later example prompts
- **THEN** the first prompt shows the explicit entrypoint-skill invocation
- **AND THEN** later natural-language prompts include the keyword `houmao` without repeating the handle

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

### Requirement: README intro narrative carries brand, rationale, and architecture

The README opening SHALL present, in order: the title and one-line summary, the central motivation (strong single agents as units, human-like cooperation without a hardcoded orchestration layer), a "who this is for" audience list (multi-agent system developers, agent system end users, Houmao extenders), and "What It Is" with the name-origin brand story, followed by "Why This Design" as short rationale paragraphs and an architecture walkthrough, all before Quick Start. The name-origin story SHALL be preserved as brand identity.

The pre-Quick-Start prose MAY use up to ~60 lines and SHALL use subheadings so the narrative stays scannable.

#### Scenario: Reader gets the full story before the first command

- **WHEN** a reader opens the README and reads toward Quick Start
- **THEN** they encounter the motivation, the audience list, the brand story, the design rationale, and the architecture walkthrough as distinct subheaded sections
- **AND THEN** the total pre-Quick-Start prose stays within ~60 lines

### Requirement: README brand language never becomes vocabulary

The name-origin and metaphor content SHALL stand alone as brand narrative. Metaphor words (for example, "strands", "clones") SHALL NOT appear as synonyms or definitions for canonical concepts such as `specialist` or `managed agent`, and the README SHALL NOT present a metaphor-to-concept mapping as teaching scaffolding.

#### Scenario: Metaphor stays in the brand story

- **WHEN** a reader finishes the name-origin story and continues into concept explanations
- **THEN** every concept is explained with canonical terms only
- **AND THEN** no metaphor word is reused as a synonym for a canonical term anywhere in the README

### Requirement: README architecture section teaches system view and single-agent anatomy

The architecture section SHALL narrate the existing team diagram in prose (who drives `houmao-mgr`, what each managed agent is, what gateways and the mailbox do) and SHALL include a second mermaid diagram showing one managed agent's anatomy: the provider CLI process inside tmux, the gateway sidecar, the mailbox identity, and the memory directory. Both diagrams SHALL stay conceptual and SHALL NOT embed CLI command syntax or flags.

#### Scenario: Reader understands one agent's makeup

- **WHEN** a reader finishes the architecture section
- **THEN** they have seen both the team-level diagram and the single-agent anatomy diagram
- **AND THEN** they can identify what "managed agent", "gateway", and "mailbox identity" refer to without following any link

### Requirement: README defines concepts before first use

Every load-bearing concept in the README — specialist, project profile, managed agent, gateway, mailbox, loop, and the `.houmao/` overlay — SHALL be defined in plain language at or before its first use. A one-clause definition at first use is sufficient; the Core Concepts table remains the full reference.

The opening "What It Is" paragraph SHALL NOT use more than one not-yet-defined Houmao-specific term per sentence, and SHALL prefer concrete wording (for example, "a real `claude` or `codex` process running in its own tmux session") over abstraction-nouns a newcomer cannot guess (for example, "posture", "surface" as a noun, "credential lane", "pack closure", "turn evidence").

#### Scenario: Newcomer reads top to bottom without a glossary

- **WHEN** a reader who knows nothing about Houmao reads the README from the top
- **THEN** every Houmao-specific term they encounter has been defined in plain language at or before that point
- **AND THEN** they do not need to consult the Core Concepts table or linked docs to finish the "What It Is" and Quick Start sections

### Requirement: README Quick Start presents a single golden path with visible outcomes

The Quick Start SHALL present exactly one recommended sequence: prerequisites check, `uv tool install houmao`, `command -v tmux`, `npx skills add https://github.com/igamenovoer/houmao-skills`, start the CLI agent from the project directory, and invoke `$houmao-admin-welcome start-guided-tour`. Each step SHALL state in one line what success looks like.

The Quick Start SHALL close with the first `You:`/`AI:` exchange inline (for example, create a reviewer specialist, launch it, ask for a review), so the reader sees a complete zero-to-first-managed-agent arc before running anything.

Alternative installation paths — pinned-tag installs, `houmao-mgr system-skills install` variants, explicit home resolution, offline or copy-paste installation — SHALL each appear as at most one sentence with a link to the relevant doc, and SHALL NOT appear as peer command blocks inside the golden path.

#### Scenario: Reader knows exactly what to run and what to expect

- **WHEN** a reader finishes the Quick Start
- **THEN** they can name the single command sequence they are expected to run
- **AND THEN** they know what success looks like at each step and have seen the first agent-driven exchange

#### Scenario: Reader needs a non-default install

- **WHEN** a reader needs a pinned version, explicit home, or offline install
- **THEN** they find a one-sentence pointer to the doc covering that path
- **AND THEN** the pointer does not interrupt the golden-path flow with additional command blocks

### Requirement: README teaches the welcome skill as the single entry invocation

The README SHALL frame `$houmao-admin-welcome start-guided-tour` as the one skill invocation a newcomer must remember, both in Quick Start and in the System Skills section, where the welcome skill SHALL be listed or named first as the starting skill.

#### Scenario: Reader remembers one thing

- **WHEN** a reader retains only a single invocation from the README
- **THEN** the README has consistently positioned `$houmao-admin-welcome start-guided-tour` as that invocation

### Requirement: README states prerequisites before the install block

The README SHALL state prerequisites immediately before or at the start of the Quick Start install block: Python 3.11+ with `uv`, `tmux`, a supported platform (Linux or macOS), and `npx` availability for the preferred skill installer.

#### Scenario: Reader checks their machine before installing

- **WHEN** a reader begins the Quick Start
- **THEN** they can verify their platform, `uv`, `tmux`, and `npx` prerequisites before running the first install command

### Requirement: README sentences respect readability limits

README prose sentences SHALL NOT exceed approximately 30 words. Tables, code blocks, and the mermaid diagrams are exempt. Where a current sentence exceeds the limit, it SHALL be split without dropping factual content.

#### Scenario: Long-sentence sweep

- **WHEN** the revised README prose is scanned sentence by sentence
- **THEN** no prose sentence exceeds approximately 30 words
- **AND THEN** every fact present in the previous README text is still present in the README or in a directly linked doc

### Requirement: README explains skill invocation syntax at first use

The first time a `$houmao-*` invocation appears, the README SHALL explain in one sentence that `$name` invokes an installed skill from the CLI agent's chat.

#### Scenario: Reader encounters the first skill invocation

- **WHEN** a reader reaches the first `$houmao-*` invocation in the README
- **THEN** they have been told what the `$` prefix means and where to type it

### Requirement: README embedded media is captioned

Embedded or linked media in the README (such as the writer-team demo video) SHALL have a preceding sentence or caption stating what the media shows. A bare URL without surrounding context SHALL NOT appear as a standalone paragraph.

#### Scenario: Reader reaches the demo video

- **WHEN** a reader reaches the writer-team demo video link
- **THEN** a sentence or caption tells them what the video demonstrates before or as the link appears

### Requirement: README states the project license

The README SHALL state the project's license, either as a short section or as a clearly labeled line near the end of the document.

#### Scenario: Reader looks for licensing terms

- **WHEN** a reader scans the README for licensing information
- **THEN** they find the license named without leaving the document
