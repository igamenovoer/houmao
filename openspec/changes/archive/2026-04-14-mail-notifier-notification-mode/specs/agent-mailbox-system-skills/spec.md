## ADDED Requirements

### Requirement: Notifier-driven mailbox skills honor notification mode
The runtime-owned `houmao-process-emails-via-gateway` workflow skill SHALL understand notifier prompts that identify notification mode as `any_inbox` or `unread_only`.

When the prompt identifies mode `any_inbox`, the workflow SHALL direct the agent to list open inbox mail through the shared gateway mailbox API and process relevant selected mail for the round.

When the prompt identifies mode `unread_only`, the workflow SHALL direct the agent to start from unread inbox mail through the shared gateway mailbox API for that round.

In both modes, the workflow SHALL keep archive as the completion action for successfully processed mail and SHALL NOT treat reading, peeking, replying, or acknowledging as implicit completion.

#### Scenario: Any-inbox notification uses open inbox triage
- **WHEN** an agent begins a notifier-driven round whose prompt states mode `any_inbox`
- **THEN** the workflow skill directs the agent to list open inbox mail through the shared gateway mailbox API
- **AND THEN** selected processed mail is archived only after the corresponding work and any required reply succeed

#### Scenario: Unread-only notification starts from unread inbox triage
- **WHEN** an agent begins a notifier-driven round whose prompt states mode `unread_only`
- **THEN** the workflow skill directs the agent to start from unread inbox mail through the shared gateway mailbox API
- **AND THEN** it keeps archive as the completion action for any successfully processed selected mail

#### Scenario: Skill does not restore read-as-completion semantics
- **WHEN** an agent follows the notifier-driven workflow in either mode
- **THEN** the workflow does not tell the agent that marking a message read completes the mailbox work
- **AND THEN** deferred, skipped, or unfinished messages remain unarchived for later handling according to the configured notifier mode
