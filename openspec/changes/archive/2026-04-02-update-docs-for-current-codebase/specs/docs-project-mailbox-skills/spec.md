## ADDED Requirements

### Requirement: Project mailbox skills reference page exists

The mailbox reference SHALL include a page at `docs/reference/mailbox/contracts/project-mailbox-skills.md` documenting native project mailbox skill projection for Claude and other tools. The page SHALL explain:

- What mailbox skills are: system-level SKILL.md files that are automatically injected into an agent's runtime home during the build phase when the agent has a mailbox binding.
- When skill projection activates: during `BrainBuilder.build()` when the build request includes a resolved mailbox configuration.
- What skills are provided: the set of mailbox-related actions (check mail, send mail, reply, etc.) that become available to the agent as tool capabilities.
- How this relates to the build phase: skills are projected from `agents/realm_controller/assets/system_skills/` into the agent's home directory alongside user-defined skills.
- Tool-specific behavior: how Claude receives these skills natively vs how other tools may consume them.

The page SHALL be derived from `agents/mailbox_runtime_support.py` and the skill assets under `agents/realm_controller/assets/`.

#### Scenario: Reader understands when mailbox skills are injected

- **WHEN** a reader opens the project mailbox skills page
- **THEN** they find a clear explanation that mailbox skills are automatically projected during the build phase when a mailbox binding is present
- **AND THEN** they understand that no explicit configuration is needed beyond having a mailbox binding in the preset or build request

#### Scenario: Reader can identify which skills are projected

- **WHEN** a reader wants to know what mailbox capabilities an agent receives
- **THEN** the page lists the projected skill actions (check, send, reply, status) with brief descriptions of each
- **AND THEN** the page references the source skill assets directory for the authoritative definitions

#### Scenario: Reader understands tool-specific projection

- **WHEN** a reader is setting up a Claude agent with mailbox support
- **THEN** the page explains that Claude receives mailbox skills as native SKILL.md projections in its home directory
- **AND THEN** the page notes any differences in how other tools (Codex, Gemini) consume the same skills
