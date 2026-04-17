## ADDED Requirements

### Requirement: LLM Wiki utility skill uses the flat packaged asset layout
The packaged `houmao-utils-llm-wiki` system skill SHALL live directly under `src/houmao/agents/assets/system_skills/houmao-utils-llm-wiki/`.

The catalog `asset_subpath` for `houmao-utils-llm-wiki` SHALL equal `houmao-utils-llm-wiki` and SHALL NOT include a family namespace segment such as `utils/` or `llm-wiki/`.

#### Scenario: Maintainer inspects the packaged utility skill path
- **WHEN** a maintainer inspects the packaged system-skill asset root
- **THEN** `houmao-utils-llm-wiki` lives directly under that root
- **AND THEN** the catalog uses `houmao-utils-llm-wiki` as the asset subpath

### Requirement: LLM Wiki utility skill keeps flat visible projection paths
The shared installer SHALL project `houmao-utils-llm-wiki` into the same flat tool-native skill roots used by other Houmao-owned system skills.

Claude, Codex, and Copilot SHALL project the skill under `skills/houmao-utils-llm-wiki/`.

Gemini SHALL project the skill under `.gemini/skills/houmao-utils-llm-wiki/`.

#### Scenario: Codex installs the LLM Wiki utility skill
- **WHEN** Houmao installs `houmao-utils-llm-wiki` into a Codex home
- **THEN** the skill projects under `skills/houmao-utils-llm-wiki/`
- **AND THEN** Codex does not require a visible utility family subdirectory

#### Scenario: Gemini installs the LLM Wiki utility skill
- **WHEN** Houmao installs `houmao-utils-llm-wiki` into a Gemini home
- **THEN** the skill projects under `.gemini/skills/houmao-utils-llm-wiki/`
- **AND THEN** Gemini does not require a visible utility family subdirectory
