## ADDED Requirements

### Requirement: README introduces the three-skill public surface
The README System Skills subsection SHALL present `houmao-admin-welcome`, `houmao-admin-entrypoint`, and `houmao-agent-entrypoint` as the complete public Houmao system-skill surface.

It SHALL describe protected routines as nested implementation, SHALL avoid a long flat routine table, and SHALL link to the System Skills Overview for the audience matrix and command-family detail.

#### Scenario: Reader scans the README system-skills section
- **WHEN** a reader wants the shortest public-surface explanation
- **THEN** the README identifies the welcome, admin execution, and managed-agent execution roles
- **AND THEN** it does not present protected logical ids as peer installable skills

### Requirement: README quick start begins with the admin welcome
The skill-driven quick start SHALL install the admin pack into the user's CLI-agent home and SHALL make `$houmao-admin-welcome start-guided-tour` the recommended first-use prompt.

The README SHALL explain that welcome is read-only and hands concrete work to `$houmao-admin-entrypoint ...`. It SHALL NOT recommend `$houmao-touring` as a current invocation.

#### Scenario: First-time user follows quick start
- **WHEN** the user completes system-skill installation for an external home
- **THEN** the next prompt invokes `houmao-admin-welcome`
- **AND THEN** the README shows the admin entrypoint as the execution owner

### Requirement: README distinguishes external and managed pack defaults
The README SHALL state that explicit external-home installation defaults to the admin pack, while managed launch, rebuild, relaunch, and join default to the agent pack.

It SHALL state that the admin welcome and entrypoint install atomically, no default installs both actors, and `houmao-auto-system-prompt` remains separate managed bootstrap content.

#### Scenario: Reader compares two homes
- **WHEN** a reader compares a human-operated CLI-agent home with a Houmao-managed home
- **THEN** the README identifies the admin pack for the first and the agent pack for the second
- **AND THEN** it does not describe `core`, `extensions`, or `all` as current selectors

### Requirement: README examples use public entrypoint invocations
System-skill examples SHALL begin with one of the three public skill names.

The README MAY name important protected routines when explaining ownership, but SHALL label them as nested routes and SHALL not use a protected id as a top-level `$skill` prompt. Help examples SHALL remain read-only and role-appropriate.

#### Scenario: README mentions agent-definition behavior
- **WHEN** the README explains specialist or profile authoring
- **THEN** it starts the executable example from `$houmao-admin-entrypoint`
- **AND THEN** it may identify protected `houmao-agent-definition` as the nested owner

## REMOVED Requirements

### Requirement: README usage section introduces system skills
**Reason**: The old introduction describes a flat agent capability catalog.
**Migration**: Introduce the three public roles and protected routing model.

### Requirement: README skill catalog lists the unified email-comms skill
**Reason**: Email comms is protected rather than a public catalog row.
**Migration**: Mention it only as a nested route when mailbox context requires it.

### Requirement: README default-install paragraph matches current system_skills.py defaults
**Reason**: Old defaults resolve `core`, `extensions`, and `all`.
**Migration**: Document admin and agent pack defaults from the manifest.

### Requirement: README system-skills subsection lists the packaged mailbox-admin skill
**Reason**: Mailbox administration is protected shared content.
**Migration**: Keep detailed ownership in the overview route map.

### Requirement: README system-skills subsection lists the touring skill
**Reason**: `houmao-touring` is retired.
**Migration**: List `houmao-admin-welcome` as the first-use surface.

### Requirement: README system-skills table enumerates every catalog entry
**Reason**: The flat catalog is replaced by a small public surface and protected route map.
**Migration**: Keep only the three public roles in README and link to detailed docs.

### Requirement: README auto-install wording includes all pairwise variants when `core` includes them
**Reason**: Pairwise variants and the core set are retired.
**Migration**: Describe managed installation as the agent pack.

### Requirement: README system-skills narrative count tracks the catalog
**Reason**: One flat count no longer communicates public and protected records.
**Migration**: Avoid a hard-coded total or state counts by manifest record type.

### Requirement: README §4 introduces all loop skill options
**Reason**: Loop routines are nested and reached through entrypoints.
**Migration**: Introduce pro and lite as protected choices within public workflows.

### Requirement: README explains current core, extensions, and all set surface
**Reason**: Those sets are removed.
**Migration**: Explain admin and agent pack selection.

### Requirement: README system-skills table lists the workspace-manager utility skill
**Reason**: Workspace manager is a protected route.
**Migration**: Mention it only in workflow prose or detailed route docs.

### Requirement: README system-skill prose describes unified agent definition
**Reason**: Agent definition is no longer a public peer skill.
**Migration**: Describe it as the protected owner behind the admin entrypoint.

### Requirement: README system-skills narrative lists pro as the loop skill
**Reason**: Pro is protected and lite also remains maintained.
**Migration**: Present both through entrypoint-owned loop workflows.

### Requirement: README system-skill inventory lists lite alongside pro
**Reason**: README no longer carries a flat routine inventory.
**Migration**: Mention loop choices in workflow prose and link to the overview.

### Requirement: README mentions system-skill help
**Reason**: Help examples must now use public roles.
**Migration**: Show welcome or entrypoint help and link to detailed docs.

### Requirement: README mentions explicit read-only skill help
**Reason**: Direct help on every old peer skill is removed.
**Migration**: Use role-appropriate public help examples.

