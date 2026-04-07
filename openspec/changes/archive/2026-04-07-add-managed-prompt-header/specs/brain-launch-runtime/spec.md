## MODIFIED Requirements

### Requirement: Role prompt applied before first user turn
The system SHALL apply the effective launch prompt as the initial tool instructions before the first user prompt is processed when that effective launch prompt contains prompt content.

The effective launch prompt MAY be the raw selected role prompt or a launch-owned composition around that role prompt.

When the selected role package intentionally contains an empty system prompt, launch SHALL remain valid. If no launch-owned prompt composition adds content, the runtime SHALL treat that role as having no startup prompt content.

#### Scenario: Role is injected on session start
- **WHEN** a session is started with role `R` whose effective launch prompt contains prompt content
- **THEN** the tool is initialized with that effective launch prompt as initial instructions using a tool-supported mechanism when available
- **AND THEN** if the tool lacks a native mechanism, the system sends that effective launch prompt as a clearly delimited bootstrap message before the first user prompt

#### Scenario: Empty role prompt skips startup injection when no launch-owned prompt content exists
- **WHEN** a session is started with role `R` whose `system-prompt.md` is intentionally empty
- **AND WHEN** the launch context does not add any launch-owned prompt content
- **THEN** session startup remains valid
- **AND THEN** the runtime does not pass empty native developer instructions, empty appended system-prompt arguments, or an empty bootstrap message to the provider

#### Scenario: Managed launch can inject startup prompt content even when the source role prompt is empty
- **WHEN** a managed session is started with role `R` whose `system-prompt.md` is intentionally empty
- **AND WHEN** the launch context resolves to non-empty managed-header prompt content
- **THEN** session startup remains valid
- **AND THEN** the runtime injects that non-empty effective launch prompt instead of treating the launch as promptless

#### Scenario: Role bootstrap is not replayed on resumed headless turns
- **WHEN** a headless session has already applied its effective launch prompt during bootstrap
- **AND WHEN** a developer sends a follow-up prompt using the persisted resume identity
- **THEN** the system does not replay role bootstrap content unless the caller explicitly starts a new session

### Requirement: Runtime-generated CAO agent profiles from roles
When using CAO, the system SHALL generate CAO agent profiles at runtime from the effective launch prompt for the selected role and launch context rather than requiring committed or static CAO profile files.

For plain role launches with no additional launch-owned prompt composition, the generated profile system prompt SHALL still be derived from `agents/roles/<R>/system-prompt.md`, including the empty-string case for promptless roles.

#### Scenario: Generate and install a CAO profile for a role
- **WHEN** a developer launches a CAO-backed session with role `R`
- **THEN** the system generates an agent profile whose system prompt is derived from the effective launch prompt for that launch context
- **AND THEN** the CAO terminal launch references that generated profile by name

#### Scenario: Promptless role stays valid for CAO profile generation when launch-owned prompt content is absent
- **WHEN** a developer launches a CAO-backed session with role `R` whose `system-prompt.md` is intentionally empty
- **AND WHEN** the launch context does not add any launch-owned prompt content
- **THEN** the generated profile uses an empty system prompt
- **AND THEN** launch remains valid rather than failing role validation

#### Scenario: Managed launch profile generation can become non-empty even when the source role prompt is empty
- **WHEN** a managed CAO-backed launch uses role `R` whose `system-prompt.md` is intentionally empty
- **AND WHEN** the launch context resolves to non-empty managed-header prompt content
- **THEN** the generated profile uses that non-empty effective launch prompt
- **AND THEN** compatibility profile generation does not incorrectly force the empty-string source role prompt through unchanged
