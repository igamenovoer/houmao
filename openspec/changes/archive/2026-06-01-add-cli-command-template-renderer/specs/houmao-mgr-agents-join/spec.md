## ADDED Requirements

### Requirement: Agent join CLI surface provides a command-template entry
The CLI-owned command-template registry SHALL provide a template entry for `houmao-mgr agents join`.

The join template SHALL describe agent selectors, provider selection, workdir, launch args, launch env, resume id, headless posture, and skill-installation flags supported by the maintained join command.

#### Scenario: Join renders explicit selector only
- **WHEN** an agent renders `agents.join` with an explicit agent name
- **THEN** the rendered argv includes that selector
- **AND THEN** omitted provider, posture, launch args, launch env, and resume fields remain absent

#### Scenario: Join selector conflict blocks rendering
- **WHEN** an agent renders `agents.join` with mutually exclusive selectors
- **THEN** the renderer reports a blocker
- **AND THEN** it does not return executable argv
