# managed-agent-auto-skills Specification

## Purpose
TBD - created by archiving change add-auto-system-prompt-skill. Update Purpose after archive.
## Requirements
### Requirement: Houmao packages managed auto skills separately from system skills
The system SHALL package Houmao-managed auto skills under `src/houmao/agents/assets/auto_skills`.

Auto skills SHALL be injected only by Houmao-managed launch, relaunch, rebuild, or join logic that owns a provider bootstrap requirement.

Auto skills SHALL NOT be part of the Houmao system-skill catalog, user-installable system-skill sets, project starter skill assets, or operator-selected project/private skill lists.

#### Scenario: Auto-skill asset root is separate
- **WHEN** a maintainer inspects Houmao packaged skill assets
- **THEN** auto skills are stored under `src/houmao/agents/assets/auto_skills`
- **AND THEN** installable Houmao system skills remain under `src/houmao/agents/assets/system_skills`
- **AND THEN** the packaged system-skill catalog does not list auto-skill names

#### Scenario: User system-skill commands do not install auto skills
- **WHEN** an operator runs a Houmao system-skill install, status, or uninstall command
- **THEN** the command manages catalog-known system skills
- **AND THEN** it does not expose `houmao-auto-system-prompt` as an installable, reportable, or removable system skill

### Requirement: Auto system prompt skill defines trigger metadata and workflow body
The system SHALL package an auto skill named `houmao-auto-system-prompt`.

The skill metadata SHALL describe only when the provider should read the skill: at chat-session start, after context compaction, after resume or relaunch, and before first substantive task work when the Houmao system prompt is not confirmed loaded.

The skill body SHALL contain a `## Workflow` section that tells the provider to run `houmao-mgr agents self system-prompt show --format text`, read the full returned prompt, treat it as the standing Houmao system prompt for the chat session, repeat the workflow after context compaction or resume, and fail closed if the command cannot load the prompt.

The skill body SHALL NOT tell the provider to read `houmao-memo.md`, inspect runtime manifests directly, or mutate memory as part of loading the system prompt.

#### Scenario: Skill metadata is trigger-only
- **WHEN** a maintainer opens `houmao-auto-system-prompt/SKILL.md`
- **THEN** the frontmatter `description` and `whenToUse` fields describe when to read the skill
- **AND THEN** those fields do not contain the full prompt-loading command workflow

#### Scenario: Skill workflow loads the prompt through Houmao CLI
- **WHEN** a provider reads the `houmao-auto-system-prompt` skill body
- **THEN** the `## Workflow` section instructs it to run `houmao-mgr agents self system-prompt show --format text`
- **AND THEN** the workflow instructs it to follow the returned prompt before performing user task work

#### Scenario: Skill fails closed when prompt loading fails
- **WHEN** the provider follows the `houmao-auto-system-prompt` workflow
- **AND WHEN** `houmao-mgr agents self system-prompt show --format text` fails or returns no usable prompt
- **THEN** the workflow instructs the provider to report that the Houmao system prompt could not be loaded
- **AND THEN** the workflow instructs the provider not to continue with substantive task work

### Requirement: Auto-skill names are reserved managed-launch names
The system SHALL reserve packaged auto-skill names for Houmao-managed projection.

Managed launch SHALL fail clearly if a project skill, profile-private skill, or selected user skill would project to the same visible name as a packaged auto skill.

#### Scenario: Project skill cannot shadow auto system prompt skill
- **WHEN** a managed launch requires `houmao-auto-system-prompt`
- **AND WHEN** the selected project or private skill set contains a skill named `houmao-auto-system-prompt`
- **THEN** brain construction fails with a diagnostic that names the reserved auto-skill collision
- **AND THEN** the provider process is not started with an ambiguous skill projection
