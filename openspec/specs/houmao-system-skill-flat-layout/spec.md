## Purpose
Define the flat packaged asset layout for the current Houmao-owned system-skill catalog.

## Requirements

### Requirement: Houmao-owned system skills use a flat packaged asset layout
The system SHALL package each current Houmao-owned system skill as one top-level directory directly under the maintained system-skill asset root.

For each current packaged skill, the catalog `asset_subpath` SHALL equal that skill directory name and SHALL NOT include a family namespace segment such as `mailbox/` or `project/`.

The packaged asset tree SHALL NOT require family-specific subdirectories to distinguish mailbox-oriented skills from project-oriented skills.

#### Scenario: Maintainer inspects the packaged skill asset root
- **WHEN** a maintainer inspects the maintained Houmao-owned system-skill asset root
- **THEN** each current skill lives under `src/houmao/agents/assets/system_skills/<houmao-skill>/`
- **AND THEN** the packaged catalog uses `<houmao-skill>` as that skill's `asset_subpath`
- **AND THEN** the maintained asset root does not rely on `mailbox/` or `project/` subdirectories for current skills

### Requirement: Grouping is expressed through reserved names and named sets rather than filesystem families
The system SHALL use reserved `houmao-` skill names and named skill sets to distinguish and group Houmao-owned system skills.

Logical groupings such as mailbox workflows and project-easy authoring SHALL be represented through catalog sets, descriptions, or docs rather than through visible installed path segments or packaged family directory names.

#### Scenario: Operator inspects current Houmao-owned skill inventory
- **WHEN** an operator lists the packaged Houmao-owned system skills and named sets
- **THEN** the current skills remain distinguishable through their reserved `houmao-` names
- **AND THEN** mailbox-oriented and project-oriented groupings remain expressible through named sets such as `mailbox-full` and `project-easy`
- **AND THEN** those groupings do not require `mailbox/` or `project/` filesystem namespaces

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
