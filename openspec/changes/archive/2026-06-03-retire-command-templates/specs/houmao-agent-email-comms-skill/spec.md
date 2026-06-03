## REMOVED Requirements

### Requirement: `houmao-agent-email-comms` uses CLI-owned templates for managed-agent mail fallback commands
**Reason**: Managed-agent mail fallback command templates are retired with the command-template renderer.
**Migration**: Document direct scoped `houmao-mgr agents ... mail ...` fallback commands in fenced `bash` blocks while keeping HTTP-vs-CLI routing in skill prose.

#### Scenario: Mail fallback authoring does not use templates
- **WHEN** the packaged skill selects CLI fallback for managed-agent mail
- **THEN** it shows a direct scoped mail command rather than a command-template id

## ADDED Requirements

### Requirement: `houmao-agent-email-comms` uses direct command snippets for managed-agent mail fallback commands
The packaged `houmao-agent-email-comms` skill SHALL document supported managed-agent mail fallback commands as fenced `bash` snippets.

At minimum, covered fallback commands SHALL include `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`.

The skill SHALL keep gateway HTTP selection logic, transport-specific mailbox workflow, and message-processing guidance in skill text.

The skill SHALL NOT reference `houmao-mgr internals command-templates show`, `houmao-mgr internals command-templates render`, command-template ids, or template blockers.

#### Scenario: Fallback send uses direct command snippet
- **WHEN** the skill has selected fallback CLI mail send for one turn
- **THEN** it shows the direct scoped mail send command with explicit recipient, subject, and body placeholders
- **AND THEN** command shape is not loaded from a command-template registry

#### Scenario: HTTP-vs-CLI routing remains skill-owned
- **WHEN** live gateway HTTP is available and preferable for the current workflow
- **THEN** the skill may use HTTP workflow guidance directly
- **AND THEN** no command renderer is responsible for choosing that workflow
