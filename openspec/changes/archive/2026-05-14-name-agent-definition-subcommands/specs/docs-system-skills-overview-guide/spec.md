## MODIFIED Requirements

### Requirement: System-skills overview routes agent-definition concerns to unified skill
The system-skills overview guide SHALL route persisted pre-launch agent-definition concerns to `houmao-agent-definition`.

That routing SHALL include `roles`, `recipes`, `raw-profiles`, `specialists`, `profiles`, and `create-agent-fast-forward`.

The overview SHALL explain that loosely stated profile requests default to `profiles`, while `raw-profiles` is reserved for explicit raw, recipe-backed, or exact `project agents launch-profiles` requests.

The overview SHALL keep credential CRUD, mailbox administration, workspace creation, and broad live-agent lifecycle routed to their existing dedicated skills.

#### Scenario: Overview routes easy profile authoring to unified skill
- **WHEN** a reader asks which skill creates or updates one easy profile
- **THEN** the overview points to `houmao-agent-definition` and the `profiles` subcommand
- **AND THEN** it does not point to `houmao-specialist-mgr` as the primary current skill

#### Scenario: Overview distinguishes raw profiles
- **WHEN** a reader asks which skill handles `project agents launch-profiles ...`
- **THEN** the overview points to `houmao-agent-definition` and the `raw-profiles` subcommand
- **AND THEN** it explains that ordinary profile wording defaults to easy profiles

#### Scenario: Overview keeps live lifecycle separate
- **WHEN** a reader asks which skill manages already-live agents
- **THEN** the overview still points broad live-agent lifecycle work to `houmao-agent-instance`
- **AND THEN** it does not imply that unified agent-definition owns generic live lifecycle
