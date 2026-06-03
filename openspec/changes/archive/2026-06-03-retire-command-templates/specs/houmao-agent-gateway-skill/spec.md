## REMOVED Requirements

### Requirement: `houmao-agent-gateway` uses CLI-owned templates for supported gateway commands
**Reason**: Gateway command templates are retired with the command-template renderer.
**Migration**: Document direct scoped gateway commands in fenced `bash` blocks and keep reminder/gateway workflow decisions in skill prose.

#### Scenario: Gateway authoring does not use templates
- **WHEN** the packaged skill documents gateway discovery, control, notifier, or reminder commands
- **THEN** it shows direct scoped `houmao-mgr agents ... gateway ...` commands rather than command-template ids

## ADDED Requirements

### Requirement: `houmao-agent-gateway` uses direct command snippets for supported gateway commands
The packaged `houmao-agent-gateway` skill SHALL document supported gateway commands as fenced `bash` snippets.

At minimum, covered command families SHALL include gateway discovery/control/TUI helpers, mail notifier status/enable/disable, and reminders list/get/create/set/remove.

The skill SHALL keep live gateway HTTP workflow guidance, mailbox handoff prose, and semantic reminder prompt design in skill text where those concerns are not direct `houmao-mgr` command invocation.

The skill SHALL NOT reference `houmao-mgr internals command-templates show`, `houmao-mgr internals command-templates render`, command-template ids, or template blockers.

#### Scenario: Reminder create uses direct command snippet
- **WHEN** a user asks the skill to create a gateway reminder
- **THEN** the skill guidance shows a direct scoped reminder creation command
- **AND THEN** conflicts such as prompt-vs-send-keys delivery are checked by the skill before command execution

#### Scenario: Notifier enable uses direct command snippet
- **WHEN** a user asks the skill to enable the gateway mail notifier
- **THEN** the skill guidance shows a direct scoped notifier-enable command
- **AND THEN** omitted notifier policy fields remain absent unless explicitly requested
