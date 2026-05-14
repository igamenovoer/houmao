## ADDED Requirements

### Requirement: Houmao system-operation questions separate required and optional inputs
Houmao-owned system skills SHALL distinguish required and optional information whenever they ask the user for Houmao system-operation inputs.

Required inputs SHALL be values or decisions that block the requested Houmao operation when unresolved.

Optional inputs SHALL be modifiers, defaults, skip choices, or additional settings that the user may omit without blocking the operation.

When no optional input applies to the question, the skill SHALL state that no optional input is needed for that step.

This requirement SHALL apply to questions about Houmao platform, setup, routing, launch, mailbox, credential, workspace, loop-execution, and lifecycle inputs. It SHALL NOT apply to user-task or domain-intent questions unless the specific question asks for Houmao runtime behavior.

#### Scenario: Missing system target is labeled before asking
- **WHEN** a Houmao system skill cannot infer a required system target such as a project overlay, agent-definition directory, managed-agent selector, mailbox root, gateway endpoint, workspace path, or loop directory
- **THEN** the skill asks the user with a required-input section that names the missing target
- **AND THEN** the same question includes an optional-input section that lists applicable modifiers, defaults, skip choices, or states that no optional input is needed

#### Scenario: Optional modifiers do not hide blocking inputs
- **WHEN** a Houmao system skill asks for a credential, tool lane, launch profile, specialist name, lifecycle action, or validation target
- **THEN** the question separates blocking required values from optional modifiers such as launcher preference, output format, dry-run mode, background posture, filters, or skip choices
- **AND THEN** the skill does not present optional modifiers as if they were required to continue

#### Scenario: Task intent clarification keeps natural question style
- **WHEN** a Houmao system skill or generated loop-authoring flow asks about the user's objective, acceptance criteria, domain constraints, algorithm preferences, content scope, or loop business semantics
- **THEN** the question is not required to use required/optional system-input labels
- **AND THEN** the question may use the style most appropriate for clarifying the user task

### Requirement: Shared guidance covers direct and guided Houmao system questions
Houmao-owned system-skill guidance SHALL provide the required/optional question rule in shared or local reference material used by direct-operation and guided-operation skills.

Direct-operation guidance SHALL prefer concise Markdown lists or compact tables.

Guided-operation guidance SHALL preserve explanations, examples, recommended defaults, and skip paths while still identifying required and optional system inputs.

#### Scenario: Direct-operation missing input uses concise structure
- **WHEN** a direct-operation Houmao system skill asks the user for missing platform input
- **THEN** the question uses concise Markdown that visibly separates required and optional inputs
- **AND THEN** it asks only for information needed for the selected Houmao operation

#### Scenario: Guided tour keeps examples and labels
- **WHEN** `houmao-touring` asks a first-time-user system setup question
- **THEN** the question explains the concept and gives realistic examples
- **AND THEN** it labels required values separately from optional values or skip paths
