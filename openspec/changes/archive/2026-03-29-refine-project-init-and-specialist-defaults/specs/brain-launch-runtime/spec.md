## MODIFIED Requirements

### Requirement: Role prompt applied before first user turn
The system SHALL apply the selected role package as the initial tool instructions before the first user prompt is processed when the role package contains prompt content.

When the selected role package intentionally contains an empty system prompt, launch SHALL remain valid and the runtime SHALL treat that role as having no startup prompt content.

#### Scenario: Role is injected on session start
- **WHEN** a session is started with role `R` whose `system-prompt.md` contains prompt content
- **THEN** the tool is initialized with `R` as initial instructions using a tool-supported mechanism when available
- **AND THEN** if the tool lacks a native mechanism, the system sends `R` as a clearly delimited bootstrap message before the first user prompt

#### Scenario: Empty role prompt skips startup injection
- **WHEN** a session is started with role `R` whose `system-prompt.md` is intentionally empty
- **THEN** session startup remains valid
- **AND THEN** the runtime does not pass empty native developer instructions, empty appended system-prompt arguments, or an empty bootstrap message to the provider

#### Scenario: Role bootstrap is not replayed on resumed headless turns
- **WHEN** a headless session has already applied role `R` during bootstrap
- **AND WHEN** a developer sends a follow-up prompt using the persisted resume identity
- **THEN** the system does not replay role bootstrap content unless the caller explicitly starts a new session

### Requirement: Runtime-generated CAO agent profiles from roles
When using CAO, the system SHALL generate CAO agent profiles at runtime from repo role packages rather than requiring committed/static CAO profile files.

The generated profile system prompt SHALL be derived from `agents/roles/<R>/system-prompt.md`, including the empty-string case for promptless roles.

#### Scenario: Generate and install a CAO profile for a role
- **WHEN** a developer launches a CAO-backed session with role `R`
- **THEN** the system generates an agent profile whose system prompt is derived from `agents/roles/<R>/system-prompt.md`
- **AND THEN** the CAO terminal launch references that generated profile by name

#### Scenario: Promptless role stays valid for CAO profile generation
- **WHEN** a developer launches a CAO-backed session with role `R` whose `system-prompt.md` is intentionally empty
- **THEN** the generated profile uses an empty system prompt
- **AND THEN** launch remains valid rather than failing role validation
