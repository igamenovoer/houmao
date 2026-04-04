## ADDED Requirements

### Requirement: Archived mailbox demos with deprecated project-local skill contracts fail fast
Archived demo entry points that still depend on project-local runtime-owned mailbox-skill mirrors or prompt agents to open `skills/.../SKILL.md` from the copied worktree SHALL refuse to run.

The refusal SHALL happen before the demo launches agents, creates demo-owned run state, or performs mailbox side effects.

The failure message SHALL:
- state that the demo is archived or legacy-only,
- state that the blocked workflow depends on a deprecated project-local mailbox-skill mirror or skill-path prompting contract,
- direct the caller to a maintained demo surface instead of implying that the archived flow still reflects supported behavior.

#### Scenario: Operator invokes an archived demo that depends on project-local mailbox skill mirrors
- **WHEN** a caller runs a legacy mailbox demo command whose workflow still depends on copied project-local Houmao mailbox skills
- **THEN** the command exits non-zero before starting the demo workflow
- **AND THEN** it prints a clear message that the demo is archived because it relies on a deprecated project-local mailbox-skill contract

#### Scenario: Operator invokes an archived demo that teaches worktree `SKILL.md` prompting
- **WHEN** a caller runs a legacy mailbox demo command whose prompts still tell agents to open `skills/.../SKILL.md` from the copied worktree
- **THEN** the command exits non-zero before any agent or gateway launch side effects occur
- **AND THEN** the message tells the caller to use the maintained demo surface rather than the archived path-based workflow
