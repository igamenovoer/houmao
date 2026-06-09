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

The skill metadata SHALL describe that the skill loads the effective Houmao system prompt and SHALL use explicit `MUST` language requiring the provider to invoke or read the skill before doing anything else: at chat start, after context compaction, after resume or relaunch, and before first substantive task work when the Houmao system prompt is not confirmed loaded. The startup-visible description SHALL keep the immediate `MUST invoke/read this skill before doing anything else` trigger inside the provider's model-visible skill-listing summary.

The skill body SHALL contain a `## Workflow` section that tells the provider to run `houmao-mgr agents self system-prompt show --format text`, read the full returned prompt, treat it as the standing Houmao system prompt for the chat session, repeat the workflow after context compaction or resume, and fail closed if the command cannot load the prompt.

The skill body SHALL stay focused on loading the effective Houmao system prompt through the self-service CLI workflow.

#### Scenario: Skill metadata gives startup-visible trigger without workflow
- **WHEN** a maintainer opens `houmao-auto-system-prompt/SKILL.md`
- **THEN** the frontmatter `description` and `whenToUse` fields state that the provider MUST invoke or read the skill before doing anything else at chat start
- **AND THEN** those fields prohibit planning, answering, inspecting files, or processing tasks before the skill has loaded
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
