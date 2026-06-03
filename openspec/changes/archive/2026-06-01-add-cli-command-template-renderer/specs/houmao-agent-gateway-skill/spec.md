## ADDED Requirements

### Requirement: `houmao-agent-gateway` uses CLI-owned templates for supported gateway commands
The packaged `houmao-agent-gateway` skill SHALL instruct agents to use CLI-owned command templates before authoring supported `houmao-mgr agents gateway ...` commands.

At minimum, covered command families SHALL include gateway discovery/control/TUI helpers, mail notifier status/enable/disable, and reminders list/get/create/set/remove.

The skill SHALL keep live gateway HTTP workflow guidance, mailbox handoff prose, and semantic reminder prompt design in skill text where those concerns are not direct `houmao-mgr` command rendering.

#### Scenario: Reminder create uses template renderer
- **WHEN** a user asks the skill to create a gateway reminder
- **THEN** the skill guidance directs the agent to render `agents.gateway.reminders.create`
- **AND THEN** conflicts such as prompt-vs-send-keys delivery are handled by template blockers

#### Scenario: Notifier enable uses template renderer
- **WHEN** a user asks the skill to enable the gateway mail notifier
- **THEN** the skill guidance directs the agent to render the notifier-enable template
- **AND THEN** omitted notifier policy fields remain absent unless explicitly requested
