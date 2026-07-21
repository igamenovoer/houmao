## ADDED Requirements

### Requirement: `houmao-touring` is retired in favor of the admin welcome
Houmao SHALL NOT package, install, or advertise `houmao-touring` as a current public or protected system skill.

The admin pack SHALL provide `houmao-admin-welcome` as the maintained first-use, reorientation, and subsystem-exploration surface. Migration guidance SHALL map saved touring invocations to the welcome without creating a compatibility directory.

#### Scenario: Current system-skill inventory is inspected
- **WHEN** a maintainer or operator inspects current public and protected system-skill records
- **THEN** `houmao-touring` is absent
- **AND THEN** `houmao-admin-welcome` is the public guided-tour owner

### Requirement: Maintained touring behavior moves to the welcome contract
The welcome SHALL retain state-aware orientation, compact steps, explanatory questions, subsystem exploration, next-step guidance, and the maintained Single Agent Full Run, Operator-Controlled Agent Team, and Pro Agent Loop paths.

It SHALL also expose Existing Project Reorientation as a curated path and SHALL hand all executable work to `houmao-admin-entrypoint` rather than delegating to former peer skills directly.

#### Scenario: Existing-project user requests the former tour
- **WHEN** a user asks for guided reorientation in an existing Houmao project
- **THEN** `houmao-admin-welcome` inspects supported read-only posture and presents the Existing Project Reorientation path
- **AND THEN** executable follow-up uses the admin entrypoint

## REMOVED Requirements

### Requirement: Houmao provides a packaged `houmao-touring` system skill
**Reason**: The standalone admin welcome replaces the old touring skill and belongs to an atomic admin pack.
**Migration**: Invoke `$houmao-admin-welcome`.

### Requirement: `houmao-touring` presents two coverage lanes
**Reason**: Coverage lanes now belong to the admin welcome's curated route map.
**Migration**: Use welcome path selection and subsystem exploration.

### Requirement: `houmao-touring` offers three fast path use cases
**Reason**: Fast paths move to the admin welcome and gain an existing-project path.
**Migration**: Use `houmao-admin-welcome show-options` or `choose-path`.

### Requirement: `houmao-touring` offers subsystem exploration
**Reason**: Subsystem exploration is now a welcome path.
**Migration**: Select Subsystem Exploration through the admin welcome.

### Requirement: `houmao-touring` uses compact step presentation
**Reason**: Presentation behavior is owned by the new welcome skill.
**Migration**: Preserve compact steps in `houmao-admin-welcome` content.

### Requirement: `houmao-touring` presents a three-stage first-user learning path
**Reason**: The new welcome uses curated paths and explicit entrypoint handoff rather than the old stage owner.
**Migration**: Map useful stage content into welcome orientation, selection, and handoff.

### Requirement: `houmao-touring` uses stage-aware next touring actions
**Reason**: `next-step` is a public welcome command.
**Migration**: Use `houmao-admin-welcome next-step`.

### Requirement: `houmao-touring` orients from current state and supports a non-linear guided tour
**Reason**: State-aware, non-linear orientation moves to the admin welcome.
**Migration**: Preserve the behavior under the welcome contract.

### Requirement: `houmao-touring` composes the existing Houmao skill families for execution
**Reason**: Peer skill families are replaced by the admin entrypoint and protected routes.
**Migration**: Hand executable work to `$houmao-admin-entrypoint ...`.

### Requirement: `houmao-touring` asks informative, example-driven user-input questions
**Reason**: Guided questions now belong to the welcome.
**Migration**: Preserve explanatory required/optional questions in `houmao-admin-welcome`.

### Requirement: `houmao-touring` distinguishes mailbox-root setup from mailbox-account ownership choices
**Reason**: The welcome teaches the distinction but execution belongs to admin-entrypoint routes.
**Migration**: Keep the concept in the relevant welcome path and pass choices during handoff.

### Requirement: `houmao-touring` advises foreground-first gateway posture during guided launch branches
**Reason**: Welcome guidance replaces touring guidance.
**Migration**: Preserve the maintained posture in the relevant path and route execution through the admin entrypoint.

### Requirement: `houmao-touring` presents a state-adaptive welcome message
**Reason**: The standalone admin welcome now owns this behavior directly.
**Migration**: Implement state-adaptive orientation in `houmao-admin-welcome`.

### Requirement: `houmao-touring` orient branch uses an explicit posture-to-branch routing matrix
**Reason**: The admin welcome owns the curated posture-to-path map.
**Migration**: Represent the current map in welcome commands and references.

### Requirement: `houmao-touring` offers a quickstart branch that detects available host CLI tools
**Reason**: Read-only host orientation moves to the admin welcome.
**Migration**: Keep supported detection in welcome orientation without executing setup.

### Requirement: `houmao-touring` advanced-usage branch teaches advanced orchestration rather than enumerating all features
**Reason**: Advanced orientation moves to curated welcome paths.
**Migration**: Teach orchestration at the welcome layer and execute through the admin entrypoint.

### Requirement: `houmao-touring` ships a self-contained concepts reference
**Reason**: Concepts are owned by the self-contained admin welcome.
**Migration**: Move maintained concepts into welcome-local references.

### Requirement: `houmao-touring` content is self-contained inside its packaged asset directory
**Reason**: The old asset directory is removed.
**Migration**: Keep welcome teaching content self-contained inside `houmao-admin-welcome`.

### Requirement: Touring system-input questions label required and optional values
**Reason**: Welcome questions use the actor-aware guided-input contract.
**Migration**: Apply `houmao-system-skill-input-questions` to the admin welcome.

### Requirement: Touring presents pro as the current loop path
**Reason**: The welcome presents maintained pro and lite choices through protected routes.
**Migration**: Use the Pro Agent Loop welcome path and entrypoint-qualified loop routes.

### Requirement: Touring presents lite and pro as current loop branches
**Reason**: The old touring owner is removed.
**Migration**: Explain maintained loop choices in the admin welcome and route execution through the admin entrypoint.

