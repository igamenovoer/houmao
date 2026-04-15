## Purpose
Define the README structure and onboarding order for the primary Houmao project documentation entry point.
## Requirements
### Requirement: README section ordering follows specialist-first onboarding

The README SHALL present sections in this order: title/intro, What It Is, Quick Start (steps 0–6), Typical Use Cases, System Skills, Subsystems, Runnable Demos, CLI Entry Points, Full Documentation, Development. The Quick Start steps SHALL be numbered 0 through 6.

#### Scenario: Reader scans the Quick Start headings
- **WHEN** a reader opens README.md and scans section headings
- **THEN** they see step 0 (Install & Prerequisites), step 1 (Drive with Your CLI Agent), step 2 (Initialize a Project), step 3 (Create Specialists & Launch Agents), step 4 (Agent Loop), step 5 (Adopt an Existing Session), step 6 (Full Recipes and Launch Profiles)

### Requirement: system-skills install is step 0

The Quick Start SHALL begin with a step 0 that instructs the user to run `houmao-mgr system-skills install --tool <tool> --home <home>` before any other Houmao workflow. The step SHALL explain that without system skills, agents cannot self-manage through their native skill interface.

#### Scenario: User follows step 0
- **WHEN** a user reads step 0 and runs the install command
- **THEN** the system skills are installed into their tool home and subsequent agent launches gain self-management capabilities

#### Scenario: Skip note for join-only users
- **WHEN** a user only wants to try `agents join` without project setup
- **THEN** a visible note directs them to skip to step 4, explaining system skills are recommended but not required for the join path

### Requirement: Drive with Your CLI Agent is step 1

Step 1 SHALL be titled "Drive with Your CLI Agent (Recommended)" and SHALL present the skill-driven path as the primary recommended entry point. It SHALL instruct the user to run `houmao-mgr system-skills install --tool <tool>` to install system skills into the project-local tool home, then start their agent from the same directory and invoke the `houmao-touring` skill. A note SHALL state that the remaining steps show the manual CLI equivalents for reference.

#### Scenario: User follows step 1
- **WHEN** a user reads step 1 and installs system skills then starts their agent
- **THEN** they know to invoke `houmao-touring` for a guided walkthrough and understand the rest of the Quick Start is a manual reference

#### Scenario: Step 1 is clearly positioned as recommended
- **WHEN** a reader scans the Quick Start section headings
- **THEN** step 1 carries a "(Recommended)" qualifier that distinguishes it from the manual steps that follow

### Requirement: project init is step 2

Step 2 SHALL introduce `houmao-mgr project init` and explain the `.houmao/` overlay. The overlay description SHALL include `memory/` as one of the listed subdirectories, described as the per-agent memory root family for free-form memo files and contained pages.

#### Scenario: User initializes a project
- **WHEN** a user reads step 2 and runs `houmao-mgr project init`
- **THEN** they understand the `.houmao/` directory is the project scaffold and can proceed to create specialists

#### Scenario: memory/ appears in the overlay layout description
- **WHEN** a reader scans the overlay layout bullet list in step 2
- **THEN** `memory/` appears as an entry alongside agents/, content/, mailbox/, catalog.sqlite, and houmao-config.toml

### Requirement: Specialist creation and launch is the primary path (step 2)

Step 2 SHALL show the full `houmao-mgr project easy specialist create` command with `--name`, `--tool`, `--api-key`, and `--system-prompt` flags, followed by `houmao-mgr project easy instance launch`, and then management commands (`agents prompt`, `agents stop`). The section SHALL mention easy profiles as the next step for reusable launch defaults.

#### Scenario: User creates and launches a specialist
- **WHEN** a user follows step 2 commands
- **THEN** they have a running managed agent created from a specialist, controllable through `houmao-mgr agents` commands

### Requirement: Agent loop section showcases pairwise coordination (step 3)

Step 3 SHALL contain: (a) a brief explanation of pairwise loops (master drives edges to workers, user stays outside execution loop), (b) the agentsys2 story-writing example with specialist creation commands for 3 agents (story-writer/claude, character-designer/claude, story-reviewer/codex), (c) the loop plan objective summary, (d) the mermaid control graph from the loop plan, (e) a listing of produced artifacts (chapters, character profiles, review reports), and (f) a reference to the `houmao-agent-loop-pairwise` skill for the full lifecycle vocabulary.

#### Scenario: Reader understands the loop example
- **WHEN** a reader finishes step 3
- **THEN** they understand: what a pairwise loop is, how specialists are set up for it, what the loop plan looks like, what artifacts it produces, and where to find the full skill docs

#### Scenario: Non-coding context note
- **WHEN** the story-writing example is presented
- **THEN** a note explains that the same pattern works for code review, optimization, or any multi-agent pipeline

### Requirement: agents join is a secondary path (step 4)

Step 4 SHALL document `agents join` with the existing mermaid sequence diagram, step-by-step commands, and the capabilities table. It SHALL be introduced as the lightweight/ad-hoc path for users who already have a running coding agent and want management on top, not as the recommended starting point.

The managed-header callout block within or after step 4 SHALL describe the five-section architecture: `identity`, `houmao-runtime-guidance`, and `automation-notice` default enabled; `task-reminder` and `mail-ack` default disabled. The callout SHALL name `--managed-header-section SECTION=enabled|disabled` as the per-launch section override and `--no-managed-header` as the whole-header opt-out. The callout SHALL mention that the automation-notice section prevents interactive user-question tools and routes mailbox-driven clarification to reply-enabled mailbox threads. The callout SHALL link to the Managed Launch Prompt Header reference page.

#### Scenario: Join section positioning
- **WHEN** a reader encounters step 4
- **THEN** it is clearly framed as "if you already have a coding agent running" rather than the default path

#### Scenario: Reader understands section-level managed-header control from README

- **WHEN** a reader scans the managed-header callout block in README.md
- **THEN** they learn that the header has five sections with three on by default and two off
- **AND THEN** they see the `--managed-header-section` flag for per-launch section override
- **AND THEN** they see `--no-managed-header` for whole-header opt-out
- **AND THEN** they can follow the link to the reference page for the full section list, resolution precedence, and stored-profile policy

### Requirement: System Skills section lists every shipped skill with its purpose

The System Skills table in README.md SHALL list `houmao-specialist-mgr` with a description that includes the "set" (edit/patch) verb alongside create, list, inspect, remove, launch, and stop.

#### Scenario: Reader sees specialist editing in the skill table

- **WHEN** a reader scans the System Skills table in README.md
- **THEN** the `houmao-specialist-mgr` row includes "set" in its verb list

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

The README opening "What It Is" paragraph SHALL mention Copilot as a supported system-skills install target alongside the three launch-capable tools (`claude`, `codex`, `gemini`). The mention SHALL use a qualifier that makes clear Copilot is a skill-install surface, not a launch backend.

#### Scenario: Reader understands Copilot scope

- **WHEN** a reader reads the README "What It Is" section
- **THEN** they see that Houmao manages `claude`, `codex`, and `gemini` as launch backends and additionally supports `copilot` for system-skill installation
- **AND THEN** they do not conclude that Copilot is a launch backend

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
