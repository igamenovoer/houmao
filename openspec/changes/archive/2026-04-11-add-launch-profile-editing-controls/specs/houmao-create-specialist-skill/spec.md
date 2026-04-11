## ADDED Requirements

### Requirement: `houmao-specialist-mgr` routes easy-profile editing commands
The packaged `houmao-specialist-mgr` skill SHALL treat specialist-backed easy-profile editing as part of its easy-profile authoring responsibility.

When a user asks to update one existing easy profile's stored launch defaults, the skill SHALL route to `houmao-mgr project easy profile set --name <profile> ...`.

When a user asks to replace one existing easy profile definition, the skill SHALL route to `houmao-mgr project easy profile create --name <profile> --specialist <specialist> ... --yes` after identifying the replacement intent.

The skill SHALL NOT route ordinary easy-profile stored-default edits through manual remove/recreate.

#### Scenario: Skill routes easy-profile patch request to set
- **WHEN** a user asks an agent using `houmao-specialist-mgr` to change the workdir on easy profile `alice`
- **THEN** the skill guidance routes that request through `project easy profile set --name alice --workdir <path>`
- **AND THEN** it does not instruct the agent to remove and recreate `alice`

#### Scenario: Skill distinguishes replacement from patch
- **WHEN** a user asks an agent using `houmao-specialist-mgr` to rebuild easy profile `alice` over a different specialist
- **THEN** the skill guidance treats that as replacement
- **AND THEN** it routes through `project easy profile create --name alice --specialist <specialist> --yes`
