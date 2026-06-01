## ADDED Requirements

### Requirement: `houmao-agent-email-comms` uses CLI-owned templates for managed-agent mail fallback commands
The packaged `houmao-agent-email-comms` skill SHALL use CLI-owned command templates when it needs to author supported `houmao-mgr agents mail ...` fallback commands.

At minimum, covered fallback commands SHALL include `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`.

The skill SHALL keep gateway HTTP selection logic, transport-specific mailbox workflow, and message-processing guidance in skill text, because those concerns are not command-template rendering.

#### Scenario: Fallback send uses template renderer
- **WHEN** the skill has selected fallback CLI mail send for one turn
- **THEN** it renders `agents.mail.send` with explicit recipient, subject, and body fields
- **AND THEN** command shape comes from the template registry

#### Scenario: HTTP-vs-CLI routing remains skill-owned
- **WHEN** live gateway HTTP is available and preferable for the current workflow
- **THEN** the skill may use HTTP workflow guidance directly
- **AND THEN** the command-template renderer is not responsible for choosing that workflow
