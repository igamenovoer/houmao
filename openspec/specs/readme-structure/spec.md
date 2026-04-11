## Purpose
Define the README structure and onboarding order for the primary Houmao project documentation entry point.

## Requirements

### Requirement: README section ordering follows specialist-first onboarding

The README SHALL present sections in this order: title/intro, What It Is, Quick Start (steps 0-5), Typical Use Cases, System Skills, Subsystems, Runnable Demos, CLI Entry Points, Full Documentation, Development. The Quick Start steps SHALL be numbered 0 through 5.

#### Scenario: Reader scans the Quick Start headings
- **WHEN** a reader opens README.md and scans section headings
- **THEN** they see step 0 (Install & Prerequisites), step 1 (Initialize a Project), step 2 (Create Specialists & Launch Agents), step 3 (Agent Loop), step 4 (Adopt an Existing Session), step 5 (Full Recipes and Launch Profiles)

### Requirement: system-skills install is step 0

The Quick Start SHALL begin with a step 0 that instructs the user to run `houmao-mgr system-skills install --tool <tool> --home <home>` before any other Houmao workflow. The step SHALL explain that without system skills, agents cannot self-manage through their native skill interface.

#### Scenario: User follows step 0
- **WHEN** a user reads step 0 and runs the install command
- **THEN** the system skills are installed into their tool home and subsequent agent launches gain self-management capabilities

#### Scenario: Skip note for join-only users
- **WHEN** a user only wants to try `agents join` without project setup
- **THEN** a visible note directs them to skip to step 4, explaining system skills are recommended but not required for the join path

### Requirement: project init is step 1

Step 1 SHALL introduce `houmao-mgr project init` and briefly explain the `.houmao/` overlay: that it holds specialists, profiles, credentials, mailbox, and agent definitions for the project.

#### Scenario: User initializes a project
- **WHEN** a user reads step 1 and runs `houmao-mgr project init`
- **THEN** they understand the `.houmao/` directory is the project scaffold and can proceed to create specialists

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

### Requirement: Intro condensed to two sections

The introductory content SHALL be condensed from four subsections (What It Is, Core Idea, What The Framework Provides, Why This Is Useful) into two: **What It Is** (one paragraph covering what Houmao does and the real-CLI-process model) and **Why This Approach** (bullet list of capabilities, specialist/project/loop first, join as one bullet). The name-origin blockquote SHALL be preserved.

#### Scenario: Intro brevity
- **WHEN** a reader finishes the intro sections
- **THEN** they have read no more than ~20 lines of prose before reaching Quick Start
