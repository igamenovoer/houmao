## ADDED Requirements

### Requirement: `houmao-project-mgr` documents explicit launch-profile replacement
The packaged `houmao-project-mgr` skill SHALL document the supported explicit launch-profile management surface as including `list`, `get`, `add`, `set`, and `remove`.

When a user asks to update one existing explicit launch profile's stored launch defaults, the skill SHALL route to `houmao-mgr project agents launch-profiles set --name <profile> ...`.

When a user asks to replace one existing explicit launch profile definition, the skill SHALL route to `houmao-mgr project agents launch-profiles add --name <profile> --recipe <recipe> ... --yes` after identifying the replacement intent.

The skill SHALL NOT route ordinary explicit launch-profile stored-default edits through manual remove/recreate.

#### Scenario: Skill routes explicit launch-profile patch request to set
- **WHEN** a user asks an agent using `houmao-project-mgr` to change the auth override on explicit launch profile `alice`
- **THEN** the skill guidance routes that request through `project agents launch-profiles set --name alice --auth <name>`
- **AND THEN** it does not instruct the agent to remove and recreate `alice`

#### Scenario: Skill routes explicit launch-profile replacement request to add yes
- **WHEN** a user asks an agent using `houmao-project-mgr` to recreate explicit launch profile `alice` over a different recipe
- **THEN** the skill guidance treats that as replacement
- **AND THEN** it routes through `project agents launch-profiles add --name alice --recipe <recipe> --yes`
