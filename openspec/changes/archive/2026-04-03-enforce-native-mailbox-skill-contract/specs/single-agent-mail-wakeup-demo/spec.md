## ADDED Requirements

### Requirement: The supported TUI wake-up demo uses runtime-home mailbox skills without project-local mirrors
The supported `single-agent-mail-wakeup` demo SHALL rely on the installed runtime-home Houmao mailbox skill surface for its wake-up flow and SHALL NOT copy runtime-owned mailbox skills into the copied project worktree as project content.

The demo's inspect and verify surfaces SHALL treat runtime-home mailbox skill availability as the maintained contract and SHALL NOT define success by the presence of a copied `project/skills` or `skills/mailbox` mirror inside the copied project.

#### Scenario: Demo start keeps the copied project free of Houmao mailbox skill mirrors
- **WHEN** the supported TUI demo starts a maintained Claude or Codex lane
- **THEN** the copied project worktree does not contain a runtime-owned Houmao mailbox-skill mirror
- **AND THEN** the demo relies on the mailbox skills already installed into the selected brain home

#### Scenario: Demo verification checks runtime-home skill availability instead of a project mirror
- **WHEN** the supported TUI demo inspects or verifies a completed run
- **THEN** it records whether the runtime-home mailbox skill surface for the selected tool is present
- **AND THEN** it does not require a project-local mailbox skill surface as part of a successful maintained run
