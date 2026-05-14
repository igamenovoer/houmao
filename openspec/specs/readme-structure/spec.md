## Purpose
Define the README structure and onboarding order for the primary Houmao project documentation entry point.
## Requirements
### Requirement: README section ordering follows specialist-first onboarding

The README SHALL present sections in this order: title/intro, What It Is, Quick Start (steps 0–6), Typical Use Cases, System Skills, Subsystems, Runnable Demos, CLI Entry Points, Full Documentation, Development. The Quick Start steps SHALL be numbered 0 through 6.

#### Scenario: Reader scans the Quick Start headings
- **WHEN** a reader opens README.md and scans section headings
- **THEN** they see step 0 (Install & Prerequisites), step 1 (Drive with Your CLI Agent), step 2 (Initialize a Project), step 3 (Create Specialists & Launch Agents), step 4 (Agent Loop), step 5 (Adopt an Existing Session), step 6 (Full Recipes and Launch Profiles)

### Requirement: Drive with Your CLI Agent is step 1

Step 1 SHALL be titled "Drive with Your CLI Agent (Recommended)" and SHALL present the skill-driven path as the primary recommended entry point. It SHALL instruct the user to install system skills, start their agent from the same directory, and invoke `houmao-touring`.

When `npx` is available and the target machine has internet access, step 1 SHALL recommend installing from the GitHub main-branch system-skill collection with:

```bash
npx skills add https://github.com/igamenovoer/houmao/tree/main/src/houmao/agents/assets/system_skills/
```

Step 1 SHALL present `houmao-mgr system-skills install --tool <tool>[,<tool>...]` as the Houmao-owned installation path for environments without `npx` or internet access, installed-package/offline workflows, named sets, subset skills, explicit homes, symlink/copy projection, or retired-skill cleanup.

Step 1 SHALL explain that omitted `--home` resolves each selected tool through its own env/default home rules, and that explicit `--home` is valid only for a single selected tool.

Step 1 SHALL mention that installed Houmao system skills support explicit read-only help such as `$houmao-touring help` or `$houmao-agent-email-comms help`.

Step 1 SHALL NOT present `--set` as the current named system-skill set selection flag.

A note SHALL state that the remaining steps show the manual CLI equivalents for reference.

#### Scenario: User follows step 1 with npx available
- **WHEN** a user reads step 1 on a machine with `npx` and internet access
- **THEN** they see the `npx skills add` command pointed at the GitHub main-branch `system_skills/` directory
- **AND THEN** they understand that the Skills CLI lets them choose which packaged skill or skills to install
- **AND THEN** they know to start their agent and invoke `houmao-touring`

#### Scenario: User follows step 1 without npx or with custom install needs
- **WHEN** a user reads step 1 without `npx`, without internet access, or with explicit selection or home needs
- **THEN** they see `houmao-mgr system-skills install --tool <tool>[,<tool>...]` as the supported Houmao-owned path
- **AND THEN** they understand omitted-home and single-tool explicit-home behavior

#### Scenario: User discovers read-only skill help from step 1
- **WHEN** a reader finishes the recommended agent-driven setup guidance
- **THEN** they see at least one explicit skill-help prompt example
- **AND THEN** the README describes help as read-only usage guidance before workflows

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

### Requirement: README skill table uses unified agent-definition row
The System Skills table in README.md SHALL list `houmao-agent-definition` with a description that includes low-level roles/recipes, `raw-profiles`, specialists, easy `profiles`, and `create-agent-fast-forward`.

If the README still mentions `houmao-specialist-mgr`, that mention SHALL identify it as compatibility or migration guidance rather than as a primary separate row for current specialist management.

#### Scenario: README table names the fast-forward path
- **WHEN** the README System Skills table is inspected
- **THEN** the `houmao-agent-definition` row includes `create-agent-fast-forward` or one-click agent profile preparation in its description
- **AND THEN** specialist/easy-profile authoring is not described as belonging only to a separate primary skill

#### Scenario: README table uses raw profile terminology
- **WHEN** the README System Skills table mentions low-level recipe-backed profiles
- **THEN** it names that lane as `raw-profiles`
- **AND THEN** it keeps `profiles` available for specialist-backed easy profiles

### Requirement: Install prerequisites are step 0

The README Quick Start step 0 SHALL remain titled "Install & Prerequisites" or an equivalent install/prerequisite heading. It SHALL focus on installing Houmao itself and verifying host prerequisites such as `tmux`.

Step 0 SHALL NOT be the only place where system-skill installation is introduced. System-skill installation choices SHALL appear in the recommended agent-driven step.

#### Scenario: Reader sees Houmao install prerequisites first
- **WHEN** a reader scans the README Quick Start section
- **THEN** step 0 explains how to install Houmao and verify prerequisites
- **AND THEN** system-skill installation choices are handled in the recommended agent-driven step rather than being the sole purpose of step 0

