## ADDED Requirements

### Requirement: Current system skills expose a read-only help operation
Every current packaged Houmao system skill declared in `src/houmao/agents/assets/system_skills/catalog.toml` SHALL expose a `help` meta operation from its top-level `SKILL.md`.

The help operation SHALL be read-only.

The help operation SHALL answer explicit skill-help intent before the skill performs normal operation routing, action-page routing, branch routing, missing-input collection, command execution, filesystem mutation, mailbox mutation, gateway mutation, or managed-agent lifecycle mutation.

Explicit skill-help intent SHALL include at least:

- `<skill-name> help`
- `help for <skill-name>`
- `usage for <skill-name>`
- `available functionality for <skill-name>`
- `what can <skill-name> do`

The help operation SHALL NOT claim a generic "help me do X" task when the user clearly asks the skill to perform an ordinary supported workflow.

Retired legacy skill assets under `src/houmao/agents/assets/system_skills/legacy/` SHALL NOT be required to expose this help operation.

#### Scenario: Explicit help request stays read-only
- **WHEN** a user invokes a current system skill with explicit help intent
- **THEN** the agent responds with usage guidance for that skill
- **AND THEN** the agent does not run Houmao commands, mutate files, send mail, change gateway state, change agent lifecycle state, or collect missing operational inputs for the underlying workflow

#### Scenario: Ordinary task still routes normally
- **WHEN** a user asks a current system skill to perform a concrete supported task such as sending mail, launching an agent, inspecting state, or creating a workspace
- **THEN** the skill routes to the normal workflow for that task
- **AND THEN** it does not stop at generic help text solely because the request contains the word `help`

### Requirement: Help responses show available functionality
The help operation for each current system skill SHALL explain that skill's purpose in one short response.

The help operation SHALL show available functionality for that skill as a short list or table.

The help operation SHALL include common starting prompts or examples that a user can copy or adapt.

The help operation SHALL identify related Houmao skills, out-of-scope concerns, or routing boundaries when another current Houmao skill owns adjacent work.

The help operation SHALL keep the response concise enough to be useful inside an agent chat turn and SHALL NOT restate the entire `SKILL.md` file or all local reference pages.

#### Scenario: User sees what the skill can do
- **WHEN** a user asks for help on a current system skill
- **THEN** the response states the skill's purpose
- **AND THEN** it lists the main actions, operations, modes, patterns, or surfaces available through that skill
- **AND THEN** it includes at least one common starting prompt or example

#### Scenario: User sees when to use another skill
- **WHEN** a current system skill has adjacent work owned by another Houmao system skill
- **THEN** the help response identifies the related owning skill or boundary
- **AND THEN** the response does not imply that the current skill owns every Houmao management task

### Requirement: Operation-heavy skills list help beside operations
For current system skills that already expose named operations in their top-level `SKILL.md`, the skill SHALL list `help` as a named operation or equivalent meta operation beside those operations.

The help operation SHALL be checked before default operations such as `init`, `plan`, `status`, `start`, `send`, `launch`, `execute`, or other mutating or state-inspecting workflows.

#### Scenario: Loop skill help does not initialize a loop
- **WHEN** a user invokes an operation-heavy loop skill with explicit help intent and no `<loop-dir>`
- **THEN** the skill returns help text
- **AND THEN** it does not treat the request as `init`
- **AND THEN** it does not ask for `<loop-dir>`

### Requirement: Router-style skills handle help before page selection
For current system skills that select local action pages, transport pages, branch pages, patterns, references, or subskills, the top-level `SKILL.md` SHALL handle explicit help intent before selecting those pages.

The help response MAY summarize the routed pages, but SHALL NOT require the agent to open every routed page before answering ordinary help.

#### Scenario: Router help does not open action pages
- **WHEN** a user asks a router-style system skill for help
- **THEN** the top-level skill can answer from its help section
- **AND THEN** the skill does not need to choose or execute a specific action page first

### Requirement: Future current skills include the help operation
Any newly added current packaged Houmao system skill SHALL include the standard help operation before it is added to the packaged catalog.

Tests for the packaged catalog SHALL fail when a current catalog skill lacks a top-level `## Help` section or equivalent standard help marker.

#### Scenario: Catalog test catches missing help
- **WHEN** a maintainer adds a new current skill to `catalog.toml`
- **AND WHEN** that skill's top-level `SKILL.md` does not expose the standard help operation
- **THEN** the system-skill content tests fail
- **AND THEN** the maintainer must add help guidance before the skill can pass verification
