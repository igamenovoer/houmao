## REMOVED Requirements

### Requirement: `houmao-agent-gateway` uses CLI-owned templates for supported gateway commands
**Reason**: The command-template renderer has been retired; supported gateway commands are documented directly in the packaged skill.

**Migration**: Use direct scoped `houmao-mgr agents self gateway ...` and `houmao-mgr agents single ... gateway ...` command snippets.

#### Scenario: Gateway commands no longer use template rendering
- **WHEN** a user asks the skill for gateway CLI work
- **THEN** the skill shows direct scoped gateway commands
- **AND THEN** it does not tell the agent to render a command-template id first

## ADDED Requirements

### Requirement: `houmao-agent-gateway` uses direct scoped command snippets for supported gateway commands
The packaged `houmao-agent-gateway` skill SHALL document supported gateway commands as direct fenced `bash` snippets or equivalent explicit command shapes.

At minimum, covered command families SHALL include scoped gateway discovery/control/TUI helpers, mail notifier status/enable/disable, and reminders list/get/create/set/remove.

The skill SHALL keep live gateway HTTP workflow guidance, mailbox handoff prose, and semantic reminder prompt design in skill text where those concerns are not direct `houmao-mgr` command spelling.

The skill SHALL NOT reference `houmao-mgr internals command-templates`, command-template ids, template blockers, or command-template support when explaining gateway commands.

#### Scenario: Reminder create uses direct scoped command shape
- **WHEN** a user asks the skill to create a gateway reminder for selected agent `reviewer`
- **THEN** the skill guidance shows a direct command under `houmao-mgr agents single --agent-name reviewer gateway reminders create ...`
- **AND THEN** it does not direct the agent to render a reminder command-template id
