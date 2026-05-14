## ADDED Requirements

### Requirement: `houmao-agent-definition` is the canonical pre-launch agent-definition skill
The packaged `houmao-agent-definition` skill SHALL be the canonical Houmao-owned skill for persisted pre-launch agent definition workflows.

That unified skill SHALL route these lanes:

- low-level roles;
- low-level recipes or presets;
- explicit recipe-backed launch profiles;
- project-easy specialists;
- specialist-backed easy profiles;
- ready easy-profile generation;
- limited easy launch and stop entry points that hand off broader live lifecycle work to `houmao-agent-instance`.

#### Scenario: Unified skill routes both low-level and easy definition requests
- **WHEN** an agent reads the packaged `houmao-agent-definition` skill
- **THEN** the top-level page routes low-level role or recipe work and project-easy specialist or easy-profile work through local subskills
- **AND THEN** it does not require users to know whether to invoke a separate specialist-management skill for ordinary easy-profile authoring

### Requirement: `houmao-agent-definition` uses lane-specific subskills
The unified `houmao-agent-definition` skill SHALL keep its entry page concise and SHALL route detailed behavior into lane-specific local subskills or references.

At minimum, the skill SHALL distinguish low-level roles, low-level recipes, explicit recipe-backed launch profiles, easy specialists, easy profiles, ready-profile generation, easy launch, and easy stop.

The skill SHALL include shared guidance for launcher resolution, missing-input handling, profile-lane terminology, and credential-routing boundaries.

#### Scenario: Entry page loads only the relevant lane
- **WHEN** the user asks to update one easy profile
- **THEN** `houmao-agent-definition` routes to the easy-profile subskill
- **AND THEN** it does not load or flatten unrelated low-level recipe, explicit launch-profile, or easy-instance launch instructions into the entry page

### Requirement: Unified skill keeps neighboring platform concerns out of scope
The unified `houmao-agent-definition` skill SHALL NOT become the owner for credential bundle CRUD, mailbox root/account administration, workspace creation, broad live managed-agent lifecycle, or direct filesystem edits under `.houmao/`.

It SHALL route those concerns to `houmao-credential-mgr`, `houmao-mailbox-mgr`, `houmao-utils-workspace-mgr`, `houmao-agent-instance`, or other maintained Houmao skills as appropriate.

#### Scenario: Credential content mutation is routed away
- **WHEN** a user asks to mutate auth files or environment variables inside a credential bundle while using `houmao-agent-definition`
- **THEN** the skill routes the request to `houmao-credential-mgr`
- **AND THEN** it does not treat credential-bundle content mutation as specialist, recipe, or profile authoring
