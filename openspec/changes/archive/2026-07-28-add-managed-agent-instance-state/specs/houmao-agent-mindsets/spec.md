## ADDED Requirements

### Requirement: Definitions declare named mindsets and skill bindings
The instance contract SHALL declare stable mindset names, ordered stable question ids, default question text, bounded record fields, and static skills that require each mindset.

#### Scenario: Skill references an unknown mindset
- **WHEN** a skill binding names no declared mindset
- **THEN** definition validation SHALL reject the instance contract

### Requirement: Mindsets remain low-authority data
Mindset declarations and records SHALL not grant tools, override instructions, satisfy workflow gates, or store credentials.

#### Scenario: Question attempts to grant authority
- **WHEN** a mindset question or record claims new tool authority
- **THEN** validation or mutation SHALL reject the authority-bearing content

### Requirement: Fresh launch initializes every declared mindset
Fresh launch SHALL create independent revision-one records for every declared mindset. V1 SHALL have no implicit active subset or undeclared initial override.

#### Scenario: Two peers launch
- **WHEN** two agents launch from the same instance contract
- **THEN** they SHALL receive independent records initialized from the same declarations

### Requirement: Required skills use an explicit snapshot protocol
A static skill bound to a mindset SHALL instruct the agent to obtain one verified-self immutable snapshot before task logic and to stop when lookup fails.

#### Scenario: Snapshot succeeds
- **WHEN** a bound skill follows the protocol
- **THEN** the command SHALL return one named record revision that remains stable for that invocation

#### Scenario: Required record is missing
- **WHEN** snapshot lookup cannot verify the named record for self
- **THEN** the skill protocol SHALL stop before task logic

### Requirement: Houmao validates the protocol without claiming invocation interception
Definition validation SHALL verify skill-to-mindset bindings and maintained snapshot instructions. Behavior tests SHALL cover manual and implicit skill invocation.

#### Scenario: Bound skill omits snapshot instructions
- **WHEN** a packaged skill declares a required mindset but omits the maintained snapshot phase
- **THEN** definition validation SHALL reject the skill binding

### Requirement: Admins revise one explicit named mindset
Mindset mutation SHALL require an explicit agent target, stable mindset name, and expected prior revision. Managed self SHALL remain read-only.

#### Scenario: Admin revises questions or bounded notes
- **WHEN** the target, name, content, and expected revision are valid
- **THEN** Houmao SHALL write the next revision and report a semantic diff

### Requirement: Mindset state follows preserved instance identity
A compatible preserved instance SHALL retain its mindset revisions. A fresh peer SHALL receive new revision-one records.

#### Scenario: Definition deployment changes
- **WHEN** a deployment proposes an incompatible instance-contract digest while an instance is live or preserved
- **THEN** the deployment update SHALL be blocked rather than resetting the record
