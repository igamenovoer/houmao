## ADDED Requirements

### Requirement: `houmao-specialist-mgr` routes specialist update requests
The packaged `houmao-specialist-mgr` skill SHALL instruct agents to route existing-specialist update requests through `houmao-mgr project easy specialist set --name <specialist> ...`.

The top-level skill router SHALL include specialist update as an easy-workflow action and SHALL distinguish it from specialist creation, same-name specialist replacement, easy-profile update, and easy-instance runtime work.

The specialist update guidance SHALL require the specialist name and at least one explicit update or clear option before running the command.

The specialist update guidance SHALL tell agents that omitted fields are preserved and that already-running managed agents are not mutated in place.

#### Scenario: Installed skill routes specialist skill edits to set
- **WHEN** a user asks an agent to add or remove a skill on an existing specialist
- **THEN** the installed `houmao-specialist-mgr` skill routes the agent to `project easy specialist set`
- **AND THEN** it does not instruct the agent to remove and recreate the specialist for that ordinary edit

#### Scenario: Installed skill asks before running an empty specialist update
- **WHEN** a user asks to update specialist `researcher` but does not state any concrete update field
- **THEN** the installed `houmao-specialist-mgr` skill tells the agent to ask for the missing update details
- **AND THEN** it does not run `project easy specialist set --name researcher` without an update or clear flag

#### Scenario: Installed skill distinguishes profile update from specialist update
- **WHEN** a user asks to update a reusable launch default on an easy profile
- **THEN** the installed `houmao-specialist-mgr` skill routes the agent to `project easy profile set`
- **AND THEN** it does not use `project easy specialist set` for profile-owned birth-time defaults
