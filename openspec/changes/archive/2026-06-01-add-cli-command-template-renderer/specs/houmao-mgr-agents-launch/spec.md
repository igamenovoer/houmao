## ADDED Requirements

### Requirement: Agent launch CLI surfaces provide command-template entries
The CLI-owned command-template registry SHALL provide template entries for maintained `houmao-mgr agents launch` surfaces, including direct agent selection and launch-profile launch.

Each launch template SHALL map structured fields to CLI options and SHALL document selector requirements, auth/workdir/env overrides, prompt/model/reasoning overrides, mailbox launch flags, managed-header section overrides, and launch posture omission semantics.

#### Scenario: Launch-profile launch omits posture by default
- **WHEN** an agent renders a launch-profile launch template with a profile name and instance name but no explicit launch posture
- **THEN** the rendered argv does not include headless posture flags
- **AND THEN** the output reports posture as omitted for launch policy resolution

#### Scenario: Launch source selection is exclusive
- **WHEN** an agent renders a launch template with conflicting launch sources
- **THEN** the renderer reports a blocker
- **AND THEN** it does not return executable argv

### Requirement: Agent relaunch CLI surface provides a command-template entry
The CLI-owned command-template registry SHALL provide a template entry for `houmao-mgr agents relaunch`.

The relaunch template SHALL describe agent selectors, explicit chat-session mode fields, explicit chat-session id fields, and conflicts between mutually exclusive relaunch targets or chat-session policies.

#### Scenario: Relaunch omits chat-session policy by default
- **WHEN** an agent renders `agents.relaunch` with an explicit agent name but no explicit chat-session policy
- **THEN** the rendered argv includes the agent selector
- **AND THEN** chat-session mode and chat-session id options remain absent

#### Scenario: Relaunch chat-session conflict blocks rendering
- **WHEN** an agent renders `agents.relaunch` with conflicting chat-session policy fields
- **THEN** the renderer reports a blocker
- **AND THEN** it does not return executable argv
