# docs-project-mailbox-skills Specification

## Purpose
Define the documentation requirements for the project mailbox skills reference page.

## Requirements

### Requirement: Project mailbox skills reference page exists

The mailbox reference SHALL include a page at `docs/reference/mailbox/contracts/project-mailbox-skills.md` documenting native mailbox skill projection into runtime homes for Claude and other tools. The page SHALL explain:

- What mailbox skills are: system-level SKILL.md assets that are automatically injected into an agent's runtime home during the build phase when the agent has a mailbox binding.
- When skill projection activates: during `BrainBuilder.build()` when the build request includes a resolved mailbox configuration.
- What skills are provided: the set of mailbox-related actions and workflow layers that become available to the agent as runtime-owned tool capabilities.
- How this relates to the build phase: skills are projected from `agents/realm_controller/assets/system_skills/` into the agent's runtime home alongside user-defined skills.
- Tool-specific behavior: how Claude, Codex, and Gemini receive these skills through their maintained runtime-home skill destinations.
- Contract boundaries: runtime-owned mailbox skills are not copied into ordinary project content for maintained flows, and ordinary prompting uses native skill invocation guidance rather than telling agents to open copied `skills/.../SKILL.md` paths from the worktree.

The page SHALL be derived from `agents/mailbox_runtime_support.py` and the skill assets under `agents/realm_controller/assets/`.

#### Scenario: Reader understands when mailbox skills are injected

- **WHEN** a reader opens the project mailbox skills page
- **THEN** they find a clear explanation that mailbox skills are automatically projected during the build phase when a mailbox binding is present
- **AND THEN** they understand that no explicit configuration is needed beyond having a mailbox binding in the preset or build request

#### Scenario: Reader can identify which skills are projected

- **WHEN** a reader wants to know what mailbox capabilities an agent receives
- **THEN** the page lists the projected skill actions and workflow layers with brief descriptions of each
- **AND THEN** the page references the source skill assets directory for the authoritative definitions

#### Scenario: Reader understands tool-specific projection

- **WHEN** a reader is setting up a Claude, Codex, or Gemini agent with mailbox support
- **THEN** the page explains that the runtime projects mailbox skills into the tool's native runtime-home skill destination
- **AND THEN** the page notes the tool-specific differences in the visible installed skill surface

#### Scenario: Reader understands mailbox skills are not copied into maintained project content

- **WHEN** a reader studies the mailbox skills reference to understand where those skills live during maintained runtime flows
- **THEN** the page explains that runtime-owned mailbox skills belong to the runtime home rather than to copied project content
- **AND THEN** it does not teach copied project-local mailbox skill mirrors as part of the maintained contract
