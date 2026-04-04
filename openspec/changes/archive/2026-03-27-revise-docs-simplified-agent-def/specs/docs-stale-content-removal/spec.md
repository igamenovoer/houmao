## ADDED Requirements

### Requirement: Legacy agents_brains.md deleted

The file `docs/reference/agents_brains.md` SHALL be deleted. It described the old recipe/blueprint/brains directory layout which was replaced by the simplified `tools/`/`roles/`/`skills/`/presets model documented in `docs/getting-started/agent-definitions.md`.

#### Scenario: agents_brains.md no longer exists

- **WHEN** listing files under `docs/reference/`
- **THEN** `agents_brains.md` does not exist

### Requirement: README agent-definition section uses new layout

The README's agent-definition directory section SHALL describe the current layout: `tools/<tool>/adapter.yaml`, `tools/<tool>/setups/<setup>/`, `tools/<tool>/auth/<auth>/`, `roles/<role>/system-prompt.md`, `roles/<role>/presets/<tool>/<setup>.yaml`, `skills/<skill>/SKILL.md`. The section SHALL NOT reference `brains/`, `brain-recipes/`, `cli-configs/`, `blueprints/`, `config_profile`, or `credential_profile`.

#### Scenario: README shows new directory tree

- **WHEN** reading the README agent-definition section
- **THEN** the directory tree shows `tools/`, `roles/`, `skills/` as top-level entries with the new sub-layout

#### Scenario: No old terminology in README

- **WHEN** searching `README.md` for `brains/brain-recipes`, `brains/cli-configs`, `brains/api-creds`, `brains/tool-adapters`, `config_profile`, `credential_profile`, or `blueprints/`
- **THEN** zero matches are found

### Requirement: LLM context files use new layout

The files `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and `.github/copilot-instructions.md` SHALL describe the current agent definition directory layout using `tools/`, `roles/`, `skills/`, `setup`, and `auth` terminology. They SHALL NOT reference `brains/brain-recipes/`, `brains/cli-configs/`, `brains/api-creds/`, `brains/tool-adapters/`, `config_profile`, `credential_profile`, or `blueprints/` as current concepts.

#### Scenario: No old paths in AGENTS.md

- **WHEN** searching `AGENTS.md` for `brains/brain-recipes`, `brains/cli-configs`, `brains/api-creds`, `brains/tool-adapters`
- **THEN** zero matches are found

#### Scenario: No old paths in CLAUDE.md

- **WHEN** searching `CLAUDE.md` for `brains/brain-recipes`, `brains/cli-configs`, `brains/api-creds`, `brains/tool-adapters`, `config_profile`, `credential_profile`
- **THEN** zero matches are found

#### Scenario: No old paths in GEMINI.md

- **WHEN** searching `GEMINI.md` for `brains/brain-recipes`, `brains/cli-configs`, `brains/api-creds`, `brains/tool-adapters`, `config_profile`, `credential_profile`
- **THEN** zero matches are found

#### Scenario: No old paths in copilot-instructions.md

- **WHEN** searching `.github/copilot-instructions.md` for `brains/brain-recipes`, `brains/cli-configs`, `brains/api-creds`, `brains/tool-adapters`, `config_profile`, `credential_profile`
- **THEN** zero matches are found

### Requirement: Surviving reference docs use new paths

The file `docs/reference/houmao_server_agent_api_live_suite.md` SHALL reference agent definition paths using the new layout (`tools/<tool>/setups/`, `tools/<tool>/auth/`, `roles/<role>/presets/`) and SHALL NOT reference `brains/brain-recipes/`, `brains/cli-configs/`, or `brains/api-creds/`.

#### Scenario: No old paths in live suite doc

- **WHEN** searching `docs/reference/houmao_server_agent_api_live_suite.md` for `brains/brain-recipes`, `brains/cli-configs`, `brains/api-creds`
- **THEN** zero matches are found

## MODIFIED Requirements

### Requirement: Internal cross-references updated after deletions

After deleting retired files, the migration section, and the three build-phase/legacy reference docs (`agents_brains.md`, `brain-builder.md`, `recipes-and-adapters.md`), all remaining docs SHALL be checked for broken internal links pointing to deleted files. Broken links SHALL be removed or redirected to the relevant replacement page in the getting-started section.

#### Scenario: No broken internal links to deleted files

- **WHEN** searching remaining docs for links to deleted filenames (e.g., `cao_interactive_demo.md`, `migration-guide.md`, `agents_brains.md`, `brain-builder.md`, `recipes-and-adapters.md`)
- **THEN** zero matches are found
