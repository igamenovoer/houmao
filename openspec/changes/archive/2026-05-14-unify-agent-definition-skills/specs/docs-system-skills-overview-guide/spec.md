## ADDED Requirements

### Requirement: System-skills overview routes agent-definition concerns to unified skill
The system-skills overview guide SHALL route persisted pre-launch agent-definition concerns to `houmao-agent-definition`.

That routing SHALL include low-level roles, recipes, explicit launch profiles, specialists, easy profiles, and ready-profile creation.

The overview SHALL keep credential CRUD, mailbox administration, workspace creation, and broad live-agent lifecycle routed to their existing dedicated skills.

#### Scenario: Overview routes easy profile authoring to unified skill
- **WHEN** a reader asks which skill creates or updates one easy profile
- **THEN** the overview points to `houmao-agent-definition`
- **AND THEN** it does not point to `houmao-specialist-mgr` as the primary current skill

#### Scenario: Overview keeps live lifecycle separate
- **WHEN** a reader asks which skill manages already-live agents
- **THEN** the overview still points broad live-agent lifecycle work to `houmao-agent-instance`
- **AND THEN** it does not imply that unified agent-definition owns generic live lifecycle
